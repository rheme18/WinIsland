"""
WinIsland - Configuration & Design Tokens
Author: WinIsland System Architecture
"""

from PyQt6.QtGui import QColor


class Dimensions:
    """Island geometry dimension presets."""
    TOP_MARGIN: int = 10

    # 1. Compact Idle State (Sleek hardware pill)
    COMPACT_WIDTH: int = 180
    COMPACT_HEIGHT: int = 32
    RADIUS_COMPACT: int = 16

    # 2. Horizontal Alert / Pill Notification State (iPhone Dynamic Island alert style)
    ALERT_WIDTH: int = 390
    ALERT_HEIGHT: int = 36
    RADIUS_ALERT: int = 18

    # 3. Hover preview: concise horizontal summary, never the full dashboard.
    HOVER_WIDTH: int = 420
    HOVER_HEIGHT: int = 36

    # 4. Expanded Full Dashboard State — Spacious layout with dynamic per-section heights
    EXPANDED_WIDTH: int = 620
    EXPANDED_HEIGHT: int = 175
    EXPANDED_CC_HEIGHT: int = 210
    EXPANDED_CAL_HEIGHT: int = 255
    EXPANDED_PIXEL_HEIGHT: int = 245
    EXPANDED_AI_HEIGHT: int = 280
    RADIUS_EXPANDED: int = 26

    # Caps Lock badge extra width on compact right side (comfortable spacing for visualizer + arrow)
    CAPS_BADGE_EXTRA: int = 28


class Timing:
    """Animation and auto-collapse durations in milliseconds."""
    ANIMATION_SPRING_MS: int = 240
    ALERT_TIMEOUT_MS: int = 3000
    BANNER_TIMEOUT_MS: int = 3000
    CLIPBOARD_TIMEOUT_MS: int = 2200
    HOVER_LEAVE_DELAY_MS: int = 90
    BATTERY_POLL_INTERVAL_MS: int = 250    # Responsive charge events without tight polling.
    TELEMETRY_POLL_INTERVAL_MS: int = 1500
    MEDIA_POLL_INTERVAL_MS: int = 1000
    PULSE_CYCLE_MS: int = 1000
    VOLUME_SYNC_INTERVAL_MS: int = 400


class Thresholds:
    """Telemetry alert thresholds."""
    CPU_CRITICAL_PERCENT: float = 98.0
    RAM_CRITICAL_PERCENT: float = 98.0
    BATTERY_LOW_PERCENT: float = 20.0


class Palette:
    """High-contrast dark obsidian design system colors with glass accents."""
    BG_SURFACE_TOP: QColor = QColor(8, 9, 10, 255)
    BG_SURFACE_BOTTOM: QColor = QColor(5, 6, 7, 255)
    BG_SURFACE_HOVER_TOP: QColor = QColor(14, 15, 16, 255)
    BG_SURFACE_HOVER_BOTTOM: QColor = QColor(8, 9, 10, 255)

    # Borders & Highlights (Ultra-thin crisp Apple specular border)
    BG_BORDER_TOP: QColor = QColor(255, 255, 255, 28)
    BG_BORDER_SIDE: QColor = QColor(255, 255, 255, 14)
    BG_BORDER_BOTTOM: QColor = QColor(255, 255, 255, 8)

    # Specular highlight strip
    BG_SPECULAR: QColor = QColor(255, 255, 255, 0)

    # Text
    TEXT_PRIMARY: QColor = QColor(248, 249, 250)
    TEXT_SECONDARY: QColor = QColor(161, 161, 170)
    TEXT_MUTED: QColor = QColor(113, 113, 122)

    # Accents
    ACCENT_MEDIA: QColor = QColor(225, 228, 232)
    ACCENT_CPU: QColor = QColor(205, 210, 216)
    ACCENT_RAM: QColor = QColor(164, 170, 178)
    ACCENT_BATTERY: QColor = QColor(220, 224, 228)
    ACCENT_BATTERY_LOW: QColor = QColor(245, 158, 11)  # Amber
    ACCENT_SUCCESS: QColor = QColor(220, 224, 228)
    ACCENT_CRITICAL: QColor = QColor(239, 68, 68)      # Crimson pulse
    ACCENT_PRIVACY_MIC: QColor = QColor(249, 115, 22)  # Amber Orange
    ACCENT_PRIVACY_CAM: QColor = QColor(34, 197, 94)   # Emerald Green
    ACCENT_RECORDING: QColor = QColor(239, 68, 68)     # Recording red
    ACCENT_BLUETOOTH: QColor = QColor(220, 224, 228)
    ACCENT_AI: QColor = QColor(220, 224, 228)

    # Control Buttons
    BTN_BG: QColor = QColor(255, 255, 255, 16)
    BTN_BG_HOVER: QColor = QColor(255, 255, 255, 36)
    BTN_PLAY_BG: QColor = QColor(248, 249, 250)
    BTN_PLAY_BG_HOVER: QColor = QColor(255, 255, 255)
    BTN_PLAY_ICON: QColor = QColor(14, 15, 18)


class Typography:
    """System typography configurations."""
    FONT_FAMILY: str = "Segoe UI"
    FONT_DISPLAY: str = "Segoe UI Semibold"
    FONT_CODE: str = "Cascadia Code, Consolas, monospace"


IPC_PIPE_NAME: str = "WinIsland_IPC"
# Keep accepting notifications from scripts written before the WinIsland rename.
LEGACY_IPC_PIPE_NAME: str = "RhemeIsland_IPC"
