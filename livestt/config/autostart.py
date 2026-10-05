"""Windows "launch with Windows" support via the HKCU Run registry key.

This module only does anything meaningful on Windows (winreg is a Windows-only stdlib
module); on other platforms it logs and no-ops, so the rest of the app stays importable
and testable cross-platform.
"""
from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger(__name__)

_RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "LiveSpeechSTT"


def _executable_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    main_py = os.path.abspath(sys.argv[0])
    return f'"{sys.executable}" "{main_py}"'


def is_supported() -> bool:
    return os.name == "nt"


def set_autostart(enabled: bool) -> bool:
    if not is_supported():
        logger.warning("Autostart is only supported on Windows; ignoring request.")
        return False

    import winreg  # noqa: PLC0415 - Windows-only import, kept local on purpose

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, _VALUE_NAME, 0, winreg.REG_SZ, _executable_command())
            else:
                try:
                    winreg.DeleteValue(key, _VALUE_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError as exc:
        logger.error("Failed to update autostart registry key: %s", exc)
        return False


def is_autostart_enabled() -> bool:
    if not is_supported():
        return False
    import winreg  # noqa: PLC0415

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, _VALUE_NAME)
            return True
    except FileNotFoundError:
        return False
    except OSError:
        return False
