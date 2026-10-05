"""Test doubles for engines/devices that don't exist on a non-Windows CI/dev machine."""
from __future__ import annotations

import numpy as np

from livestt.stt.base import SpeechRecognizer, TranscriptionResult


class FakeEngine(SpeechRecognizer):
    """Deterministic stand-in for a real STT model: returns a canned sentence once the
    accumulated audio passes a size threshold, so tests can assert on the pipeline's
    sequencing/throttling logic without needing real model weights.
    """

    supports_partial = True

    def __init__(self, final_text: str = "привет это тест", partial_text: str = "привет"):
        self.final_text = final_text
        self.partial_text = partial_text
        self.warmup_called = False
        self.calls: list[bool] = []  # records is_final for each transcribe() call

    def warmup(self) -> None:
        self.warmup_called = True

    def transcribe(self, audio: np.ndarray, sample_rate: int, language_hint, is_final: bool) -> TranscriptionResult:
        self.calls.append(is_final)
        text = self.final_text if is_final else self.partial_text
        return TranscriptionResult(text=text, is_final=is_final, language="ru")

    def close(self) -> None:
        pass


class FailingEngine(SpeechRecognizer):
    supports_partial = True

    def warmup(self) -> None:
        pass

    def transcribe(self, audio, sample_rate, language_hint, is_final):
        return TranscriptionResult(text="", is_final=is_final, error="boom")

    def close(self) -> None:
        pass
