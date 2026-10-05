"""Centralized logging: rotating file handler + in-memory ring buffer for the Diagnostics UI."""
from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from collections import deque
from pathlib import Path


class RingBufferHandler(logging.Handler):
    """Keeps the last N log records in memory so the Diagnostics window can display them live."""

    def __init__(self, capacity: int = 500):
        super().__init__()
        self.buffer: deque[str] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.buffer.append(self.format(record))
        except Exception:
            pass

    def snapshot(self) -> list[str]:
        return list(self.buffer)


_ring_handler: RingBufferHandler | None = None


def get_ring_handler() -> RingBufferHandler:
    assert _ring_handler is not None, "logging not configured yet; call setup_logging() first"
    return _ring_handler


def get_app_data_dir(app_name: str = "LiveSpeechSTT") -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    else:
        # Linux/mac fallback, used only during cross-platform development/testing.
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    path = Path(base) / app_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def setup_logging(app_name: str = "LiveSpeechSTT", level: int = logging.INFO) -> Path:
    global _ring_handler

    log_dir = get_app_data_dir(app_name) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%H:%M:%S")

    root = logging.getLogger()
    root.setLevel(level)

    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(fmt)
    root.addHandler(console_handler)

    _ring_handler = RingBufferHandler()
    _ring_handler.setFormatter(fmt)
    root.addHandler(_ring_handler)

    return log_file
