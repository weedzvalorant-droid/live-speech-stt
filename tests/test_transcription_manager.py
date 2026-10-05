"""Integration test of the real orchestration logic in TranscriptionManager: real
StreamingVAD (real webrtcvad), real QThreadPool worker execution, real Qt signal/slot
delivery across threads -- only the STT model itself is replaced with a deterministic
FakeEngine (no GPU/model weights available in this environment). This proves the
speech-detection -> partial-throttling -> finalize -> commit pipeline actually works,
not just that the pieces compile.
"""
from __future__ import annotations

import time

import numpy as np
import pytest
from PySide6.QtCore import QCoreApplication

from livestt.audio.device_manager import AudioDeviceManager
from livestt.audio.vad import StreamingVAD
from livestt.pipeline.transcription_manager import TranscriptionManager

from tests.fakes import FailingEngine, FakeEngine

SAMPLE_RATE = 16000


@pytest.fixture(scope="module")
def qapp():
    app = QCoreApplication.instance() or QCoreApplication([])
    yield app


def _noisy_speech_like(ms: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(SAMPLE_RATE * ms / 1000)
    return (rng.standard_normal(n) * 0.3).astype(np.float32)


def _silence(ms: int, seed: int = 1000) -> np.ndarray:
    # Real background "silence" always has a tiny noise floor; feeding exact digital
    # zero makes webrtcvad's internal adaptive energy threshold behave inconsistently
    # (it's tuned for real audio, not a mathematically perfect zero signal).
    rng = np.random.default_rng(seed)
    n = int(SAMPLE_RATE * ms / 1000)
    return (rng.standard_normal(n) * 0.001).astype(np.float32)


def _make_manager(engine, partial_interval_ms=0):
    manager = TranscriptionManager(AudioDeviceManager())
    manager._vad = StreamingVAD(sample_rate=SAMPLE_RATE, sensitivity=0.9, min_silence_ms=200, min_speech_ms=100)
    manager._engine = engine
    manager._settings = {"partial_interval_ms": partial_interval_ms}
    manager._pending_language = None
    return manager


def _pump_until(app, predicate, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_speech_then_silence_produces_final_committed_text(qapp):
    engine = FakeEngine(final_text="привет это тест")
    manager = _make_manager(engine)

    finals = []
    manager.final_text_changed.connect(finals.append)

    for _ in range(15):  # ~300ms of noisy "speech"
        manager._on_audio_chunk(_noisy_speech_like(20))
    for i in range(40):  # ~800ms of silence -> should cross min_silence_ms and finalize
        manager._on_audio_chunk(_silence(20, seed=1000 + i))

    assert _pump_until(qapp, lambda: len(finals) > 0 and finals[-1] != "")
    assert finals[-1] == "Привет это тест."
    assert True in engine.calls  # a final (is_final=True) call really happened


def test_partial_text_is_throttled_and_never_duplicated(qapp):
    engine = FakeEngine(partial_text="привет всем")
    manager = _make_manager(engine, partial_interval_ms=10_000)  # effectively once per utterance

    partials = []
    manager.partial_text_changed.connect(partials.append)

    for _ in range(15):
        manager._on_audio_chunk(_noisy_speech_like(20))

    assert _pump_until(qapp, lambda: len(partials) > 0)
    # Because partial_interval_ms is huge, feeding more speech chunks must NOT trigger
    # a second concurrent partial request while one throttle window is open.
    partial_count_after_first = len(partials)
    for _ in range(5):
        manager._on_audio_chunk(_noisy_speech_like(20))
    qapp.processEvents()
    assert len(partials) == partial_count_after_first
    # no entry should ever contain the text duplicated (e.g. "привет всем привет всем")
    for text in partials:
        assert text.count("привет всем") <= 1


def test_short_noise_burst_is_dropped_without_calling_engine(qapp):
    """A blip shorter than the VAD's min_speech_ms must never reach the STT engine --
    this is the 'don't waste CPU/GPU on nothing' requirement."""
    engine = FakeEngine()
    manager = _make_manager(engine)

    manager._on_audio_chunk(_noisy_speech_like(20))  # 20ms, below min_speech_ms=100
    manager._on_audio_chunk(_silence(20))
    qapp.processEvents()

    assert engine.calls == []


def test_engine_error_sets_error_state_without_crashing(qapp):
    manager = _make_manager(FailingEngine())
    states = []
    manager.state_changed.connect(states.append)

    for _ in range(15):
        manager._on_audio_chunk(_noisy_speech_like(20))
    for i in range(40):
        manager._on_audio_chunk(_silence(20, seed=1000 + i))

    assert _pump_until(qapp, lambda: "error" in states)


def test_clear_text_resets_committed_text(qapp):
    engine = FakeEngine(final_text="какой-то текст")
    manager = _make_manager(engine)
    finals = []
    manager.final_text_changed.connect(finals.append)

    for _ in range(15):
        manager._on_audio_chunk(_noisy_speech_like(20))
    for i in range(40):
        manager._on_audio_chunk(_silence(20, seed=1000 + i))
    assert _pump_until(qapp, lambda: len(finals) > 0 and finals[-1])

    manager.clear_text()
    assert manager.get_full_text() == ""
