from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout,
                               QLineEdit, QTextEdit, QDialogButtonBox,
                               QMessageBox, QWidget, QPushButton, QHBoxLayout,
                               QProgressBar)
import urllib.request
import os
from PySide6.QtWidgets import QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
from src.gui.widgets.password_entry import PasswordEntry
from src.core.vault.password_generator import PasswordGenerator


class EntryDialog(QDialog):
    def __init__(self, parent=None, title="Добавить запись", entry_data=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(500, 400)
        self.setModal(True)

        self.result_data = None
        self.entry_data = entry_data or {}
        self.password_gen = PasswordGenerator()

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)

        self.title_edit = QLineEdit()
        self.username_edit = QLineEdit()

        password_layout = QHBoxLayout()
        self.password_edit = PasswordEntry()
        self.password_edit.textChanged.connect(self.check_strength)
        self.generate_btn = QPushButton("Сгенерировать")
        self.generate_btn.clicked.connect(self.generate_password)
        password_layout.addWidget(self.password_edit)
        password_layout.addWidget(self.generate_btn)

        self.strength_bar = QProgressBar()
        self.strength_bar.setMaximum(4)
        self.strength_bar.setValue(0)
        self.strength_bar.setFixedHeight(5)

        self.url_edit = QLineEdit()
        self.url_edit.textChanged.connect(self.auto_load_favicon)

        self.favicon_label = QLabel()
        self.favicon_label.setFixedSize(16, 16)
        self.favicon_label.setScaledContents(True)

        self.category_edit = QLineEdit()
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(100)

        form_layout.addRow("Название:", self.title_edit)
        form_layout.addRow("Имя пользователя:", self.username_edit)
        form_layout.addRow("Пароль:", password_layout)
        form_layout.addRow("", self.strength_bar)

        url_layout = QHBoxLayout()
        url_layout.addWidget(self.favicon_label)
        url_layout.addWidget(self.url_edit)
        form_layout.addRow("URL:", url_layout)

        form_layout.addRow("Категория:", self.category_edit)
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
            self.category_edit.setText(self.entry_data.get("category", ""))
            self.notes_edit.setPlainText(self.entry_data.get("notes", ""))

    def calculate_strength(self, password):
        score = 0
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        if any(c.isupper() for c in password):
            score += 0.5
        if any(c.islower() for c in password):
            score += 0.5
        if any(c.isdigit() for c in password):
            score += 0.5
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            score += 0.5
        return min(4, int(score))

    def check_strength(self):
        password = self.password_edit.text()
        strength = self.calculate_strength(password)
        self.strength_bar.setValue(strength)

    def auto_load_favicon(self):
        """Автоматическая загрузка фавиконки при вводе URL"""
        url = self.url_edit.text().strip()
        if not url:
            return

        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url

        try:
            domain = url.split("//")[1].split("/")[0]
            favicon_url = f"https://www.google.com/s2/favicons?domain={domain}"

            os.makedirs("favicons", exist_ok=True)
            favicon_path = f"favicons/{domain}.png"

            if not os.path.exists(favicon_path):
                urllib.request.urlretrieve(favicon_url, favicon_path)
                pixmap = QPixmap(favicon_path)
                self.favicon_label.setPixmap(pixmap)
            else:
                pixmap = QPixmap(favicon_path)
                self.favicon_label.setPixmap(pixmap)

            self.favicon_path = favicon_path
        except Exception as e:
            pass  # Игнорируем ошибки, фавиконка не обязательна


    def save(self):
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.critical(self, "Ошибка", "Название обязательно")
            return

        password = self.password_edit.text().strip()
        if not password:
            QMessageBox.critical(self, "Ошибка", "Пароль не может быть пустым")
            return

        url = self.url_edit.text().strip()
        if url and not url.startswith(('http://', 'https://')):
            url = 'http://' + url
            self.url_edit.setText(url)

        url = self.url_edit.text().strip()
        domain = ""
        if url:
            if "://" in url:
                domain = url.split("://")[1].split("/")[0]
            else:
                domain = url.split("/")[0]

        self.result_data = {
            "title": title,
            "username": self.username_edit.text().strip(),
            "password": password,
            "url": self.url_edit.text().strip(),
            "domain": domain,
            "category": self.category_edit.text().strip(),
            "notes": self.notes_edit.toPlainText().strip()
        }

        self.password_edit.clear()
        self.accept()

    def generate_password(self):
        password = self.password_gen.generate()
        self.password_edit.setText(password)
        self.check_strength()

    def check_strength(self):
        password = self.password_edit.text()
        strength = self.calculate_strength(password)
        self.strength_bar.setValue(strength)

    def show(self):
        result = self.exec()
        if result == QDialog.Accepted:
            return self.result_data
        return None
