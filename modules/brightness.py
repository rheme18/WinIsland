"""
WinIsland - Screen Brightness Controller for Windows
Supports laptop displays and compatible monitors via WMI / PowerShell.
"""

import subprocess
import threading
from typing import Optional
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


class BrightnessManager(QObject):
    """Manages Windows display brightness asynchronously."""
    brightness_changed = pyqtSignal(int)

    _instance = None

    def __init__(self):
        super().__init__()
        self._current_brightness: int = 70
        self._is_supported: bool = True
        self._poll_running = False
        self._init_brightness()
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(1800)
        self._poll_timer.timeout.connect(self._poll_brightness)
        self._poll_timer.start()

    @classmethod
    def get_instance(cls) -> "BrightnessManager":
        if cls._instance is None:
            cls._instance = BrightnessManager()
        return cls._instance

    def _init_brightness(self) -> None:
        def worker():
            try:
                cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                       "(Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightness).CurrentBrightness"]
                out = subprocess.check_output(cmd, timeout=2, creationflags=_NO_WINDOW).decode().strip()
                if out.isdigit():
                    self._current_brightness = int(out)
                    self.brightness_changed.emit(self._current_brightness)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def get_brightness(self) -> int:
        return self._current_brightness

    def _poll_brightness(self) -> None:
        if self._poll_running:
            return
        self._poll_running = True

        def worker():
            try:
                cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                       "(Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightness).CurrentBrightness"]
                out = subprocess.check_output(cmd, timeout=2, creationflags=_NO_WINDOW,
                                             stderr=subprocess.DEVNULL).decode().strip()
                if out.isdigit():
                    level = max(0, min(100, int(out)))
                    if level != self._current_brightness:
                        self._current_brightness = level
                        self.brightness_changed.emit(level)
            except Exception:
                pass
            finally:
                self._poll_running = False

        threading.Thread(target=worker, daemon=True).start()

    def set_brightness(self, level: int) -> None:
        level = max(0, min(100, int(level)))
        self._current_brightness = level
        self.brightness_changed.emit(level)

        def worker():
            try:
                cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                       f"(Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1, {level})"]
                subprocess.run(cmd, timeout=2, creationflags=_NO_WINDOW,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()
