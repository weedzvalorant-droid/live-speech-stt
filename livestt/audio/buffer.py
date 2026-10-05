"""In-memory accumulator for the audio belonging to the utterance currently being spoken."""
from __future__ import annotations

import numpy as np


class UtteranceBuffer:
    def __init__(self, sample_rate: int = 16000, max_seconds: float = 30.0):
        self.sample_rate = sample_rate
        self._max_samples = int(sample_rate * max_seconds)
        self._chunks: list[np.ndarray] = []
        self._total_samples = 0

    def append(self, samples: np.ndarray) -> None:
        if samples.size == 0:
            return
        self._chunks.append(samples)
        self._total_samples += samples.size
        # Hard safety cap so a VAD glitch (never detecting silence) cannot grow memory forever.
        while self._total_samples > self._max_samples and len(self._chunks) > 1:
            dropped = self._chunks.pop(0)
            self._total_samples -= dropped.size

    def get(self) -> np.ndarray:
        if not self._chunks:
            return np.zeros(0, dtype=np.float32)
        if len(self._chunks) == 1:
            return self._chunks[0]
        merged = np.concatenate(self._chunks)
        self._chunks = [merged]
        return merged

    def clear(self) -> None:
        self._chunks = []
        self._total_samples = 0

    def duration_seconds(self) -> float:
        return self._total_samples / float(self.sample_rate)

    def __len__(self) -> int:
        return self._total_samples
