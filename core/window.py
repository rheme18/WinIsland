"""
WinIsland - Dynamic Island Native Window Architecture
High-performance, frameless, translucent always-on-top island with spring/cubic animations.
Features:
- Windows Native Acrylic/Blur-Behind Glass (via user32.SetWindowCompositionAttribute)
- Pocket Mode (temporary drag-in & drag-out file pouch)
- Smart Notification Badge (iOS-style non-intrusive alert dot)
- Aurora Glow Drag-Drop Feedback (Zero ugly dashed lines)
- Pixel the Tamagotchi companion
"""

import math
import os
import time
import subprocess
import ctypes
from ctypes import wintypes
from enum import Enum, auto
from typing import Optional, List
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, QTimer, QEvent, pyqtProperty, pyqtSlot, pyqtSignal,
    QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, QUrl, QMimeData
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath, QPixmap, QScreen, QLinearGradient, QFont, QDrag
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QStackedLayout, QApplication
)

from core.config import Dimensions, Timing, Palette, Typography
from ui.widgets import (
    CompactCapsuleWidget, HorizontalAlertWidget, ExpandedDashboard, HoverPreviewWidget
)
from ui.settings_dialog import ModernSettingsDialog
from modules.settings_manager import SettingsManager
from modules.media import MediaTrackData
from modules.system_stats import SystemStatsData, _get_fast_power_status


class IslandState(Enum):
    COMPACT = auto()   # 180×32: minimal pill, camera, visualizer
    ALERT = auto()     # 340×36: iPhone-style horizontal alert
    HOVER = auto()     # Horizontal preview only; click/scroll opens dashboard
    EXPANDED = auto()  # Responsive multi-page dashboard


def _apply_native_acrylic(hwnd: int, enabled: bool = True) -> None:
    """Enable or clear the optional Windows blur-behind effect."""
    try:
        class ACCENT_POLICY(ctypes.Structure):
            _fields_ = [
                ('AccentState', ctypes.c_uint),
                ('AccentFlags', ctypes.c_uint),
                ('GradientColor', ctypes.c_uint),
                ('AnimationId', ctypes.c_uint)
            ]

        class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
            _fields_ = [
                ('Attribute', ctypes.c_int),
                ('Data', ctypes.c_void_p),
                ('SizeOfData', ctypes.c_size_t)
            ]

        accent = ACCENT_POLICY()
        accent.AccentState = 3 if enabled else 0  # Blur-behind / disabled
        accent.GradientColor = 0x8812141A  # Deep frosted acrylic tint

        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19  # WCA_ACCENT_POLICY
        data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p)
        data.SizeOfData = ctypes.sizeof(accent)

        ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
    except Exception:
        pass


