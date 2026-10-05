"""Real-time system-audio capture, running its own reader thread so it never blocks Qt's
event loop. Emits Qt signals (mono float32 @16kHz chunks, VU level, errors, device-lost)
that are safe to connect across threads with Qt's default auto-queued connections.

Windows: WASAPI loopback via pyaudiowpatch (true system-audio capture).
macOS/other: plain PyAudio reading from a BlackHole (or similar) virtual input device
that the user has routed system audio into -- see README for the one-time setup.
"""
from __future__ import annotations

import logging
import threading
import time

import numpy as np
from PySide6.QtCore import QObject, Signal

from livestt.audio.device_manager import (
    IS_WINDOWS,
    AUDIO_BACKEND_AVAILABLE,
    AudioDevice,
    AudioDeviceManager,
)
from livestt.audio.resample import downmix_to_mono, int16_bytes_to_float32, resample_linear, rms_level

logger = logging.getLogger(__name__)

TARGET_SAMPLE_RATE = 16000
_RECONNECT_DELAY_S = 2.0


class AudioCapture(QObject):
    chunk_ready = Signal(object)  # np.ndarray float32 mono @ TARGET_SAMPLE_RATE
    level_updated = Signal(float)  # 0..1
    error_occurred = Signal(str)
    device_lost = Signal(str)
    started = Signal()
    stopped = Signal()

    def __init__(self, device_manager: AudioDeviceManager, chunk_ms: int = 500):
        super().__init__()
        self._device_manager = device_manager
        self._chunk_ms = chunk_ms
        self._device_index: int | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._running = False

    def set_device(self, device_index: int | None) -> None:
        self._device_index = device_index

    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return
        if not AUDIO_BACKEND_AVAILABLE:
            if IS_WINDOWS:
                self.error_occurred.emit(
                    "Захват звука недоступен: модуль pyaudiowpatch не установлен."
                )
            else:
                self.error_occurred.emit(
                    "Захват звука недоступен: модуль PyAudio не установлен "
                    "(pip install pyaudio; на macOS может понадобиться 'brew install portaudio')."
                )
            return
        self._stop_event.clear()
        self._running = True
        self._thread = threading.Thread(target=self._run, name="AudioCaptureThread", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        self.stopped.emit()

    # -- worker thread ----------------------------------------------------
    @staticmethod
    def _enumerate_devices(pyaudio_module, pa) -> list[AudioDevice]:
        """Enumerates candidate devices using the SAME PyAudio instance that will open the
        stream. PortAudio device indices are only valid within the instance that produced
        them -- resolving a device via one PyAudio() object and opening it via another can
        yield a stale/mismatched index and fail with 'Invalid device' (-9996), even though
        the device itself is fine.
        """
        if IS_WINDOWS:
            return AudioCapture._enumerate_windows_loopback(pyaudio_module, pa)
        return AudioCapture._enumerate_generic_inputs(pa)

    @staticmethod
    def _enumerate_windows_loopback(pyaudio_module, pa) -> list[AudioDevice]:
        default_name = None
        try:
            wasapi_info = pa.get_host_api_info_by_type(pyaudio_module.paWASAPI)
            default_out = pa.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            default_name = default_out["name"]
        except Exception as exc:
            logger.debug("Could not resolve default WASAPI output device: %s", exc)

        devices: list[AudioDevice] = []
        for info in pa.get_loopback_device_info_generator():
            devices.append(
                AudioDevice(
                    index=info["index"],
                    name=info["name"],
                    sample_rate=int(info["defaultSampleRate"]),
                    channels=int(info["maxInputChannels"]),
                    is_default=bool(default_name) and default_name in info["name"],
                )
            )
        return devices

    @staticmethod
    def _enumerate_generic_inputs(pa) -> list[AudioDevice]:
        devices: list[AudioDevice] = []
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if info.get("maxInputChannels", 0) <= 0:
                continue
            name = info.get("name", f"Device {i}")
            devices.append(
                AudioDevice(
                    index=i,
                    name=name,
                    sample_rate=int(info.get("defaultSampleRate", 48000)),
                    channels=int(info["maxInputChannels"]),
                    is_default="blackhole" in name.lower(),
                )
            )
        return devices

    def _resolve_device_name(self) -> str | None:
        """Looked up once per connection attempt via the long-lived device_manager
        instance, purely to get a NAME to match against -- never used for its index."""
        if self._device_index is None:
            return None
        dev = self._device_manager.get_device_by_index(self._device_index)
        if dev is None:
            logger.warning("Configured device index %s not found; falling back to default", self._device_index)
            return None
        return dev.name

    def _run(self) -> None:
        if IS_WINDOWS:
            import pyaudiowpatch as pyaudio
        else:
            import pyaudio

        target_name = self._resolve_device_name()

        while not self._stop_event.is_set():
            pa = None
            stream = None
            try:
                pa = pyaudio.PyAudio()
                candidates = self._enumerate_devices(pyaudio, pa)
                device = None
                if target_name:
                    device = next((d for d in candidates if d.name == target_name), None)
                    if device is None:
                        logger.warning("Device %r not present this time; using default instead", target_name)
                if device is None:
                    device = next((d for d in candidates if d.is_default), None) or (candidates[0] if candidates else None)
                if device is None:
                    hint = "" if IS_WINDOWS else " Установи BlackHole и выбери его в настройках."
                    self.error_occurred.emit(f"Не найдено ни одного устройства для захвата звука.{hint}")
                    time.sleep(_RECONNECT_DELAY_S)
                    continue

                frames_per_buffer = max(1, int(device.sample_rate * self._chunk_ms / 1000))
                stream = pa.open(
                    format=pyaudio.paInt16,
                    channels=device.channels,
                    rate=device.sample_rate,
                    frames_per_buffer=frames_per_buffer,
                    input=True,
                    input_device_index=device.index,
                )
                self.started.emit()
                logger.info("Audio capture started: %s @ %dHz/%dch", device.name, device.sample_rate, device.channels)

                while not self._stop_event.is_set():
                    raw = stream.read(frames_per_buffer, exception_on_overflow=False)
                    samples = int16_bytes_to_float32(raw)
                    mono = downmix_to_mono(samples, device.channels)
                    self.level_updated.emit(rms_level(mono))
                    resampled = resample_linear(mono, device.sample_rate, TARGET_SAMPLE_RATE)
                    self.chunk_ready.emit(resampled)

            except Exception as exc:
                logger.error("Audio capture error: %s", exc)
                self.device_lost.emit(str(exc))
                self.error_occurred.emit(f"Ошибка аудиоустройства: {exc}. Повторная попытка подключения...")
                time.sleep(_RECONNECT_DELAY_S)
            finally:
                try:
                    if stream is not None:
                        stream.stop_stream()
                        stream.close()
                except Exception:
                    pass
                try:
                    if pa is not None:
                        pa.terminate()
                except Exception:
                    pass
