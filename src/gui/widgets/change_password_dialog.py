from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit,
                               QPushButton, QMessageBox, QHBoxLayout, QProgressBar)
from PySide6.QtCore import Qt, QTimer
from src.core.crypto.key_derivation import KeyDerivation
from src.core.vault.encryption_service import AESGCMEncryption
from src.database.db import Database
import json


class ChangePasswordDialog(QDialog):
    def __init__(self, parent=None, db_path=None, old_key=None):
        super().__init__(parent)
        self.setWindowTitle("Смена мастер-пароля")
        self.resize(450, 300)
        self.setModal(True)

        self.db_path = db_path
        self.old_key = old_key
        self.key_derivation = KeyDerivation()
        self.crypto = AESGCMEncryption()

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

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
        layout.addWidget(self.new_password)

        layout.addWidget(QLabel("Подтверждение:"))
        self.confirm_password = QLineEdit()
        self.confirm_password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.confirm_password)

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
        layout.addWidget(self.hint_label)

    def try_change(self):
        old = self.old_password.text()
        new = self.new_password.text()
        confirm = self.confirm_password.text()

        if not old or not new or not confirm:
            self.hint_label.setText("Заполните все поля")
            return

        if len(new) < 6:
            self.hint_label.setText("Новый пароль должен быть не менее 6 символов")
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
            self.hint_label.setText("Ошибка базы данных: хэш не найден")
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

            # Получаем все записи (encrypted_data вместо encrypted_password)
            cursor.execute("SELECT id, encrypted_data FROM vault_entries")
            rows = cursor.fetchall()
            total = len(rows)

            new_password = self.new_password.text()
            new_auth = self.key_derivation.create_auth_hash(new_password)
            new_key, new_salt, new_params = self.key_derivation.derive_encryption_key(new_password)

            if total > 0:
                for i, (entry_id, old_encrypted_blob) in enumerate(rows):
                    if old_encrypted_blob:
                        # Расшифровываем старым ключом
                        decrypted_data = self.crypto.decrypt_entry(old_encrypted_blob, self.old_key)
                        # Шифруем новым ключом
                        new_encrypted_blob = self.crypto.encrypt_entry(decrypted_data, new_key)
                        cursor.execute(
                            "UPDATE vault_entries SET encrypted_data=? WHERE id=?",
                            (new_encrypted_blob, entry_id)
                        )
                    progress = int((i + 1) / total * 100)
                    self.progress.setValue(progress)

            cursor.execute(
                "UPDATE key_store SET key_data=? WHERE key_type='auth_hash'",
                (new_auth['hash'],)
            )
            cursor.execute(
                "UPDATE key_store SET key_data=? WHERE key_type='enc_salt'",
                (new_salt.hex(),)
            )
            cursor.execute(
                "UPDATE key_store SET key_data=? WHERE key_type='argon2_params'",
                (json.dumps(new_auth['params']),)
            )
            cursor.execute(
                "UPDATE key_store SET key_data=? WHERE key_type='pbkdf2_params'",
                (json.dumps(new_params),)
            )

            db.conn.commit()
            db.close()

            QMessageBox.information(self, "Готово", "Пароль успешно изменён")
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сменить пароль: {e}")
            self.reject()