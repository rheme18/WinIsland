"""
WinIsland - System Telemetry Module (psutil + kernel32)
Real-time monitoring for CPU, RAM, Battery, and Mic/Webcam Privacy Indicators.
Uses Windows power status plus periodic CPU, memory and privacy checks.
"""

import ctypes
import time
from ctypes import wintypes
from dataclasses import dataclass
from typing import Optional
import winreg
import psutil
from PyQt6.QtCore import QThread, pyqtSignal

from core.config import Timing, Thresholds
from modules.i18n import t


class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ('ACLineStatus', wintypes.BYTE),
        ('BatteryFlag', wintypes.BYTE),
        ('BatteryLifePercent', wintypes.BYTE),
        ('SystemStatusFlag', wintypes.BYTE),
        ('BatteryLifeTime', wintypes.DWORD),
        ('BatteryFullLifeTime', wintypes.DWORD),
    ]


def _get_fast_power_status() -> tuple[bool, int, bool]:
    """
    Query Windows kernel32 directly with zero overhead (<0.1ms).
    Returns (has_battery, percent, is_plugged).
    """
    try:
        s = SYSTEM_POWER_STATUS()
        if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s)):
            is_plugged = (s.ACLineStatus == 1)
            percent = int(s.BatteryLifePercent)
            if percent > 100:
                percent = 100
            has_battery = (s.BatteryFlag != 128 and s.BatteryFlag != 255)
            return (has_battery, percent, is_plugged)
    except Exception:
        pass
    return (False, 100, True)


def check_privacy_sensor(device_type: str) -> bool:
    """Query Windows CapabilityAccessManager to check if microphone or camera is active."""
    base_path = f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\{device_type}"
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(root, base_path) as key:
                num_subkeys = winreg.QueryInfoKey(key)[0]
                for i in range(num_subkeys):
                    subkey_name = winreg.EnumKey(key, i)
                    try:
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            stop_time, _ = winreg.QueryValueEx(subkey, "LastUsedTimeStop")
                            if stop_time == 0:
                                return True
                    except Exception:
                        pass
        except Exception:
            pass
    return False


@dataclass
class SystemStatsData:
    cpu_percent: float
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float
    has_battery: bool
    battery_percent: int
    power_plugged: bool
    is_critical: bool
    mic_active: bool = False
    cam_active: bool = False
    critical_message: Optional[str] = None


