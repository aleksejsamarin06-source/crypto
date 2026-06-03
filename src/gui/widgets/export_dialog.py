from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QComboBox, QCheckBox, QTreeWidget, QTreeWidgetItem,
                               QLineEdit, QPushButton, QFileDialog, QMessageBox,
                               QInputDialog, QGroupBox, QHeaderView)
from PySide6.QtCore import Qt
import os

from src.core.import_export.exporter import VaultExporter


class ExportDialog(QDialog):
    def __init__(self, parent=None, entry_manager=None, master_password=None, source_db_path=None):
        super().__init__(parent)
        self.setWindowTitle("Экспорт хранилища")
        self.resize(620, 520)
        self.entry_manager = entry_manager
        self.master_password = master_password
        self.source_db_path = source_db_path
        self.public_key_path = None
        self.entries = entry_manager.get_all_entries() if entry_manager else []
        self._updating_checks = False
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        if self.source_db_path:
            layout.addWidget(QLabel(f"Источник: {os.path.basename(self.source_db_path)}"))

        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Формат:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["encrypted_json", "csv", "bitwarden_json"])
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)

        encryption_group = QGroupBox("Шифрование")
        encryption_layout = QVBoxLayout(encryption_group)

        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("Способ:"))
        self.encryption_method = QComboBox()
        self.encryption_method.addItem("Пароль", "password")
        self.encryption_method.addItem("Публичный ключ получателя", "public_key")
        self.encryption_method.currentIndexChanged.connect(self.on_encryption_method_changed)
        method_layout.addWidget(self.encryption_method)
        encryption_layout.addLayout(method_layout)

        self.export_password = QLineEdit()
        self.export_password.setEchoMode(QLineEdit.Password)
        self.export_password.setPlaceholderText("Пароль для экспортного файла")

        public_key_layout = QHBoxLayout()
        self.public_key_input = QLineEdit()
        self.public_key_input.setReadOnly(True)
        self.public_key_input.setPlaceholderText("Файл публичного ключа получателя (.pem)")
        self.public_key_btn = QPushButton("Выбрать .pem")
        self.public_key_btn.clicked.connect(self.choose_public_key)
        public_key_layout.addWidget(self.public_key_input)
        public_key_layout.addWidget(self.public_key_btn)

        self.key_bits = QComboBox()
        self.key_bits.addItems(["256", "128"])
        self.allow_plaintext = QCheckBox("Разрешить plaintext для CSV/Bitwarden")
        self.compress = QCheckBox("Сжать GZIP перед шифрованием")
        encryption_layout.addWidget(self.export_password)
        encryption_layout.addLayout(public_key_layout)
        encryption_layout.addWidget(QLabel("Стойкость ключа:"))
        encryption_layout.addWidget(self.key_bits)
        encryption_layout.addWidget(self.compress)
        encryption_layout.addWidget(self.allow_plaintext)
        layout.addWidget(encryption_group)

        field_group = QGroupBox("Поля")
        field_layout = QVBoxLayout(field_group)
        self.field_checks = {}
        for field in ["title", "username", "password", "url", "notes", "category"]:
            checkbox = QCheckBox(field)
            checkbox.setChecked(True)
            self.field_checks[field] = checkbox
            field_layout.addWidget(checkbox)
        layout.addWidget(field_group)

        layout.addWidget(QLabel("Записи:"))
        self.entry_tree = QTreeWidget()
        self.entry_tree.setColumnCount(7)
        self.entry_tree.setHeaderLabels(["ID", "Название", "Логин", "Пароль", "URL", "Категория", "Изменено"])
        self.entry_tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.entry_tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.entry_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.entry_tree.header().setSectionResizeMode(3, QHeaderView.Stretch)
        self.entry_tree.header().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.entry_tree.itemChanged.connect(self.on_entry_check_changed)
        self.reload_entry_tree()
        layout.addWidget(self.entry_tree)

        buttons = QHBoxLayout()
        self.preview_btn = QPushButton("Предпросмотр")
        self.preview_btn.clicked.connect(self.preview)
        self.export_btn = QPushButton("Экспорт")
        self.export_btn.clicked.connect(self.export)
        buttons.addWidget(self.preview_btn)
        buttons.addWidget(self.export_btn)
        buttons.addStretch()
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.reject)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

        self.on_format_changed(self.format_combo.currentText())
        self.on_encryption_method_changed()

    def choose_public_key(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите публичный ключ получателя",
            "",
            "PEM files (*.pem);;All files (*)"
        )
        if file_path:
            self.public_key_path = file_path
            self.public_key_input.setText(file_path)

    def reload_entry_tree(self):
        self._updating_checks = True
        self.entry_tree.clear()
        grouped = self.group_entries_by_category(self.entries)
        for category, entries in grouped.items():
            category_item = QTreeWidgetItem([f"{category} ({len(entries)})", "", "", "", "", category, ""])
            category_item.setData(0, Qt.UserRole, {"type": "category"})
            category_item.setFlags(category_item.flags() | Qt.ItemIsUserCheckable)
            category_item.setCheckState(0, Qt.Checked)
            self.entry_tree.addTopLevelItem(category_item)

            for entry in entries:
                item = QTreeWidgetItem(self.entry_columns(entry))
                item.setData(0, Qt.UserRole, {"type": "entry", "id": entry.get("id")})
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(0, Qt.Checked)
                category_item.addChild(item)

            category_item.setExpanded(True)
        self._updating_checks = False

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

    def on_entry_check_changed(self, item, column):
        if self._updating_checks or column != 0:
            return
        data = item.data(0, Qt.UserRole) or {}
        self._updating_checks = True
        if data.get("type") == "category":
            state = item.checkState(0)
            for index in range(item.childCount()):
                item.child(index).setCheckState(0, state)
        elif data.get("type") == "entry" and item.parent():
            parent = item.parent()
            checked = 0
            partial = 0
            for index in range(parent.childCount()):
                state = parent.child(index).checkState(0)
                if state == Qt.Checked:
                    checked += 1
                elif state == Qt.PartiallyChecked:
                    partial += 1
            if checked == parent.childCount():
                parent.setCheckState(0, Qt.Checked)
            elif checked == 0 and partial == 0:
                parent.setCheckState(0, Qt.Unchecked)
            else:
                parent.setCheckState(0, Qt.PartiallyChecked)
        self._updating_checks = False

    def update_export_controls(self):
        has_source = self.entry_manager is not None
        self.preview_btn.setEnabled(has_source)
        self.export_btn.setEnabled(has_source)

    def on_format_changed(self, export_format):
        plaintext_allowed = export_format in ("csv", "bitwarden_json")
        self.allow_plaintext.setEnabled(plaintext_allowed)
        if not plaintext_allowed:
            self.allow_plaintext.setChecked(False)

    def on_encryption_method_changed(self):
        method = self.encryption_method.currentData()
        use_password = method == "password"
        self.export_password.setEnabled(use_password)
        self.public_key_input.setEnabled(not use_password)
        self.public_key_btn.setEnabled(not use_password)

    def selected_entry_ids(self):
        ids = []
        for category_index in range(self.entry_tree.topLevelItemCount()):
            category_item = self.entry_tree.topLevelItem(category_index)
            for child_index in range(category_item.childCount()):
                item = category_item.child(child_index)
                data = item.data(0, Qt.UserRole) or {}
                if item.checkState(0) == Qt.Checked and data.get("type") == "entry":
                    ids.append(data.get("id"))
        return ids

    def selected_fields(self):
        return [field for field, checkbox in self.field_checks.items() if checkbox.isChecked()]

    def preview(self):
        count = len(self.selected_entry_ids())
        fields = ", ".join(self.selected_fields())
        QMessageBox.information(self, "Предпросмотр", f"К экспорту выбрано записей: {count}\nПоля: {fields}")

    def export(self):
        if not self.entry_manager:
            QMessageBox.warning(self, "Ошибка", "Хранилище не открыто")
            return

        if not self.selected_entry_ids():
            QMessageBox.warning(self, "Ошибка", "Выберите хотя бы одну запись для экспорта")
            return

        export_format = self.format_combo.currentText()
        encryption_method = self.encryption_method.currentData()
        password = self.export_password.text() if encryption_method == "password" else None
        public_key = None
        allow_plain = self.allow_plaintext.isChecked() and export_format in ("csv", "bitwarden_json")

        if encryption_method == "password" and not password and not allow_plain:
            QMessageBox.warning(self, "Ошибка", "Укажите пароль экспорта или разрешите plaintext для CSV/Bitwarden")
            return

        if encryption_method == "public_key" and not allow_plain:
            if not self.public_key_path:
                QMessageBox.warning(self, "Ошибка", "Укажите файл публичного ключа получателя")
                return
            try:
                with open(self.public_key_path, "rb") as key_file:
                    public_key = key_file.read()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка ключа", f"Не удалось прочитать публичный ключ:\n{e}")
                return

        if allow_plain:
            password = None
            public_key = None

        if not password and not public_key and not allow_plain:
            QMessageBox.warning(self, "Ошибка", "Укажите пароль экспорта или публичный ключ получателя")
            return

        confirm, ok = QInputDialog.getText(self, "Подтверждение", "Мастер-пароль:", QLineEdit.Password)
        if not ok or confirm != self.master_password:
            QMessageBox.warning(self, "Ошибка", "Неверный мастер-пароль")
            return

        default_name = "cryptosafe_export.csv" if export_format == "csv" and allow_plain else "cryptosafe_export.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить экспорт",
            default_name,
            "JSON files (*.json);;CSV files (*.csv);;All files (*)"
        )
        if not file_path:
            return

        try:
            exporter = VaultExporter(self.entry_manager)
            data = exporter.export_vault(
                entry_ids=self.selected_entry_ids(),
                password=password,
                public_key=public_key,
                export_format=export_format,
                include_fields=self.selected_fields(),
                key_bits=int(self.key_bits.currentText()),
                compress=self.compress.isChecked(),
                allow_plaintext=allow_plain,
            )
            exporter.save_export(file_path, data)
            QMessageBox.information(self, "Экспорт", f"Экспорт сохранен:\n{file_path}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", str(e))
