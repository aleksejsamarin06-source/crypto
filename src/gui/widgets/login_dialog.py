from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit,
                               QPushButton, QMessageBox, QHBoxLayout)
from PySide6.QtCore import Qt
from src.core.crypto.authentication import Authentication


class LoginDialog(QDialog):
    def __init__(self, parent=None, db_connection=None):
        super().__init__(parent)
        self.setWindowTitle("Вход в CryptoSafe")
        self.resize(400, 200)
        self.setModal(True)

        self.db = db_connection
        self.auth = Authentication(db_connection)
        self.password = None

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        title = QLabel("Введите мастер-пароль")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Мастер-пароль")
        layout.addWidget(self.password_input)

        button_layout = QHBoxLayout()

        self.login_button = QPushButton("Войти")
        self.login_button.clicked.connect(self.try_login)

        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        self.hint_label = QLabel("")
        self.hint_label.setStyleSheet("color: red;")
        layout.addWidget(self.hint_label)

        self.password_input.returnPressed.connect(self.try_login)
        self.encryption_key = None

    def try_login(self):
        password = self.password_input.text()

        if not password:
            self.hint_label.setText("Введите пароль")
            return

        if self.auth.login(password):
            self.password = password
            self.encryption_key = self.auth.get_encryption_key()
            self.accept()
        else:
            self.hint_label.setText("Неверный пароль")
            self.password_input.clear()
            self.password_input.setFocus()
