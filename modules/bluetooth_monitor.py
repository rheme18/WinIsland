"""
WinIsland - Bluetooth Audio Device Monitor
Detects headphone/earphone connections via PowerShell + psutil.
"""

import json
import subprocess
from dataclasses import dataclass
from typing import Optional
from PyQt6.QtCore import QThread, pyqtSignal


AUDIO_KEYWORDS = [
    "avrcp", "headphone", "headset", "earphone", "earbuds", "speaker",
    "kulaklık", "kulaklı", "airpod", "soundcore", "jbl", "sony",
    "samsung earbuds", "buds", "audio", "M19", "m19"
]
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


@dataclass
class BluetoothDevice:
    name: str
    is_audio: bool


def _is_audio_device(name: str) -> bool:
    low = name.lower()
    return any(k.lower() in low for k in AUDIO_KEYWORDS)


def _get_bt_devices() -> list[BluetoothDevice]:
    try:
        r = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
             "Get-PnpDevice -Class Bluetooth | Where-Object {$_.Status -eq 'OK'} "
             "| Select-Object FriendlyName | ConvertTo-Json"],
            capture_output=True, timeout=5, encoding="utf-8", errors="replace",
            creationflags=_NO_WINDOW
        )
        raw = r.stdout.strip()
        if not raw:
            return []
        data = json.loads(raw)
        if isinstance(data, dict):
            data = [data]
        devices = []
        for d in data:
            name = d.get("FriendlyName", "").strip()
            if name:
                devices.append(BluetoothDevice(name=name, is_audio=_is_audio_device(name)))
        return devices
    except Exception:
        return []


class BluetoothMonitor(QThread):
    """Monitors Bluetooth device connections and emits events on change."""
    device_connected    = pyqtSignal(str, bool)   # (name, is_audio)
    device_disconnected = pyqtSignal(str, bool)   # (name, is_audio)
    audio_device_changed = pyqtSignal(str, bool)  # (name, connected)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._known: dict[str, BluetoothDevice] = {}

    def stop(self) -> None:
        self._running = False
        self.wait(1000)

    def run(self) -> None:
        # Initial scan without signalling
        for d in _get_bt_devices():
            self._known[d.name] = d

        while self._running:
            self.msleep(3000)
            try:
                current = {d.name: d for d in _get_bt_devices()}

                # Newly connected
                for name, dev in current.items():
                    if name not in self._known:
                        self.device_connected.emit(name, dev.is_audio)
                        if dev.is_audio:
                            self.audio_device_changed.emit(name, True)

                # Disconnected
                for name, dev in self._known.items():
                    if name not in current:
                        self.device_disconnected.emit(name, dev.is_audio)
                        if dev.is_audio:
                            self.audio_device_changed.emit(name, False)

                self._known = current
            except Exception:
                pass
