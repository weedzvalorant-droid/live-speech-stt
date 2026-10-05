"""Small reusable widgets: audio level meter and a colored status dot."""
from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QPainter, QLinearGradient
from PySide6.QtWidgets import QWidget


class LevelMeter(QWidget):
    """Horizontal VU-style bar, green -> yellow -> red as the level rises."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = 0.0
        self.setMinimumHeight(10)
        self.setMaximumHeight(14)

    def set_level(self, level: float) -> None:
        self._level = max(0.0, min(1.0, level))
        self.update()

    def sizeHint(self) -> QSize:
        return QSize(200, 12)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#151619"))
        painter.drawRoundedRect(rect, 5, 5)

        if self._level <= 0.0:
            return

        filled_width = int(rect.width() * self._level)
        gradient = QLinearGradient(0, 0, rect.width(), 0)
        gradient.setColorAt(0.0, QColor("#22c55e"))
        gradient.setColorAt(0.65, QColor("#eab308"))
        gradient.setColorAt(1.0, QColor("#dc2626"))
        painter.setBrush(gradient)
        painter.drawRoundedRect(0, 0, filled_width, rect.height(), 5, 5)


class StatusDot(QWidget):
    COLORS = {
        "idle": "#6b6468",
        "listening": "#22c55e",
        "partial": "#eab308",
        "final": "#ff6b61",
        "loading": "#eab308",
        "error": "#ff3b30",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "idle"
        self.setFixedSize(14, 14)

    def set_state(self, state: str) -> None:
        self._state = state
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(self.COLORS.get(self._state, "#6b7280")))
        painter.drawEllipse(1, 1, 12, 12)
