from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout,
                               QLineEdit, QTextEdit, QDialogButtonBox,
                               QMessageBox, QWidget)
from PySide6.QtCore import Qt
from src.gui.widgets.password_entry import PasswordEntry


class EntryDialog(QDialog):
    def __init__(self, parent=None, title="Добавить запись", entry_data=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(500, 400)
        self.setModal(True)

        self.result_data = None
        self.entry_data = entry_data or {}

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)

        self.title_edit = QLineEdit()
        self.username_edit = QLineEdit()
        self.password_edit = PasswordEntry()
        self.url_edit = QLineEdit()
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(100)

        form_layout.addRow("Название:", self.title_edit)
        form_layout.addRow("Имя пользователя:", self.username_edit)
        form_layout.addRow("Пароль:", self.password_edit)
        form_layout.addRow("URL:", self.url_edit)
        form_layout.addRow("Заметки:", self.notes_edit)

        layout.addWidget(form_widget)

        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_data(self):
        if self.entry_data:
            self.title_edit.setText(self.entry_data.get("title", ""))
            self.username_edit.setText(self.entry_data.get("username", ""))
            self.password_edit.setText(self.entry_data.get("password", ""))
            self.url_edit.setText(self.entry_data.get("url", ""))
            self.notes_edit.setPlainText(self.entry_data.get("notes", ""))

    def save(self):
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.critical(self, "Ошибка", "Название обязательно")
            return

        password = self.password_edit.text().strip()

        self.result_data = {
            "title": title,
            "username": self.username_edit.text().strip(),
            "password": password,  # сохраняем пароль
            "url": self.url_edit.text().strip(),
            "notes": self.notes_edit.toPlainText().strip()
        }

        self.password_edit.clear()

        self.accept()

    def show(self):
        result = self.exec()
        if result == QDialog.Accepted:
            return self.result_data
        return None