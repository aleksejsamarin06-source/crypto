import unittest
import time
from PySide6.QtCore import QCoreApplication, QTimer
from src.core.clipboard.clipboard_service import ClipboardService
from src.core.events import event_system


class TestClipboardTiming(unittest.TestCase):
    def setUp(self):
        self.app = QCoreApplication.instance()
        if not self.app:
            self.app = QCoreApplication([])

        self.clipboard_service = ClipboardService(timeout=2)
        self.clear_time = None
        event_system.subscribe('ClipboardCleared', self.on_cleared)

    def on_cleared(self, data):
        self.clear_time = time.time()

    def tearDown(self):
        event_system.subscribers = {}

    def test_timeout_configuration_bounds(self):
        self.clipboard_service.set_auto_clear_timeout(10)
        self.assertEqual(self.clipboard_service.auto_clear_timeout, 10)

        self.clipboard_service.set_auto_clear_timeout(301)
        self.assertEqual(self.clipboard_service.auto_clear_timeout, 10)
