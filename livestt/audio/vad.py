"""Voice Activity Detection.

Default backend is WebRTC VAD: tiny, pure-C, no GPU/torch dependency, and good enough to
tell speech from silence/noise on 16kHz mono frames. It's wrapped behind VadBackend so a
more accurate backend (e.g. Silero VAD) can be swapped in later without touching the
streaming trigger/hangover logic below.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from livestt.audio.resample import float32_to_int16_bytes

logger = logging.getLogger(__name__)

try:
    import webrtcvad

    WEBRTCVAD_AVAILABLE = True
except Exception:  # pragma: no cover
    webrtcvad = None
    WEBRTCVAD_AVAILABLE = False


class VadBackend(ABC):
    """Classifies a single fixed-size frame as speech/non-speech."""

    @abstractmethod
    def is_speech(self, frame: np.ndarray, sample_rate: int) -> bool: ...

    @property
    @abstractmethod
    def frame_ms(self) -> int: ...


class WebRtcVadBackend(VadBackend):
    _VALID_RATES = (8000, 16000, 32000, 48000)
    _FRAME_MS = 20

    def __init__(self, sensitivity: float = 0.5):
        if not WEBRTCVAD_AVAILABLE:
            raise RuntimeError("webrtcvad package is not installed")
        # sensitivity 0..1 (higher = more sensitive) -> webrtcvad mode 3..0 (0 = least aggressive filtering)
        mode = int(round((1.0 - max(0.0, min(1.0, sensitivity))) * 3))
        self._vad = webrtcvad.Vad(mode)

    @property
    def frame_ms(self) -> int:
        return self._FRAME_MS

    def is_speech(self, frame: np.ndarray, sample_rate: int) -> bool:
        if sample_rate not in self._VALID_RATES:
            raise ValueError(f"webrtcvad only supports {self._VALID_RATES}, got {sample_rate}")
        return self._vad.is_speech(float32_to_int16_bytes(frame), sample_rate)


@dataclass
class VadEvent:
    is_speech: bool
    speech_started: bool = False
    speech_ended: bool = False


class StreamingVAD:
    """Turns a stream of raw audio chunks into speech-start/speech-end events with hangover
    smoothing, so single noisy frames don't chop words or fire spurious utterances.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        sensitivity: float = 0.5,
        min_silence_ms: int = 500,
        min_speech_ms: int = 200,
        backend: VadBackend | None = None,
    ):
        self.sample_rate = sample_rate
        self._backend = backend or WebRtcVadBackend(sensitivity)
        self._frame_samples = int(sample_rate * self._backend.frame_ms / 1000)
        self._min_silence_ms = min_silence_ms
        self._min_speech_ms = min_speech_ms

        self._in_speech = False
        self._speech_run_ms = 0
        self._silence_run_ms = 0
        self._leftover = np.zeros(0, dtype=np.float32)
        self._dither_rng = np.random.default_rng(1234)

    def reset(self) -> None:
        self._in_speech = False
        self._speech_run_ms = 0
        self._silence_run_ms = 0
        self._leftover = np.zeros(0, dtype=np.float32)

    def process(self, chunk: np.ndarray) -> VadEvent:
        """Feed an arbitrary-length chunk; internally sliced into fixed VAD frames.

        Returns the event for the chunk as a whole: is_speech is the latest frame's
        classification OR'd across frames (true if ANY frame in the chunk was speech),
        while speech_started/speech_ended reflect state transitions during this call.
        """
        buf = np.concatenate([self._leftover, chunk]) if self._leftover.size else chunk
        n_frames = buf.size // self._frame_samples
        usable = n_frames * self._frame_samples
        self._leftover = buf[usable:].copy()

        any_speech = False
        started = False
        ended = False

        for i in range(n_frames):
            frame = buf[i * self._frame_samples : (i + 1) * self._frame_samples]
            try:
                # Tiny inaudible dither on the classification-only copy (the real audio
                # sent to the STT engine, `chunk`, is never touched). This guards against
                # edge cases some VAD backends have on mathematically perfect digital
                # silence. Note: measured separately, webrtcvad itself has ~300-400ms of
                # built-in hysteresis after loud audio before it reports non-speech again,
                # regardless of dithering -- that lag adds to vad_min_silence_ms and is a
                # real, expected contributor to end-of-utterance latency (see README).
                dithered = frame + self._dither_rng.uniform(-1e-4, 1e-4, size=frame.shape).astype(np.float32)
                speech = self._backend.is_speech(dithered, self.sample_rate)
            except Exception as exc:
                logger.debug("VAD frame classification failed: %s", exc)
                speech = False

            frame_ms = self._backend.frame_ms
            if speech:
                any_speech = True
                self._speech_run_ms += frame_ms
                self._silence_run_ms = 0
                if not self._in_speech and self._speech_run_ms >= self._min_speech_ms:
                    self._in_speech = True
                    started = True
            else:
                self._silence_run_ms += frame_ms
                self._speech_run_ms = 0
                if self._in_speech and self._silence_run_ms >= self._min_silence_ms:
                    self._in_speech = False
                    ended = True

        return VadEvent(is_speech=any_speech, speech_started=started, speech_ended=ended)

    @property
    def in_speech(self) -> bool:
        return self._in_speech
