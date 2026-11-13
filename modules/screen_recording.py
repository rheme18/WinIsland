"""
WinIsland - Screen Recording Detector
Polls running processes for known recorder executables.
Emits recording_started(app_name) / recording_stopped() / duration_updated(seconds).
"""

import time
from typing import Optional
from PyQt6.QtCore import QThread, pyqtSignal

try:
    import psutil
    _PSUTIL_OK = True
except ImportError:
    _PSUTIL_OK = False

# Known screen recording process names (lowercase)
RECORDER_PROCS = {
    "obs64.exe": "OBS Studio",
    "obs32.exe": "OBS Studio",
    "obs.exe": "OBS Studio",
    "action.exe": "Action!",
    "bandicam.exe": "Bandicam",
    "fraps.exe": "FRAPS",
    "dxtory.exe": "Dxtory",
    "shadowplay.exe": "ShadowPlay",
    "xsplit.core.exe": "XSplit",
    "screencastify.exe": "Screencastify",
    "apowerrec.exe": "ApowerREC",
    "flashback.exe": "FlashBack",
    "camstudio.exe": "CamStudio",
}

POLL_INTERVAL_MS = 2000


class ScreenRecordingMonitor(QThread):
    """
    Polls every 2 s for known screen recording applications.
    Emits signals when recording starts or stops.
    """
    recording_started = pyqtSignal(str)   # app display name
    recording_stopped = pyqtSignal()
    duration_updated = pyqtSignal(float)  # seconds since start

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._recording_app: Optional[str] = None
        self._start_time: Optional[float] = None

    def stop(self) -> None:
        self._running = False
        self.wait(2000)

    def run(self) -> None:
        if not _PSUTIL_OK:
            return

        while self._running:
            self.msleep(POLL_INTERVAL_MS)
            try:
                detected: Optional[str] = None
                for proc in psutil.process_iter(["name"]):
                    try:
                        name = (proc.info.get("name") or "").lower()
                        if name in RECORDER_PROCS:
                            detected = RECORDER_PROCS[name]
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                if detected and self._recording_app is None:
                    # Recording just started
                    self._recording_app = detected
                    self._start_time = time.time()
                    self.recording_started.emit(detected)

                elif not detected and self._recording_app is not None:
                    # Recording just stopped
                    self._recording_app = None
                    self._start_time = None
                    self.recording_stopped.emit()

                elif detected and self._start_time is not None:
                    # Ongoing — update duration
                    self.duration_updated.emit(time.time() - self._start_time)

            except Exception:
                pass
