"""
WinIsland - Pixel the Tamagotchi Desktop Pet State Machine
Manages Pixel's mood, activities, health reminders, and reactions to system events.
Zero evolution tiers / zero eggs — Pixel is immediately active as a lively companion.
"""

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot

from core.config import Thresholds


class PetState(Enum):
    IDLE          = auto()
    SLEEPING      = auto()
    HAPPY         = auto()
    PANICKING     = auto()
    BLOATED       = auto()
    FLYING        = auto()
    CODING        = auto()
    SHOCKED       = auto()
    PEEKING_LEFT  = auto()
    PEEKING_RIGHT = auto()
    DANCING       = auto()
    HIDING        = auto()


# Keep PetEvolution for backwards compatibility with any existing imports
class PetEvolution(Enum):
    CAT    = 1
    DRAGON = 2

    @staticmethod
    def from_xp(xp: int) -> "PetEvolution":
        return PetEvolution.CAT


@dataclass
class PetStats:
    xp: int                    = 150
    level: int                 = 1
    hunger: float              = 100.0
    energy: float              = 100.0
    happiness: float           = 90.0
    wpm: float                 = 0.0
    last_active_time: float    = field(default_factory=time.time)
    water_last_time: float     = field(default_factory=time.time)
    break_last_time: float     = field(default_factory=time.time)
    species: str               = "cat"


class PetManager(QObject):
    """
    Central state engine for Pixel.
    Integrates system load, keyboard WPM, battery charging, music, and file drop events.
    """
    state_changed      = pyqtSignal(PetState, PetEvolution)
    xp_gained          = pyqtSignal(int)
    reminder_triggered = pyqtSignal(str)  # "water" | "break"
    evolution_occurred = pyqtSignal(PetEvolution)

    _WATER_INTERVAL     = 3600   # 1 hour
    _BREAK_INTERVAL     = 1200   # 20 minutes
    _IDLE_SLEEP_DELAY   = 300    # 5 minutes without keyboard/mouse activity -> SLEEPING
    _HAPPY_DURATION     = 4.5
    _SHOCKED_DURATION   = 2.2
    _PEEK_MIN_INTERVAL  = 35.0
    _PEEK_MAX_INTERVAL  = 75.0
    _PEEK_DURATION      = 2.5

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.stats = PetStats()
        self._state = PetState.IDLE
        self._evolution = PetEvolution.CAT

        self._cpu: float = 0.0
        self._ram: float = 0.0
        self._battery_pct: int = 100
        self._plugged: bool = True
        self._last_plugged: Optional[bool] = None

        self._media_playing: bool = False
        self._happy_until: float = 0.0
        self._shocked_until: float = 0.0

        self._next_peek_time: float = time.time() + random.uniform(
            self._PEEK_MIN_INTERVAL, self._PEEK_MAX_INTERVAL
        )
        self._peek_until: float = 0.0
        self._peek_direction: PetState = PetState.PEEKING_LEFT

        self._tick_count: int = 0
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    @pyqtSlot(object)
    def on_telemetry_updated(self, stats) -> None:
        self._cpu = float(stats.cpu_percent)
        self._ram = float(stats.ram_percent)
        if stats.has_battery:
            self._battery_pct = int(stats.battery_percent)
            self._plugged = bool(stats.power_plugged)
            self.stats.energy = float(self._battery_pct)

            if self._last_plugged is not None and self._plugged and not self._last_plugged:
                # Charger just plugged in -> SHOCKED then HAPPY!
                self._shocked_until = time.time() + self._SHOCKED_DURATION
                self._happy_until = time.time() + self._SHOCKED_DURATION + self._HAPPY_DURATION
                self._award_xp(15)

            self._last_plugged = self._plugged

    @pyqtSlot(object)
    def on_media_updated(self, track) -> None:
        self._media_playing = bool(track.is_playing)
        if self._media_playing:
            self._award_xp(1)

    @pyqtSlot()
    def on_key_pressed(self) -> None:
        self.stats.last_active_time = time.time()

    @pyqtSlot()
    def on_git_commit_detected(self) -> None:
        self._happy_until = time.time() + self._HAPPY_DURATION
        self._award_xp(25)

    @pyqtSlot(list)
    def on_file_dropped(self, paths: list) -> None:
        """Triggered when files are dropped onto the island."""
        self._happy_until = time.time() + self._HAPPY_DURATION
        self._award_xp(20)

    @pyqtSlot(float)
    def on_wpm_updated(self, wpm: float) -> None:
        self.stats.wpm = wpm
        self.stats.last_active_time = time.time()
        if wpm > 0:
            self._award_xp(max(1, int(wpm / 25)))

    @pyqtSlot(str)
    def on_reminder_acknowledged(self, kind: str) -> None:
        now = time.time()
        self._happy_until = now + self._HAPPY_DURATION
        if kind == "water":
            self.stats.water_last_time = now
            self._award_xp(15)
        elif kind == "break":
            self.stats.break_last_time = now
            self._award_xp(10)

    def _tick(self) -> None:
        self._tick_count += 1
        now = time.time()

        if self._tick_count % 5 == 0:
            self._check_reminders(now)

        new_state = self._resolve_state(now)
        if new_state != self._state:
            self._state = new_state
            self.state_changed.emit(self._state, self._evolution)

    def _resolve_state(self, now: float) -> PetState:
        if now < self._shocked_until:
            return PetState.SHOCKED

        if now < self._happy_until:
            return PetState.HAPPY

        if now < self._peek_until:
            return self._peek_direction

        if now >= self._next_peek_time:
            self._start_peek(now)
            return self._peek_direction

        # Critical conditions
        if self._cpu >= Thresholds.CPU_CRITICAL_PERCENT:
            return PetState.PANICKING

        if self._ram >= Thresholds.RAM_CRITICAL_PERCENT:
            return PetState.BLOATED

        # Inactivity
        idle_seconds = now - self.stats.last_active_time
        if idle_seconds > self._IDLE_SLEEP_DELAY:
            return PetState.SLEEPING

        # Media & Typing
        if self._media_playing:
            return PetState.DANCING

        if self.stats.wpm > 50:
            return PetState.CODING

        if self.stats.energy < 15 and not self._plugged:
            return PetState.HIDING

        return PetState.IDLE

    def _start_peek(self, now: float) -> None:
        self._peek_direction = random.choice([PetState.PEEKING_LEFT, PetState.PEEKING_RIGHT])
        self._peek_until = now + self._PEEK_DURATION
        self._next_peek_time = now + self._PEEK_DURATION + random.uniform(
            self._PEEK_MIN_INTERVAL, self._PEEK_MAX_INTERVAL
        )

    def _check_reminders(self, now: float) -> None:
        if now - self.stats.water_last_time >= self._WATER_INTERVAL:
            self.reminder_triggered.emit("water")
            self.stats.water_last_time = now

        if now - self.stats.break_last_time >= self._BREAK_INTERVAL:
            self.reminder_triggered.emit("break")
            self.stats.break_last_time = now

    def _award_xp(self, amount: int) -> None:
        if amount <= 0:
            return
        self.stats.xp += amount
        self.xp_gained.emit(amount)

    @property
    def current_state(self) -> PetState:
        return self._state

    @property
    def current_evolution(self) -> PetEvolution:
        return self._evolution

    def stop(self) -> None:
        self._timer.stop()
