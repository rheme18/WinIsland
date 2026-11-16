"""
WinIsland - Hardware Device Monitor
Detects USB flash drives and external storage insertion / removal on Windows.
Emits device_event(connected: bool, title: str, subtitle: str, icon_type: str).
"""

import time
import psutil
from typing import Set, Dict
from PyQt6.QtCore import QThread, pyqtSignal
from modules.i18n import t


class HardwareMonitor(QThread):
    """
    Monitors Windows disk partitions to detect removable USB drives and external storage.
    Periodically checks for partition arrivals and removals.
    """
    device_event = pyqtSignal(bool, str, str, str)  # (is_connected, title, subtitle, icon_type)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._known_drives: Dict[str, str] = {}
        self._initialized = False

    def run(self) -> None:
        # Initial scan to populate existing drives without triggering alerts
        self._scan_drives(is_initial=True)
        self._initialized = True

        while self._running:
            self._scan_drives(is_initial=False)
            # Poll interval: 1.2s is very responsive for USB plug/unplug with minimal CPU impact
            for _ in range(12):
                if not self._running:
                    return
                self.msleep(100)

    def _scan_drives(self, is_initial: bool = False) -> None:
        try:
            current_partitions = psutil.disk_partitions(all=False)
            current_drives: Dict[str, str] = {}
            for p in current_partitions:
                # Capture mountpoint (e.g. "E:\\") and drive filesystem/opts
                opts = p.opts.lower()
                # Track removable drives or newly mounted drives
                is_removable = "removable" in opts or "cdrom" in opts or p.fstype.lower() in ("exfat", "fat32")
                current_drives[p.device] = "removable" if is_removable else "fixed"

            if not is_initial and self._initialized:
                # 1. Check for newly plugged-in drives
                for drive, dtype in current_drives.items():
                    if drive not in self._known_drives:
                        clean_name = drive.rstrip("\\")
                        title = t("alert_usb_connected_title") if dtype == "removable" else t("alert_drive_connected_title")
                        subtitle = t("alert_drive_ready", drive=clean_name)
                        self.device_event.emit(True, title, subtitle, "usb")

                # 2. Check for removed drives
                for drive, dtype in self._known_drives.items():
                    if drive not in current_drives:
                        clean_name = drive.rstrip("\\")
                        title = t("alert_usb_removed_title") if dtype == "removable" else t("alert_drive_removed_title")
                        subtitle = t("alert_drive_removed", drive=clean_name)
                        self.device_event.emit(False, title, subtitle, "usb")

            self._known_drives = current_drives
        except Exception:
            pass

    def stop(self) -> None:
        self._running = False
        self.wait(1500)
