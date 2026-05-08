# src/core/clipboard/clipboard_monitor.py
import threading
import time
from typing import Optional
from PySide6.QtCore import QTimer
from src.core.events import event_system
from src.core.clipboard.platform_adapter import get_platform_adapter


class ClipboardMonitor:
    def __init__(self, clipboard_service):
        self.service = clipboard_service
        self.platform = get_platform_adapter()
        self.monitoring = False
        self.last_content: Optional[str] = None
        self.read_detected_count = 0
        self.timer = None

    def start_monitoring(self):
        """Запуск мониторинга буфера обмена"""
        self.monitoring = True
        self.last_content = self.platform.get_clipboard_content()
        self.timer = QTimer()
        self.timer.timeout.connect(self._check)
        self.timer.start(500)  # проверка каждые 500 мс

    def stop_monitoring(self):
        """Остановка мониторинга"""
        self.monitoring = False
        if self.timer:
            self.timer.stop()
            self.timer = None

    def _check(self):
        """Проверка изменений буфера"""
        if not self.monitoring:
            return

        current = self.platform.get_clipboard_content()

        # Если содержимое изменилось
        if current != self.last_content:
            self.last_content = current
            event_system.publish('ClipboardChanged', {'content': current})

        # Проверка на подозрительную активность (упрощённо)
        if self.service.current_item and self.service.current_item.data:
            # Если в буфере наши данные и другой процесс их прочитал
            # (на уровне ОС это сложно, имитируем через частые проверки)
            pass

    def report_suspicious_activity(self):
        """Сообщение о подозрительной активности"""
        self.read_detected_count += 1
        event_system.publish('ClipboardSuspicious', {'count': self.read_detected_count})

        # Ускоренная очистка при подозрительной активности
        if self.service.current_item:
            self.service.clear()
            from src.core.events import event_system
            event_system.publish('ClipboardCleared', {'reason': 'suspicious'})

    def reset_suspicious_count(self):
        """Сброс счётчика подозрительных активностей"""
        self.read_detected_count = 0