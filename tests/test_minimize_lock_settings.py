import os
import tempfile
import unittest

from src.core.settings_manager import SettingsManager


class TestMinimizeLockSettings(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_default_minimize_lock_settings(self):
        settings = SettingsManager(self.db_path)

        self.assertEqual(settings.get_minimize_lock_mode(), 'delayed')
        self.assertEqual(settings.get_minimize_lock_delay_seconds(), 300)

        settings.close()

    def test_save_minimize_lock_settings(self):
        settings = SettingsManager(self.db_path)
        settings.set_minimize_lock_mode('immediate')
        settings.set_minimize_lock_delay_seconds(600)
        settings.close()

        settings = SettingsManager(self.db_path)
        self.assertEqual(settings.get_minimize_lock_mode(), 'immediate')
        self.assertEqual(settings.get_minimize_lock_delay_seconds(), 600)
        settings.close()

    def test_invalid_minimize_lock_settings_fallback(self):
        settings = SettingsManager(self.db_path)
        settings.set('minimize_lock_mode', 'bad-mode')
        settings.set('minimize_lock_delay_seconds', 'bad-delay')

        self.assertEqual(settings.get_minimize_lock_mode(), 'delayed')
        self.assertEqual(settings.get_minimize_lock_delay_seconds(), 300)

        settings.close()

    def test_default_theme_settings(self):
        settings = SettingsManager(self.db_path)

        self.assertEqual(settings.get_app_theme(), 'dark')
        settings.set_app_theme('light')
        self.assertEqual(settings.get_app_theme(), 'light')
        settings.set_app_theme('system')
        self.assertEqual(settings.get_app_theme(), 'system')
        settings.set_app_theme('bad-theme')
        self.assertEqual(settings.get_app_theme(), 'dark')

        settings.close()


if __name__ == '__main__':
    unittest.main()
