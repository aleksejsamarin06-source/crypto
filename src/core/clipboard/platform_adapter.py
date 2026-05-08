# src/core/clipboard/platform_adapter.py
import sys
import os
import platform
from abc import ABC, abstractmethod
from typing import Optional

class ClipboardAdapter(ABC):
    @abstractmethod
    def copy_to_clipboard(self, data: str) -> bool:
        pass

    @abstractmethod
    def clear_clipboard(self) -> bool:
        pass

    @abstractmethod
    def get_clipboard_content(self) -> Optional[str]:
        pass

class FallbackClipboardAdapter(ClipboardAdapter):
    """Базовый адаптер через pyperclip (работает везде)"""
    def __init__(self):
        try:
            import pyperclip
            self.pyperclip = pyperclip
        except ImportError:
            raise ImportError("pyperclip не установлен. Установите: pip install pyperclip")

    def copy_to_clipboard(self, data: str) -> bool:
        try:
            self.pyperclip.copy(data)
            return True
        except:
            return False

    def clear_clipboard(self) -> bool:
        try:
            self.pyperclip.copy("")
            return True
        except:
            return False

    def get_clipboard_content(self) -> Optional[str]:
        try:
            return self.pyperclip.paste()
        except:
            return None


class WindowsClipboardAdapter(ClipboardAdapter):
    """Windows адаптер через win32clipboard"""

    def __init__(self):
        try:
            import win32clipboard
            self.win32clipboard = win32clipboard
        except ImportError:
            raise ImportError("pywin32 не установлен. Установите: pip install pywin32")

    def _encrypt_memory(self, data: str) -> str:
        """Шифрование данных в памяти через CryptProtectMemory"""
        try:
            import ctypes
            data_bytes = data.encode('utf-16le')
            # CryptProtectMemory требует длину, кратную 4
            if len(data_bytes) % 4 != 0:
                data_bytes += b'\x00' * (4 - len(data_bytes) % 4)

            crypt32 = ctypes.windll.crypt32
            crypt32.CryptProtectMemory.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong]
            crypt32.CryptProtectMemory.restype = ctypes.c_bool

            if crypt32.CryptProtectMemory(ctypes.addressof(ctypes.c_char.from_buffer(data_bytes)),
                                          len(data_bytes), 0):
                return data_bytes.decode('utf-16le')
        except Exception as e:
            print(f"CryptProtectMemory не удалось: {e}")
        return data

    def copy_to_clipboard(self, data: str) -> bool:
        try:
            # Шифруем данные в памяти перед копированием
            encrypted_data = self._encrypt_memory(data)

            self.win32clipboard.OpenClipboard()
            self.win32clipboard.EmptyClipboard()
            self.win32clipboard.SetClipboardText(encrypted_data, self.win32clipboard.CF_UNICODETEXT)
            self.win32clipboard.CloseClipboard()
            return True
        except:
            return False

    def clear_clipboard(self) -> bool:
        try:
            self.win32clipboard.OpenClipboard()
            self.win32clipboard.EmptyClipboard()
            self.win32clipboard.CloseClipboard()
            return True
        except:
            return False

    def get_clipboard_content(self) -> Optional[str]:
        try:
            self.win32clipboard.OpenClipboard()
            if self.win32clipboard.IsClipboardFormatAvailable(self.win32clipboard.CF_UNICODETEXT):
                data = self.win32clipboard.GetClipboardData(self.win32clipboard.CF_UNICODETEXT)
            else:
                data = None
            self.win32clipboard.CloseClipboard()
            return data
        except:
            return None

class MacClipboardAdapter(ClipboardAdapter):
    """macOS адаптер через pyobjc (NSPasteboard)"""
    def __init__(self):
        try:
            from Cocoa import NSPasteboard, NSStringPboardType
            self.NSPasteboard = NSPasteboard
            self.NSStringPboardType = NSStringPboardType
        except ImportError:
            raise ImportError("pyobjc не установлен. Установите: pip install pyobjc")

    def copy_to_clipboard(self, data: str) -> bool:
        try:
            pb = self.NSPasteboard.generalPasteboard()
            pb.clearContents()
            pb.setString_forType_(data, self.NSStringPboardType)
            return True
        except:
            return False

    def clear_clipboard(self) -> bool:
        try:
            pb = self.NSPasteboard.generalPasteboard()
            pb.clearContents()
            return True
        except:
            return False

    def get_clipboard_content(self) -> Optional[str]:
        try:
            pb = self.NSPasteboard.generalPasteboard()
            return pb.stringForType_(self.NSStringPboardType)
        except:
            return None

# Linux адаптер оставим через fallback (pyperclip), так как xclip/xsel требуют дополнительной установки

def get_platform_adapter() -> ClipboardAdapter:
    """Фабрика: возвращает адаптер для текущей ОС"""
    system = platform.system().lower()

    if system == 'windows':
        try:
            return WindowsClipboardAdapter()
        except ImportError:
            return FallbackClipboardAdapter()

    elif system == 'darwin':
        try:
            return MacClipboardAdapter()
        except ImportError:
            return FallbackClipboardAdapter()

    else:  # Linux и другие
        # Проверяем Wayland
        if 'WAYLAND_DISPLAY' in os.environ:
            try:
                return WaylandClipboardAdapter()
            except ImportError:
                pass

        # Fallback на pyperclip (xclip/xsel)
        return FallbackClipboardAdapter()

class WaylandClipboardAdapter(ClipboardAdapter):
    """Linux Wayland адаптер через wl-clipboard"""
    def __init__(self):
        try:
            import subprocess
            self.subprocess = subprocess
            # Проверяем наличие wl-copy и wl-paste
            self.subprocess.run(['wl-copy', '--version'], capture_output=True, check=True)
            self.subprocess.run(['wl-paste', '--version'], capture_output=True, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            raise ImportError("wl-clipboard не установлен. Установите: sudo apt install wl-clipboard")

    def copy_to_clipboard(self, data: str) -> bool:
        try:
            proc = self.subprocess.run(['wl-copy'], input=data.encode('utf-8'), capture_output=True)
            return proc.returncode == 0
        except:
            return False

    def clear_clipboard(self) -> bool:
        try:
            self.subprocess.run(['wl-copy', '--clear'], capture_output=True)
            return True
        except:
            return False

    def get_clipboard_content(self) -> Optional[str]:
        try:
            proc = self.subprocess.run(['wl-paste'], capture_output=True)
            if proc.returncode == 0:
                return proc.stdout.decode('utf-8')
            return None
        except:
            return None