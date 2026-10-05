"""Loads/saves app settings as JSON. API keys are kept out of the JSON file and stored
via the OS credential store (Windows Credential Locker / keyring), never in plaintext.
"""
from __future__ import annotations

import copy
import json
import logging
import threading
from pathlib import Path
from typing import Any

from livestt.config.defaults import DEFAULT_SETTINGS
from livestt.logging_setup import get_app_data_dir

logger = logging.getLogger(__name__)

try:
    import keyring

    _KEYRING_AVAILABLE = True
except Exception:  # pragma: no cover - keyring backend missing on this platform
    keyring = None
    _KEYRING_AVAILABLE = False

_SERVICE_NAME = "LiveSpeechSTT"


class SettingsManager:
    def __init__(self, app_name: str = "LiveSpeechSTT", config_dir: Path | None = None):
        self._app_name = app_name
        self._dir = config_dir or get_app_data_dir(app_name)
        self._path = self._dir / "settings.json"
        self._lock = threading.Lock()
        self._settings: dict[str, Any] = copy.deepcopy(DEFAULT_SETTINGS)
        self.load()

    # -- plain settings -------------------------------------------------
    def config_dir(self) -> Path:
        return self._dir

    def load(self) -> dict[str, Any]:
        with self._lock:
            if self._path.exists():
                try:
                    on_disk = json.loads(self._path.read_text(encoding="utf-8"))
                    merged = copy.deepcopy(DEFAULT_SETTINGS)
                    merged.update({k: v for k, v in on_disk.items() if k in DEFAULT_SETTINGS})
                    self._settings = merged
                except (json.JSONDecodeError, OSError) as exc:
                    logger.error("Failed to read settings.json (%s); using defaults", exc)
                    self._settings = copy.deepcopy(DEFAULT_SETTINGS)
            return copy.deepcopy(self._settings)

    def save(self) -> None:
        with self._lock:
            try:
                self._dir.mkdir(parents=True, exist_ok=True)
                tmp = self._path.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(self._settings, indent=2, ensure_ascii=False), encoding="utf-8")
                tmp.replace(self._path)
            except OSError as exc:
                logger.error("Failed to save settings.json: %s", exc)

    def all(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._settings)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._settings.get(key, default)

    def set(self, key: str, value: Any, persist: bool = True) -> None:
        with self._lock:
            self._settings[key] = value
        if persist:
            self.save()

    def update(self, values: dict[str, Any], persist: bool = True) -> None:
        with self._lock:
            self._settings.update(values)
        if persist:
            self.save()

    # -- secrets ----------------------------------------------------------
    def set_api_key(self, provider: str, api_key: str) -> bool:
        if not _KEYRING_AVAILABLE:
            logger.warning(
                "keyring backend unavailable on this system; API key for %s was NOT stored securely "
                "and will not be persisted.",
                provider,
            )
            return False
        try:
            keyring.set_password(_SERVICE_NAME, provider, api_key)
            self.set("cloud_api_key_configured", True)
            return True
        except Exception as exc:
            logger.error("Failed to store API key via keyring: %s", exc)
            return False

    def get_api_key(self, provider: str) -> str | None:
        if not _KEYRING_AVAILABLE:
            return None
        try:
            return keyring.get_password(_SERVICE_NAME, provider)
        except Exception as exc:
            logger.error("Failed to read API key via keyring: %s", exc)
            return None

    def clear_api_key(self, provider: str) -> None:
        if not _KEYRING_AVAILABLE:
            return
        try:
            keyring.delete_password(_SERVICE_NAME, provider)
        except Exception:
            pass
        self.set("cloud_api_key_configured", False)
