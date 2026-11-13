"""
WinIsland - Apple iOS Control Center Pro Widget
Clean vector iconography, zero emojis, icon-first squircle action tiles,
and dual sleek monochrome sliders for Volume and Brightness.
"""

import subprocess
import os
from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPainterPath
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QPushButton, QSizePolicy
)

from core.config import Palette, Typography
from modules.i18n import t, I18nManager
from modules.brightness import BrightnessManager
from ui.slider import ModernSlider


class SliderVectorIcon(QWidget):
    """Clean monochrome vector icon for sliders (speaker and sun)."""
    def __init__(self, icon_type: str = "speaker", size: int = 16, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.icon_type = icon_type
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = float(self.width())
        h = float(self.height())
        cx = w / 2.0
        cy = h / 2.0
        color = QColor(255, 255, 255, 210)
        painter.setPen(QPen(color, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))

        if self.icon_type == "speaker":
            # Speaker cone & body
            p = QPainterPath()
            p.moveTo(cx - 5.0, cy - 2.5)
            p.lineTo(cx - 2.0, cy - 2.5)
            p.lineTo(cx + 2.0, cy - 5.5)
            p.lineTo(cx + 2.0, cy + 5.5)
            p.lineTo(cx - 2.0, cy + 2.5)
            p.lineTo(cx - 5.0, cy + 2.5)
            p.closeSubpath()
            painter.setBrush(QBrush(color))
            painter.drawPath(p)
            # Mini sound wave
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(QRectF(cx + 2.5, cy - 3.5, 4.0, 7.0), -60 * 16, 120 * 16)
        elif self.icon_type == "sun":
            # Sun center circle
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QRectF(cx - 2.8, cy - 2.8, 5.6, 5.6))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            # Sun rays (8 rays)
            for deg in (0, 45, 90, 135, 180, 225, 270, 315):
                rad = deg * 3.14159 / 180.0
                x1 = cx + 4.2 * float(math.cos(rad))
                y1 = cy + 4.2 * float(math.sin(rad))
                x2 = cx + 6.2 * float(math.cos(rad))
                y2 = cy + 6.2 * float(math.sin(rad))
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        painter.end()


import math


