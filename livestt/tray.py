"""System tray icon: minimize-to-tray and quick access to Show/Quit."""
from __future__ import annotations

from PySide6.QtGui import QAction, QIcon, QPixmap, QColor, QPainter
from PySide6.QtWidgets import QSystemTrayIcon, QMenu

from livestt.assets import icon_path


def _fallback_icon() -> QIcon:
    """Only used if assets/icon.ico is somehow missing (e.g. a broken/partial build)."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor("#0b0b0d"))
    painter = QPainter(pixmap)
    painter.setBrush(QColor("#d61f26"))
    painter.drawEllipse(10, 6, 12, 12)
    painter.end()
    return QIcon(pixmap)


def _app_icon() -> QIcon:
    path = icon_path()
    if path.exists():
        return QIcon(str(path))
    return _fallback_icon()


class TrayIcon(QSystemTrayIcon):
    def __init__(self, main_window):
        super().__init__(_app_icon(), main_window)
        self._window = main_window
        menu = QMenu()
        show_action = QAction("Показать окно", self)
        show_action.triggered.connect(self._show_window)
        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(show_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.setContextMenu(menu)
        self.setToolTip("Live Speech STT")
        self.activated.connect(self._on_activated)

    def _show_window(self) -> None:
        self._window.showNormal()
        self._window.raise_()
        self._window.activateWindow()

    def _quit(self) -> None:
        from PySide6.QtWidgets import QApplication

        QApplication.instance().quit()

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_window()
