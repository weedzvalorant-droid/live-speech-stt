"""Tests the StreamingVAD trigger/hangover state machine using the REAL webrtcvad
backend (WebRtcVadBackend) fed with real synthetic PCM: silence vs. a loud broadband
"speech-like" signal. This exercises actual webrtcvad classification, not a mock.
"""
import numpy as np

from livestt.audio.vad import StreamingVAD, WebRtcVadBackend

SAMPLE_RATE = 16000


def _silence(ms: int) -> np.ndarray:
    return np.zeros(int(SAMPLE_RATE * ms / 1000), dtype=np.float32)


def _noisy_speech_like(ms: int, seed: int = 0) -> np.ndarray:
    # Broadband noise at speech-like amplitude reliably trips webrtcvad's energy+spectrum
    # heuristics, unlike a pure sine tone which it correctly rejects as non-speech.
    rng = np.random.default_rng(seed)
    n = int(SAMPLE_RATE * ms / 1000)
    return (rng.standard_normal(n) * 0.3).astype(np.float32)


def test_webrtcvad_backend_classifies_silence_as_non_speech():
    backend = WebRtcVadBackend(sensitivity=0.5)
    frame = _silence(20)
    assert backend.is_speech(frame, SAMPLE_RATE) is False


def test_streaming_vad_requires_min_speech_duration_before_triggering():
    vad = StreamingVAD(sample_rate=SAMPLE_RATE, sensitivity=0.9, min_silence_ms=300, min_speech_ms=200)
    # Feed less than min_speech_ms worth of noisy signal -> should not fire speech_started yet.
    event = vad.process(_noisy_speech_like(60))
    assert event.speech_started is False


def test_streaming_vad_fires_speech_started_after_min_speech_duration():
    vad = StreamingVAD(sample_rate=SAMPLE_RATE, sensitivity=0.9, min_silence_ms=300, min_speech_ms=200)
    started = False
    for _ in range(20):  # up to 400ms of noisy audio, well past the 200ms threshold
        event = vad.process(_noisy_speech_like(20))
        if event.speech_started:
            started = True
            break
    assert started is True
    assert vad.in_speech is True


def test_streaming_vad_fires_speech_ended_after_min_silence_duration():
    vad = StreamingVAD(sample_rate=SAMPLE_RATE, sensitivity=0.9, min_silence_ms=200, min_speech_ms=100)
    for _ in range(20):
        vad.process(_noisy_speech_like(20))
    assert vad.in_speech is True

    ended = False
    for _ in range(20):  # up to 400ms of silence, past the 200ms threshold
        event = vad.process(_silence(20))
        if event.speech_ended:
            ended = True
            break
    assert ended is True
    assert vad.in_speech is False


def test_streaming_vad_reset_clears_state():
    vad = StreamingVAD(sample_rate=SAMPLE_RATE, sensitivity=0.9, min_silence_ms=200, min_speech_ms=100)
    for _ in range(20):
        vad.process(_noisy_speech_like(20))
    assert vad.in_speech is True
    vad.reset()
    assert vad.in_speech is False
