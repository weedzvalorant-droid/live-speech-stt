"""Live Speech STT — entry point.

Real-time system-audio speech-to-text. Windows: WASAPI loopback. macOS: PyAudio +
a BlackHole virtual device (see README). Run with: python main.py
"""
from __future__ import annotations

import logging
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from livestt.assets import icon_path
from livestt.config.settings_manager import SettingsManager
from livestt.logging_setup import setup_logging
from livestt.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


def main() -> int:
    log_file = setup_logging()
    logger.info("Starting Live Speech STT, logging to %s", log_file)

    app = QApplication(sys.argv)
    app.setApplicationName("Live Speech STT")
    app.setQuitOnLastWindowClosed(True)

    icon_file = icon_path()
    if icon_file.exists():
        app.setWindowIcon(QIcon(str(icon_file)))

    settings = SettingsManager()
    window = MainWindow(settings)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
