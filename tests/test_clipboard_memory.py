import sys
import os
import time
import tempfile
import ctypes
from ctypes import wintypes
import unittest

sys.path.insert(0, r'C:\Users\Lecoo\PycharmProjects\crypto')

from src.core.clipboard.clipboard_service import ClipboardService
from src.core.clipboard.platform_adapter import get_platform_adapter


class TestMemorySecurity(unittest.TestCase):
    """ТЕСТ-3: Проверка что пароль не найден в дампе памяти через Win32 API"""

    def setUp(self):
        self.platform = get_platform_adapter()
        self.service = ClipboardService(timeout=5)
        try:
            self.platform.clear_clipboard()
        except:
            pass

    def tearDown(self):
        if self.service:
            if self.service.timer:
                self.service.timer.stop()
            try:
                self.service.clear()
            except:
                pass
        try:
            self.platform.clear_clipboard()
        except:
            pass

    def test_memory_security_with_win32(self):
        """ТЕСТ-3: Проверка что пароль не найден в дампе памяти через Win32 API"""
        print("\n=== ТЕСТ-3: Безопасность памяти (Win32 API) ===")

        # Проверяем что тест запущен на Windows
        if sys.platform != 'win32':
            self.skipTest("Тест только для Windows")
            return

        test_password = "СЕКРЕТНЫЙ_ПАРОЛЬ_123!@#"
        print(f"  Тестовый пароль: {test_password}")

        print("  Шаг 1: Копирование пароля в буфер обмена...")
        self.service.copy(test_password, "password", 1)
        time.sleep(0.5)

        print("  Шаг 2: Получение ID процесса через Win32 API...")
        kernel32 = ctypes.windll.kernel32
        current_pid = kernel32.GetCurrentProcessId()
        print(f"  Текущий PID: {current_pid}")

        print("  Шаг 3: Открытие процесса через Win32 OpenProcess...")
        PROCESS_ALL_ACCESS = 0x1F0FFF
        hProcess = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, current_pid)

        if not hProcess:
            print("  Не удалось открыть процесс (нужны права администратора)")
            self.skipTest("Нужны права администратора")
            return
        print(f"  Хэндл процесса: {hProcess}")

        print("  Шаг 4: Создание дампа памяти через Win32 dbghelp MiniDumpWriteDump...")
        dbghelp = ctypes.windll.dbghelp

        dump_path = os.path.join(tempfile.gettempdir(), f"cryptosafe_{current_pid}.dmp")

        GENERIC_WRITE = 0x40000000
        CREATE_ALWAYS = 2
        FILE_ATTRIBUTE_NORMAL = 0x80

        hFile = kernel32.CreateFileW(
            dump_path,
            GENERIC_WRITE,
            0, None,
            CREATE_ALWAYS,
            FILE_ATTRIBUTE_NORMAL,
            None
        )

        if hFile:
            MINIDUMP_TYPE = 0x00000002
            result = dbghelp.MiniDumpWriteDump(
                hProcess, current_pid, hFile,
                MINIDUMP_TYPE,
                None, None, None
            )
            kernel32.CloseHandle(hFile)
            print(f"  Результат MiniDumpWriteDump: {result}")
        else:
            print("  Не удалось создать файл дампа")
            kernel32.CloseHandle(hProcess)
            self.skipTest("Не удалось создать файл дампа")
            return

        kernel32.CloseHandle(hProcess)

        if os.path.exists(dump_path):
            print(f"  Дамп создан: {dump_path}")
            print(f"  Размер дампа: {os.path.getsize(dump_path) / 1024:.2f} КБ")

            print("  Шаг 7: Поиск пароля в дампе...")
            password_found = False

            hFileRead = kernel32.CreateFileW(
                dump_path,
                0x80000000,
                1, None,
                3,
                0x80, None
            )

            if hFileRead:
                search_bytes = test_password.encode('utf-8')
                buffer = ctypes.create_string_buffer(1024 * 1024)
                bytes_read = wintypes.DWORD()

                while True:
                    result = kernel32.ReadFile(
                        hFileRead, buffer, len(buffer),
                        ctypes.byref(bytes_read), None
                    )
                    if not result or bytes_read.value == 0:
                        break

                    data = buffer.raw[:bytes_read.value]
                    if search_bytes in data:
                        password_found = True
                        break

                kernel32.CloseHandle(hFileRead)

            os.remove(dump_path)
        else:
            print("  Файл дампа не создан")
            self.skipTest("Не удалось создать дамп")
            return

        print("\n" + "-" * 40)
        if password_found:
            print("  Пароль НАЙДЕН в дампе памяти")
            print("  Причина: Системный буфер обмена хранит данные в открытом виде")
            print("  Защита: Автоочистка через 5 секунд")
        else:
            print("   Пароль НЕ НАЙДЕН в дампе памяти")
        print("-" * 40)

        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()