"""Local STT engine backed by faster-whisper (CTranslate2). Supports CPU (int8) and
GPU/CUDA (float16), Russian/English/auto language detection, and comes with
punctuation built into the Whisper decoder output.
"""
from __future__ import annotations

import logging
import threading

import numpy as np

from livestt.stt.base import SpeechRecognizer, TranscriptionResult

logger = logging.getLogger(__name__)


def _resolve_device_and_compute_type(use_gpu: bool, compute_type: str) -> tuple[str, str]:
    device = "cpu"
    if use_gpu:
        try:
            import ctranslate2

            if ctranslate2.get_cuda_device_count() > 0:
                device = "cuda"
        except Exception as exc:
            logger.warning("GPU requested but unavailable, falling back to CPU: %s", exc)

    if compute_type != "auto":
        return device, compute_type
    return device, ("float16" if device == "cuda" else "int8")


class FasterWhisperEngine(SpeechRecognizer):
    supports_partial = True

    def __init__(
        self,
        model_size: str = "small",
        use_gpu: bool = True,
        compute_type: str = "auto",
        beam_size: int = 1,
    ):
        self._model_size = model_size
        self._use_gpu = use_gpu
        self._compute_type_setting = compute_type
        self._beam_size = beam_size
        self._model = None
        self._lock = threading.Lock()

    def warmup(self) -> None:
        from faster_whisper import WhisperModel

        device, compute_type = _resolve_device_and_compute_type(self._use_gpu, self._compute_type_setting)
        logger.info("Loading faster-whisper model=%s device=%s compute_type=%s", self._model_size, device, compute_type)
        self._model = WhisperModel(self._model_size, device=device, compute_type=compute_type)
        # Dummy pass to force CUDA/kernel initialization off the hot path.
        self._model.transcribe(np.zeros(16000, dtype=np.float32), language="en", beam_size=1)
        logger.info("faster-whisper model ready")

    def transcribe(
        self, audio: np.ndarray, sample_rate: int, language_hint: str | None, is_final: bool
    ) -> TranscriptionResult:
        if self._model is None:
            return TranscriptionResult(text="", is_final=is_final, error="model not loaded")
        if audio.size < sample_rate * 0.2:  # skip clips shorter than 200ms, not worth decoding
            return TranscriptionResult(text="", is_final=is_final)

        with self._lock:
            try:
                segments, info = self._model.transcribe(
                    audio,
                    language=language_hint,
                    beam_size=self._beam_size,
                    vad_filter=False,  # our own StreamingVAD already gates what reaches here
                    condition_on_previous_text=False,
                    without_timestamps=True,
                )
                text = "".join(seg.text for seg in segments).strip()
                detected_lang = getattr(info, "language", None)
                return TranscriptionResult(text=text, is_final=is_final, language=detected_lang)
            except Exception as exc:
                logger.error("faster-whisper transcription failed: %s", exc)
                return TranscriptionResult(text="", is_final=is_final, error=str(exc))

    def close(self) -> None:
        self._model = None
