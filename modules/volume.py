"""
WinIsland - Windows Master Volume Controller (pycaw)
Provides hardware-accelerated volume adjustment and mute toggling.
Includes 200ms polling to sync volume changed externally through Windows.
"""

from typing import Optional
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

try:
    from pycaw.pycaw import AudioUtilities
    PYCAW_AVAILABLE = True
except Exception:
    PYCAW_AVAILABLE = False


class VolumeManager(QObject):
    """
    Manages master volume levels and mute status.
    volume_changed(int, bool) is emitted whenever volume or mute state changes,
    including when changed externally (keyboard shortcut, taskbar, etc).
    """
    volume_changed = pyqtSignal(int, bool)  # (percent 0-100, is_muted)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._vol_endpoint = None
        self._last_volume: int = -1
        self._last_muted: bool = False
        self._init_endpoint()

        # Polling at 200ms keeps external volume changes responsive without needless wakeups.
        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(200)
        self._sync_timer.timeout.connect(self._poll_system_volume)
        self._sync_timer.start()

    def _init_endpoint(self) -> None:
        if not PYCAW_AVAILABLE:
            return
        try:
            speakers = AudioUtilities.GetSpeakers()
            if speakers:
                self._vol_endpoint = speakers.EndpointVolume
        except Exception:
            self._vol_endpoint = None

    def _poll_system_volume(self) -> None:
        """Check system volume and emit only when it changes externally."""
        if not self._vol_endpoint:
            self._init_endpoint()
            if not self._vol_endpoint:
                return
        try:
            scalar = self._vol_endpoint.GetMasterVolumeLevelScalar()
            muted = bool(self._vol_endpoint.GetMute())
            vol = int(round(scalar * 100))
            if self._last_volume == -1:
                self._last_volume = vol
                self._last_muted = muted
                self.volume_changed.emit(vol, muted)
            elif vol != self._last_volume or muted != self._last_muted:
                self._last_volume = vol
                self._last_muted = muted
                self.volume_changed.emit(vol, muted)
        except Exception:
            self._vol_endpoint = None  # re-acquire on next tick if device swapped

    def get_volume(self) -> int:
        if not self._vol_endpoint:
            self._init_endpoint()
        if self._vol_endpoint:
            try:
                scalar = self._vol_endpoint.GetMasterVolumeLevelScalar()
                return int(round(scalar * 100))
            except Exception:
                pass
        return 50

    def is_muted(self) -> bool:
        if not self._vol_endpoint:
            self._init_endpoint()
        if self._vol_endpoint:
            try:
                return bool(self._vol_endpoint.GetMute())
            except Exception:
                pass
        return False

    def set_volume(self, percent: int) -> None:
        if not self._vol_endpoint:
            self._init_endpoint()
        if self._vol_endpoint:
            try:
                scalar = max(0.0, min(1.0, float(percent) / 100.0))
                self._vol_endpoint.SetMasterVolumeLevelScalar(scalar, None)
                self._last_volume = percent
                self.volume_changed.emit(percent, self.is_muted())
            except Exception:
                pass

    def toggle_mute(self) -> bool:
        if not self._vol_endpoint:
            self._init_endpoint()
        if self._vol_endpoint:
            try:
                cur = bool(self._vol_endpoint.GetMute())
                new_state = not cur
                self._vol_endpoint.SetMute(new_state, None)
                vol = self.get_volume()
                self._last_muted = new_state
                self.volume_changed.emit(vol, new_state)
                return new_state
            except Exception:
                pass
        return False
