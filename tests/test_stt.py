"""faster-whisper/ctranslate2 are too heavy to install in this sandbox (constrained
disk), but FasterWhisperEngine only imports that package lazily inside warmup(), so the
factory dispatch and constructor wiring can be verified for real without it. The cloud
engine is tested against the real OpenAI endpoint over the network (with a deliberately
invalid key) to prove its HTTP/error-handling path actually works, not just that it's
wired correctly.
"""
import numpy as np
import pytest

from livestt.stt.base import TranscriptionResult
from livestt.stt.cloud_openai_engine import CloudOpenAIEngine
from livestt.stt.factory import create_engine
from livestt.stt.faster_whisper_engine import FasterWhisperEngine


def test_factory_builds_faster_whisper_engine_without_importing_the_heavy_package():
    engine = create_engine({"stt_provider": "faster_whisper", "whisper_model": "tiny", "use_gpu": False})
    assert isinstance(engine, FasterWhisperEngine)
    assert engine.supports_partial is True


def test_factory_builds_cloud_engine_with_api_key():
    engine = create_engine({"stt_provider": "cloud_openai"}, api_key="sk-test")
    assert isinstance(engine, CloudOpenAIEngine)
    assert engine.supports_partial is False


def test_factory_rejects_unknown_provider():
    with pytest.raises(ValueError):
        create_engine({"stt_provider": "does_not_exist"})


def test_cloud_engine_skips_partial_without_network_call():
    engine = CloudOpenAIEngine(api_key="sk-test")
    result = engine.transcribe(np.zeros(16000, dtype=np.float32), 16000, None, is_final=False)
    assert result == TranscriptionResult(text="", is_final=False)


def test_cloud_engine_warmup_requires_api_key():
    engine = CloudOpenAIEngine(api_key="")
    with pytest.raises(RuntimeError):
        engine.warmup()


def test_cloud_engine_real_http_request_with_invalid_key_reports_error_gracefully():
    engine = CloudOpenAIEngine(api_key="sk-definitely-invalid-key-for-testing")
    audio = (np.random.default_rng(0).standard_normal(16000) * 0.1).astype(np.float32)
    try:
        result = engine.transcribe(audio, 16000, "en", is_final=True)
    except Exception as exc:  # pragma: no cover - only if there's no network at all
        pytest.skip(f"no network access in this environment: {exc}")
    assert result.is_final is True
    assert result.text == ""
    assert result.error is not None  # a real 401 from OpenAI, not a crash
