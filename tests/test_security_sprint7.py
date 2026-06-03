import os
import tempfile
import time
import unittest

from src.core.security.activity_monitor import ActivityMonitor
from src.core.security.memory_guard import SecureMemory, SecretHolder
from src.core.security.panic_mode import PanicMode
from src.core.security.side_channel_protection import ConstantTimeOps
from src.core.settings_manager import SettingsManager


class TestSprint7Security(unittest.TestCase):
    def test_constant_time_comparisons(self):
        self.assertTrue(ConstantTimeOps.compare_text("secret", "secret"))
        self.assertFalse(ConstantTimeOps.compare_text("secret", "public"))
        self.assertTrue(ConstantTimeOps.compare_bytes(b"abc", b"abc"))
        self.assertFalse(ConstantTimeOps.compare_bytes(b"abc", b"abd"))

    def test_secure_memory_wipe(self):
        guard = SecureMemory()
        data = bytearray(b"very-secret")
        guard.wipe_bytearray(data)
        self.assertEqual(data, bytearray(len(data)))

        holder = SecretHolder(b"secret")
        self.assertEqual(holder.get_data(), b"secret")
        holder.wipe()

    def test_panic_mode_runs_handlers_once(self):
        calls = []
        panic = PanicMode()
        panic.register_handler(lambda method: calls.append(method))

        panic.activate("test")
        panic.activate("test-again")

        self.assertEqual(calls, ["test"])

    def test_activity_monitor_timeout_callback(self):
        calls = []
        monitor = ActivityMonitor(lambda: calls.append("locked"), {
            "auto_lock_enabled": True,
            "auto_lock_timeout_seconds": 1,
            "activity_sensitivity": "high",
        })
        monitor.start_monitoring()
        time.sleep(1.3)
        monitor.stop_monitoring()

        self.assertTrue(calls)

    def test_security_settings_profiles(self):
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            settings = SettingsManager(db_path)
            self.assertEqual(settings.get_security_profile(), "standard")
            settings.set_security_profile("paranoid")
            self.assertEqual(settings.get_security_profile(), "paranoid")
            self.assertEqual(settings.get_auto_lock_timeout_seconds(), 60)
            self.assertEqual(settings.get_activity_sensitivity(), "high")
            settings.close()
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)


if __name__ == "__main__":
    unittest.main()
