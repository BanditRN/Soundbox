from PySide6.QtWidgets import ( QVBoxLayout, QHBoxLayout , QPushButton, QLabel, QTextEdit , QDialog)
from PySide6.QtGui import (QFont)
from typing import Optional
import winaccent
class KeybindDialog(QDialog):
    
    def __init__(self, action_name: str, existing_key: str = "", parent=None):
        super().__init__(parent)
        self.action_name = action_name
        self.captured_key = existing_key
        self.accepted_key = None
        self.setWindowTitle("Set Keybind")
        self.setFixedSize(350, 150)
        self.setModal(True)

        layout = QVBoxLayout(self)

        info_label = QLabel(f"Set keybind for: {action_name}")
        info_label.setFont(QFont("Arial", 11, QFont.Bold))
        info_label.setStyleSheet("color: white; background: transparent;")
        layout.addWidget(info_label)

        instruction = QLabel("Press your key combination (max 2 keys)")
        instruction.setStyleSheet("color: #aaaaaa; background: transparent;")
        layout.addWidget(instruction)

        self.key_display = QTextEdit()
        self.key_display.setReadOnly(True)
        self.key_display.setFixedHeight(40)
        self.key_display.setPlaceholderText("Press keys...")
        self.key_display.setText(existing_key)
        self.key_display.setStyleSheet("""
            QTextEdit {
                background: #2a2a2a;
                color: white;
                border: 2px solid #444;
                border-radius: 0px;
                padding: 5px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.key_display)
        
        button_layout = QHBoxLayout()
        
        self.accept_btn = QPushButton("Accept")
        self.accept_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #218838;
            }
            QPushButton:pressed {
                background: #1e7e34;
            }
        """)
        self.accept_btn.clicked.connect(self._accept_keybind)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: #dc3545;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #c82333;
            }
            QPushButton:pressed {
                background: #bd2130;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: grey;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #c82333;
            }
            QPushButton:pressed {
                background: #bd2130;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_keybind)

        button_layout.addWidget(self.accept_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.clear_btn)

        layout.addLayout(button_layout)
        
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0 y1:0, x2:1 y2:1, 
                    stop:0 #051c2a stop:1 #44315f);
                border: 2px solid """ + winaccent.accent_dark_1 + """;
                border-radius: 0px;
            }
            QLabel {
                background: transparent;
            }
        """)
    def clear_keybind(self):
        self.accepted_key = None
        self.accept()

    def update_key_display(self, key_combo: str):
        self.captured_key = key_combo
        self.key_display.setText(key_combo)
    
    def _accept_keybind(self):
        self.accepted_key = self.captured_key
        self.accept()
    
    def get_keybind(self) -> Optional[str]:
        return self.accepted_key