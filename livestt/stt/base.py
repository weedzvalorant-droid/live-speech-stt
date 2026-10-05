"""Speech-to-text engine interface. Any engine (local or cloud) implements this, so
swapping the STT backend never requires changing the pipeline or UI code.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class TranscriptionResult:
    text: str
    is_final: bool
    language: str | None = None
    error: str | None = None


class SpeechRecognizer(ABC):
    #: Whether this engine is cheap/fast enough to be called repeatedly for partial
    #: (in-progress) transcriptions. Cloud engines typically set this False to avoid
    #: hammering a paid API every ~900ms; they still produce a result on is_final=True.
    supports_partial: bool = True

    @abstractmethod
    def warmup(self) -> None:
        """Load model weights / open connections. Called once off the UI thread."""

    @abstractmethod
    def transcribe(
        self, audio: np.ndarray, sample_rate: int, language_hint: str | None, is_final: bool
    ) -> TranscriptionResult:
        """audio is mono float32 in [-1, 1]. language_hint is 'ru'/'en'/None (auto-detect)."""

    def reset(self) -> None:
        """Called when an utterance boundary is crossed; override if the engine keeps state."""

    def close(self) -> None:
        """Release model/resources."""
