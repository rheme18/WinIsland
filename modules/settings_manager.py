"""
WinIsland - Central Settings & Persistence Manager
Stores preferences in config.json and manages Windows startup registry integration.
"""

import json
import os
import sys
import winreg
from typing import Any, Dict
from PyQt6.QtCore import QObject, pyqtSignal
from modules.i18n import I18nManager


if getattr(sys, "frozen", False):
    CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "WinIsland")
    CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
else:
    CONFIG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
STARTUP_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "WinIsland"


class SettingsManager(QObject):
    """Singleton configuration and preference manager."""
    settings_changed = pyqtSignal(dict)

    _instance = None

    DEFAULT_SETTINGS: Dict[str, Any] = {
        "language": "tr",
        "scroll_action": "switch_page",  # "switch_page" or "volume"
        "launch_at_startup": False,
        "show_page_dots": True,
        "acrylic_blur": False,
        "ambient_glow": True,
        "animations_enabled": True,
        "show_notifications": True,
        "show_battery_indicator": True,
        "show_weather_indicator": True,
        "show_task_indicator": True,
        "show_system_telemetry": False,
        "gemini_api_key": ""
    }

    def __init__(self):
        super().__init__()
        self._data: Dict[str, Any] = dict(self.DEFAULT_SETTINGS)
        self.load()

    @classmethod
    def get_instance(cls) -> "SettingsManager":
        if cls._instance is None:
            cls._instance = SettingsManager()
        return cls._instance

    def load(self) -> None:
        """Load settings from config.json."""
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    disk_data = json.load(f)
                    self._data.update(disk_data)
            except Exception as e:
                print(f"[Settings] Error loading config.json: {e}")
        
        # Sync i18n
        lang = self._data.get("language", "tr")
        I18nManager.get_instance().set_language(lang)

    def save(self) -> None:
        """Save settings back to config.json."""
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Settings] Error saving config.json: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default if default is not None else self.DEFAULT_SETTINGS.get(key))

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        if key == "language":
            I18nManager.get_instance().set_language(value)
        elif key == "launch_at_startup":
            self._apply_startup_registry(bool(value))
        self.save()
        self.settings_changed.emit(self._data)

    def _apply_startup_registry(self, enable: bool) -> None:
        """Register or unregister app in Windows Run registry key."""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                STARTUP_REG_KEY,
                0,
                winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
            )
            if enable:
                # If running frozen as exe vs script
                if getattr(sys, 'frozen', False):
                    exe_path = f'"{sys.executable}"'
                else:
                    python_exe = sys.executable
                    main_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")
                    exe_path = f'"{python_exe}" "{main_py}"'
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            print(f"[Settings] Startup registry update error: {e}")
