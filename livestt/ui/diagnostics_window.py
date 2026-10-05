"""Read-only diagnostics panel: device, audio format, VAD/STT state, latency, error log."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFormLayout, QLabel, QPlainTextEdit, QVBoxLayout, QGroupBox

from livestt.logging_setup import get_ring_handler


class DiagnosticsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Диагностика")
        self.resize(520, 480)

        self._labels = {}
        form = QFormLayout()
        for key, title in [
            ("device_name", "Устройство"),
            ("sample_rate", "Sample rate"),
            ("channels", "Каналы"),
            ("audio_level", "Уровень сигнала"),
            ("vad_active", "VAD"),
            ("stt_state", "Состояние STT"),
            ("avg_latency_ms", "Средняя задержка"),
            ("chunks_processed", "Обработано чанков"),
            ("last_error", "Последняя ошибка"),
        ]:
            label = QLabel("—")
            label.setWordWrap(True)
            self._labels[key] = label
            form.addRow(title + ":", label)

        stats_box = QGroupBox("Текущее состояние")
        stats_box.setLayout(form)

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setPlainText("\n".join(get_ring_handler().snapshot()))

        log_box = QGroupBox("Журнал событий")
        log_layout = QVBoxLayout()
        log_layout.addWidget(self._log_view)
        log_box.setLayout(log_layout)

        layout = QVBoxLayout(self)
        layout.addWidget(stats_box)
        layout.addWidget(log_box, 1)

    def update_stats(self, stats) -> None:
        self._labels["device_name"].setText(stats.device_name or "—")
        self._labels["sample_rate"].setText(f"{stats.sample_rate} Гц" if stats.sample_rate else "—")
        self._labels["channels"].setText(str(stats.channels) if stats.channels else "—")
        self._labels["audio_level"].setText(f"{stats.audio_level:.2f}")
        self._labels["vad_active"].setText("речь" if stats.vad_active else "тишина")
        self._labels["stt_state"].setText(stats.stt_state)
        self._labels["avg_latency_ms"].setText(f"{stats.avg_latency_ms:.0f} мс")
        self._labels["chunks_processed"].setText(str(stats.chunks_processed))
        self._labels["last_error"].setText(stats.last_error or "—")

    def refresh_log(self) -> None:
        self._log_view.setPlainText("\n".join(get_ring_handler().snapshot()))
        self._log_view.verticalScrollBar().setValue(self._log_view.verticalScrollBar().maximum())

    def showEvent(self, event) -> None:
        self.refresh_log()
        super().showEvent(event)
