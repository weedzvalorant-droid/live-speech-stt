"""Main application window: device/language pickers, start/stop, level meter, transcript
view, copy/clear/export, autoscroll, Subtitle Mode, Always on Top, Settings, Diagnostics,
and global hotkeys. The real pipeline (audio capture + VAD + STT) runs on a dedicated
QThread (TranscriptionManager); this window only ever talks to it via signals/slots, so a
slow model load or STT decode can never freeze the UI.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QAction, QTextCursor, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QTextEdit,
    QCheckBox, QLabel, QFileDialog, QMessageBox, QApplication, QToolBar,
)

from livestt.audio.device_manager import AudioDeviceManager
from livestt.config.settings_manager import SettingsManager
from livestt.export.export_manager import ExportManager
from livestt.hotkeys.global_hotkeys import GlobalHotkeys, DEFAULT_BINDINGS
from livestt.pipeline.transcription_manager import TranscriptionManager
from livestt.tray import TrayIcon
from livestt.ui.diagnostics_window import DiagnosticsWindow
from livestt.ui.settings_window import SettingsWindow
from livestt.ui.subtitle_window import SubtitleWindow
from livestt.ui.theme import apply_theme
from livestt.ui.widgets import LevelMeter, StatusDot

logger = logging.getLogger(__name__)

_STATE_LABELS = {
    "idle": "Готово",
    "listening": "Слушаю...",
    "partial": "Распознаю...",
    "final": "Распознаю...",
    "loading": "Загрузка модели...",
    "error": "Ошибка",
}


class MainWindow(QMainWindow):
    # UI -> pipeline (cross-thread; auto-queued by Qt since TranscriptionManager lives
    # on a different QThread)
    configure_requested = Signal(dict)
    start_requested = Signal()
    stop_requested = Signal()
    clear_requested = Signal()

    def __init__(self, settings_manager: SettingsManager):
        super().__init__()
        self.setWindowTitle("Live Speech STT")
        self.resize(760, 600)

        self._settings = settings_manager
        self._device_manager = AudioDeviceManager()
        self._full_text = ""
        self._is_running = False

        self._build_ui()
        self._build_pipeline_thread()
        self._build_subtitle_window()
        self._build_diagnostics_window()
        self._build_tray()
        self._build_hotkeys()

        apply_theme(QApplication.instance(), self._settings.get("theme", "dark"))
        self.setWindowFlag(Qt.WindowStaysOnTopHint, self._settings.get("always_on_top", False))

    # -- UI construction --------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)

        controls_row = QHBoxLayout()
        controls_row.addWidget(QLabel("Устройство:"))
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(220)
        controls_row.addWidget(self.device_combo)

        controls_row.addWidget(QLabel("Язык:"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("Авто", "auto")
        self.language_combo.addItem("Русский", "ru")
        self.language_combo.addItem("English", "en")
        controls_row.addWidget(self.language_combo)
        controls_row.addStretch(1)
        root.addLayout(controls_row)

        status_row = QHBoxLayout()
        self.status_dot = StatusDot()
        status_row.addWidget(self.status_dot)
        self.status_label = QLabel(_STATE_LABELS["idle"])
        status_row.addWidget(self.status_label)
        status_row.addSpacing(16)
        self.level_meter = LevelMeter()
        status_row.addWidget(self.level_meter, 1)

        self.start_button = QPushButton("ЗАПУСТИТЬ")
        self.start_button.setObjectName("startButton")
        self.start_button.clicked.connect(self._on_start_clicked)
        status_row.addWidget(self.start_button)

        self.stop_button = QPushButton("ОСТАНОВИТЬ")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self._on_stop_clicked)
        status_row.addWidget(self.stop_button)
        root.addLayout(status_row)

        self.transcript_edit = QTextEdit()
        self.transcript_edit.setReadOnly(True)
        root.addWidget(self.transcript_edit, 1)

        bottom_row = QHBoxLayout()
        self.copy_button = QPushButton("Копировать")
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        bottom_row.addWidget(self.copy_button)

        self.clear_button = QPushButton("Очистить")
        self.clear_button.clicked.connect(self.clear_transcript)
        bottom_row.addWidget(self.clear_button)

        self.save_txt_button = QPushButton("Сохранить TXT")
        self.save_txt_button.clicked.connect(lambda: self.save_transcript("txt"))
        bottom_row.addWidget(self.save_txt_button)

        self.save_md_button = QPushButton("Сохранить Markdown")
        self.save_md_button.clicked.connect(lambda: self.save_transcript("md"))
        bottom_row.addWidget(self.save_md_button)

        bottom_row.addStretch(1)
        self.autoscroll_checkbox = QCheckBox("Автопрокрутка")
        self.autoscroll_checkbox.setChecked(self._settings.get("autoscroll", True))
        bottom_row.addWidget(self.autoscroll_checkbox)
        root.addLayout(bottom_row)

        self.setCentralWidget(central)
        self._build_toolbar()

        self.device_combo.currentIndexChanged.connect(self._on_settings_widgets_changed)
        self.language_combo.currentIndexChanged.connect(self._on_settings_widgets_changed)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        settings_action = QAction("Настройки", self)
        settings_action.triggered.connect(self.open_settings)
        toolbar.addAction(settings_action)

        subtitle_action = QAction("Режим субтитров", self)
        subtitle_action.triggered.connect(self.toggle_subtitle_window)
        toolbar.addAction(subtitle_action)

        self.always_on_top_action = QAction("Always on Top", self)
        self.always_on_top_action.setCheckable(True)
        self.always_on_top_action.setChecked(self._settings.get("always_on_top", False))
        self.always_on_top_action.toggled.connect(self._on_always_on_top_toggled)
        toolbar.addAction(self.always_on_top_action)

        diagnostics_action = QAction("Диагностика", self)
        diagnostics_action.triggered.connect(self.open_diagnostics)
        toolbar.addAction(diagnostics_action)

    # -- pipeline thread ----------------------------------------------------
    def _build_pipeline_thread(self) -> None:
        self._thread = QThread(self)
        self._manager = TranscriptionManager(self._device_manager)
        self._manager.moveToThread(self._thread)

        self.configure_requested.connect(self._manager.configure)
        self.start_requested.connect(self._manager.start)
        self.stop_requested.connect(self._manager.stop)
        self.clear_requested.connect(self._manager.clear_text)

        self._manager.partial_text_changed.connect(self._on_display_text)
        self._manager.final_text_changed.connect(self._on_final_text)
        self._manager.state_changed.connect(self._on_state_changed)
        self._manager.stats_changed.connect(self._on_stats_changed)
        self._manager.error_occurred.connect(self._on_error)

        self._thread.start()
        self._refresh_devices()
        self._apply_settings_to_pipeline()

    def _refresh_devices(self) -> None:
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        self.device_combo.addItem("Системное устройство по умолчанию", None)
        if self._device_manager.is_available():
            for device in self._device_manager.list_loopback_devices():
                self.device_combo.addItem(str(device), device.index)
        else:
            from livestt.audio.device_manager import IS_WINDOWS

            hint = "модуль pyaudiowpatch не установлен" if IS_WINDOWS else "модуль PyAudio не установлен"
            self.device_combo.addItem(f"(захват звука недоступен: {hint})", None)
        saved_index = self.device_combo.findData(self._settings.get("audio_device_index"))
        self.device_combo.setCurrentIndex(saved_index if saved_index >= 0 else 0)
        self.device_combo.blockSignals(False)

        lang_index = self.language_combo.findData(self._settings.get("language", "auto"))
        self.language_combo.blockSignals(True)
        self.language_combo.setCurrentIndex(max(0, lang_index))
        self.language_combo.blockSignals(False)

    def _apply_settings_to_pipeline(self) -> None:
        settings = self._settings.all()
        settings["audio_device_index"] = self.device_combo.currentData()
        settings["language"] = self.language_combo.currentData()
        if settings.get("stt_provider") == "cloud_openai":
            settings["_api_key"] = self._settings.get_api_key("openai")
        self.configure_requested.emit(settings)

    def _on_settings_widgets_changed(self) -> None:
        self._settings.set("audio_device_index", self.device_combo.currentData())
        self._settings.set("language", self.language_combo.currentData())
        self._apply_settings_to_pipeline()

    # -- start/stop ---------------------------------------------------------
    def _on_start_clicked(self) -> None:
        self.start_requested.emit()
        self._is_running = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def _on_stop_clicked(self) -> None:
        self.stop_requested.emit()
        self._is_running = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_dot.set_state("idle")
        self.status_label.setText(_STATE_LABELS["idle"])
        self.level_meter.set_level(0.0)

    def toggle_start_stop(self) -> None:
        if self._is_running:
            self._on_stop_clicked()
        else:
            self._on_start_clicked()

    # -- pipeline signal handlers --------------------------------------------
    def _on_display_text(self, text: str) -> None:
        self.transcript_edit.setPlainText(text)
        if self.autoscroll_checkbox.isChecked():
            cursor = self.transcript_edit.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.transcript_edit.setTextCursor(cursor)
        self._subtitle_window.set_text(self._tail_excerpt(text))

    def _on_final_text(self, text: str) -> None:
        self._full_text = text

    def _on_state_changed(self, state: str) -> None:
        self.status_dot.set_state(state)
        self.status_label.setText(_STATE_LABELS.get(state, state))

    def _on_stats_changed(self, stats) -> None:
        self.level_meter.set_level(stats.audio_level)
        if self._diagnostics_window.isVisible():
            self._diagnostics_window.update_stats(stats)

    def _on_error(self, message: str) -> None:
        logger.error(message)
        self.status_label.setText(f"Ошибка: {message}")

    @staticmethod
    def _tail_excerpt(text: str, max_chars: int = 160) -> str:
        if len(text) <= max_chars:
            return text
        tail = text[-max_chars:]
        space_idx = tail.find(" ")
        return tail[space_idx + 1 :] if space_idx != -1 else tail

    # -- text actions ---------------------------------------------------
    def copy_to_clipboard(self) -> None:
        QApplication.clipboard().setText(self._full_text)

    def clear_transcript(self) -> None:
        self._full_text = ""
        self.transcript_edit.clear()
        self._subtitle_window.set_text("")
        self.clear_requested.emit()

    def save_transcript(self, fmt: str) -> None:
        if not self._full_text.strip():
            QMessageBox.information(self, "Экспорт", "Нет текста для сохранения.")
            return
        filter_str = "Text (*.txt)" if fmt == "txt" else "Markdown (*.md)"
        default_name = "transcript.txt" if fmt == "txt" else "transcript.md"
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить расшифровку", default_name, filter_str)
        if not path:
            return
        if fmt == "txt":
            ExportManager.to_txt(self._full_text, path)
        else:
            ExportManager.to_markdown(self._full_text, path)

    # -- settings / subtitle / diagnostics / tray --------------------------
    def open_settings(self) -> None:
        dialog = SettingsWindow(self._settings, self._device_manager, self)
        dialog.settings_applied.connect(self._on_settings_applied)
        dialog.exec()

    def _on_settings_applied(self, settings: dict) -> None:
        apply_theme(QApplication.instance(), settings.get("theme", "dark"))
        self.autoscroll_checkbox.setChecked(settings.get("autoscroll", True))
        self._refresh_devices()
        self._apply_settings_to_pipeline()
        self._subtitle_window.apply_appearance()

    def _build_subtitle_window(self) -> None:
        self._subtitle_window = SubtitleWindow(self._settings)

    def toggle_subtitle_window(self) -> None:
        if self._subtitle_window.isVisible():
            self._subtitle_window.hide()
        else:
            self._subtitle_window.show()

    def _build_diagnostics_window(self) -> None:
        self._diagnostics_window = DiagnosticsWindow(self)
        self._log_timer = QTimer(self)
        self._log_timer.setInterval(2000)
        self._log_timer.timeout.connect(self._refresh_diagnostics_log)
        self._log_timer.start()

    def _refresh_diagnostics_log(self) -> None:
        if self._diagnostics_window.isVisible():
            self._diagnostics_window.refresh_log()

    def open_diagnostics(self) -> None:
        self._diagnostics_window.show()
        self._diagnostics_window.raise_()

    def _on_always_on_top_toggled(self, checked: bool) -> None:
        self._settings.set("always_on_top", checked)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, checked)
        self.show()

    def _build_tray(self) -> None:
        self._tray = TrayIcon(self)
        self._tray.show()

    def _build_hotkeys(self) -> None:
        self._hotkeys = GlobalHotkeys()
        self._hotkeys.start(
            {
                DEFAULT_BINDINGS["start_stop"]: self._hotkey_signal("toggle_start_stop"),
                DEFAULT_BINDINGS["copy"]: self._hotkey_signal("copy_to_clipboard"),
                DEFAULT_BINDINGS["clear"]: self._hotkey_signal("clear_transcript"),
                DEFAULT_BINDINGS["save"]: self._hotkey_signal("save_txt_hotkey"),
            }
        )

    def _hotkey_signal(self, method_name: str):
        """Hotkeys fire on pynput's own thread; QTimer.singleShot(0, ...) marshals the
        call back onto the Qt main thread's event loop instead of touching widgets directly
        from a foreign thread."""

        def _invoke():
            if method_name == "save_txt_hotkey":
                QTimer.singleShot(0, lambda: self.save_transcript("txt"))
            else:
                QTimer.singleShot(0, getattr(self, method_name))

        return _invoke

    # -- shutdown ---------------------------------------------------------
    def closeEvent(self, event) -> None:
        self._hotkeys.stop()
        self.stop_requested.emit()
        self._manager.shutdown()
        self._thread.quit()
        self._thread.wait(3000)
        self._device_manager.close()
        self._subtitle_window.close()
        super().closeEvent(event)