class AppleSquircleTile(QPushButton):
    """
    Apple iOS Control Center Squircle Icon Tile.
    Icon-first design with a subtle single-word label below.
    Zero emojis, pure vector rendering, tactile spring press feedback.
    """
    def __init__(self, icon_type: str, label_text: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.icon_type = icon_type
        self.label_text = label_text
        self._is_active = False
        self.setFixedHeight(50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_active(self, active: bool) -> None:
        if self._is_active != active:
            self._is_active = active
            self.update()

    def is_active(self) -> bool:
        return self._is_active

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        w = float(rect.width())
        h = float(rect.height())

        # Apple Glass Squircle Surface
        if self.isDown():
            bg_color = QColor(255, 255, 255, 50)
            border_color = QColor(255, 255, 255, 70)
        elif self._is_active:
            bg_color = QColor(255, 255, 255, 220)
            border_color = QColor(255, 255, 255, 240)
        elif self.underMouse():
            bg_color = QColor(255, 255, 255, 26)
            border_color = QColor(255, 255, 255, 45)
        else:
            bg_color = QColor(255, 255, 255, 14)
            border_color = QColor(255, 255, 255, 20)

        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 1.0))
        painter.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), 11.0, 11.0)

        # Colors
        fg_color = QColor(14, 15, 18) if self._is_active else QColor(250, 250, 252)

        # Draw Vector Icon centered on top half
        cx = w / 2.0
        cy = 19.0
        self._draw_vector_icon(painter, cx, cy, fg_color)

        # Draw Label Text on bottom half (short single-word, crisp 8.5px)
        painter.setPen(fg_color if self._is_active else QColor(255, 255, 255, 180))
        font = QFont("Segoe UI", 8)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)

        text_rect = QRectF(0, 31.0, w, 16.0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.label_text)

        painter.end()

    def _draw_vector_icon(self, painter: QPainter, cx: float, cy: float, color: QColor) -> None:
        painter.setPen(QPen(color, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        it = self.icon_type
        if it == "wifi":
            # Wi-Fi concentric waves
            painter.drawArc(QRectF(cx - 7.5, cy - 7, 15, 15), 45 * 16, 90 * 16)
            painter.drawArc(QRectF(cx - 4.5, cy - 4, 9, 9), 45 * 16, 90 * 16)
            painter.setBrush(QBrush(color))
            painter.drawEllipse(QRectF(cx - 1.2, cy + 2.5, 2.4, 2.4))

        elif it == "bluetooth":
            # Bluetooth Rune
            p = QPainterPath()
            p.moveTo(cx, cy - 7)
            p.lineTo(cx, cy + 7)
            p.lineTo(cx + 4.0, cy + 3.5)
            p.lineTo(cx - 4.0, cy - 2.5)
            p.moveTo(cx - 4.0, cy + 2.5)
            p.lineTo(cx + 4.0, cy - 3.5)
            p.lineTo(cx, cy - 7)
            painter.drawPath(p)

        elif it == "night_light":
            # Crescent Moon
            p = QPainterPath()
            p.moveTo(cx + 2.5, cy - 6.5)
            p.cubicTo(cx - 6.5, cy - 5.5, cx - 6.5, cy + 5.5, cx + 2.5, cy + 6.5)
            p.cubicTo(cx - 2.5, cy + 3.5, cx - 2.5, cy - 3.5, cx + 2.5, cy - 6.5)
            painter.setBrush(QBrush(color))
            painter.drawPath(p)

        elif it == "dnd":
            # Minus / Do Not Disturb
            painter.drawEllipse(QRectF(cx - 6.5, cy - 6.5, 13, 13))
            painter.drawLine(QPointF(cx - 4.0, cy), QPointF(cx + 4.0, cy))

        elif it == "mic_mute":
            # Microphone with slash
            painter.drawRoundedRect(QRectF(cx - 2.5, cy - 5.5, 5, 8), 2.5, 2.5)
            painter.drawArc(QRectF(cx - 4.5, cy - 3.0, 9, 7), 0, -180 * 16)
            painter.drawLine(QPointF(cx, cy + 4.0), QPointF(cx, cy + 6.5))
            painter.drawLine(QPointF(cx - 5.5, cy - 6.0), QPointF(cx + 5.5, cy + 6.0))

        elif it == "snip":
            # Clean Camera / Snip Tool icon
            painter.drawRoundedRect(QRectF(cx - 6.5, cy - 4.0, 13, 10), 2.5, 2.5)
            painter.drawEllipse(QRectF(cx - 2.5, cy - 1.5, 5, 5))
            painter.drawRect(QRectF(cx - 3.5, cy - 6.0, 3, 2))

        elif it == "lock":
            # Lock body & shackle
            painter.drawRoundedRect(QRectF(cx - 5.0, cy - 2.0, 10, 8), 2.0, 2.0)
            painter.drawArc(QRectF(cx - 3.5, cy - 6.5, 7, 7), 0, 180 * 16)

        elif it == "settings":
            # Minimalist Gear
            painter.drawEllipse(QRectF(cx - 5.5, cy - 5.5, 11, 11))
            painter.drawEllipse(QRectF(cx - 2.2, cy - 2.2, 4.4, 4.4))
            for ang in (0, 45, 90, 135, 180, 225, 270, 315):
                rad = ang * 3.14159 / 180.0
                x1 = cx + 5.5 * float(math.cos(rad))
                y1 = cy + 5.5 * float(math.sin(rad))
                x2 = cx + 7.0 * float(math.cos(rad))
                y2 = cy + 7.0 * float(math.sin(rad))
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))