class SystemStatsWorker(QThread):
    """
    Rapid kernel-level telemetry worker.
    Polls CPU/RAM and privacy every 1.5 seconds. Fast charge-state changes are
    detected separately by the window's lightweight native status timer.
    """
    stats_updated = pyqtSignal(object)              # Emits SystemStatsData
    battery_event = pyqtSignal(str, str, str)       # (title, message, icon_type)
    system_event = pyqtSignal(str, str, str)         # (title, message, icon_type)
    privacy_changed = pyqtSignal(bool, bool)        # (mic_active, cam_active)
    critical_state_changed = pyqtSignal(bool, str)  # (is_critical, message)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._last_power_plugged: Optional[bool] = None
        self._last_battery_low: bool = False
        self._last_critical: bool = False
        self._last_mic: bool = False
        self._last_cam: bool = False
        self._cached_cpu: float = 0.0
        self._cached_ram_pct: float = 0.0
        self._cached_ram_used: float = 0.0
        self._cached_ram_tot: float = 0.0
        self._disk_alerts: dict[str, bool] = {}
        self._next_disk_check: float = 0.0

    def stop(self) -> None:
        self._running = False
        self.wait(1000)

    def _check_disk_space(self) -> None:
        """Notify once when a mounted volume crosses the low-space threshold."""
        active_disks: set[str] = set()
        try:
            partitions = psutil.disk_partitions(all=False)
        except Exception:
            return

        for partition in partitions:
            options = {value.strip().lower() for value in (partition.opts or "").split(",")}
            if options.intersection({"cdrom", "removable", "remote"}):
                continue

            key = (partition.device or partition.mountpoint).casefold()
            if not key:
                continue
            active_disks.add(key)
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                percent = float(usage.percent)
                was_low = self._disk_alerts.get(key, False)
                is_low = percent >= Thresholds.DISK_LOW_PERCENT
                if was_low:
                    is_low = percent > Thresholds.DISK_CLEAR_PERCENT
                self._disk_alerts[key] = is_low

                if is_low and not was_low:
                    drive = (partition.device or partition.mountpoint).rstrip("\\/")
                    free_gb = usage.free / (1024 ** 3)
                    self.system_event.emit(
                        t("alert_disk_low_title"),
                        t("alert_disk_low_message", drive=drive,
                          percent=f"{percent:.0f}", free_gb=f"{free_gb:.1f}"),
                        "storage"
                    )
            except Exception:
                continue

        # Forget drives that were unplugged so they can notify again next time.
        self._disk_alerts = {
            key: is_low for key, is_low in self._disk_alerts.items()
            if key in active_disks
        }

    def run(self) -> None:
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            pass

        # Initial battery check
        has_battery, battery_percent, power_plugged = _get_fast_power_status()
        self._last_power_plugged = power_plugged

        while self._running:
            try:
                # 1. Battery status cached for telemetry
                has_battery, battery_percent, power_plugged = _get_fast_power_status()

                # Low battery alert (< 20%)
                is_low = has_battery and not power_plugged and (battery_percent <= Thresholds.BATTERY_LOW_PERCENT)
                if is_low and not self._last_battery_low:
                    self.battery_event.emit(
                        t("alert_low_battery_title"),
                        t("alert_low_battery_message", percent=battery_percent),
                        "battery_low"
                    )
                self._last_battery_low = is_low

                # 2. System Telemetry & Privacy Sensor (every ~1.0s)
                self._cached_cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory()
                self._cached_ram_pct = mem.percent
                self._cached_ram_used = mem.used / (1024 ** 3)
                self._cached_ram_tot = mem.total / (1024 ** 3)

                now = time.monotonic()
                if now >= self._next_disk_check:
                    self._next_disk_check = now + 30.0
                    self._check_disk_space()

                # Privacy sensors
                mic_on = check_privacy_sensor("microphone")
                cam_on = check_privacy_sensor("webcam")
                if mic_on != self._last_mic or cam_on != self._last_cam:
                    self._last_mic = mic_on
                    self._last_cam = cam_on
                    self.privacy_changed.emit(mic_on, cam_on)

                # Critical state with high threshold (trigger at 98%, clear at 92%)
                if self._last_critical:
                    is_critical = (self._cached_cpu >= 92.0 or self._cached_ram_pct >= 92.0)
                else:
                    is_critical = (self._cached_cpu >= Thresholds.CPU_CRITICAL_PERCENT or
                                   self._cached_ram_pct >= Thresholds.RAM_CRITICAL_PERCENT)

                crit_msg = ""
                if is_critical:
                    if self._cached_cpu >= Thresholds.CPU_CRITICAL_PERCENT and self._cached_ram_pct >= Thresholds.RAM_CRITICAL_PERCENT:
                        crit_msg = t("alert_cpu_ram_overload", cpu=f"{self._cached_cpu:.0f}",
                                      ram=f"{self._cached_ram_pct:.0f}")
                    elif self._cached_cpu >= Thresholds.CPU_CRITICAL_PERCENT:
                        crit_msg = t("alert_cpu_overload_desc", percent=f"{self._cached_cpu:.0f}")
                    elif self._cached_ram_pct >= Thresholds.RAM_CRITICAL_PERCENT:
                        crit_msg = t("alert_ram_overload_desc", percent=f"{self._cached_ram_pct:.0f}")
                    else:
                        crit_msg = t("alert_system_overload_desc")

                if is_critical != self._last_critical:
                    self._last_critical = is_critical
                    self.critical_state_changed.emit(is_critical, crit_msg)

                stats = SystemStatsData(
                    cpu_percent=self._cached_cpu,
                    ram_percent=self._cached_ram_pct,
                    ram_used_gb=self._cached_ram_used,
                    ram_total_gb=self._cached_ram_tot,
                    has_battery=has_battery,
                    battery_percent=battery_percent,
                    power_plugged=power_plugged,
                    is_critical=is_critical,
                    mic_active=self._last_mic,
                    cam_active=self._last_cam,
                    critical_message=crit_msg if is_critical else None
                )
                self.stats_updated.emit(stats)

                self.msleep(Timing.TELEMETRY_POLL_INTERVAL_MS)

            except Exception:
                self.msleep(Timing.TELEMETRY_POLL_INTERVAL_MS)
