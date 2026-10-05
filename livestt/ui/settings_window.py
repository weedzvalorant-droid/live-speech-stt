"""Settings dialog: device, language, model, chunk size, VAD sensitivity, GPU, API key,
font size, theme, autostart. Emits settings_applied with the full settings dict when the
user clicks "Применить"/"ОК".
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QVBoxLayout, QHBoxLayout, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QLineEdit, QPushButton, QGroupBox, QLabel, QDialogButtonBox,
)

from livestt.audio.device_manager import AudioDeviceManager
from livestt.config import autostart as autostart_mod


class SettingsWindow(QDialog):
    settings_applied = Signal(dict)

    def __init__(self, settings_manager, device_manager: AudioDeviceManager, parent=None):
        super().__init__(parent)
        self._settings = settings_manager
        self._device_manager = device_manager
        self.setWindowTitle("Настройки")
        self.resize(460, 620)

        layout = QVBoxLayout(self)

        # Audio
        audio_box = QGroupBox("Аудио")
        audio_form = QFormLayout()
        self.device_combo = QComboBox()
        self._populate_devices()
        audio_form.addRow("Устройство:", self.device_combo)

        self.chunk_spin = QSpinBox()
        self.chunk_spin.setRange(100, 2000)
        self.chunk_spin.setSingleStep(50)
        self.chunk_spin.setSuffix(" мс")
        audio_form.addRow("Размер аудиочанка:", self.chunk_spin)
        audio_box.setLayout(audio_form)

        # STT
        stt_box = QGroupBox("Распознавание речи")
        stt_form = QFormLayout()
        self.language_combo = QComboBox()
        self.language_combo.addItem("Авто", "auto")
        self.language_combo.addItem("Русский", "ru")
        self.language_combo.addItem("English", "en")
        stt_form.addRow("Язык:", self.language_combo)

        self.provider_combo = QComboBox()
        self.provider_combo.addItem("Локально (faster-whisper)", "faster_whisper")
        self.provider_combo.addItem("Облако (OpenAI API)", "cloud_openai")
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        stt_form.addRow("Движок:", self.provider_combo)

        self.model_combo = QComboBox()
        for size in ("tiny", "base", "small", "medium", "large-v3"):
            self.model_combo.addItem(size, size)
        stt_form.addRow("Модель Whisper:", self.model_combo)

        self.gpu_checkbox = QCheckBox("Использовать GPU (CUDA), если доступен")
        stt_form.addRow(self.gpu_checkbox)

        self.partial_interval_spin = QSpinBox()
        self.partial_interval_spin.setRange(200, 3000)
        self.partial_interval_spin.setSingleStep(100)
        self.partial_interval_spin.setSuffix(" мс")
        stt_form.addRow("Интервал промежуточного текста:", self.partial_interval_spin)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText(
            "сохранён (keyring)" if self._settings.get("cloud_api_key_configured") else "введите API-ключ"
        )
        stt_form.addRow("API key:", self.api_key_edit)
        stt_box.setLayout(stt_form)

        # VAD
        vad_box = QGroupBox("Voice Activity Detection")
        vad_form = QFormLayout()
        self.vad_sensitivity_spin = QDoubleSpinBox()
        self.vad_sensitivity_spin.setRange(0.0, 1.0)
        self.vad_sensitivity_spin.setSingleStep(0.05)
        vad_form.addRow("Чувствительность:", self.vad_sensitivity_spin)

        self.vad_min_silence_spin = QSpinBox()
        self.vad_min_silence_spin.setRange(100, 3000)
        self.vad_min_silence_spin.setSuffix(" мс")
        vad_form.addRow("Тишина для завершения фразы:", self.vad_min_silence_spin)

        self.vad_min_speech_spin = QSpinBox()
        self.vad_min_speech_spin.setRange(50, 2000)
        self.vad_min_speech_spin.setSuffix(" мс")
        vad_form.addRow("Мин. длительность речи:", self.vad_min_speech_spin)
        vad_box.setLayout(vad_form)

        # UI
        ui_box = QGroupBox("Интерфейс")
        ui_form = QFormLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Тёмная", "dark")
        self.theme_combo.addItem("Светлая", "light")
        ui_form.addRow("Тема:", self.theme_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 28)
        ui_form.addRow("Размер шрифта:", self.font_size_spin)

        self.autostart_checkbox = QCheckBox("Запускать вместе с Windows")
        if not autostart_mod.is_supported():
            self.autostart_checkbox.setEnabled(False)
            self.autostart_checkbox.setText("Запускать вместе с Windows (только на Windows)")
        ui_form.addRow(self.autostart_checkbox)
        ui_box.setLayout(ui_form)

        layout.addWidget(audio_box)
        layout.addWidget(stt_box)
        layout.addWidget(vad_box)
        layout.addWidget(ui_box)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load_from_settings()

    def _populate_devices(self) -> None:
        self.device_combo.clear()
        self.device_combo.addItem("Системное устройство по умолчанию", None)
        if not self._device_manager.is_available():
            from livestt.audio.device_manager import IS_WINDOWS

            hint = "pyaudiowpatch не установлен" if IS_WINDOWS else "PyAudio не установлен"
            self.device_combo.addItem(f"(недоступно: {hint})", None)
            self.device_combo.setEnabled(False)
            return
        for device in self._device_manager.list_loopback_devices():
            self.device_combo.addItem(str(device), device.index)

    def _on_provider_changed(self) -> None:
        is_cloud = self.provider_combo.currentData() == "cloud_openai"
        self.api_key_edit.setEnabled(is_cloud)
        self.model_combo.setEnabled(not is_cloud)
        self.gpu_checkbox.setEnabled(not is_cloud)

    def _load_from_settings(self) -> None:
        s = self._settings.all()
        idx = self.device_combo.findData(s.get("audio_device_index"))
        self.device_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.chunk_spin.setValue(s.get("chunk_ms", 500))
        self.language_combo.setCurrentIndex(max(0, self.language_combo.findData(s.get("language", "auto"))))
        self.provider_combo.setCurrentIndex(max(0, self.provider_combo.findData(s.get("stt_provider", "faster_whisper"))))
        self.model_combo.setCurrentIndex(max(0, self.model_combo.findData(s.get("whisper_model", "small"))))
        self.gpu_checkbox.setChecked(s.get("use_gpu", True))
        self.partial_interval_spin.setValue(s.get("partial_interval_ms", 900))
        self.vad_sensitivity_spin.setValue(s.get("vad_sensitivity", 0.5))
        self.vad_min_silence_spin.setValue(s.get("vad_min_silence_ms", 500))
        self.vad_min_speech_spin.setValue(s.get("vad_min_speech_ms", 200))
        self.theme_combo.setCurrentIndex(max(0, self.theme_combo.findData(s.get("theme", "dark"))))
        self.font_size_spin.setValue(s.get("font_size", 14))
        self.autostart_checkbox.setChecked(s.get("autostart", False))
        self._on_provider_changed()

    def _on_accept(self) -> None:
        api_key_text = self.api_key_edit.text().strip()
        if api_key_text:
            self._settings.set_api_key("openai", api_key_text)

        new_settings = {
            "audio_device_index": self.device_combo.currentData(),
            "chunk_ms": self.chunk_spin.value(),
            "language": self.language_combo.currentData(),
            "stt_provider": self.provider_combo.currentData(),
            "whisper_model": self.model_combo.currentData(),
            "use_gpu": self.gpu_checkbox.isChecked(),
            "partial_interval_ms": self.partial_interval_spin.value(),
            "vad_sensitivity": self.vad_sensitivity_spin.value(),
            "vad_min_silence_ms": self.vad_min_silence_spin.value(),
            "vad_min_speech_ms": self.vad_min_speech_spin.value(),
            "theme": self.theme_combo.currentData(),
            "font_size": self.font_size_spin.value(),
            "autostart": self.autostart_checkbox.isChecked(),
        }
        self._settings.update(new_settings)
        if autostart_mod.is_supported():
            autostart_mod.set_autostart(new_settings["autostart"])

        self.settings_applied.emit(self._settings.all())
        self.accept()
