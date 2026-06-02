from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QComboBox, QLineEdit, QPushButton, QFileDialog,
                               QMessageBox, QTextEdit, QInputDialog)

from src.core.import_export.importer import VaultImporter


class ImportDialog(QDialog):
    def __init__(self, parent=None, entry_manager=None):
        super().__init__(parent)
        self.setWindowTitle("Импорт хранилища")
        self.resize(620, 420)
        self.entry_manager = entry_manager
        self.file_path = ""
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        file_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        browse_btn = QPushButton("Обзор")
        browse_btn.clicked.connect(self.browse)
        file_layout.addWidget(self.path_input)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)

        options = QHBoxLayout()
        options.addWidget(QLabel("Формат:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["auto", "encrypted_json", "csv", "bitwarden_json", "lastpass_csv"])
        options.addWidget(self.format_combo)

        options.addWidget(QLabel("Режим:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["merge", "replace", "dry-run"])
        options.addWidget(self.mode_combo)

        options.addWidget(QLabel("Дубликаты:"))
        self.duplicate_combo = QComboBox()
        self.duplicate_combo.addItems(["create", "skip", "update"])
        options.addWidget(self.duplicate_combo)
        layout.addLayout(options)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Пароль импортируемого файла, если он зашифрован")
        layout.addWidget(self.password_input)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        layout.addWidget(self.preview_text)

        buttons = QHBoxLayout()
        preview_btn = QPushButton("Предпросмотр")
        preview_btn.clicked.connect(self.preview)
        import_btn = QPushButton("Импорт")
        import_btn.clicked.connect(self.do_import)
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.reject)
        buttons.addWidget(preview_btn)
        buttons.addWidget(import_btn)
        buttons.addStretch()
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

    def browse(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл импорта",
            "",
            "Import files (*.json *.csv);;All files (*)"
        )
        if file_path:
            self.file_path = file_path
            self.path_input.setText(file_path)

    def preview(self):
        try:
            importer = VaultImporter(self.entry_manager)
            password = self.get_import_password(importer)
            result = importer.import_file(
                self.path_input.text(),
                password=password,
                import_format=self.format_value(),
                mode="dry-run",
                duplicate_strategy=self.duplicate_combo.currentText(),
            )
            self.preview_text.setPlainText(self.format_result(result))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка предпросмотра", str(e))

    def do_import(self):
        if self.mode_combo.currentText() == "dry-run":
            self.preview()
            QMessageBox.information(self, "Импорт", "Выбран режим dry-run: данные не записаны. Для импорта выберите merge или replace.")
            return

        try:
            importer = VaultImporter(self.entry_manager)
            password = self.get_import_password(importer)
            result = importer.import_file(
                self.path_input.text(),
                password=password,
                import_format=self.format_value(),
                mode=self.mode_combo.currentText(),
                duplicate_strategy=self.duplicate_combo.currentText(),
            )
            self.preview_text.setPlainText(self.format_result(result))
            QMessageBox.information(self, "Импорт", self.format_result(result))
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", str(e))

    def get_import_password(self, importer):
        password = self.password_input.text() or None
        if password:
            return password

        file_path = self.path_input.text()
        if not file_path:
            raise ValueError("Выберите файл импорта")

        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()

        detected = self.format_value() or importer.detect_format(text)
        if detected != "encrypted_json":
            return None

        password, ok = QInputDialog.getText(
            self,
            "Пароль импорта",
            "Введите пароль импортируемого файла:",
            QLineEdit.Password
        )
        if not ok or not password:
            raise ValueError("Укажите пароль импортируемого файла")
        self.password_input.setText(password)
        return password

    def format_result(self, result):
        if result.get("mode") == "dry-run":
            return (
                "Предпросмотр импорта\n"
                f"Всего записей: {result.get('total', 0)}\n"
                f"Новых: {result.get('new', 0)}\n"
                f"Дубликатов: {result.get('duplicates', 0)}\n"
                f"Действие с дубликатами: {result.get('duplicate_strategy', '')}"
            )

        return (
            "Импорт завершен\n"
            f"Всего обработано: {result.get('total', 0)}\n"
            f"Добавлено: {result.get('imported', 0)}\n"
            f"Обновлено: {result.get('updated', 0)}\n"
            f"Пропущено: {result.get('skipped', 0)}"
        )

    def format_value(self):
        value = self.format_combo.currentText()
        return None if value == "auto" else value
