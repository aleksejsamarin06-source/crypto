from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QComboBox, QLineEdit, QPushButton, QFileDialog,
                               QMessageBox, QTreeWidget, QTreeWidgetItem,
                               QInputDialog, QHeaderView)

from src.core.import_export.importer import VaultImporter


class ImportDialog(QDialog):
    def __init__(self, parent=None, entry_manager=None):
        super().__init__(parent)
        self.setWindowTitle("Импорт хранилища")
        self.resize(620, 420)
        self.entry_manager = entry_manager
        self.file_path = ""
        self.private_key_path = ""
        self.preview_entries = []
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

        decrypt_layout = QHBoxLayout()
        decrypt_layout.addWidget(QLabel("Расшифровка:"))
        self.decrypt_method_combo = QComboBox()
        self.decrypt_method_combo.addItem("Пароль", "password")
        self.decrypt_method_combo.addItem("Приватный ключ (.pem)", "private_key")
        self.decrypt_method_combo.currentIndexChanged.connect(self.on_decrypt_method_changed)
        decrypt_layout.addWidget(self.decrypt_method_combo)
        layout.addLayout(decrypt_layout)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Пароль импортируемого файла, если он зашифрован")
        layout.addWidget(self.password_input)

        private_key_layout = QHBoxLayout()
        self.private_key_input = QLineEdit()
        self.private_key_input.setReadOnly(True)
        self.private_key_input.setPlaceholderText("Файл приватного ключа для расшифровки (.pem)")
        self.private_key_btn = QPushButton("Выбрать .pem")
        self.private_key_btn.clicked.connect(self.choose_private_key)
        private_key_layout.addWidget(self.private_key_input)
        private_key_layout.addWidget(self.private_key_btn)
        layout.addLayout(private_key_layout)

        self.preview_summary = QLabel("Предпросмотр не выполнен")
        layout.addWidget(self.preview_summary)

        self.preview_tree = QTreeWidget()
        self.preview_tree.setColumnCount(7)
        self.preview_tree.setHeaderLabels(["ID", "Название", "Логин", "Пароль", "URL", "Категория", "Изменено"])
        self.preview_tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.preview_tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.preview_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.preview_tree.header().setSectionResizeMode(3, QHeaderView.Stretch)
        self.preview_tree.header().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.preview_tree)

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

        self.on_decrypt_method_changed()

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

    def choose_private_key(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите приватный ключ для расшифровки",
            "",
            "PEM files (*.pem);;All files (*)"
        )
        if file_path:
            self.private_key_path = file_path
            self.private_key_input.setText(file_path)

    def on_decrypt_method_changed(self):
        use_password = self.decrypt_method_combo.currentData() == "password"
        self.password_input.setEnabled(use_password)
        self.private_key_input.setEnabled(not use_password)
        self.private_key_btn.setEnabled(not use_password)

    def preview(self):
        try:
            importer = VaultImporter(self.entry_manager)
            password, private_key = self.get_import_credentials(importer)
            result = importer.import_file(
                self.path_input.text(),
                password=password,
                private_key=private_key,
                import_format=self.format_value(),
                mode="dry-run",
                duplicate_strategy=self.duplicate_combo.currentText(),
            )
            self.show_preview_result(result)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка предпросмотра", str(e))

    def do_import(self):
        if self.mode_combo.currentText() == "dry-run":
            self.preview()
            QMessageBox.information(self, "Импорт", "Выбран режим dry-run: данные не записаны. Для импорта выберите merge или replace.")
            return

        try:
            importer = VaultImporter(self.entry_manager)
            password, private_key = self.get_import_credentials(importer)
            result = importer.import_file(
                self.path_input.text(),
                password=password,
                private_key=private_key,
                import_format=self.format_value(),
                mode=self.mode_combo.currentText(),
                duplicate_strategy=self.duplicate_combo.currentText(),
            )
            self.show_preview_result(result)
            QMessageBox.information(self, "Импорт", self.format_result(result))
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", str(e))

    def show_preview_result(self, result):
        self.preview_entries = result.get("preview_entries", result.get("preview", []))
        self.preview_summary.setText(self.format_result(result).replace("\n", " | "))
        self.reload_preview_tree(self.preview_entries)

    def reload_preview_tree(self, entries):
        self.preview_tree.clear()
        grouped = self.group_entries_by_category(entries)
        for category, category_entries in grouped.items():
            category_item = QTreeWidgetItem([f"{category} ({len(category_entries)})", "", "", "", "", category, ""])
            self.preview_tree.addTopLevelItem(category_item)
            for entry in category_entries:
                category_item.addChild(QTreeWidgetItem(self.entry_columns(entry)))
            category_item.setExpanded(True)

    def group_entries_by_category(self, entries):
        grouped = {}
        for entry in entries:
            category = entry.get("category") or "Без категории"
            grouped.setdefault(category, []).append(entry)
        return dict(sorted(grouped.items(), key=lambda item: item[0].lower()))

    def entry_columns(self, entry):
        username = entry.get("username", "")
        masked_username = username[:4] + "••••" if len(username) > 4 else username + "••••"
        url = entry.get("url", "")
        domain = url.split("://", 1)[1] if "://" in url else url
        domain = domain.split("/", 1)[0] if "/" in domain else domain
        updated_at = entry.get("updated_at", entry.get("created_at", ""))
        updated_date = updated_at.split("T")[0] if updated_at else ""
        return [
            str(entry.get("id", "")),
            entry.get("title", ""),
            masked_username,
            "••••••••",
            domain,
            entry.get("category", ""),
            updated_date,
        ]

    def get_import_credentials(self, importer):
        file_path = self.path_input.text()
        if not file_path:
            raise ValueError("Выберите файл импорта")

        with open(file_path, "r", encoding="utf-8") as file:
            text = file.read()

        import json
        try:
            data = json.loads(text)
        except Exception:
            data = None

        detected = self.format_value() or importer.detect_format(text, data)
        if detected != "encrypted_json":
            return None, None

        encryption_method = ""
        if isinstance(data, dict):
            encryption_method = data.get("encryption", {}).get("method", "")

        selected_method = self.decrypt_method_combo.currentData()
        if encryption_method == "public_key" and selected_method != "private_key":
            raise ValueError("Файл зашифрован публичным ключом. Выберите приватный .pem ключ для расшифровки")
        if encryption_method == "password" and selected_method != "password":
            raise ValueError("Файл зашифрован паролем. Выберите расшифровку паролем")

        if selected_method == "private_key":
            if not self.private_key_path:
                raise ValueError("Укажите файл приватного ключа для расшифровки")
            with open(self.private_key_path, "rb") as key_file:
                return None, key_file.read()

        password = self.password_input.text() or None
        if password:
            return password, None

        password, ok = QInputDialog.getText(
            self,
            "Пароль импорта",
            "Введите пароль импортируемого файла:",
            QLineEdit.Password
        )
        if not ok or not password:
            raise ValueError("Укажите пароль импортируемого файла")
        self.password_input.setText(password)
        return password, None

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
