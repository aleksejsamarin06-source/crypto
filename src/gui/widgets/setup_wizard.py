from PySide6.QtWidgets import (QWizard, QWizardPage, QVBoxLayout, QLabel,
                               QLineEdit, QFileDialog, QPushButton, QHBoxLayout,
                               QMessageBox, QCheckBox)
from PySide6.QtCore import Qt
import os


class SetupWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Первый запуск CryptoSafe")
        self.resize(550, 400)

        self.setWizardStyle(QWizard.ModernStyle)

        self.db_path = ""
        self.master_password = ""

        self.addPage(MasterPasswordPage(self))
        self.addPage(DatabaseLocationPage(self))

        self.setButtonText(QWizard.NextButton, "Далее")
        self.setButtonText(QWizard.BackButton, "Назад")
        self.setButtonText(QWizard.FinishButton, "Создать")
        self.setButtonText(QWizard.CancelButton, "Отмена")


class MasterPasswordPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Создание мастер-пароля")
        self.setSubTitle("Придумайте пароль для доступа к хранилищу")

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        layout.addWidget(QLabel("Мастер-пароль:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Не менее 6 символов")
        layout.addWidget(self.password_input)

        layout.addWidget(QLabel("Подтверждение:"))
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setPlaceholderText("Введите пароль еще раз")
        layout.addWidget(self.confirm_input)

        self.show_password = QCheckBox("Показать пароль")
        self.show_password.stateChanged.connect(self.toggle_password_visibility)
        layout.addWidget(self.show_password)

        layout.addStretch()

        self.registerField("master_password*", self.password_input)
        self.registerField("confirm_password*", self.confirm_input)

    def toggle_password_visibility(self, state):
        if state == Qt.Checked:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.confirm_input.setEchoMode(QLineEdit.Normal)
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.confirm_input.setEchoMode(QLineEdit.Password)

    def validatePage(self):
        password = self.password_input.text()
        confirm = self.confirm_input.text()

        if len(password) < 6:
            QMessageBox.warning(self, "Ошибка", "Пароль должен быть не менее 6 символов")
            return False

        if password != confirm:
            QMessageBox.warning(self, "Ошибка", "Пароли не совпадают")
            return False

        self.wizard().master_password = password
        return True


class DatabaseLocationPage(QWizardPage):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Расположение базы данных")
        self.setSubTitle("Выберите место для хранения данных")

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        layout.addWidget(QLabel("Путь к файлу базы данных:"))

        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setText(os.path.expanduser("~/cryptosafe.db"))

        browse_button = QPushButton("Обзор")
        browse_button.setFixedWidth(80)
        browse_button.clicked.connect(self.browse_folder)

        path_layout.addWidget(self.path_input)
        path_layout.addWidget(browse_button)
        layout.addLayout(path_layout)

        layout.addStretch()

        self.registerField("db_path*", self.path_input)

    def browse_folder(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Выберите место для базы данных",
            os.path.dirname(self.path_input.text()),
            "Database files (*.db)"
        )
        if file_path:
            if not file_path.endswith('.db'):
                file_path += '.db'
            self.path_input.setText(file_path)

    def validatePage(self):
        path = self.path_input.text()
        if not path:
            QMessageBox.warning(self, "Ошибка", "Укажите путь для базы данных")
            return False

        folder = os.path.dirname(path)
        if folder and not os.path.exists(folder):
            try:
                os.makedirs(folder)
            except:
                QMessageBox.warning(self, "Ошибка", "Не удалось создать папку")
                return False

        self.wizard().db_path = path
        return True

    def isFinalPage(self):
        return True