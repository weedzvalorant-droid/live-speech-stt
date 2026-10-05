"""Minimal dependency-free audio helpers: downmix to mono and linear resampling.

Linear interpolation is not a brick-wall anti-aliasing filter, but for 44.1/48kHz -> 16kHz
speech downsampling it is cheap, allocation-light, and good enough for both VAD and Whisper
(most speech energy lives well under 8kHz). Swap this for scipy.signal.resample_poly later
if higher fidelity is ever needed.
"""
from __future__ import annotations

import numpy as np


def downmix_to_mono(samples: np.ndarray, channels: int) -> np.ndarray:
    if channels <= 1:
        return samples.astype(np.float32, copy=False)
    reshaped = samples.reshape(-1, channels)
    return reshaped.mean(axis=1).astype(np.float32)


def int16_bytes_to_float32(raw: bytes) -> np.ndarray:
    ints = np.frombuffer(raw, dtype=np.int16)
    return (ints.astype(np.float32)) / 32768.0


def float32_to_int16_bytes(samples: np.ndarray) -> bytes:
    clipped = np.clip(samples, -1.0, 1.0)
    return (clipped * 32767.0).astype(np.int16).tobytes()


def resample_linear(x: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr or x.size == 0:
        return x.astype(np.float32, copy=False)
    duration = x.shape[0] / float(orig_sr)
    target_len = max(1, int(round(duration * target_sr)))
    orig_idx = np.linspace(0.0, x.shape[0] - 1, num=x.shape[0])
    target_idx = np.linspace(0.0, x.shape[0] - 1, num=target_len)
    return np.interp(target_idx, orig_idx, x).astype(np.float32)


def rms_level(samples: np.ndarray) -> float:
    """Returns a 0..1-ish level (RMS, not true dBFS) suitable for a VU meter."""
    if samples.size == 0:
        return 0.0
    rms = float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))
    # Speech RMS rarely exceeds ~0.3 in normalized float32; scale so the meter is readable.
    return min(1.0, rms * 3.5)
