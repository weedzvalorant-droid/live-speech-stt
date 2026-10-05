"""Black/red app theme (default) with a light alternative. Colors match the app icon:
bright red #ff3b30, mid red #d61f26, dark red #8e0000, near-black #0b0b0d.
"""

DARK_QSS = """
QWidget { background-color: #0b0b0d; color: #f2eef0; font-family: 'Segoe UI', sans-serif; }
QMainWindow, QDialog { background-color: #0b0b0d; }
QToolBar { background-color: #131114; border: none; spacing: 6px; padding: 4px; }
QToolBar QToolButton {
    background-color: transparent; color: #f2eef0; border-radius: 6px; padding: 6px 10px;
}
QToolBar QToolButton:hover { background-color: #241217; }
QPushButton {
    background-color: #1a181b; border: 1px solid #332226; border-radius: 6px;
    padding: 6px 14px; color: #f2eef0;
}
QPushButton:hover { background-color: #241c1e; border-color: #4a2a2e; }
QPushButton:pressed { background-color: #150f11; }
QPushButton:disabled { color: #6b6468; border-color: #241c1e; }
QPushButton#startButton {
    background-color: #d61f26; border: 1px solid #ff3b30; color: #ffffff; font-weight: 600;
}
QPushButton#startButton:hover { background-color: #ff3b30; }
QPushButton#startButton:disabled { background-color: #3a1316; border-color: #3a1316; color: #8a6468; }
QPushButton#stopButton {
    background-color: transparent; border: 1px solid #5a2328; color: #ff6b61; font-weight: 600;
}
QPushButton#stopButton:hover { background-color: #2a1013; border-color: #ff3b30; color: #ff3b30; }
QPushButton#stopButton:disabled { border-color: #241c1e; color: #6b6468; }
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #151316; border: 1px solid #332226; border-radius: 6px; padding: 4px 8px;
    selection-background-color: #d61f26;
}
QComboBox:hover, QLineEdit:hover { border-color: #4a2a2e; }
QComboBox::drop-down { border: none; width: 22px; }
QTextEdit, QPlainTextEdit {
    background-color: #100e10; border: 1px solid #2a2024; border-radius: 8px; padding: 8px;
    selection-background-color: #d61f26; selection-color: #ffffff;
}
QCheckBox { spacing: 8px; }
QCheckBox::indicator {
    width: 16px; height: 16px; border-radius: 4px; border: 1px solid #4a2a2e; background: #151316;
}
QCheckBox::indicator:checked { background: #d61f26; border-color: #ff3b30; }
QGroupBox {
    border: 1px solid #2a2024; border-radius: 8px; margin-top: 10px; padding-top: 10px; font-weight: 600;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #ff6b61; }
QLabel#statusDot { font-size: 16px; }
QScrollBar:vertical { background: #0b0b0d; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #332226; border-radius: 5px; min-height: 24px; }
QScrollBar::handle:vertical:hover { background: #4a2a2e; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QDialogButtonBox QPushButton { min-width: 72px; }
QMenu { background-color: #131114; border: 1px solid #332226; }
QMenu::item:selected { background-color: #2a1013; }
"""

LIGHT_QSS = """
QWidget { background-color: #f6f3f3; color: #1c1315; font-family: 'Segoe UI', sans-serif; }
QMainWindow, QDialog { background-color: #f6f3f3; }
QToolBar { background-color: #ffffff; border: none; spacing: 6px; padding: 4px; }
QPushButton {
    background-color: #ffffff; border: 1px solid #e3d4d5; border-radius: 6px;
    padding: 6px 14px; color: #1c1315;
}
QPushButton:hover { background-color: #fbeceb; border-color: #e8a7a3; }
QPushButton:pressed { background-color: #f3dcdb; }
QPushButton#startButton { background-color: #d61f26; border: none; color: white; font-weight: 600; }
QPushButton#startButton:hover { background-color: #ff3b30; }
QPushButton#stopButton { background-color: #ffffff; border: 1px solid #d61f26; color: #d61f26; font-weight: 600; }
QPushButton#stopButton:hover { background-color: #fbeceb; }
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #ffffff; border: 1px solid #e3d4d5; border-radius: 6px; padding: 4px 8px;
}
QTextEdit, QPlainTextEdit {
    background-color: #ffffff; border: 1px solid #e3d4d5; border-radius: 8px; padding: 8px;
    selection-background-color: #d61f26; selection-color: #ffffff;
}
QGroupBox {
    border: 1px solid #e3d4d5; border-radius: 8px; margin-top: 10px; padding-top: 10px; font-weight: 600;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #d61f26; }
QScrollBar:vertical { background: #f6f3f3; width: 10px; }
QScrollBar::handle:vertical { background: #e3d4d5; border-radius: 5px; }
"""


def apply_theme(app, theme: str) -> None:
    app.setStyleSheet(DARK_QSS if theme == "dark" else LIGHT_QSS)
