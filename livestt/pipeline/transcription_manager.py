"""Orchestrates the full pipeline: AudioCapture -> StreamingVAD -> UtteranceBuffer ->
SpeechRecognizer -> TextProcessor -> Qt signals consumed by the UI.

Lives in its own QThread. STT inference (the slow part) runs on a QThreadPool so a model
decode never blocks incoming audio chunks or the UI. Partial decodes are throttled by time
and "latest wins" (a new partial request is skipped while one is already running, rather
than queued), so the pipeline never builds a backlog. Final decodes are never dropped.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from livestt.audio.buffer import UtteranceBuffer
from livestt.audio.capture import TARGET_SAMPLE_RATE, AudioCapture
from livestt.audio.device_manager import AudioDeviceManager
from livestt.audio.vad import StreamingVAD
from livestt.pipeline.text_processor import TextProcessor
from livestt.stt.base import SpeechRecognizer, TranscriptionResult

logger = logging.getLogger(__name__)


@dataclass
class PipelineStats:
    chunks_processed: int = 0
    vad_active: bool = False
    stt_state: str = "idle"  # idle | loading | partial | final | error
    avg_latency_ms: float = 0.0
    last_error: str = ""
    device_name: str = ""
    sample_rate: int = 0
    channels: int = 0
    audio_level: float = 0.0


class _TaskSignals(QObject):
    partial_done = Signal(object)  # TranscriptionResult
    final_done = Signal(object)  # TranscriptionResult
    latency_measured = Signal(float)  # milliseconds


class _TranscribeTask(QRunnable):
    def __init__(self, engine: SpeechRecognizer, audio: np.ndarray, sample_rate: int,
                 language_hint: str | None, is_final: bool, signals: _TaskSignals):
        super().__init__()
        self._engine = engine
        self._audio = audio
        self._sample_rate = sample_rate
        self._language_hint = language_hint
        self._is_final = is_final
        self._signals = signals

    def run(self) -> None:
        start = time.monotonic()
        try:
            result = self._engine.transcribe(self._audio, self._sample_rate, self._language_hint, self._is_final)
        except Exception as exc:
            logger.exception("Unhandled STT engine error")
            result = TranscriptionResult(text="", is_final=self._is_final, error=str(exc))
        elapsed_ms = (time.monotonic() - start) * 1000.0
        self._signals.latency_measured.emit(elapsed_ms)
        if self._is_final:
            self._signals.final_done.emit(result)
        else:
            self._signals.partial_done.emit(result)


class TranscriptionManager(QObject):
    partial_text_changed = Signal(str)  # current full text incl. in-flight partial
    final_text_changed = Signal(str)  # full committed text only
    state_changed = Signal(str)
    stats_changed = Signal(object)  # PipelineStats
    error_occurred = Signal(str)

    def __init__(self, device_manager: AudioDeviceManager):
        super().__init__()
        self._device_manager = device_manager
        self._capture: AudioCapture | None = None
        self._vad: StreamingVAD | None = None
        self._utterance = UtteranceBuffer(sample_rate=TARGET_SAMPLE_RATE)
        self._text_processor = TextProcessor()
        self._engine: SpeechRecognizer | None = None

        self._task_signals = _TaskSignals()
        self._task_signals.partial_done.connect(self._on_partial_done)
        self._task_signals.final_done.connect(self._on_final_done)
        self._task_signals.latency_measured.connect(self._on_latency_measured)
        self._pool = QThreadPool.globalInstance()

        self._partial_busy = False
        self._final_busy = False
        self._last_partial_ts = 0.0
        self._pending_language: str | None = None

        self._settings: dict = {}
        self._stats = PipelineStats()
        self._latencies: list[float] = []

    # -- configuration ------------------------------------------------------
    @Slot(object)
    def configure(self, settings: dict) -> None:
        """Rebuilds capture/VAD/engine from settings. Safe to call while stopped."""
        self._settings = settings
        was_running = self._capture is not None and self._capture.is_running()
        if was_running:
            self._stop_capture_only()

        self._vad = StreamingVAD(
            sample_rate=TARGET_SAMPLE_RATE,
            sensitivity=settings.get("vad_sensitivity", 0.5),
            min_silence_ms=settings.get("vad_min_silence_ms", 500),
            min_speech_ms=settings.get("vad_min_speech_ms", 200),
        )

        if self._capture is None:
            self._capture = AudioCapture(self._device_manager, chunk_ms=settings.get("chunk_ms", 500))
            self._capture.chunk_ready.connect(self._on_audio_chunk)
            self._capture.level_updated.connect(self._on_level_updated)
            self._capture.error_occurred.connect(self._on_capture_error)
            self._capture.started.connect(self._on_capture_started)
        self._capture.set_device(settings.get("audio_device_index"))

        lang = settings.get("language", "auto")
        self._pending_language = None if lang == "auto" else lang

        if self._engine is not None:
            self._engine.close()
        from livestt.stt.factory import create_engine

        api_key = settings.get("_api_key")  # injected by caller, never persisted to JSON
        self._engine = create_engine(settings, api_key=api_key)
        self._set_state("loading")
        try:
            self._engine.warmup()
            self._set_state("idle")
        except Exception as exc:
            logger.error("Engine warmup failed: %s", exc)
            self._set_state("error")
            self.error_occurred.emit(f"Не удалось инициализировать распознавание речи: {exc}")

        if was_running:
            self.start()

    # -- lifecycle ------------------------------------------------------
    @Slot()
    def start(self) -> None:
        if self._capture is None or self._engine is None:
            self.error_occurred.emit("Пайплайн не настроен (вызовите configure() перед start()).")
            return
        self._utterance.clear()
        self._text_processor.reset()
        if self._vad:
            self._vad.reset()
        self._capture.start()
        self._set_state("idle")

    @Slot()
    def stop(self) -> None:
        self._stop_capture_only()
        self._set_state("idle")

    def _stop_capture_only(self) -> None:
        if self._capture is not None:
            self._capture.stop()

    # -- audio chunk handling (runs on this QThread's event loop) -------
    @Slot(object)
    def _on_audio_chunk(self, chunk: np.ndarray) -> None:
        if self._vad is None:
            return
        self._stats.chunks_processed += 1
        event = self._vad.process(chunk)
        self._stats.vad_active = self._vad.in_speech

        if event.is_speech:
            self._utterance.append(chunk)
            self._maybe_request_partial()

        if event.speech_ended:
            self._request_final()

        self._emit_stats()

    @Slot(float)
    def _on_level_updated(self, level: float) -> None:
        self._stats.audio_level = level
        self._emit_stats()

    @Slot()
    def _on_capture_started(self) -> None:
        dev = self._device_manager.get_device_by_index(self._settings.get("audio_device_index")) \
            or self._device_manager.get_default_loopback_device()
        if dev:
            self._stats.device_name = dev.name
            self._stats.sample_rate = dev.sample_rate
            self._stats.channels = dev.channels
        self._emit_stats()

    @Slot(str)
    def _on_capture_error(self, message: str) -> None:
        self._stats.last_error = message
        self.error_occurred.emit(message)
        self._emit_stats()

    # -- partial / final decoding ------------------------------------------
    def _maybe_request_partial(self) -> None:
        if self._engine is None or not self._engine.supports_partial:
            return
        if self._partial_busy:
            return  # latest-wins: skip, next tick will pick up fresher audio
        interval_s = self._settings.get("partial_interval_ms", 900) / 1000.0
        now = time.monotonic()
        if now - self._last_partial_ts < interval_s:
            return
        if self._utterance.duration_seconds() < 0.3:
            return

        self._last_partial_ts = now
        self._partial_busy = True
        self._set_state("partial")
        audio = self._utterance.get().copy()
        task = _TranscribeTask(self._engine, audio, TARGET_SAMPLE_RATE, self._pending_language,
                                is_final=False, signals=self._task_signals)
        self._pool.start(task)

    def _request_final(self) -> None:
        if self._engine is None:
            self._utterance.clear()
            return
        audio = self._utterance.get().copy()
        self._utterance.clear()
        if audio.size < int(TARGET_SAMPLE_RATE * 0.05):
            # Negligible fragment (e.g. a single VAD frame right at startup). The real
            # speech/non-speech decision already happened in StreamingVAD per the user's
            # own vad_min_speech_ms setting -- we must not re-apply a stricter hardcoded
            # floor here, or legitimately short utterances ("да", "ok") would silently
            # never reach the STT engine.
            return

        self._final_busy = True
        self._set_state("final")
        task = _TranscribeTask(self._engine, audio, TARGET_SAMPLE_RATE, self._pending_language,
                                is_final=True, signals=self._task_signals)
        self._pool.start(task)

    @Slot(object)
    def _on_partial_done(self, result: TranscriptionResult) -> None:
        self._partial_busy = False
        if result.error:
            self._stats.last_error = result.error
            self._set_state("error")
            self._emit_stats()
            return
        self._set_state("idle" if not self._vad or not self._vad.in_speech else "listening")
        if result.text:
            self.partial_text_changed.emit(self._text_processor.full_text(result.text))

    @Slot(object)
    def _on_final_done(self, result: TranscriptionResult) -> None:
        self._final_busy = False
        if result.error:
            self._stats.last_error = result.error
            self._set_state("error")
            self._emit_stats()
            return
        self._set_state("idle")
        if result.text:
            committed = self._text_processor.commit_final(result.text)
            self.final_text_changed.emit(committed)
            self.partial_text_changed.emit(committed)

    @Slot(float)
    def _on_latency_measured(self, latency_ms: float) -> None:
        self._latencies.append(latency_ms)
        if len(self._latencies) > 50:
            self._latencies.pop(0)
        self._stats.avg_latency_ms = sum(self._latencies) / len(self._latencies)
        self._emit_stats()

    # -- misc -----------------------------------------------------------
    def _set_state(self, state: str) -> None:
        self._stats.stt_state = state
        self.state_changed.emit(state)

    def _emit_stats(self) -> None:
        self.stats_changed.emit(self._stats)

    @Slot()
    def clear_text(self) -> None:
        self._text_processor.reset()
        self.final_text_changed.emit("")
        self.partial_text_changed.emit("")

    def get_full_text(self) -> str:
        return self._text_processor.committed_text

    @Slot()
    def shutdown(self) -> None:
        self._stop_capture_only()
        if self._engine is not None:
            self._engine.close()
