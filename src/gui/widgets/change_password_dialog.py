import json

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
)

from src.core.crypto.key_derivation import KeyDerivation
from src.core.vault.encryption_service import AESGCMEncryption
from src.database.db import Database


class ChangePasswordDialog(QDialog):
    MIN_PASSWORD_LENGTH = 8

    def __init__(self, parent=None, db_path=None, old_key=None):
        super().__init__(parent)
        self.setWindowTitle("Смена мастер-пароля")
        self.resize(480, 420)
        self.setModal(True)

        self.db_path = db_path
        self.old_key = old_key
        self.key_derivation = KeyDerivation()
        self.crypto = AESGCMEncryption()

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Смена мастер-пароля")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        layout.addWidget(QLabel("Текущий пароль:"))
        self.old_password = QLineEdit()
        self.old_password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.old_password)

        layout.addWidget(QLabel("Новый пароль:"))
        self.new_password = QLineEdit()
        self.new_password.setEchoMode(QLineEdit.Password)
        self.new_password.setPlaceholderText(f"Не менее {self.MIN_PASSWORD_LENGTH} символов")
        self.new_password.textChanged.connect(self.update_password_requirements)
        layout.addWidget(self.new_password)

        layout.addWidget(QLabel("Подтверждение:"))
        self.confirm_password = QLineEdit()
        self.confirm_password.setEchoMode(QLineEdit.Password)
        self.confirm_password.textChanged.connect(self.update_password_requirements)
        layout.addWidget(self.confirm_password)

        self.strength_label = QLabel()
        self.strength_label.setWordWrap(True)
        layout.addWidget(self.strength_label)

        self.requirements_label = QLabel()
        self.requirements_label.setWordWrap(True)
        layout.addWidget(self.requirements_label)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        button_layout = QHBoxLayout()
        self.change_button = QPushButton("Сменить пароль")
        self.change_button.clicked.connect(self.try_change)
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.change_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.hint_label = QLabel("")
        self.hint_label.setStyleSheet("color: red;")
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

        self.update_password_requirements()

    def get_password_requirements(self, password):
        requirements = [
            (len(password) >= self.MIN_PASSWORD_LENGTH, f"минимум {self.MIN_PASSWORD_LENGTH} символов"),
            (any(char.isupper() for char in password), "хотя бы одна заглавная буква"),
            (any(char.isdigit() for char in password), "хотя бы одна цифра"),
        ]
        recommendations = [
            (any(not char.isalnum() for char in password), "спецсимвол для большей стойкости"),
        ]
        return requirements, recommendations

    def get_password_strength(self, password):
        score = 0
        if len(password) >= self.MIN_PASSWORD_LENGTH:
            score += 1
        if len(password) >= 12:
            score += 1
        if any(char.isupper() for char in password):
            score += 1
        if any(char.islower() for char in password):
            score += 1
        if any(char.isdigit() for char in password):
            score += 1
        if any(not char.isalnum() for char in password):
            score += 1

        if score <= 2:
            return "слабая", "#b00020"
        if score <= 4:
            return "средняя", "#b36b00"
        return "надёжная", "#1b7f35"

    def update_password_requirements(self):
        password = self.new_password.text()
        confirm = self.confirm_password.text()
        requirements, recommendations = self.get_password_requirements(password)

        missing = [text for passed, text in requirements if not passed]
        recommended = [text for passed, text in recommendations if not passed]
        strength, color = self.get_password_strength(password)

        self.strength_label.setText(f"Надёжность нового пароля: {strength}")
        self.strength_label.setStyleSheet(f"color: {color}; font-weight: bold;")

        messages = []
        if missing:
            messages.append("Не выполнено: " + "; ".join(missing))
        if recommended:
            messages.append("Рекомендация: " + "; ".join(recommended))
        if password and confirm and password != confirm:
            messages.append("Новые пароли не совпадают")
        if not messages:
            messages.append("Все обязательные требования выполнены")

        self.requirements_label.setText("\n".join(messages))

    def validate_new_password(self, password):
        requirements, _ = self.get_password_requirements(password)
        return [text for passed, text in requirements if not passed]

    def try_change(self):
        old = self.old_password.text()
        new = self.new_password.text()
        confirm = self.confirm_password.text()

        if not old or not new or not confirm:
            self.hint_label.setText("Заполните все поля")
            return

        missing = self.validate_new_password(new)
        if missing:
            self.hint_label.setText("Новый пароль не соответствует требованиям:\n- " + "\n- ".join(missing))
            return

        if new != confirm:
            self.hint_label.setText("Новые пароли не совпадают")
            return

        db = Database(self.db_path)
        db.connect()
        cursor = db.conn.cursor()

        cursor.execute(
            "SELECT key_data FROM key_store WHERE key_type = 'auth_hash' ORDER BY version DESC LIMIT 1"
        )
        result = cursor.fetchone()

        if not result:
            self.hint_label.setText("Ошибка базы данных: хеш не найден")
            db.close()
            return

        if not self.key_derivation.verify_password(old, result[0]):
            self.hint_label.setText("Неверный текущий пароль")
            db.close()
            return

        db.close()

        self.change_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)

        QTimer.singleShot(100, self.do_reencrypt)

    def do_reencrypt(self):
        try:
            db = Database(self.db_path)
            db.connect()
            cursor = db.conn.cursor()

            cursor.execute("SELECT id, encrypted_data FROM vault_entries")
            rows = cursor.fetchall()
            total = len(rows)

            new_password = self.new_password.text()
            new_auth = self.key_derivation.create_auth_hash(new_password)
            new_key, new_salt, new_params = self.key_derivation.derive_encryption_key(new_password)

            if total > 0:
                for index, (entry_id, old_encrypted_blob) in enumerate(rows):
                    if old_encrypted_blob:
                        decrypted_data = self.crypto.decrypt_entry(old_encrypted_blob, self.old_key)
                        new_encrypted_blob = self.crypto.encrypt_entry(decrypted_data, new_key)
                        cursor.execute(
                            "UPDATE vault_entries SET encrypted_data=? WHERE id=?",
                            (new_encrypted_blob, entry_id),
                        )
                    progress = int((index + 1) / total * 100)
                    self.progress.setValue(progress)

            cursor.execute(
                "UPDATE key_store SET key_data=? WHERE key_type='auth_hash'",
                (new_auth["hash"],),
            )
            cursor.execute(
                "UPDATE key_store SET key_data=? WHERE key_type='enc_salt'",
                (new_salt.hex(),),
            )
            cursor.execute(
                "UPDATE key_store SET key_data=? WHERE key_type='argon2_params'",
                (json.dumps(new_auth["params"]),),
            )
            cursor.execute(
                "UPDATE key_store SET key_data=? WHERE key_type='pbkdf2_params'",
                (json.dumps(new_params),),
            )

            db.conn.commit()
            db.close()

            from src.core.events import event_system

            event_system.publish("password_changed", {"user_id": "user"})

            QMessageBox.information(self, "Готово", "Пароль успешно изменён")
            self.accept()

        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сменить пароль: {exc}")
            self.reject()
