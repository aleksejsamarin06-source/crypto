from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal


class PasswordEntry(QWidget):
    textChanged = Signal(str)

    def __init__(self, parent=None, placeholder=""):
        super().__init__(parent)

        self.setFixedHeight(25)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText(placeholder)
        self.password_input.textChanged.connect(self._on_text_changed)

        self.toggle_button = QPushButton("👁")
        self.toggle_button.setFixedSize(25, 23)
        self.toggle_button.setCheckable(True)
        self.toggle_button.toggled.connect(self.toggle_visibility)

        layout.addWidget(self.password_input)
        layout.addWidget(self.toggle_button)

    def _on_text_changed(self, text):
        self.textChanged.emit(text)

    def toggle_visibility(self, checked):
        if checked:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.toggle_button.setText("🔒")
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.toggle_button.setText("👁")

    def text(self):
        return self.password_input.text()

    def setText(self, text):
        self.password_input.setText(text)

    def clear(self):
        self.password_input.clear()
