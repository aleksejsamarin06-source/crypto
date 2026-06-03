import os

from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)


class SetupWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Первый запуск CryptoSafe")
        self.resize(550, 430)

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
    MIN_PASSWORD_LENGTH = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Создание мастер-пароля")
        self.setSubTitle("Придумайте пароль для доступа к хранилищу")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Мастер-пароль:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText(f"Не менее {self.MIN_PASSWORD_LENGTH} символов")
        self.password_input.textChanged.connect(self.update_password_requirements)
        layout.addWidget(self.password_input)

        layout.addWidget(QLabel("Подтверждение:"))
        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setPlaceholderText("Введите пароль ещё раз")
        self.confirm_input.textChanged.connect(self.update_password_requirements)
        layout.addWidget(self.confirm_input)

        self.show_password = QCheckBox("Показать пароль")
        self.show_password.toggled.connect(self.toggle_password_visibility)
        layout.addWidget(self.show_password)

        self.strength_label = QLabel()
        self.strength_label.setWordWrap(True)
        layout.addWidget(self.strength_label)

        self.requirements_label = QLabel()
        self.requirements_label.setWordWrap(True)
        layout.addWidget(self.requirements_label)

        layout.addStretch()

        self.registerField("master_password*", self.password_input)
        self.registerField("confirm_password*", self.confirm_input)
        self.update_password_requirements()

    def toggle_password_visibility(self, checked):
        echo_mode = QLineEdit.Normal if checked else QLineEdit.Password
        self.password_input.setEchoMode(echo_mode)
        self.confirm_input.setEchoMode(echo_mode)

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
        password = self.password_input.text()
        confirm = self.confirm_input.text()
        requirements, recommendations = self.get_password_requirements(password)

        missing = [text for passed, text in requirements if not passed]
        recommended = [text for passed, text in recommendations if not passed]

        strength, color = self.get_password_strength(password)
        self.strength_label.setText(f"Надёжность пароля: {strength}")
        self.strength_label.setStyleSheet(f"color: {color}; font-weight: bold;")

        messages = []
        if missing:
            messages.append("Не выполнено: " + "; ".join(missing))
        if recommended:
            messages.append("Рекомендация: " + "; ".join(recommended))
        if password and confirm and password != confirm:
            messages.append("Пароли не совпадают")
        if not messages:
            messages.append("Все обязательные требования выполнены")

        self.requirements_label.setText("\n".join(messages))

    def validatePage(self):
        password = self.password_input.text()
        confirm = self.confirm_input.text()
        requirements, _ = self.get_password_requirements(password)
        missing = [text for passed, text in requirements if not passed]

        if missing:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Пароль не соответствует требованиям:\n- " + "\n- ".join(missing)
            )
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
        self.path_input.setText(os.path.expanduser("~/CryptoSafe.db"))
        self.path_input.setPlaceholderText("Можно изменить имя файла, например work_passwords.db")

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
            self,
            "Выберите место для базы данных",
            os.path.dirname(self.path_input.text()),
            "Database files (*.db)",
        )
        if file_path:
            if not file_path.endswith(".db"):
                file_path += ".db"
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
            except OSError:
                QMessageBox.warning(self, "Ошибка", "Не удалось создать папку")
                return False

        self.wizard().db_path = path
        return True

    def isFinalPage(self):
        return True
