import json

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QSpinBox, QCheckBox, QPushButton,
                               QFileDialog, QMessageBox, QTextEdit)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPixmap

from src.core.import_export.sharing_service import SharingService
from src.core.import_export.key_exchange import QRCodeService


class QRCodeDialog(QDialog):
    def __init__(self, parent=None, chunks=None):
        super().__init__(parent)
        self.setWindowTitle("QR код")
        self.resize(420, 500)
        self.chunks = chunks or []
        self.current_index = 0
        self.setup_ui()
        self.show_current_chunk()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.info_label = QLabel("")
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label)

        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.qr_label)

        buttons = QHBoxLayout()
        self.prev_btn = QPushButton("Назад")
        self.prev_btn.clicked.connect(self.previous_chunk)
        self.next_btn = QPushButton("Вперёд")
        self.next_btn.clicked.connect(self.next_chunk)
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(self.prev_btn)
        buttons.addWidget(self.next_btn)
        buttons.addStretch()
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

    def show_current_chunk(self):
        if not self.chunks:
            self.info_label.setText("Нет данных для QR")
            self.qr_label.clear()
            return

        chunk = self.chunks[self.current_index]
        total = chunk.get("total", len(self.chunks))
        number = chunk.get("chunk", self.current_index + 1)
        self.info_label.setText(f"QR часть {number} из {total}")
        self.qr_label.setPixmap(self.build_qr_pixmap(chunk))
        self.prev_btn.setEnabled(self.current_index > 0)
        self.next_btn.setEnabled(self.current_index < len(self.chunks) - 1)

    def previous_chunk(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.show_current_chunk()

    def next_chunk(self):
        if self.current_index < len(self.chunks) - 1:
            self.current_index += 1
            self.show_current_chunk()

    def build_qr_pixmap(self, chunk):
        try:
            import qrcode
        except ImportError as exc:
            raise RuntimeError("Для отображения QR установите зависимость: pip install qrcode") from exc

        data = json.dumps(chunk, ensure_ascii=False, sort_keys=True)
        qr = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(data)
        qr.make(fit=True)
        matrix = qr.get_matrix()
        scale = max(1, 360 // len(matrix))
        size = len(matrix) * scale
        image = QImage(size, size, QImage.Format_RGB32)
        image.fill(QColor("white"))
        black = QColor("black")

        for row_index, row in enumerate(matrix):
            for col_index, enabled in enumerate(row):
                if not enabled:
                    continue
                for y in range(row_index * scale, (row_index + 1) * scale):
                    for x in range(col_index * scale, (col_index + 1) * scale):
                        image.setPixelColor(x, y, black)

        return QPixmap.fromImage(image)


class ShareDialog(QDialog):
    def __init__(self, parent=None, entry_manager=None, entry_id=None):
        super().__init__(parent)
        self.setWindowTitle("Поделиться записью")
        self.resize(620, 480)
        self.entry_manager = entry_manager
        self.entry_id = entry_id
        self.package = None
        self.qr_chunks = []
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
        self.expiration.setRange(1, 30 * 24 * 60)
        self.expiration.setValue(60)
        self.expiration.setSuffix(" мин")
        options.addWidget(self.edit_checkbox)
        options.addWidget(self.exclude_notes)
        options.addWidget(QLabel("Срок:"))
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
        qr_btn = QPushButton("QR код")
        qr_btn.clicked.connect(self.show_qr_code)
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
                expires_in_minutes=self.expiration.value(),
            )
            self.package = result["package"]
            self.qr_chunks = []
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

    def show_qr_code(self):
        self.create_package()
        if not self.package:
            return
        try:
            qr = QRCodeService(validity_seconds=self.expiration.value() * 60)
            payload = qr.build_payload("encrypted_entry", self.package)
            self.qr_chunks = qr.generate_qr_chunks(payload, chunk_size=512)
            dialog = QRCodeDialog(self, self.qr_chunks)
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка QR", str(e))
