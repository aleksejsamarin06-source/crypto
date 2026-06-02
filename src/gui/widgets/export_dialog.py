from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QComboBox, QCheckBox, QListWidget, QListWidgetItem,
                               QLineEdit, QPushButton, QFileDialog, QMessageBox,
                               QInputDialog, QGroupBox)
from PySide6.QtCore import Qt

from src.core.import_export.exporter import VaultExporter


class ExportDialog(QDialog):
    def __init__(self, parent=None, entry_manager=None, master_password=None):
        super().__init__(parent)
        self.setWindowTitle("Экспорт хранилища")
        self.resize(620, 520)
        self.entry_manager = entry_manager
        self.master_password = master_password
        self.entries = entry_manager.get_all_entries() if entry_manager else []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Формат:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["encrypted_json", "csv", "bitwarden_json"])
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)

        encryption_group = QGroupBox("Шифрование")
        encryption_layout = QVBoxLayout(encryption_group)
        self.export_password = QLineEdit()
        self.export_password.setEchoMode(QLineEdit.Password)
        self.export_password.setPlaceholderText("Пароль для экспортного файла")
        self.key_bits = QComboBox()
        self.key_bits.addItems(["256", "128"])
        self.allow_plaintext = QCheckBox("Разрешить plaintext для CSV/Bitwarden")
        self.compress = QCheckBox("Сжать GZIP перед шифрованием")
        encryption_layout.addWidget(self.export_password)
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
        self.entry_list = QListWidget()
        for entry in self.entries:
            item = QListWidgetItem(f"{entry.get('id')}: {entry.get('title', '')}")
            item.setData(Qt.UserRole, entry.get("id"))
            item.setCheckState(Qt.Checked)
            self.entry_list.addItem(item)
        layout.addWidget(self.entry_list)

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

    def on_format_changed(self, export_format):
        plaintext_allowed = export_format in ("csv", "bitwarden_json")
        self.allow_plaintext.setEnabled(plaintext_allowed)
        if not plaintext_allowed:
            self.allow_plaintext.setChecked(False)

    def selected_entry_ids(self):
        ids = []
        for row in range(self.entry_list.count()):
            item = self.entry_list.item(row)
            if item.checkState() == Qt.Checked:
                ids.append(item.data(Qt.UserRole))
        return ids

    def selected_fields(self):
        return [field for field, checkbox in self.field_checks.items() if checkbox.isChecked()]

    def preview(self):
        count = len(self.selected_entry_ids())
        fields = ", ".join(self.selected_fields())
        QMessageBox.information(self, "Предпросмотр", f"Записей: {count}\nПоля: {fields}")

    def export(self):
        if not self.entry_manager:
            QMessageBox.warning(self, "Ошибка", "Хранилище не открыто")
            return

        export_format = self.format_combo.currentText()
        password = self.export_password.text()
        allow_plain = self.allow_plaintext.isChecked() and export_format in ("csv", "bitwarden_json")
        if not password and not allow_plain:
            QMessageBox.warning(self, "Ошибка", "Укажите пароль экспорта или разрешите plaintext для CSV/Bitwarden")
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
                password=password or None,
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
