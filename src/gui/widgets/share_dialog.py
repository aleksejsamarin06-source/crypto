import json

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QSpinBox, QCheckBox, QPushButton,
                               QFileDialog, QMessageBox, QTextEdit)

from src.core.import_export.sharing_service import SharingService
from src.core.import_export.key_exchange import QRCodeService


class ShareDialog(QDialog):
    def __init__(self, parent=None, entry_manager=None, entry_id=None):
        super().__init__(parent)
        self.setWindowTitle("Поделиться записью")
        self.resize(620, 480)
        self.entry_manager = entry_manager
        self.entry_id = entry_id
        self.package = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"ID записи: {self.entry_id}"))

        self.recipient_input = QLineEdit()
        self.recipient_input.setPlaceholderText("Получатель")
        layout.addWidget(self.recipient_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Пароль для shared package")
        layout.addWidget(self.password_input)

        options = QHBoxLayout()
        self.edit_checkbox = QCheckBox("Можно редактировать")
        self.exclude_notes = QCheckBox("Исключить заметки")
        self.expiration = QSpinBox()
        self.expiration.setRange(1, 30)
        self.expiration.setValue(7)
        options.addWidget(self.edit_checkbox)
        options.addWidget(self.exclude_notes)
        options.addWidget(QLabel("Дней:"))
        options.addWidget(self.expiration)
        layout.addLayout(options)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        buttons = QHBoxLayout()
        create_btn = QPushButton("Создать пакет")
        create_btn.clicked.connect(self.create_package)
        save_btn = QPushButton("Сохранить файл")
        save_btn.clicked.connect(self.save_package)
        qr_btn = QPushButton("QR payload")
        qr_btn.clicked.connect(self.show_qr_payload)
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.reject)
        buttons.addWidget(create_btn)
        buttons.addWidget(save_btn)
        buttons.addWidget(qr_btn)
        buttons.addStretch()
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

    def create_package(self):
        try:
            service = SharingService(self.entry_manager)
            result = service.share_entry(
                self.entry_id,
                self.recipient_input.text() or "recipient",
                password=self.password_input.text() or None,
                permissions={
                    "read": True,
                    "edit": self.edit_checkbox.isChecked(),
                    "exclude_notes": self.exclude_notes.isChecked(),
                },
                expires_in_days=self.expiration.value(),
            )
            self.package = result["package"]
            self.output.setPlainText(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def save_package(self):
        if not self.package:
            self.create_package()
        if not self.package:
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить shared package", "shared_entry.json", "JSON files (*.json)")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(self.package, file, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "Готово", f"Пакет сохранен:\n{file_path}")

    def show_qr_payload(self):
        if not self.package:
            self.create_package()
        if not self.package:
            return
        qr = QRCodeService()
        payload = qr.build_payload("encrypted_entry", self.package)
        chunks = qr.generate_qr_chunks(payload)
        self.output.setPlainText(json.dumps(chunks, ensure_ascii=False, indent=2))
