"""Enumerates audio capture devices for "what you hear" recording.

Two backends, chosen automatically by OS:
  - Windows: pyaudiowpatch's WASAPI loopback devices (true system-audio capture, no
    extra driver needed).
  - macOS (and other non-Windows platforms): plain PyAudio, listing normal input
    devices. macOS has no built-in loopback API, so the user installs a free virtual
    audio driver (BlackHole) and routes system output to it via a Multi-Output Device;
    BlackHole then just shows up here as a regular input device. Any device whose name
    contains "BlackHole" is flagged as the recommended pick.

Either way the import is guarded so the rest of the codebase stays importable/testable
even where neither backend is installed.
"""
from __future__ import annotations

import logging
import sys
from dataclasses import dataclass

logger = logging.getLogger(__name__)

IS_WINDOWS = sys.platform == "win32"
_import_error: Exception | None = None

if IS_WINDOWS:
    try:
        import pyaudiowpatch as pyaudio

        AUDIO_BACKEND_AVAILABLE = True
    except Exception as exc:  # pragma: no cover - expected off Windows
        pyaudio = None
        AUDIO_BACKEND_AVAILABLE = False
        _import_error = exc
else:
    try:
        import pyaudio

        AUDIO_BACKEND_AVAILABLE = True
    except Exception as exc:  # pragma: no cover - expected when PyAudio isn't installed
        pyaudio = None
        AUDIO_BACKEND_AVAILABLE = False
        _import_error = exc

# Kept for backwards compatibility with code/tests written against the old name.
WASAPI_LOOPBACK_AVAILABLE = AUDIO_BACKEND_AVAILABLE


@dataclass(frozen=True)
class AudioDevice:
    index: int
    name: str
    sample_rate: int
    channels: int
    is_default: bool = False

    def __str__(self) -> str:  # nice for QComboBox display
        suffix = " (рекомендуется)" if self.is_default else ""
        return f"{self.name}{suffix}"


class AudioDeviceError(RuntimeError):
    pass


class AudioDeviceManager:
    """Lists candidate "system audio" capture devices for the current OS."""

    def __init__(self):
        self._pa = None
        if AUDIO_BACKEND_AVAILABLE:
            self._pa = pyaudio.PyAudio()
        else:
            logger.warning(
                "No audio capture backend available (%s). On Windows this needs "
                "pyaudiowpatch; on macOS it needs PyAudio + BlackHole.",
                _import_error if _import_error is not None else "unknown reason",
            )

    def is_available(self) -> bool:
        return self._pa is not None

    def list_loopback_devices(self) -> list[AudioDevice]:
        """Returns candidate devices: WASAPI loopback devices on Windows, or all input
        devices on macOS/other (with BlackHole, if present, flagged as recommended)."""
        if self._pa is None:
            return []
        return self._list_windows_loopback() if IS_WINDOWS else self._list_generic_inputs()

    def _list_windows_loopback(self) -> list[AudioDevice]:
        default_name = None
        try:
            wasapi_info = self._pa.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_out = self._pa.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            default_name = default_out["name"]
        except Exception as exc:
            logger.debug("Could not resolve default WASAPI output device: %s", exc)

        devices: list[AudioDevice] = []
        try:
            for info in self._pa.get_loopback_device_info_generator():
                is_default = bool(default_name) and default_name in info["name"]
                devices.append(
                    AudioDevice(
                        index=info["index"],
                        name=info["name"],
                        sample_rate=int(info["defaultSampleRate"]),
                        channels=int(info["maxInputChannels"]),
                        is_default=is_default,
                    )
                )
        except Exception as exc:
            logger.error("Failed to enumerate WASAPI loopback devices: %s", exc)
        return devices

    def _list_generic_inputs(self) -> list[AudioDevice]:
        devices: list[AudioDevice] = []
        try:
            for i in range(self._pa.get_device_count()):
                info = self._pa.get_device_info_by_index(i)
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
        except Exception as exc:
            logger.error("Failed to enumerate input devices: %s", exc)
        return devices

    def get_default_loopback_device(self) -> AudioDevice | None:
        devices = self.list_loopback_devices()
        for d in devices:
            if d.is_default:
                return d
        return devices[0] if devices else None

    def get_device_by_index(self, index: int) -> AudioDevice | None:
        for d in self.list_loopback_devices():
            if d.index == index:
                return d
        return None

    def close(self) -> None:
        if self._pa is not None:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None