class IOSControlCenterWidget(QWidget):
    """
    WinIsland Apple iOS Control Center Dashboard View.
    Zero emojis, pure monochrome vector iconography, and balanced squircle layout.
    """
    volume_changed = pyqtSignal(int)
    open_settings_requested = pyqtSignal()
    lock_pc_requested = pyqtSignal()
    take_screenshot_requested = pyqtSignal()
    dnd_toggled = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._brightness_mgr = BrightnessManager.get_instance()
        self._brightness_mgr.brightness_changed.connect(self._on_brightness_updated)
        I18nManager.get_instance().language_changed.connect(self._on_language_changed)
        self._setup_ui()
        self._on_language_changed(I18nManager.get_instance().current_language)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 6)
        layout.setSpacing(8)

        # ── Row 1: Dual Monochrome Sliders (Volume & Brightness) ─────────
        sliders_row = QHBoxLayout()
        sliders_row.setSpacing(12)

        # Volume Slider
        vol_box = QHBoxLayout()
        vol_box.setSpacing(6)
        self.ic_vol = SliderVectorIcon("speaker", 16, self)
        self.slider_vol = ModernSlider(is_range_100=True, accent_color=Palette.ACCENT_CPU)
        self.slider_vol.setFixedHeight(14)
        self.slider_vol.valueChanged.connect(lambda v: self.volume_changed.emit(int(v)))
        vol_box.addWidget(self.ic_vol)
        vol_box.addWidget(self.slider_vol, stretch=1)
        sliders_row.addLayout(vol_box, stretch=1)

        # Brightness Slider
        bri_box = QHBoxLayout()
        bri_box.setSpacing(6)
        self.ic_bri = SliderVectorIcon("sun", 16, self)
        self.slider_bri = ModernSlider(is_range_100=True, accent_color=Palette.ACCENT_CPU)
        self.slider_bri.setFixedHeight(14)
        self.slider_bri.setValue(self._brightness_mgr.get_brightness())
        self.slider_bri.valueChanged.connect(lambda v: self._brightness_mgr.set_brightness(int(v)))
        bri_box.addWidget(self.ic_bri)
        bri_box.addWidget(self.slider_bri, stretch=1)
        sliders_row.addLayout(bri_box, stretch=1)

        layout.addLayout(sliders_row)

        # ── Row 2 & 3: 4x2 Apple Squircle Tiles Grid ─────────────────────
        grid = QGridLayout()
        grid.setSpacing(7)
        grid.setContentsMargins(0, 0, 0, 0)

        # Row 1 of tiles
        self.tile_wifi = AppleSquircleTile("wifi", "Wi-Fi", self)
        self.tile_wifi.clicked.connect(self._open_wifi_settings)
        grid.addWidget(self.tile_wifi, 0, 0)

        self.tile_bt = AppleSquircleTile("bluetooth", "Bluetooth", self)
        self.tile_bt.clicked.connect(self._open_bt_settings)
        grid.addWidget(self.tile_bt, 0, 1)

        self.tile_dnd = AppleSquircleTile("dnd", t("cc_dnd"), self)
        self.tile_dnd.clicked.connect(self._toggle_dnd)
        grid.addWidget(self.tile_dnd, 0, 2)

        self.tile_night = AppleSquircleTile("night_light", t("cc_night_light"), self)
        self.tile_night.clicked.connect(self._open_night_light)
        grid.addWidget(self.tile_night, 0, 3)

        # Row 2 of tiles
        self.tile_snip = AppleSquircleTile("snip", "Kırp", self)
        self.tile_snip.clicked.connect(self.take_screenshot_requested.emit)
        grid.addWidget(self.tile_snip, 1, 0)

        self.tile_mic = AppleSquircleTile("mic_mute", "Mikrofon", self)
        self.tile_mic.clicked.connect(self._toggle_mic_mute)
        grid.addWidget(self.tile_mic, 1, 1)

        self.tile_lock = AppleSquircleTile("lock", "Kilitle", self)
        self.tile_lock.clicked.connect(self.lock_pc_requested.emit)
        grid.addWidget(self.tile_lock, 1, 2)

        self.tile_settings = AppleSquircleTile("settings", "Ayarlar", self)
        self.tile_settings.clicked.connect(self.open_settings_requested.emit)
        grid.addWidget(self.tile_settings, 1, 3)

        layout.addLayout(grid)

    def set_volume(self, val: int) -> None:
        self.slider_vol.setValue(val)

    def _on_brightness_updated(self, val: int) -> None:
        self.slider_bri.setValue(val)

    def _open_wifi_settings(self) -> None:
        os.system("start ms-settings:network-wifi")

    def _open_bt_settings(self) -> None:
        os.system("start ms-settings:bluetooth")

    def _open_night_light(self) -> None:
        os.system("start ms-settings:nightlight")

    def _toggle_dnd(self) -> None:
        self.tile_dnd.set_active(not self.tile_dnd.is_active())
        self.dnd_toggled.emit()

    def _toggle_mic_mute(self) -> None:
        self.tile_mic.set_active(not self.tile_mic.is_active())

    def _on_language_changed(self, lang: str) -> None:
        # Update tiles labels based on language
        is_tr = (lang == "tr")
        self.tile_dnd.label_text = t("cc_dnd")
        self.tile_night.label_text = t("cc_night_light")
        self.tile_snip.label_text = t("cc_snip")
        self.tile_mic.label_text = t("cc_mic_mute")
        self.tile_lock.label_text = t("cc_lock")
        self.tile_settings.label_text = t("cc_settings")
        for tile in (self.tile_dnd, self.tile_night, self.tile_snip, self.tile_mic,
                     self.tile_lock, self.tile_settings):
            tile.update()
        self.update()
