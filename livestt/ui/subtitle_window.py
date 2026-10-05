"""Compact, draggable, resizable, semi-transparent "Subtitle Mode" overlay window."""
from __future__ import annotations

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizeGrip, QHBoxLayout


class SubtitleWindow(QWidget):
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self._settings = settings_manager
        self._drag_offset: QPoint | None = None

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint
            if self._settings.get("subtitle_always_on_top", True)
            else Qt.FramelessWindowHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumSize(300, 70)

        self._label = QLabel("")
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setTextInteractionFlags(Qt.NoTextInteraction)

        grip_row = QHBoxLayout()
        grip_row.addStretch(1)
        grip = QSizeGrip(self)
        grip_row.addWidget(grip, 0, Qt.AlignBottom | Qt.AlignRight)
        grip_row.setContentsMargins(0, 0, 0, 0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 4)
        layout.addWidget(self._label, 1)
        layout.addLayout(grip_row)

        self.apply_appearance()

        geom = self._settings.get("subtitle_geometry")
        if geom and len(geom) == 4:
            self.setGeometry(*geom)
        else:
            self.resize(560, 120)

    def apply_appearance(self) -> None:
        opacity = self._settings.get("subtitle_opacity", 0.85)
        font_size = self._settings.get("subtitle_font_size", 22)
        show_bg = self._settings.get("subtitle_background", True)

        self.setWindowOpacity(1.0)  # keep window opaque; fade only the background via rgba
        bg = f"rgba(20, 20, 24, {opacity})" if show_bg else "transparent"
        self._label.setStyleSheet(f"background: {bg}; color: white; border-radius: 10px; padding: 10px;")
        self._label.setFont(QFont("Segoe UI", font_size, QFont.DemiBold))

    def set_text(self, text: str) -> None:
        self._label.setText(text)

    def set_always_on_top(self, enabled: bool) -> None:
        flags = Qt.FramelessWindowHint | Qt.Tool
        if enabled:
            flags |= Qt.WindowStaysOnTopHint
        was_visible = self.isVisible()
        self.setWindowFlags(flags)
        if was_visible:
            self.show()

    # -- dragging ---------------------------------------------------------
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, _event) -> None:
        self._drag_offset = None

    def closeEvent(self, event) -> None:
        geom = self.geometry()
        self._settings.set("subtitle_geometry", [geom.x(), geom.y(), geom.width(), geom.height()])
        super().closeEvent(event)
