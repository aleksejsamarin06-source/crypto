# src/core/clipboard/clipboard_service.py
from datetime import datetime
from typing import Optional
from PySide6.QtCore import QTimer
from src.core.clipboard.platform_adapter import get_platform_adapter, ClipboardAdapter
from src.core.events import event_system
import secrets
import ctypes

def secure_zero_memory(data: str):
    """Безопасное затирание временной копии без записи во внутренности Python str."""
    if not data:
        return
    try:
        buffer = bytearray(data.encode('utf-8'))
        for i in range(len(buffer)):
            buffer[i] = 0
    except:
        pass

class SecureClipboardItem:
    def __init__(self, data: str, data_type: str, source_entry_id: Optional[int], timeout: int):
        self.data = data
        self.data_type = data_type
        self.source_entry_id = source_entry_id
        self.copied_at = datetime.now()
        self.timeout = timeout

    def secure_wipe(self):
        if self.data:
            secure_zero_memory(self.data)
            self.data = None
        self.data_type = None
        self.source_entry_id = None

class ClipboardService:
    def __init__(self, timeout: int = 30):
        self.platform: ClipboardAdapter = get_platform_adapter()
        self.current_item: Optional[SecureClipboardItem] = None
        self.timer: Optional[QTimer] = None
        self.auto_clear_timeout = timeout

    def obfuscate(self, data: str) -> str:
        mask = secrets.token_bytes(len(data))
        obfuscated = bytes([ord(data[i]) ^ mask[i] for i in range(len(data))])
        return obfuscated.hex()

    def deobfuscate(self, obfuscated_hex: str) -> str:
        return obfuscated_hex

    def set_auto_clear_timeout(self, seconds: int):
        if 5 <= seconds <= 300:
            self.auto_clear_timeout = seconds

    def copy(self, data: str, data_type: str = "text", source_entry_id: Optional[int] = None) -> bool:
        print(f"Копирование: тип={data_type}, длина данных={len(data)}")
        try:
            self.clear_current()

            obfuscated_data = self.obfuscate(data)
            self.current_item = SecureClipboardItem(obfuscated_data, data_type, source_entry_id,
                                                    self.auto_clear_timeout)

            if not self.platform.copy_to_clipboard(data):
                self.current_item = None
                print("Ошибка: не удалось скопировать в системный буфер")
                return False

            print(f"Таймер запущен на {self.auto_clear_timeout} секунд")
            self.timer = QTimer()
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.on_timeout)
            self.timer.start(self.auto_clear_timeout * 1000)

            event_system.publish('ClipboardCopied', {
                'data_type': data_type,
                'source_entry_id': source_entry_id,
                'timeout': self.auto_clear_timeout
            })

            return True
        except Exception as e:
            print(f"Ошибка при копировании: {e}")
            return False


    def clear(self) -> bool:
        return self.clear_current()

    def clear_current(self) -> bool:
        if self.timer:
            self.timer.stop()
            self.timer = None

        if self.current_item:
            self.current_item.secure_wipe()
            self.current_item = None

        result = self.platform.clear_clipboard()
        event_system.publish('ClipboardCleared', {'reason': 'manual'})
        return result

    def on_timeout(self):
        print("Таймер сработал!")
        event_system.publish('ClipboardWillClear', {'reason': 'timeout', 'seconds': 5})
        self.do_clear()

    def do_clear(self):
        print("do_clear вызван")
        if self.current_item:
            print("Очищаем буфер и память")
            self.platform.clear_clipboard()
            self.current_item.secure_wipe()
            self.current_item = None
        self.timer = None
        event_system.publish('ClipboardCleared', {'reason': 'timeout'})

    def get_current_item(self) -> Optional[SecureClipboardItem]:
        return self.current_item

    def get_remaining_time(self) -> int:
        if self.current_item and self.timer:
            return max(0, self.timer.remainingTime() // 1000)
        return 0
