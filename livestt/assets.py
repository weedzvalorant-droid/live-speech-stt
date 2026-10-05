"""Resolves bundled asset paths, working both when run from source and when frozen by
PyInstaller (where files live under sys._MEIPASS instead of next to the source tree).
"""
from __future__ import annotations

import sys
from pathlib import Path


def asset_path(name: str) -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).resolve().parent.parent
    return base / "assets" / name


def icon_path() -> Path:
    return asset_path("icon.icns" if sys.platform == "darwin" else "icon.ico")
