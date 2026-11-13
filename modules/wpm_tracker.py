"""
WinIsland - WPM Tracker & Caps Lock Monitor
Hooks keyboard events to calculate Words Per Minute and detect Caps Lock state.
Uses the `keyboard` library (global hook, works without focus).
"""

import time
import collections
from typing import Deque
from PyQt6.QtCore import QThread, pyqtSignal

try:
    import keyboard as _kb
    _KB_OK = True
except ImportError:
    _KB_OK = False

EMIT_INTERVAL_S = 2.0      # WPM update interval
WINDOW_S = 60.0            # Rolling 60-second window for WPM calc
CHARS_PER_WORD = 5.0       # Standard WPM calculation


class WPMTracker(QThread):
    """
    Global keyboard hook for WPM calculation and Caps Lock monitoring.
    Signals:
        wpm_updated(float)        — emitted every 2 s
        caps_lock_changed(bool)   — emitted on caps lock state change
        activity_detected()       — emitted on each keypress (for pet XP)
    """
    wpm_updated = pyqtSignal(float)
    caps_lock_changed = pyqtSignal(bool)
    activity_detected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._timestamps: Deque[float] = collections.deque()
        self._last_caps: bool = False
        self._last_emit: float = 0.0

    def stop(self) -> None:
        self._running = False
        if _KB_OK:
            try:
                _kb.unhook_all()
            except Exception:
                pass
        self.wait(2000)

    def _on_key(self, event) -> None:
        """Called on every key-down event (global hook)."""
        try:
            now = time.monotonic()
            self._timestamps.append(now)
            # Prune old timestamps outside the window
            cutoff = now - WINDOW_S
            while self._timestamps and self._timestamps[0] < cutoff:
                self._timestamps.popleft()

            # Emit activity signal for pet
            self.activity_detected.emit()

            # Check Caps Lock state
            try:
                caps = _kb.is_pressed("caps lock")
                # Also check toggle state via Windows API (more reliable)
                import ctypes
                caps_toggle = bool(ctypes.WinDLL("user32").GetKeyState(0x14) & 0x0001)
                if caps_toggle != self._last_caps:
                    self._last_caps = caps_toggle
                    self.caps_lock_changed.emit(caps_toggle)
            except Exception:
                pass

            # Emit WPM every EMIT_INTERVAL_S
            if now - self._last_emit >= EMIT_INTERVAL_S:
                self._last_emit = now
                chars = len(self._timestamps)
                wpm = (chars / CHARS_PER_WORD) * (60.0 / WINDOW_S)
                self.wpm_updated.emit(wpm)

        except Exception:
            pass

    def run(self) -> None:
        if not _KB_OK:
            # Fallback: just poll Caps Lock state via ctypes every 500ms
            self._run_caps_only_fallback()
            return

        try:
            _kb.on_press(self._on_key, suppress=False)
        except Exception:
            self._run_caps_only_fallback()
            return

        # Keep thread alive until stopped
        while self._running:
            self.msleep(200)

        try:
            _kb.unhook_all()
        except Exception:
            pass

    def _run_caps_only_fallback(self) -> None:
        """When `keyboard` library is unavailable, only track Caps Lock."""
        try:
            import ctypes
            user32 = ctypes.WinDLL("user32")
            while self._running:
                self.msleep(300)
                try:
                    state = bool(user32.GetKeyState(0x14) & 0x0001)
                    if state != self._last_caps:
                        self._last_caps = state
                        self.caps_lock_changed.emit(state)
                except Exception:
                    pass
        except Exception:
            pass
