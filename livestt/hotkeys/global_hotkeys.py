"""System-wide hotkeys (work even when the app window isn't focused), via pynput.
Callbacks fire on pynput's own listener thread; wrap them in a Qt Signal.emit() from the
caller so the actual work runs safely on the Qt (main) thread via auto-queued connections.
"""
from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger(__name__)

try:
    from pynput import keyboard

    PYNPUT_AVAILABLE = True
except Exception as exc:  # pragma: no cover - e.g. missing X server on headless Linux CI
    keyboard = None
    PYNPUT_AVAILABLE = False
    _import_error = exc


class GlobalHotkeys:
    def __init__(self):
        self._listener = None

    def start(self, bindings: dict[str, Callable[[], None]]) -> bool:
        if not PYNPUT_AVAILABLE:
            logger.warning("Global hotkeys unavailable: %s", _import_error if "_import_error" in globals() else "pynput missing")
            return False
        try:
            self._listener = keyboard.GlobalHotKeys(bindings)
            self._listener.start()
            return True
        except Exception as exc:
            logger.error("Failed to register global hotkeys: %s", exc)
            return False

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None


# Canonical bindings used by the app (pynput's GlobalHotKeys string format).
DEFAULT_BINDINGS = {
    "start_stop": "<ctrl>+<shift>+<space>",
    "copy": "<ctrl>+<shift>+c",
    "clear": "<ctrl>+<shift>+x",
    "save": "<ctrl>+<shift>+s",
}
