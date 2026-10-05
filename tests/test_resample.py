import numpy as np

from livestt.audio.resample import (
    downmix_to_mono,
    float32_to_int16_bytes,
    int16_bytes_to_float32,
    resample_linear,
    rms_level,
)


def test_downmix_stereo_to_mono_averages_channels():
    stereo = np.array([1.0, -1.0, 0.5, 0.5], dtype=np.float32)  # 2 frames, L/R
    mono = downmix_to_mono(stereo, channels=2)
    assert mono.shape[0] == 2
    assert mono[0] == 0.0
    assert mono[1] == 0.5


def test_downmix_mono_passthrough():
    mono_in = np.array([0.1, 0.2], dtype=np.float32)
    assert np.array_equal(downmix_to_mono(mono_in, channels=1), mono_in)


def test_int16_roundtrip():
    samples = np.array([0.5, -0.5, 0.0], dtype=np.float32)
    raw = float32_to_int16_bytes(samples)
    back = int16_bytes_to_float32(raw)
    assert np.allclose(back, samples, atol=1e-3)


def test_resample_same_rate_is_noop():
    x = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    assert np.array_equal(resample_linear(x, 16000, 16000), x)


def test_resample_downsamples_48k_to_16k_length():
    x = np.zeros(48000, dtype=np.float32)  # 1 second @ 48kHz
    y = resample_linear(x, 48000, 16000)
    assert y.shape[0] == 16000  # exactly 1 second @ 16kHz


def test_resample_empty_array():
    x = np.zeros(0, dtype=np.float32)
    assert resample_linear(x, 48000, 16000).shape[0] == 0


def test_rms_level_silence_is_zero():
    assert rms_level(np.zeros(100, dtype=np.float32)) == 0.0


def test_rms_level_increases_with_amplitude():
    quiet = rms_level(np.full(100, 0.05, dtype=np.float32))
    loud = rms_level(np.full(100, 0.3, dtype=np.float32))
    assert loud > quiet
    assert 0.0 <= quiet <= 1.0
    assert 0.0 <= loud <= 1.0