class DynamicIslandWindow(QWidget):
    """
    Main Dynamic Island Window with native Windows Acrylic glass blur,
    Pocket mode file storage, and non-intrusive smart notification badges.
    """
    file_pocket_updated = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self._state: IslandState = IslandState.COMPACT
        self._target_state: IslandState = IslandState.COMPACT

        # Animated geometry
        self._width: float = float(Dimensions.COMPACT_WIDTH)
        self._height: float = float(Dimensions.COMPACT_HEIGHT)
        self._transition_radius: Optional[float] = None

        # Feature state
        self._is_hovered: bool = False
        self._is_drag_hover: bool = False
        self._is_critical: bool = False
        self._has_shown_critical_alert: bool = False
        self._pulse_alpha: float = 0.0
        self._caps_active: bool = False
        self._recording_active: bool = False
        self._recording_pulse_phase: float = 0.0
        self._bt_connected: bool = False
        self._bt_device_name: Optional[str] = None
        self._venv_info: Optional[str] = None
        self._ai_open: bool = False
        self._dnd_active: bool = False
        self._initial_vol_synced: bool = False
        self._initial_brightness_synced: bool = False

        # Pomodoro Focus Timer
        self._pomodoro_active: bool = False
        self._pomodoro_secs: int = 25 * 60
        self._pomodoro_timer = QTimer(self)
        self._pomodoro_timer.setInterval(1000)
        self._pomodoro_timer.timeout.connect(self._tick_pomodoro)

        # Pocket Mode: Stored files in Pixel's pouch
        self._pocket_files: List[str] = []

        # Smart Notification Badge state
        self._has_unread_notification: bool = False
        self._pending_notification_text: str = ""

        # Cached data
        self._current_media: Optional[MediaTrackData] = None
        self._current_stats: Optional[SystemStatsData] = None
        self._cached_pixmap: Optional[QPixmap] = None

        # Path cache
        self._pill_path = QPainterPath()

        # Timers
        self._alert_timer = QTimer(self)
        self._alert_timer.setSingleShot(True)
        self._alert_timer.timeout.connect(self._on_alert_timeout)

        self._leave_timer = QTimer(self)
        self._leave_timer.setSingleShot(True)
        self._leave_timer.timeout.connect(self._on_leave_timeout)

        # Battery change detection uses a lightweight 250ms native status poll.
        self._last_fast_plugged: Optional[bool] = None
        self._fast_battery_timer = QTimer(self)
        self._fast_battery_timer.setInterval(Timing.BATTERY_POLL_INTERVAL_MS)
        self._fast_battery_timer.timeout.connect(self._check_fast_battery)

        # Recording dot pulse
        self._rec_timer = QTimer(self)
        self._rec_timer.setInterval(40)
        self._rec_timer.timeout.connect(self._tick_recording_pulse)

        # Animation groups (must be initialized to None before first transition_to call)
        self._anim_group: Optional[QParallelAnimationGroup] = None
        self._drawer_anim: Optional[QPropertyAnimation] = None
        self._caps_anim: Optional[QPropertyAnimation] = None

        # Pulse animation for critical threshold
        self._pulse_anim: Optional[QPropertyAnimation] = None
        # Startup intro animation
        self._intro_anim: Optional[QPropertyAnimation] = None

        self._init_window_flags()
        self._init_layout_and_views()
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)
        self._settings = SettingsManager.get_instance()
        self._settings.settings_changed.connect(self._on_settings_changed)
        self._setup_pulse_animation()
        # Set initial width to 0 for center-out intro animation
        self._width = 2.0
        self._update_geometry_and_path()
        self._listen_screen_changes()
        # Fire intro center-out animation after event loop starts
        QTimer.singleShot(80, self._play_intro_animation)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._apply_surface_preference()

    def _on_settings_changed(self, _settings: dict) -> None:
        self._apply_surface_preference()
        if (not self._settings.get("show_notifications", True)
                and self._target_state == IslandState.ALERT):
            self.transition_to(IslandState.COMPACT)

    def _apply_surface_preference(self) -> None:
        if not self.isVisible():
            return
        _apply_native_acrylic(int(self.winId()), bool(self._settings.get("acrylic_blur", False)))

    # ── Window initialization ────────────────────────────────────────────

    def _init_window_flags(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setWindowTitle("WinIsland")

    def _init_layout_and_views(self) -> None:
        self.setMinimumSize(0, 0)
        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)
        self._root_layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetNoConstraint)

        self._stack = QStackedLayout()
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._stack.setSizeConstraint(QStackedLayout.SizeConstraint.SetNoConstraint)

        self.view_compact = CompactCapsuleWidget(self)
        self.view_compact.setMinimumSize(0, 0)
        self._stack.addWidget(self.view_compact)

        self.view_alert = HorizontalAlertWidget(self)
        self.view_alert.setMinimumSize(0, 0)
        self._stack.addWidget(self.view_alert)
        self.view_hover = HoverPreviewWidget(self)
        self.view_hover.setMinimumSize(0, 0)
        self._stack.addWidget(self.view_hover)

        self.view_expanded = ExpandedDashboard(self)
        self.view_expanded.setMinimumSize(0, 0)
        self.view_expanded.ai_drawer_toggled.connect(self._on_ai_drawer_toggled)
        self.view_expanded.pomodoro_toggled.connect(self._toggle_pomodoro)
        self.view_expanded.bring_music_clicked.connect(self._bring_music_app)
        self.view_expanded.dnd_toggled.connect(self._toggle_dnd)
        self.view_expanded.clear_pocket_clicked.connect(self._clear_pocket)
        self.view_expanded.sound_settings_clicked.connect(self._open_sound_settings)
        self.view_expanded.optimize_ram_clicked.connect(self._optimize_ram)
        self.view_expanded.take_screenshot_clicked.connect(self._take_screenshot)
        self.view_expanded.power_mode_clicked.connect(self._toggle_power_mode)
        self.view_expanded.open_settings_requested.connect(self.open_settings_dialog)
        self.view_expanded.section_height_changed.connect(self._on_section_height_changed)
        self._stack.addWidget(self.view_expanded)

        self._root_layout.addLayout(self._stack)
        self._stack.setCurrentWidget(self.view_compact)
        self._fast_battery_timer.start()

    def minimumSizeHint(self):
        return QRectF(0, 0, 10, 10).toRect().size()

    def _play_intro_animation(self) -> None:
        """Center-out intro animation: island expands from 2px → COMPACT_WIDTH from the center."""
        if self._target_state != IslandState.COMPACT or self._state != IslandState.COMPACT:
            return
        if self._intro_anim is not None:
            self._intro_anim.stop()
        self._intro_anim = QPropertyAnimation(self, b"islandWidth", self)
        self._intro_anim.setDuration(310)
        self._intro_anim.setStartValue(2.0)
        self._intro_anim.setEndValue(float(Dimensions.COMPACT_WIDTH))
        self._intro_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._intro_anim.start()

    def _setup_pulse_animation(self) -> None:
        self._pulse_anim = QPropertyAnimation(self, b"pulseAlpha", self)
        self._pulse_anim.setDuration(Timing.PULSE_CYCLE_MS)
        self._pulse_anim.setStartValue(0.15)
        self._pulse_anim.setEndValue(0.95)
        self._pulse_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._pulse_anim.setLoopCount(-1)

    def _listen_screen_changes(self) -> None:
        primary = QApplication.primaryScreen()
        if primary:
            primary.geometryChanged.connect(self._on_screen_geometry_changed)
        app = QApplication.instance()
        if app:
            app.primaryScreenChanged.connect(self._on_screen_geometry_changed)

    def _on_screen_geometry_changed(self, *args) -> None:
        self._update_geometry_and_path()

    # ── Animated Qt Properties ──────────────────────────────────────────

    @pyqtProperty(float)
    def islandWidth(self) -> float:
        return self._width

    @islandWidth.setter
    def islandWidth(self, val: float) -> None:
        self._width = val
        self._update_geometry_and_path()

    @pyqtProperty(float)
    def islandHeight(self) -> float:
        return self._height

    @islandHeight.setter
    def islandHeight(self, val: float) -> None:
        self._height = val
        self._update_geometry_and_path()

    @pyqtProperty(float)
    def islandProgress(self) -> float:
        return 0.0

    @islandProgress.setter
    def islandProgress(self, val: float) -> None:
        # One geometry/layout update per frame avoids the duplicate work caused
        # by parallel width and height property animations.
        self._width = self._anim_start_width + (self._anim_end_width - self._anim_start_width) * val
        self._height = self._anim_start_height + (self._anim_end_height - self._anim_start_height) * val
        self._transition_radius = self._anim_start_radius + (self._anim_end_radius - self._anim_start_radius) * val
        self._update_geometry_and_path()

    @pyqtProperty(float)
    def pulseAlpha(self) -> float:
        return self._pulse_alpha

    @pulseAlpha.setter
    def pulseAlpha(self, val: float) -> None:
        self._pulse_alpha = val
        self.update()

    # ── Geometry ────────────────────────────────────────────────────────

    def _current_radius(self) -> float:
        if self._transition_radius is not None:
            return self._transition_radius
        return self._radius_for_state(self._state)

    @staticmethod
    def _radius_for_state(state: IslandState) -> float:
        if state == IslandState.COMPACT:
            return float(Dimensions.RADIUS_COMPACT)
        elif state in (IslandState.ALERT, IslandState.HOVER):
            return float(Dimensions.RADIUS_ALERT)
        return float(Dimensions.RADIUS_EXPANDED)

    def _target_compact_width(self) -> int:
        base = Dimensions.COMPACT_WIDTH
        if self._caps_active:
            return base + Dimensions.CAPS_BADGE_EXTRA
        return base

    def _update_geometry_and_path(self) -> None:
        screen: Optional[QScreen] = QApplication.primaryScreen()
        if not screen:
            return
        s_geo = screen.geometry()
        w = max(10, int(self._width))
        h = max(10, int(self._height))
        x = s_geo.x() + (s_geo.width() - w) // 2
        y = s_geo.y() + Dimensions.TOP_MARGIN
        self.setGeometry(x, y, w, h)
        radius = min(self._current_radius(), (h - 1.0) / 2.0)
        self._pill_path = QPainterPath()
        self._pill_path.addRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), radius, radius)
        self.update()

    # ── State Transitions ───────────────────────────────────────────────

    def transition_to(self, new_state: IslandState, duration_override: Optional[int] = None) -> None:
        if new_state == IslandState.ALERT and not self._settings.get("show_notifications", True):
            self.view_alert.clear_for_transition()
            new_state = IslandState.COMPACT
        # Guard: already heading there — do nothing (prevents jitter/stutter on rapid hover)
        if self._target_state == new_state:
            return

        radius_start = self._current_radius()
        self._target_state = new_state

        # User interaction takes over from the startup intro animation.
        if self._intro_anim is not None:
            self._intro_anim.stop()
            self._intro_anim = None

        # ── 1. Stop & fully disconnect the OLD animation group FIRST ──────
        if hasattr(self, '_anim_group') and self._anim_group is not None:
            self._anim_group.stop()
            try:
                self._anim_group.finished.disconnect()
            except Exception:
                pass
            self._anim_group = None

        # A section/AI drawer can own a separate height animation while the
        # dashboard is open. Stop it before the island's state transition so
        # only one animation writes the window geometry at a time.
        if self._drawer_anim is not None:
            self._drawer_anim.stop()
            self._drawer_anim = None

        # ── 2. Switch visible view AFTER stopping old animation ───────────
        if new_state == IslandState.COMPACT:
            self._ai_open = False
            self.view_expanded.close_ai_drawer()
            self.view_expanded.show_section(-1)
            self.view_alert.clear_for_transition()
            self._apply_stacked_widget(IslandState.COMPACT)
        elif new_state == IslandState.ALERT:
            self._ai_open = False
            self.view_expanded.close_ai_drawer()
            self.view_compact.clear_for_transition()
            self._apply_stacked_widget(IslandState.ALERT)
        elif new_state == IslandState.HOVER:
            self._apply_stacked_widget(IslandState.HOVER)
        elif new_state == IslandState.EXPANDED:
            self._apply_stacked_widget(IslandState.EXPANDED)

        target_w, target_h = self._get_target_dimensions(new_state)
        if not self._settings.get("animations_enabled", True):
            self._transition_radius = None
            self._width, self._height = float(target_w), float(target_h)
            self._state = self._target_state = new_state
            self._update_geometry_and_path()
            return
        duration = duration_override or Timing.ANIMATION_SPRING_MS

        # ── 3. Build new group starting from CURRENT actual values ────────
        self._anim_start_width = self._width
        self._anim_start_height = self._height
        self._anim_end_width = float(target_w)
        self._anim_end_height = float(target_h)
        self._anim_start_radius = radius_start
        self._anim_end_radius = self._radius_for_state(new_state)
        self._transition_radius = radius_start
        self._anim_group = QParallelAnimationGroup(self)
        anim = QPropertyAnimation(self, b"islandProgress", self)
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim_group.addAnimation(anim)

        # Capture target in closure — avoids stale self._target_state reads
        _captured_target = new_state

        def on_finished():
            self._state = _captured_target
            self._target_state = _captured_target
            self._transition_radius = None
            self._update_geometry_and_path()

        self._anim_group.finished.connect(on_finished)
        self._anim_group.start()

    def _get_target_dimensions(self, state: IslandState) -> tuple[int, int]:
        if state == IslandState.COMPACT:
            return self._target_compact_width(), Dimensions.COMPACT_HEIGHT
        elif state == IslandState.ALERT:
            return Dimensions.ALERT_WIDTH, Dimensions.ALERT_HEIGHT
        elif state == IslandState.HOVER:
            return Dimensions.HOVER_WIDTH, Dimensions.HOVER_HEIGHT
        elif state == IslandState.EXPANDED:
            if self._ai_open:
                h = Dimensions.EXPANDED_AI_HEIGHT
            else:
                curr_sec = getattr(self.view_expanded, "_current_section_index", -1)
                if curr_sec == 0:    # Control Center
                    h = Dimensions.EXPANDED_CC_HEIGHT
                elif curr_sec == 1:  # Calendar & Tasks
                    h = Dimensions.EXPANDED_CAL_HEIGHT
                elif curr_sec == 3:  # Pixel
                    h = Dimensions.EXPANDED_PIXEL_HEIGHT
                else:
                    h = Dimensions.EXPANDED_HEIGHT
            return Dimensions.EXPANDED_WIDTH, h
        return Dimensions.COMPACT_WIDTH, Dimensions.COMPACT_HEIGHT

    def _on_section_height_changed(self, target_h: int) -> None:
        """Dynamic Apple-style morphing height when user switches dashboard tabs."""
        if (self._state == IslandState.EXPANDED
                and self._target_state == IslandState.EXPANDED
                and not self._ai_open):
            if not self._settings.get("animations_enabled", True):
                self._height = float(target_h)
                self._update_geometry_and_path()
                return
            if self._drawer_anim is not None:
                self._drawer_anim.stop()
                try:
                    self._drawer_anim.finished.disconnect()
                except Exception:
                    pass
                self._drawer_anim = None
            self._drawer_anim = QPropertyAnimation(self, b"islandHeight", self)
            self._drawer_anim.setDuration(220)
            self._drawer_anim.setStartValue(self._height)
            self._drawer_anim.setEndValue(float(target_h))
            self._drawer_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._drawer_anim.start()

    def _apply_stacked_widget(self, state: IslandState) -> None:
        if state == IslandState.COMPACT:
            self._stack.setCurrentWidget(self.view_compact)
        elif state == IslandState.ALERT:
            self._stack.setCurrentWidget(self.view_alert)
        elif state == IslandState.HOVER:
            self._stack.setCurrentWidget(self.view_hover)
        elif state == IslandState.EXPANDED:
            self._stack.setCurrentWidget(self.view_expanded)

    def _on_ai_drawer_toggled(self, is_open: bool) -> None:
        self._ai_open = is_open
        if (self._state == IslandState.EXPANDED
                and self._target_state == IslandState.EXPANDED):
            # Stop & disconnect old drawer animation to prevent conflicts
            if self._drawer_anim is not None:
                self._drawer_anim.stop()
                try:
                    self._drawer_anim.finished.disconnect()
                except Exception:
                    pass
                self._drawer_anim = None
            target_h = Dimensions.EXPANDED_AI_HEIGHT if is_open else Dimensions.EXPANDED_HEIGHT
            self._drawer_anim = QPropertyAnimation(self, b"islandHeight", self)
            self._drawer_anim.setDuration(200)
            self._drawer_anim.setStartValue(self._height)
            self._drawer_anim.setEndValue(float(target_h))
            self._drawer_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._drawer_anim.start()

    # ── Mouse & Drag-Drop Events ────────────────────────────────────────

    def enterEvent(self, event) -> None:
        self._is_hovered = True
        self._leave_timer.stop()

        # Alert banners keep their original horizontal presentation and timeout.
        # Hover expansion applies only to the compact capsule.
        if self._target_state == IslandState.ALERT or self._state == IslandState.ALERT:
            super().enterEvent(event)
            return

        # Clear notification badge when user inspects the island
        if self._has_unread_notification:
            self._has_unread_notification = False
            self.view_compact.set_notification_badge(False)
            if self._pending_notification_text:
                self.view_expanded.pet_lounge.show_notification_bubble(self._pending_notification_text)
                self._pending_notification_text = ""

        if self._state == IslandState.COMPACT:
            self.transition_to(IslandState.HOVER)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._is_hovered = False
        if self._state == IslandState.ALERT or self._target_state == IslandState.ALERT:
            # If its timeout elapsed while inspected, dismiss it on exit instead
            # of leaving a horizontal banner stuck on screen.
            if not self._alert_timer.isActive():
                self.transition_to(IslandState.COMPACT)
            super().leaveEvent(event)
            return
        self._leave_timer.start(Timing.HOVER_LEAVE_DELAY_MS)
        super().leaveEvent(event)

    def _on_leave_timeout(self) -> None:
        if not self._is_hovered and self._target_state in (IslandState.EXPANDED, IslandState.HOVER):
            self.transition_to(IslandState.COMPACT)

    def eventFilter(self, watched, event) -> bool:
        # Keep wheel gestures inside the calendar/task page. The task list
        # scrolls normally; the calendar itself consumes the gesture instead
        # of letting it bubble to the island's page carousel.
        if (event.type() == QEvent.Type.Wheel
                and self._target_state == IslandState.EXPANDED
                and getattr(self.view_expanded, "_current_section_index", -1) == 1):
            try:
                if not isinstance(watched, QWidget) or not (watched is self or self.isAncestorOf(watched)):
                    return super().eventFilter(watched, event)
                point = event.globalPosition().toPoint()
                if self.frameGeometry().contains(point):
                    calendar_page = self.view_expanded.page_cal
                    task_scroll = calendar_page.scroll
                    scroll_rect = task_scroll.rect()
                    scroll_rect.moveTopLeft(task_scroll.mapToGlobal(scroll_rect.topLeft()))
                    if scroll_rect.contains(point):
                        # Let QScrollArea handle angle and high-resolution
                        # pixel deltas itself. It consumes the gesture without
                        # turning task-list scrolling into dashboard paging.
                        return super().eventFilter(watched, event)
                    page_rect = calendar_page.rect()
                    page_rect.moveTopLeft(calendar_page.mapToGlobal(page_rect.topLeft()))
                    if page_rect.contains(point):
                        # The mini calendar/header has no scrollable content;
                        # keep its wheel gesture from reaching the page carousel.
                        event.accept()
                        return True
            except (AttributeError, RuntimeError):
                pass
        return super().eventFilter(watched, event)

    def _on_alert_timeout(self) -> None:
        if (not self._is_hovered
                and (self._state == IslandState.ALERT or self._target_state == IslandState.ALERT)):
            self.transition_to(IslandState.COMPACT)

    def wheelEvent(self, event) -> None:
        """
        Apple Carousel Navigation via Mouse Wheel:
        Scrolling over the island smoothly switches dashboard pages or adjusts volume.
        """
        if self._state == IslandState.ALERT or self._target_state == IslandState.ALERT:
            event.accept()
            return

        delta = event.angleDelta().y()
        now = time.time()
        # Debounce rapid scroll ticks to maintain buttery smooth feeling
        if now - getattr(self, "_last_wheel_time", 0.0) < 0.11:
            event.accept()
            return
        self._last_wheel_time = now

        settings = SettingsManager.get_instance()
        scroll_action = settings.get("scroll_action", "switch_page")

        if self._state == IslandState.EXPANDED:
            if scroll_action == "volume":
                step = 3 if delta > 0 else -3
                curr_vol = getattr(self, "_current_vol", 50)
                new_vol = max(0, min(100, curr_vol + step))
                self.view_expanded.volume_changed.emit(new_vol)
            else:
                if delta < 0:
                    self.view_expanded.next_section()
                elif delta > 0:
                    self.view_expanded.prev_section()
        elif self._state in (IslandState.COMPACT, IslandState.HOVER):
            if scroll_action == "volume":
                step = 3 if delta > 0 else -3
                curr_vol = getattr(self, "_current_vol", 50)
                new_vol = max(0, min(100, curr_vol + step))
                self.view_expanded.volume_changed.emit(new_vol)
            else:
                # Select the destination first so the opening animation uses
                # that page's full height (CC, calendar and Pixel differ).
                if delta < 0:
                    self.view_expanded.next_section()
                elif delta > 0:
                    self.view_expanded.prev_section()
                self.transition_to(IslandState.EXPANDED)

        event.accept()

    def mousePressEvent(self, event) -> None:
        # A click on the compact capsule opens the same dashboard as hover.
        # Alert banners remain owned by their existing notification lifecycle.
        if (event.button() == Qt.MouseButton.LeftButton
                and self._state in (IslandState.COMPACT, IslandState.HOVER)
                and self._target_state in (IslandState.COMPACT, IslandState.HOVER)):
            self._is_hovered = True
            self._leave_timer.stop()
            self.transition_to(IslandState.EXPANDED)
            event.accept()
            return
        super().mousePressEvent(event)

    def open_settings_dialog(self) -> None:
        """Opens standalone macOS/iOS style Settings Window."""
        if not hasattr(self, "_settings_dialog") or self._settings_dialog is None:
            self._settings_dialog = ModernSettingsDialog()
        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()

    # ── Pocket Mode: Drag & Drop Pouch ──────────────────────────────────

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()
            self._is_drag_hover = True
            self.update()

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:
        self._is_drag_hover = False
        self.update()

    def dropEvent(self, event) -> None:
        self._is_drag_hover = False
        urls = event.mimeData().urls()
        if urls:
            paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
            if paths:
                # Add to Pocket
                self._pocket_files.extend(paths)
                self.view_expanded.set_pocket_files(self._pocket_files)

                first_name = os.path.basename(paths[0])
                msg = t("alert_pocket_single", name=first_name) if len(paths) == 1 else t("alert_pocket_multi", count=len(paths))

                # Pocket Mode: Does NOT expand down! Shows sleek 1.5s compact alert
                self.view_alert.display(
                    title=t("alert_pocket_title"),
                    subtitle=msg,
                    icon_type="clipboard"
                )
                self.transition_to(IslandState.ALERT)
                self._alert_timer.start(1600)

                # Pixel celebrates with a happy flip
                self.view_expanded.pet_lounge.pet_avatar.trigger_happy_flip()
                self.file_pocket_updated.emit(self._pocket_files)
        self.update()

    # ── Recording Pulse ─────────────────────────────────────────────────

    def _tick_recording_pulse(self) -> None:
        self._recording_pulse_phase += 0.15
        self.update()

    # ── Public Slots ────────────────────────────────────────────────────

    @pyqtSlot(object)
    def on_media_updated(self, track: MediaTrackData) -> None:
        self._current_media = track
        pixmap = None
        if track.thumbnail_bytes:
            pixmap = QPixmap()
            pixmap.loadFromData(track.thumbnail_bytes)
        self._cached_pixmap = pixmap
        self.view_compact.set_playing(track.is_playing, track.title)
        self.view_expanded.update_media(
            track.title, track.artist, track.is_playing, pixmap,
            track.position_sec, track.duration_sec
        )

    @pyqtSlot(bool, bool)
    def on_privacy_changed(self, mic_active: bool, cam_active: bool) -> None:
        self.view_compact.set_privacy(mic_active, cam_active)

    @pyqtSlot(int, bool)
    def on_volume_changed(self, percent: int, is_muted: bool) -> None:
        self._current_vol = percent
        self.view_expanded.update_volume(percent, is_muted)
        if hasattr(self.view_expanded, "page_cc") and hasattr(self.view_expanded.page_cc, "set_volume"):
            self.view_expanded.page_cc.set_volume(percent)
        if not self._initial_vol_synced:
            self._initial_vol_synced = True
            return

        # Fluid volume feedback INSIDE the compact pill
        self.view_compact.show_volume_bar(percent, is_muted)
        # Expand to ALERT to show Apple Dynamic Island volume notification when not already expanded
        if not self._is_hovered and self._state != IslandState.EXPANDED and not self._dnd_active:
            title = t("alert_volume_muted") if is_muted else t("alert_volume", percent=percent)
            self.view_alert.display(
                title=title,
                subtitle="",
                icon_type="speaker_mute" if is_muted else "speaker",
                pixmap=None,
                show_visualizer=False
            )
            self.transition_to(IslandState.ALERT)
            self._alert_timer.start(1400)

    @pyqtSlot(object)
    def on_track_changed(self, track: MediaTrackData) -> None:
        self._current_media = track
        pixmap = None
        if track.thumbnail_bytes:
            pixmap = QPixmap()
            pixmap.loadFromData(track.thumbnail_bytes)
        self._cached_pixmap = pixmap
        self.view_compact.set_playing(track.is_playing, track.title)
        self.view_expanded.update_media(track.title, track.artist, track.is_playing, pixmap)
        if not self._is_hovered:
            self.view_alert.display(
                title=track.title or t("alert_media_playing"),
                subtitle=track.artist,
                icon_type="music",
                pixmap=pixmap,
                show_visualizer=True
            )
            self.transition_to(IslandState.ALERT)
            self._alert_timer.start(Timing.ALERT_TIMEOUT_MS)

    @pyqtSlot()
    def on_media_idle(self) -> None:
        self._current_media = None
        self._cached_pixmap = None
        self.view_compact.set_playing(False, "")
        self.view_expanded.update_media("", "", False, None)

    @pyqtSlot(object)
    def on_telemetry_updated(self, stats: SystemStatsData) -> None:
        self._current_stats = stats
        self.view_expanded.update_telemetry(
            cpu=stats.cpu_percent,
            ram=stats.ram_percent,
            ram_used=stats.ram_used_gb,
            ram_tot=stats.ram_total_gb,
            bat_pct=stats.battery_percent,
            plugged=stats.power_plugged,
            has_bat=stats.has_battery
        )
        self.view_hover.update_telemetry(stats.cpu_percent, stats.ram_percent)
        self.view_hover.update_battery(int(stats.battery_percent), stats.power_plugged, stats.has_battery)

    @pyqtSlot(bool, str)
    def on_critical_state_changed(self, is_critical: bool, message: str) -> None:
        self._is_critical = is_critical
        if is_critical:
            if self._pulse_anim.state() != QPropertyAnimation.State.Running:
                self._pulse_anim.start()
            # Alert only 1 time per overload episode! Never nag or spam the user
            if not self._has_shown_critical_alert and not self._is_hovered and self._state == IslandState.COMPACT:
                self._has_shown_critical_alert = True
                self.view_alert.display(
                    title=t("alert_system_overload"),
                    subtitle=message,
                    icon_type="warning",
                    pixmap=None, show_visualizer=False
                )
                self.transition_to(IslandState.ALERT)
                self._alert_timer.start(3500)
        else:
            if self._pulse_anim.state() == QPropertyAnimation.State.Running:
                self._pulse_anim.stop()
            self._pulse_alpha = 0.0
            self.update()

    @pyqtSlot(str, str, str)
    def on_battery_event(self, title: str, message: str, icon_type: str) -> None:
        pct = self._current_stats.battery_percent if self._current_stats else 100.0
        self.view_expanded.battery_pill.update_battery(int(pct), "charging" in icon_type, True)
        self.view_hover.update_battery(int(pct), "charging" in icon_type, True)
        if not self._is_hovered and not self._dnd_active:
            self.view_alert.display(title, message, icon_type=icon_type, pixmap=None,
                                    show_visualizer=False, battery_pct=float(pct))
            self.transition_to(IslandState.ALERT)
            self._alert_timer.start(Timing.ALERT_TIMEOUT_MS)

    def _check_fast_battery(self) -> None:
        has_battery, pct, plugged = _get_fast_power_status()
        if not has_battery:
            return
        self.view_hover.update_battery(pct, plugged, has_battery)
        if self._last_fast_plugged is not None and plugged != self._last_fast_plugged:
            self._last_fast_plugged = plugged
            self.view_expanded.battery_pill.update_battery(pct, plugged, has_battery)
            self.view_compact.flash_charging(pct, plugged)
            if plugged:
                self.on_battery_event(t("alert_battery_plugged"), f"{t('sys_battery')} %{pct} · {t('sys_charging')}", "battery_charging")
            else:
                self.on_battery_event(t("alert_battery_unplugged"), f"{t('sys_battery')} %{pct}", "battery")
        else:
            self._last_fast_plugged = plugged

    # ── 3-Dot Options Action Handlers ──────────────────────────────────

    def _optimize_ram(self) -> None:
        try:
            import psutil
            psapi = ctypes.windll.psapi
            kernel32 = ctypes.windll.kernel32
            mem_before = psutil.virtual_memory().percent
            freed_count = 0
            for proc in psutil.process_iter(['pid']):
                try:
                    h = kernel32.OpenProcess(0x001F0FFF, False, proc.info['pid'])
                    if h:
                        psapi.EmptyWorkingSet(h)
                        kernel32.CloseHandle(h)
                        freed_count += 1
                except Exception:
                    pass
            mem_after = psutil.virtual_memory().percent
            diff = max(0.0, mem_before - mem_after)
            self.view_alert.display(
                t("alert_ram_cleared"),
                t("alert_ram_done", percent=f"{mem_after:.0f}", freed=f"{diff:.0f}"),
                icon_type="clipboard"
            )
            self.view_expanded.pet_lounge.pet_avatar.trigger_happy_flip()
            self.transition_to(IslandState.ALERT)
            self._alert_timer.start(2800)
        except Exception:
            pass

    @pyqtSlot(int)
    def on_brightness_changed(self, percent: int) -> None:
        if not self._initial_brightness_synced:
            self._initial_brightness_synced = True
            return
        if self._state == IslandState.EXPANDED or self._dnd_active:
            return
        self.view_alert.display(
            title=t("alert_brightness", percent=percent),
            subtitle="",
            icon_type="sun",
            pixmap=None,
            show_visualizer=False,
        )
        self.transition_to(IslandState.ALERT)
        self._alert_timer.start(2200)

    def _take_screenshot(self) -> None:
        try:
            screen = QApplication.primaryScreen()
            if screen:
                pix = screen.grabWindow(0)
                clipboard = QApplication.clipboard()
                if clipboard:
                    clipboard.setPixmap(pix)
                self.view_alert.display(
                    t("alert_screenshot_title"),
                    t("alert_screenshot_desc"),
                    icon_type="clipboard"
                )
                self.view_expanded.pet_lounge.pet_avatar.trigger_happy_flip()
                self.transition_to(IslandState.ALERT)
                self._alert_timer.start(2500)
        except Exception:
            pass

    def _toggle_power_mode(self) -> None:
        try:
            if not hasattr(self, '_power_mode_perf'):
                self._power_mode_perf = False
            self._power_mode_perf = not self._power_mode_perf
            mode_name = t("power_high") if self._power_mode_perf else t("power_balanced")
            guid = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c" if self._power_mode_perf else "381b4222-f694-41f0-9685-ff5bb260df2e"
            subprocess.Popen(f"powercfg /setactive {guid}", shell=True)
            self.view_alert.display(t("alert_power_title"), mode_name, icon_type="battery_charging")
            self.transition_to(IslandState.ALERT)
            self._alert_timer.start(2400)
        except Exception:
            pass

    def _toggle_pomodoro(self) -> None:
        if self._pomodoro_active:
            self._pomodoro_active = False
            self._pomodoro_timer.stop()
            self.view_compact.set_playing(False, "")
            self.view_alert.display(t("alert_pomodoro_off"), t("alert_pomodoro_cancel"), icon_type="clipboard", show_visualizer=False)
            self.transition_to(IslandState.ALERT)
            self._alert_timer.start(2200)
        else:
            self._pomodoro_active = True
            self._pomodoro_secs = 25 * 60
            self._pomodoro_timer.start()
            self.view_compact.set_playing(True, "25:00")
            self.view_alert.display(t("alert_pomodoro_on"), t("alert_pomodoro_desc"), icon_type="clipboard", show_visualizer=False)
            self.transition_to(IslandState.ALERT)
            self._alert_timer.start(2800)

    def _tick_pomodoro(self) -> None:
        if not self._pomodoro_active:
            return
        self._pomodoro_secs -= 1
        m = self._pomodoro_secs // 60
        s = self._pomodoro_secs % 60
        if self._pomodoro_secs <= 0:
            self._pomodoro_active = False
            self._pomodoro_timer.stop()
            self.view_compact.set_playing(False, "")
            self.view_alert.display(t("alert_pomodoro_done"), t("alert_break_desc"), icon_type="clipboard", show_visualizer=False)
            self.view_expanded.pet_lounge.pet_avatar.trigger_happy_flip()
            self.transition_to(IslandState.ALERT)
            self._alert_timer.start(4500)
        else:
            if self._state == IslandState.COMPACT:
                self.view_compact.set_playing(True, f"{m}:{s:02d}")

    def _bring_music_app(self) -> None:
        try:
            cmd = """powershell -Command "$p = Get-Process | Where-Object { $_.MainWindowTitle -match 'Spotify|YouTube|Music' } | Select-Object -First 1; if ($p) { (New-Object -ComObject WScript.Shell).AppActivate($p.Id) }" """
            subprocess.Popen(cmd, shell=True)
            self.view_alert.display(t("alert_music_window"), t("alert_brought_forward"), icon_type="music", show_visualizer=False)
            self.transition_to(IslandState.ALERT)
            self._alert_timer.start(2000)
        except Exception:
            pass

    def _toggle_dnd(self) -> None:
        self._dnd_active = not self._dnd_active
        title = t("alert_dnd_on") if self._dnd_active else t("alert_dnd_off")
        subtitle = t("alert_muted") if self._dnd_active else t("alert_active")
        self.view_alert.display(title, subtitle, icon_type="clipboard", show_visualizer=False)
        self.transition_to(IslandState.ALERT)
        self._alert_timer.start(2500)

    def _clear_pocket(self) -> None:
        self._pocket_files = []
        self.view_expanded.set_pocket_files([])
        self.file_pocket_updated.emit([])
        self.view_alert.display(t("alert_pocket_cleared"), t("alert_pocket_cleared_desc"), icon_type="clipboard", show_visualizer=False)
        self.transition_to(IslandState.ALERT)
        self._alert_timer.start(2200)

    def _open_sound_settings(self) -> None:
        try:
            os.system("start mmsys.cpl")
        except Exception:
            pass

    @pyqtSlot(str, str, object, str)
    def on_clipboard_event(self, title: str, subtitle: str,
                            pixmap: Optional[QPixmap], icon_type: str) -> None:
        if not self._is_hovered:
            self.view_alert.display(title, subtitle, icon_type=icon_type, pixmap=pixmap,
                                    show_visualizer=False)
            self.transition_to(IslandState.ALERT)
            self._alert_timer.start(Timing.CLIPBOARD_TIMEOUT_MS)

    @pyqtSlot(str, str, str, int)
    def on_ipc_notification(self, title: str, message: str, n_type: str, duration_ms: int) -> None:
        if not self._is_hovered:
            self.view_alert.display(title, message, icon_type="clipboard", pixmap=None,
                                    show_visualizer=False)
            self.transition_to(IslandState.ALERT)
            self._alert_timer.start(max(1500, duration_ms))

    @pyqtSlot(bool)
    def on_caps_lock_changed(self, active: bool) -> None:
        if self._caps_active == active:
            return
        self._caps_active = active
        # Update the dedicated CapsBadgeWidget in CompactCapsuleWidget (zero overlap!)
        self.view_compact.set_caps_lock(active)
        if self._state == IslandState.COMPACT:
            target_w = self._target_compact_width()
            anim = QPropertyAnimation(self, b"islandWidth", self)
            anim.setDuration(190)
            anim.setStartValue(self._width)
            anim.setEndValue(float(target_w))
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            anim.start()
            self._caps_anim = anim
        self.update()

    @pyqtSlot(str, bool)
    def on_bt_audio_changed(self, name: str, connected: bool) -> None:
        self._bt_connected = connected
        self._bt_device_name = name if connected else None
        self.view_compact.set_bluetooth_active(connected)
        if not self._is_hovered:
            verb = t("alert_bt_connected") if connected else t("alert_bt_disconnected")
            self.view_alert.display(
                title=f"{name} {verb} ",
                subtitle=t("alert_bt_device"),
                icon_type="bluetooth"
            )
            self.transition_to(IslandState.ALERT)
            self._alert_timer.start(Timing.ALERT_TIMEOUT_MS)

    @pyqtSlot(str)
    def on_recording_started(self, app_name: str) -> None:
        self._recording_active = True
        self._rec_timer.start()
        if not self._is_hovered:
            self.view_alert.display(
                title=t("alert_recording_title", app=app_name),
                subtitle=t("alert_recording"),
                icon_type="record_dot"
            )
            self.transition_to(IslandState.ALERT)
            self._alert_timer.start(Timing.ALERT_TIMEOUT_MS)

    @pyqtSlot()
    def on_recording_stopped(self) -> None:
        self._recording_active = False
        self._rec_timer.stop()
        self.update()

    @pyqtSlot(str, str)
    def on_venv_activated(self, name: str, py_version: str) -> None:
        self._venv_info = f"{name} • {py_version}"
        self.view_compact.lbl_center.setText(f"{name}")
        self.update()

    @pyqtSlot()
    def on_venv_deactivated(self) -> None:
        self._venv_info = None
        self.view_compact.lbl_center.setText("")
        self.update()

    @pyqtSlot(object, object)
    def on_pet_state_changed(self, state, evolution) -> None:
        self.view_expanded.update_pet(state)

    @pyqtSlot(str)
    def on_pet_reminder(self, kind: str) -> None:
        """Smart Notification Badge: illuminates badge without jarringly expanding island!"""
        self._has_unread_notification = True
        self.view_compact.set_notification_badge(True)
        if kind == "water":
            self._pending_notification_text = t("pet_reminder_water")
        else:
            self._pending_notification_text = t("pet_reminder_eye")

    @pyqtSlot(str, str, str)
    def on_weather_updated(self, temp: str, condition: str, icon_type: str) -> None:
        """Update the weather pill in the expanded dashboard header."""
        self.view_expanded.update_weather(temp, condition, icon_type)
        self.view_hover.update_weather(temp, icon_type)

    @pyqtSlot(bool, str, str, str)
    def on_hardware_device_event(self, is_connected: bool, title: str, subtitle: str, icon_type: str) -> None:
        """USB / hardware device plug/unplug notification in the island."""
        if not self._is_hovered and self._state != IslandState.EXPANDED:
            self.view_alert.display(
                title=title,
                subtitle=subtitle,
                icon_type=icon_type,
                pixmap=None,
                show_visualizer=False
            )
            self.transition_to(IslandState.ALERT)
            self._alert_timer.start(3500)

    # ── paintEvent ──────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())
        radius = min(self._current_radius(), (h - 1.0) / 2.0)
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)

        # 1. Glass fill (Deep obsidian capsule with zero rectangular blur artifacts!)
        grad = QLinearGradient(0.0, 0.0, 0.0, h)
        if self._is_hovered:
            grad.setColorAt(0.0, QColor(13, 14, 15, 255))
            grad.setColorAt(1.0, QColor(7, 8, 9, 255))
        else:
            grad.setColorAt(0.0, QColor(9, 10, 11, 255))
            grad.setColorAt(1.0, QColor(5, 6, 7, 255))
        painter.fillPath(path, QBrush(grad))

        # 2. Specular top highlight shimmer
        spec_path = QPainterPath()
        spec_path.addRoundedRect(QRectF(1.0, 1.0, w - 2.0, 2.0), 1.0, 1.0)
        painter.fillPath(spec_path, QBrush(Palette.BG_SPECULAR))

        # 3. Border & Aurora Glass Glow for Drag-Drop
        if self._is_drag_hover:
            # Elegant glowing aurora halo (zero ugly dashed lines!)
            glow_pen = QPen(QColor(225, 228, 232, 150), 2.0)
            painter.setPen(glow_pen)
            painter.setBrush(QBrush(QColor(225, 228, 232, 22)))
            painter.drawPath(path)
        else:
            border_grad = QLinearGradient(0.0, 0.0, 0.0, h)
            border_grad.setColorAt(0.0, Palette.BG_BORDER_TOP)
            border_grad.setColorAt(0.5, Palette.BG_BORDER_SIDE)
            border_grad.setColorAt(1.0, Palette.BG_BORDER_BOTTOM)
            painter.setPen(QPen(QBrush(border_grad), 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

        # 4. Caps Lock badge is now a dedicated CapsBadgeWidget in the CompactCapsuleWidget layout.
        # No paintEvent drawing needed — the widget handles its own rendering without overlaps.

        # 5. Screen recording pulsing dot on left
        if self._recording_active and self._state == IslandState.COMPACT:
            alpha = int((math.sin(self._recording_pulse_phase) * 0.4 + 0.6) * 255)
            rec_color = QColor(239, 68, 68, alpha)
            painter.setBrush(QBrush(rec_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(6.0, h / 2.0), 3.5, 3.5)
