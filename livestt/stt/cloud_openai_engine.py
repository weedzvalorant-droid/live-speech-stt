"""Cloud STT provider example: OpenAI's /audio/transcriptions REST endpoint.

Cloud round-trips (~0.3-1.5s) are too slow to use for partial (in-progress) text without
either incurring heavy cost or visible redundant requests, so this engine only answers on
is_final=True (supports_partial=False) — the pipeline skips calling it for partial ticks,
which also satisfies the "don't waste API calls during silence/partial speech" requirement.

This is one concrete implementation of SpeechRecognizer; a true low-latency streaming
cloud provider (e.g. Deepgram's websocket API) can be dropped in the same way without
touching the pipeline or UI.
"""
from __future__ import annotations

import io
import logging
import wave

import numpy as np
import requests

from livestt.stt.base import SpeechRecognizer, TranscriptionResult

logger = logging.getLogger(__name__)

_ENDPOINT = "https://api.openai.com/v1/audio/transcriptions"
_LANG_MAP = {"ru": "ru", "en": "en"}


class CloudOpenAIEngine(SpeechRecognizer):
    supports_partial = False

    def __init__(self, api_key: str, model: str = "whisper-1", timeout_s: float = 15.0):
        self._api_key = api_key
        self._model = model
        self._timeout_s = timeout_s

    def warmup(self) -> None:
        if not self._api_key:
            raise RuntimeError("Cloud STT selected but no API key is configured (see Settings).")

    def transcribe(
        self, audio: np.ndarray, sample_rate: int, language_hint: str | None, is_final: bool
    ) -> TranscriptionResult:
        if not is_final:
            return TranscriptionResult(text="", is_final=False)
        if audio.size < sample_rate * 0.2:
            return TranscriptionResult(text="", is_final=True)

        wav_bytes = self._to_wav_bytes(audio, sample_rate)
        data = {"model": self._model}
        lang = _LANG_MAP.get(language_hint or "")
        if lang:
            data["language"] = lang

        try:
            response = requests.post(
                _ENDPOINT,
                headers={"Authorization": f"Bearer {self._api_key}"},
                data=data,
                files={"file": ("audio.wav", wav_bytes, "audio/wav")},
                timeout=self._timeout_s,
            )
            response.raise_for_status()
            payload = response.json()
            return TranscriptionResult(text=payload.get("text", "").strip(), is_final=True)
        except Exception as exc:
            logger.error("Cloud transcription request failed: %s", exc)
            return TranscriptionResult(text="", is_final=True, error=str(exc))

    @staticmethod
    def _to_wav_bytes(audio: np.ndarray, sample_rate: int) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            int16 = np.clip(audio, -1.0, 1.0)
            wf.writeframes((int16 * 32767.0).astype(np.int16).tobytes())
        return buf.getvalue()

    def close(self) -> None:
        pass
