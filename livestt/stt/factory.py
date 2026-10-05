"""Builds a SpeechRecognizer from settings. This is the single place that knows about
concrete engine classes — swapping/adding an STT backend means adding a branch here.
"""
from __future__ import annotations

from typing import Any

from livestt.stt.base import SpeechRecognizer


def create_engine(settings: dict[str, Any], api_key: str | None = None) -> SpeechRecognizer:
    provider = settings.get("stt_provider", "faster_whisper")

    if provider == "faster_whisper":
        from livestt.stt.faster_whisper_engine import FasterWhisperEngine

        return FasterWhisperEngine(
            model_size=settings.get("whisper_model", "small"),
            use_gpu=settings.get("use_gpu", True),
            compute_type=settings.get("compute_type", "auto"),
        )

    if provider == "cloud_openai":
        from livestt.stt.cloud_openai_engine import CloudOpenAIEngine

        return CloudOpenAIEngine(api_key=api_key or "")

    raise ValueError(f"Unknown STT provider: {provider!r}")
