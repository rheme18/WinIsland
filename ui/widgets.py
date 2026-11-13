"""
WinIsland - UI Content Widgets & Controls
Hardware-accelerated vector icons, media scrubber, master volume,
AI Interactive Drawer, Pocket Mode (drag-in/drag-out), and Pixel companion lounge.
"""

import math
import subprocess
import ctypes
import os
from typing import Optional, List
from PyQt6.QtCore import (
    Qt, QTimer, QRectF, pyqtSignal, pyqtProperty, QPointF, QUrl, QMimeData,
    QPropertyAnimation, QEasingCurve
)
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QPainterPath, QPixmap, QLinearGradient, QDrag
)
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSizePolicy, QLineEdit, QTextEdit, QMenu, QScrollArea,
    QStackedWidget, QGraphicsOpacityEffect
)

from core.config import Palette, Typography, Timing
from ui.pet_widget import PetWidget, PetLoungeWidget
from modules.i18n import t, I18nManager
from modules.settings_manager import SettingsManager
from modules.todo_manager import TodoManager
from ui.calendar_todo_widget import CalendarTodoWidget
from ui.ios_cc_widget import IOSControlCenterWidget
from ui.page_dots import PageDotsIndicator


# ---------------------------------------------------------------------------
# VectorIcon — crisp resolution-independent icon renderer
# ---------------------------------------------------------------------------

class VectorIcon(QWidget):
    def __init__(self, icon_type: str = "camera_lens", size: int = 20,
                 color: Optional[QColor] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.icon_type = icon_type
        self._size = size
        self.color = color or Palette.TEXT_PRIMARY
        self.value_percent: float = 100.0
        self.setFixedSize(size, size)

    def set_type(self, icon_type: str, color: Optional[QColor] = None) -> None:
        self.icon_type = icon_type
        if color:
            self.color = color
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = float(self.width())
        h = float(self.height())
        self._draw(painter, w, h)

    def _draw(self, painter: QPainter, w: float, h: float) -> None:
        if self.icon_type == "camera_lens":
            center = QPointF(w / 2.0, h / 2.0)
            r = min(w, h) / 2.0 - 1.0
            painter.setBrush(QBrush(QColor(18, 20, 26)))
            painter.setPen(QPen(QColor(255, 255, 255, 18), 1.0))
            painter.drawEllipse(center, r, r)
            painter.setBrush(QBrush(QColor(6, 7, 10)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, r * 0.72, r * 0.72)
            glint_pos = QPointF(center.x() - r * 0.28, center.y() - r * 0.28)
            painter.setBrush(QBrush(QColor(60, 90, 140, 190)))
            painter.drawEllipse(glint_pos, r * 0.25, r * 0.25)

        elif self.icon_type == "warning":
            cx = w / 2.0; cy = h / 2.0
            tw = min(w, h) * 0.88
            th = tw * 0.84
            top_y = cy - th / 2.0
            bot_y = cy + th / 2.0
            tri = QPainterPath()
            tri.moveTo(cx, top_y)
            tri.lineTo(cx + tw / 2.0, bot_y)
            tri.lineTo(cx - tw / 2.0, bot_y)
            tri.closeSubpath()
            painter.setBrush(QBrush(QColor(245, 158, 11)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(tri)
            # Crisp dark exclamation mark
            painter.setPen(QPen(QColor(14, 15, 18), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(cx, top_y + th * 0.35), QPointF(cx, top_y + th * 0.65))
            painter.setBrush(QBrush(QColor(14, 15, 18)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(cx, bot_y - 2.8), 1.1, 1.1)

        elif self.icon_type in ("battery", "battery_charging", "battery_low"):
            bw = w * 0.78; bh = h * 0.44
            bx = (w - bw - 2.0) / 2.0; by = (h - bh) / 2.0
            painter.setPen(QPen(QColor(255, 255, 255, 140), 1.3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(bx, by, bw, bh), 2.5, 2.5)
            cap_h = bh * 0.42; cap_y = by + (bh - cap_h) / 2.0
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 140)))
            painter.drawRoundedRect(QRectF(bx + bw + 0.8, cap_y, 2.0, cap_h), 1.0, 1.0)
            fill_pct = max(0.05, min(1.0, self.value_percent / 100.0))
            fill_w = (bw - 3.0) * fill_pct
            fill_color = Palette.ACCENT_BATTERY
            if self.icon_type == "battery_low" or self.value_percent <= 20.0:
                fill_color = Palette.ACCENT_BATTERY_LOW
            painter.setBrush(QBrush(fill_color))
            painter.drawRoundedRect(QRectF(bx + 1.5, by + 1.5, max(2.0, fill_w), bh - 3.0), 1.5, 1.5)
            if self.icon_type == "battery_charging":
                bolt = QPainterPath()
                bolt.moveTo(bx + bw * 0.55, by - 1.0)
                bolt.lineTo(bx + bw * 0.35, by + bh * 0.55)
                bolt.lineTo(bx + bw * 0.52, by + bh * 0.55)
                bolt.lineTo(bx + bw * 0.45, by + bh + 1.0)
                bolt.lineTo(bx + bw * 0.68, by + bh * 0.45)
                bolt.lineTo(bx + bw * 0.52, by + bh * 0.45)
                bolt.closeSubpath()
                painter.setBrush(QBrush(QColor(255, 255, 255)))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawPath(bolt)

        elif self.icon_type == "speaker":
            sw = min(w, h)
            ox = (w - sw) / 2.0; oy = (h - sw) / 2.0
            cone = QPainterPath()
            cone.moveTo(ox + sw * 0.12, oy + sw * 0.35)
            cone.lineTo(ox + sw * 0.36, oy + sw * 0.35)
            cone.lineTo(ox + sw * 0.60, oy + sw * 0.18)
            cone.lineTo(ox + sw * 0.60, oy + sw * 0.82)
            cone.lineTo(ox + sw * 0.36, oy + sw * 0.65)
            cone.lineTo(ox + sw * 0.12, oy + sw * 0.65)
            cone.closeSubpath()
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(cone)
            painter.setPen(QPen(self.color, 1.25, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(QRectF(ox + sw * 0.44, oy + sw * 0.32, sw * 0.30, sw * 0.36), -55 * 16, 110 * 16)
            painter.drawArc(QRectF(ox + sw * 0.52, oy + sw * 0.20, sw * 0.38, sw * 0.60), -55 * 16, 110 * 16)

        elif self.icon_type == "speaker_mute":
            sw = min(w, h)
            ox = (w - sw) / 2.0; oy = (h - sw) / 2.0
            cone = QPainterPath()
            cone.moveTo(ox + sw * 0.12, oy + sw * 0.35)
            cone.lineTo(ox + sw * 0.36, oy + sw * 0.35)
            cone.lineTo(ox + sw * 0.60, oy + sw * 0.18)
            cone.lineTo(ox + sw * 0.60, oy + sw * 0.82)
            cone.lineTo(ox + sw * 0.36, oy + sw * 0.65)
            cone.lineTo(ox + sw * 0.12, oy + sw * 0.65)
            cone.closeSubpath()
            painter.setBrush(QBrush(Palette.TEXT_MUTED))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(cone)
            painter.setPen(QPen(Palette.ACCENT_CRITICAL, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(ox + sw * 0.70, oy + sw * 0.36), QPointF(ox + sw * 0.90, oy + sw * 0.64))
            painter.drawLine(QPointF(ox + sw * 0.90, oy + sw * 0.36), QPointF(ox + sw * 0.70, oy + sw * 0.64))

        elif self.icon_type == "usb":
            cx = w / 2.0; cy = h / 2.0
            painter.setPen(QPen(self.color, 1.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            # Center stem
            painter.drawLine(QPointF(cx, cy + h * 0.32), QPointF(cx, cy - h * 0.24))
            # Left branch
            painter.drawLine(QPointF(cx, cy + h * 0.06), QPointF(cx - w * 0.26, cy - h * 0.08))
            painter.drawLine(QPointF(cx - w * 0.26, cy - h * 0.08), QPointF(cx - w * 0.26, cy - h * 0.22))
            # Right branch
            painter.drawLine(QPointF(cx, cy - h * 0.04), QPointF(cx + w * 0.26, cy - h * 0.12))
            painter.drawLine(QPointF(cx + w * 0.26, cy - h * 0.12), QPointF(cx + w * 0.26, cy - h * 0.22))
            # Top arrow
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            arr = QPainterPath()
            arr.moveTo(cx, cy - h * 0.38)
            arr.lineTo(cx - w * 0.12, cy - h * 0.24)
            arr.lineTo(cx + w * 0.12, cy - h * 0.24)
            arr.closeSubpath()
            painter.drawPath(arr)
            # Shapes
            painter.drawEllipse(QPointF(cx - w * 0.26, cy - h * 0.24), 1.8, 1.8)
            painter.drawRect(QRectF(cx + w * 0.26 - 1.8, cy - h * 0.24 - 1.8, 3.6, 3.6))

        elif self.icon_type == "weather_sun":
            cx = w / 2.0; cy = h / 2.0
            r = min(w, h) * 0.23
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(cx, cy), r, r)
            painter.setPen(QPen(self.color, 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            import math
            for i in range(8):
                ang = i * (math.pi / 4.0)
                r1 = r + 2.0
                r2 = r + 4.2
                x1 = cx + math.cos(ang) * r1
                y1 = cy + math.sin(ang) * r1
                x2 = cx + math.cos(ang) * r2
                y2 = cy + math.sin(ang) * r2
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        elif self.icon_type in ("weather_cloud", "weather_partly_cloudy", "weather_rain", "weather_snow"):
            cx = w / 2.0; cy = h / 2.0
            if self.icon_type == "weather_partly_cloudy":
                painter.setBrush(QBrush(QColor(251, 191, 36)))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(cx + 2.8, cy - 3.2), 2.8, 2.8)

            cloud = QPainterPath()
            cloud.moveTo(cx - 4.5, cy + 2.0)
            cloud.arcTo(QRectF(cx - 5.5, cy - 0.5, 3.5, 3.5), 180, 90)
            cloud.arcTo(QRectF(cx - 3.5, cy - 3.2, 4.2, 4.2), 160, 140)
            cloud.arcTo(QRectF(cx + 0.5, cy - 1.8, 3.8, 3.8), 70, 120)
            cloud.lineTo(cx + 4.5, cy + 2.0)
            cloud.closeSubpath()
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(cloud)

            if self.icon_type == "weather_rain":
                painter.setPen(QPen(QColor(56, 189, 248), 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.drawLine(QPointF(cx - 2.0, cy + 3.0), QPointF(cx - 2.8, cy + 5.5))
                painter.drawLine(QPointF(cx + 1.8, cy + 3.0), QPointF(cx + 1.0, cy + 5.5))
            elif self.icon_type == "weather_snow":
                painter.setBrush(QBrush(QColor(240, 245, 255)))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(cx - 2.0, cy + 4.0), 1.0, 1.0)
                painter.drawEllipse(QPointF(cx + 1.8, cy + 4.0), 1.0, 1.0)

        elif self.icon_type == "system_chip":
            cx = w / 2.0; cy = h / 2.0
            body = QRectF(cx - 4.0, cy - 4.0, 8.0, 8.0)
            painter.setPen(QPen(self.color, 1.2, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(body, 1.5, 1.5)
            for offset in (-2.5, 0.0, 2.5):
                painter.drawLine(QPointF(cx + offset, cy - 6.0), QPointF(cx + offset, cy - 4.0))
                painter.drawLine(QPointF(cx + offset, cy + 4.0), QPointF(cx + offset, cy + 6.0))
                painter.drawLine(QPointF(cx - 6.0, cy + offset), QPointF(cx - 4.0, cy + offset))
                painter.drawLine(QPointF(cx + 4.0, cy + offset), QPointF(cx + 6.0, cy + offset))

        elif self.icon_type == "lock":
            lx = (w - 11.0) / 2.0; ly = (h - 13.0) / 2.0
            painter.setPen(QPen(self.color, 1.3))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawArc(QRectF(lx + 2.0, ly, 7.0, 8.0), 0, 180 * 16)
            painter.setBrush(QBrush(self.color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(lx, ly + 4.5, 11.0, 8.0), 1.5, 1.5)

        elif self.icon_type == "bluetooth":
            cx = w / 2.0; cy = h / 2.0
            half_h = h * 0.40
            painter.setPen(QPen(self.color, 1.5))
            painter.drawLine(int(cx), int(cy - half_h), int(cx), int(cy + half_h))
            painter.drawLine(int(cx), int(cy - half_h), int(cx + w * 0.30), int(cy - h * 0.18))
            painter.drawLine(int(cx + w * 0.30), int(cy - h * 0.18), int(cx - w * 0.25), int(cy + h * 0.20))
            painter.drawLine(int(cx), int(cy + half_h), int(cx + w * 0.30), int(cy + h * 0.18))
            painter.drawLine(int(cx + w * 0.30), int(cy + h * 0.18), int(cx - w * 0.25), int(cy - h * 0.20))

        elif self.icon_type == "ai_sparkle":
            cx = w / 2.0; cy = h / 2.0
            p = QPainterPath()
            p.moveTo(cx, cy - h * 0.45)
            p.quadTo(cx, cy, cx + w * 0.45, cy)
            p.quadTo(cx, cy, cx, cy + h * 0.45)
            p.quadTo(cx, cy, cx - w * 0.45, cy)
            p.quadTo(cx, cy, cx, cy - h * 0.45)
            painter.setBrush(QBrush(Palette.ACCENT_AI))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(p)

        elif self.icon_type == "clipboard":
            cw = 13.0; ch = 15.0
            cx = (w - cw) / 2.0; cy = (h - ch) / 2.0
            painter.setPen(QPen(Palette.TEXT_PRIMARY, 1.2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(cx, cy, cw, ch), 2.0, 2.0)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(Palette.TEXT_PRIMARY))
            painter.drawRoundedRect(QRectF(cx + cw * 0.25, cy - 1.5, cw * 0.5, 3.0), 1.0, 1.0)
            painter.setPen(QPen(QColor(255, 255, 255, 140), 1.0))
            painter.drawLine(int(cx + 3), int(cy + 6), int(cx + cw - 3), int(cy + 6))
            painter.drawLine(int(cx + 3), int(cy + 9), int(cx + cw - 3), int(cy + 9))


# ---------------------------------------------------------------------------
# AudioVisualizer
# ---------------------------------------------------------------------------

class AudioVisualizer(QWidget):
    def __init__(self, parent: Optional[QWidget] = None, bar_count: int = 3,
                 bar_color: QColor = Palette.ACCENT_MEDIA):
        super().__init__(parent)
        self.bar_count = bar_count
        self.bar_color = bar_color
        self._is_active = False
        self._phase = 0.0
        self.setFixedSize(18, 14)
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._animate_step)

    def set_active(self, active: bool) -> None:
        if self._is_active != active:
            self._is_active = active
            self._sync_timer()
            self.update()

    def _sync_timer(self) -> None:
        if self._is_active and self.isVisible():
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._sync_timer()

    def hideEvent(self, event) -> None:
        self._timer.stop()
        super().hideEvent(event)

    def _animate_step(self) -> None:
        self._phase += 0.25
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = float(self.width())
        h = float(self.height())
        bar_w = 2.5
        gap = (w - (self.bar_count * bar_w)) / max(1, self.bar_count - 1)
        painter.setPen(Qt.PenStyle.NoPen)
        for i in range(self.bar_count):
            if self._is_active:
                osc = math.sin(self._phase + i * 1.4) * 0.5 + 0.5
                bar_h = max(2.5, osc * (h - 2.0))
                painter.setBrush(QBrush(self.bar_color))
            else:
                bar_h = 2.5
                painter.setBrush(QBrush(QColor(100, 100, 110)))
            x = i * (bar_w + gap)
            y = (h - bar_h) / 2.0
            painter.drawRoundedRect(QRectF(x, y, bar_w, bar_h), 1.2, 1.2)


# ---------------------------------------------------------------------------
# ModernSlider
# ---------------------------------------------------------------------------
from ui.slider import ModernSlider


# ---------------------------------------------------------------------------
# ActionButton — Animated glass pill button with tactile press feedback
# ---------------------------------------------------------------------------

class ActionButton(QPushButton):
    def __init__(self, icon_type: str, label: str, parent: Optional[QWidget] = None):
        super().__init__("", parent)
        self.icon_type = icon_type
        self.label = label
        self.setAccessibleName(label)
        if label:
            self.setToolTip(label)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(24)
        self._hover_progress: float = 0.0
        self._press_offset: float = 0.0
        self._hover_anim: Optional[QPropertyAnimation] = None

    def set_label(self, label: str) -> None:
        if self.label != label:
            self.label = label
            self.setAccessibleName(label)
            self.update()

    @pyqtProperty(float)
    def hoverProgress(self) -> float:
        return self._hover_progress

    @hoverProgress.setter
    def hoverProgress(self, val: float) -> None:
        self._hover_progress = val
        self.update()

    def enterEvent(self, event) -> None:
        if self._hover_anim is not None:
            self._hover_anim.stop()
        self._hover_anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_anim.setDuration(130)
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self._hover_anim is not None:
            self._hover_anim.stop()
        self._hover_anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_anim.setDuration(160)
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_offset = 1.0
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._press_offset = 0.0
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        w = float(self.width())
        h = float(self.height())
        p = self._hover_progress
        po = self._press_offset

        rect = QRectF(0.5, 0.5 + po, w - 1.0, h - 1.0)
        bg_alpha = int(12 + 24 * p)
        border_alpha = int(18 + 36 * p)
        painter.setBrush(QBrush(QColor(255, 255, 255, bg_alpha)))
        painter.setPen(QPen(QColor(255, 255, 255, border_alpha), 1.0))
        painter.drawRoundedRect(rect, h / 2.0, h / 2.0)

        # Draw mini vector icon if icon_type is set
        has_icon = bool(self.icon_type)
        ix = 8.0
        iy = (h - 10.0) / 2.0 + po
        icon_color = QColor(255, 255, 255, int(190 + 65 * p))

        if has_icon:
            painter.setPen(QPen(icon_color, 1.25, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.setBrush(Qt.BrushStyle.NoBrush)

            if self.icon_type == "lock":
                painter.drawArc(QRectF(ix + 1.8, iy, 5.5, 5.5), 0, 180 * 16)
                painter.setBrush(QBrush(icon_color))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(QRectF(ix + 0.5, iy + 3.2, 8.0, 6.2), 1.2, 1.2)
            elif self.icon_type == "ai_sparkle":
                sp = QPainterPath()
                scx = ix + 4.5; scy = iy + 4.5
                sp.moveTo(scx, iy)
                sp.quadTo(scx, scy, ix + 9.0, scy)
                sp.quadTo(scx, scy, scx, iy + 9.0)
                sp.quadTo(scx, scy, ix, scy)
                sp.quadTo(scx, scy, scx, iy)
                painter.setBrush(QBrush(Palette.ACCENT_AI))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawPath(sp)
            elif self.icon_type == "screenshot":
                painter.drawRoundedRect(QRectF(ix, iy + 0.8, 9.0, 7.4), 1.4, 1.4)
                painter.drawEllipse(QPointF(ix + 4.5, iy + 4.5), 1.8, 1.8)
            elif self.icon_type == "calendar":
                painter.drawRoundedRect(QRectF(ix + 0.8, iy + 1.0, 8.2, 8.0), 1.2, 1.2)
                painter.drawLine(QPointF(ix + 1.0, iy + 3.8), QPointF(ix + 8.8, iy + 3.8))
                painter.drawLine(QPointF(ix + 3.0, iy), QPointF(ix + 3.0, iy + 2.2))
                painter.drawLine(QPointF(ix + 6.8, iy), QPointF(ix + 6.8, iy + 2.2))
                painter.setBrush(QBrush(icon_color))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(ix + 3.0, iy + 6.1), 0.7, 0.7)
                painter.drawEllipse(QPointF(ix + 6.8, iy + 6.1), 0.7, 0.7)
            elif self.icon_type == "dnd":
                painter.drawEllipse(QRectF(ix, iy + 0.5, 8.5, 8.5))
                painter.drawLine(QPointF(ix + 2.0, iy + 4.8), QPointF(ix + 6.5, iy + 4.8))
            elif self.icon_type == "settings":
                painter.drawEllipse(QPointF(ix + 4.5, iy + 4.5), 2.0, 2.0)
                import math
                for i in range(6):
                    ang = i * (math.pi / 3.0)
                    painter.drawLine(
                        QPointF(ix + 4.5 + math.cos(ang) * 2.5, iy + 4.5 + math.sin(ang) * 2.5),
                        QPointF(ix + 4.5 + math.cos(ang) * 4.2, iy + 4.5 + math.sin(ang) * 4.2)
                    )
            elif self.icon_type == "clipboard":
                painter.drawRoundedRect(QRectF(ix + 0.5, iy + 1.2, 7.5, 7.5), 1.2, 1.2)
                painter.drawLine(QPointF(ix + 2.4, iy + 1.2), QPointF(ix + 2.4, iy))
                painter.drawLine(QPointF(ix + 2.4, iy), QPointF(ix + 6.0, iy))
                painter.drawLine(QPointF(ix + 6.0, iy), QPointF(ix + 6.0, iy + 1.2))

        # Typography: Crisp bold modern Apple font
        t_val = int(220 + 35 * p)
        font = QFont("Segoe UI Semibold", 8, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(t_val, t_val, t_val))

        clean_label = self.label.strip()
        if has_icon:
            painter.drawText(QRectF(ix + 11.0, po, w - ix - 13.0, h),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, clean_label)
        else:
            painter.drawText(QRectF(0, po, w, h), Qt.AlignmentFlag.AlignCenter, clean_label)


# ---------------------------------------------------------------------------
# BatteryPill
# ---------------------------------------------------------------------------

class BatteryPill(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._pct = 100
        self._plugged = False
        self._has_bat = True
        self.setFixedSize(62, 24)

    def update_battery(self, pct: int, plugged: bool, has_bat: bool) -> None:
        self._pct = pct
        self._plugged = plugged
        self._has_bat = has_bat
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = float(self.width())
        h = float(self.height())

        painter.setBrush(QBrush(QColor(255, 255, 255, 14)))
        painter.setPen(QPen(QColor(255, 255, 255, 28), 1.0))
        painter.drawRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), h / 2.0, h / 2.0)

        bw = 18.0; bh = 9.5
        bx = 6.0; by = (h - bh) / 2.0

        fill_color = Palette.ACCENT_BATTERY if (self._pct > 20 or self._plugged) else Palette.ACCENT_BATTERY_LOW
        painter.setPen(QPen(QColor(255, 255, 255, 70), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(bx, by, bw, bh), 2.0, 2.0)

        cap_h = 3.5; cap_y = by + (bh - cap_h) / 2.0
        painter.setBrush(QBrush(QColor(255, 255, 255, 70)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(bx + bw + 0.6, cap_y, 1.5, cap_h), 0.6, 0.6)

        fill_pct = max(0.05, min(1.0, self._pct / 100.0))
        painter.setBrush(QBrush(fill_color))
        painter.drawRoundedRect(QRectF(bx + 1.2, by + 1.2, max(1.5, (bw - 2.4) * fill_pct), bh - 2.4), 1.0, 1.0)

        if self._plugged:
            bolt = QPainterPath()
            bcx = bx + bw / 2.0
            bolt.moveTo(bcx + 1.0, by - 0.5)
            bolt.lineTo(bcx - 1.5, by + bh * 0.6)
            bolt.lineTo(bcx + 0.4, by + bh * 0.6)
            bolt.lineTo(bcx - 1.2, by + bh + 0.5)
            bolt.lineTo(bcx + 1.6, by + bh * 0.42)
            bolt.lineTo(bcx + 0.0, by + bh * 0.42)
            bolt.closeSubpath()
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawPath(bolt)

        font = QFont(Typography.FONT_FAMILY, 8, QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(fill_color if self._pct <= 20 and not self._plugged else Palette.TEXT_PRIMARY)
        painter.drawText(QRectF(bx + bw + 4.0, 0, w - bx - bw - 4.0, h),
                         Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"%{self._pct}")


# ---------------------------------------------------------------------------
# Media Controls
# ---------------------------------------------------------------------------

class MediaThumbnail(QWidget):
    def __init__(self, size: int = 44, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._size = size
        self._pixmap: Optional[QPixmap] = None
        self.setFixedSize(size, size)

    def set_pixmap(self, pixmap: Optional[QPixmap]) -> None:
        self._pixmap = pixmap
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self._size, self._size), 8.0, 8.0)
        painter.setClipPath(path)
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self._size, self._size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            x_off = (scaled.width() - self._size) / 2.0
            y_off = (scaled.height() - self._size) / 2.0
            painter.drawPixmap(int(-x_off), int(-y_off), scaled)
        else:
            grad = QLinearGradient(0, 0, self._size, self._size)
            grad.setColorAt(0.0, QColor(36, 40, 52))
            grad.setColorAt(1.0, QColor(20, 22, 28))
            painter.fillRect(self.rect(), grad)
            painter.setPen(QPen(QColor(255, 255, 255, 60), 1.5))
            cx = self._size / 2.0
            cy = self._size / 2.0
            painter.setPen(QPen(QColor(238, 240, 243), 2.0, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawLine(QPointF(cx + 4, cy - 5), QPointF(cx + 4, cy + 2))
            painter.drawLine(QPointF(cx + 4, cy - 5), QPointF(cx + 9, cy - 6))
            painter.drawLine(QPointF(cx + 9, cy - 6), QPointF(cx + 9, cy + 1))
            painter.setBrush(QBrush(QColor(238, 240, 243)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(cx + 1, cy + 3), 3, 2)
            painter.drawEllipse(QPointF(cx + 6, cy + 2), 3, 2)


class VectorMediaButton(QPushButton):
    def __init__(self, action_type: str = "play", is_primary: bool = False,
                 parent: Optional[QWidget] = None):
        super().__init__("", parent)
        self.action_type = action_type
        self.is_primary = is_primary
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        size = 32 if is_primary else 26
        self.setFixedSize(size, size)
        self._hover_progress: float = 0.0
        self._press_offset: float = 0.0
        self._hover_anim: Optional[QPropertyAnimation] = None

    @pyqtProperty(float)
    def hoverProgress(self) -> float:
        return self._hover_progress

    @hoverProgress.setter
    def hoverProgress(self, val: float) -> None:
        self._hover_progress = val
        self.update()

    def set_action(self, action_type: str) -> None:
        self.action_type = action_type
        self.update()

    def enterEvent(self, event) -> None:
        if self._hover_anim is not None:
            self._hover_anim.stop()
        self._hover_anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_anim.setDuration(130)
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self._hover_anim is not None:
            self._hover_anim.stop()
        self._hover_anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_anim.setDuration(160)
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_offset = 1.0
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._press_offset = 0.0
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = float(self.width())
        h = float(self.height())
        p = self._hover_progress
        po = self._press_offset
        center = QPointF(w / 2.0, h / 2.0 + po)
        radius = w / 2.0 - 1.0

        if self.is_primary:
            bg_val = int(245 + 10 * p)
            painter.setBrush(QBrush(QColor(bg_val, bg_val, bg_val)))
            painter.setPen(QPen(QColor(255, 255, 255, int(120 + 80 * p)), 1.0))
            painter.drawEllipse(center, radius, radius)
            icon_color = Palette.BTN_PLAY_ICON
        else:
            bg_a = int(14 + 28 * p)
            bd_a = int(22 + 45 * p)
            painter.setBrush(QBrush(QColor(255, 255, 255, bg_a)))
            painter.setPen(QPen(QColor(255, 255, 255, bd_a), 1.0))
            painter.drawEllipse(center, radius, radius)
            icon_color = QColor(int(215 + 40 * p), int(215 + 40 * p), int(215 + 40 * p))

        painter.setBrush(QBrush(icon_color))
        painter.setPen(Qt.PenStyle.NoPen)
        cx = center.x(); cy = center.y()

        if self.action_type == "play":
            path = QPainterPath()
            path.moveTo(cx - 3.5, cy - 5.5)
            path.lineTo(cx + 5.5, cy)
            path.lineTo(cx - 3.5, cy + 5.5)
            path.closeSubpath()
            painter.drawPath(path)
        elif self.action_type == "pause":
            bar_w = 2.5; bar_h = 10.0
            y = cy - bar_h / 2.0
            painter.drawRoundedRect(QRectF(cx - 4.5, y, bar_w, bar_h), 1.0, 1.0)
            painter.drawRoundedRect(QRectF(cx + 2.0, y, bar_w, bar_h), 1.0, 1.0)
        elif self.action_type == "next":
            painter.setBrush(QBrush(icon_color))
            painter.setPen(Qt.PenStyle.NoPen)
            path = QPainterPath()
            path.moveTo(cx - 3.5, cy - 4.5)
            path.lineTo(cx + 1.5, cy)
            path.lineTo(cx - 3.5, cy + 4.5)
            path.closeSubpath()
            painter.drawPath(path)
            painter.drawRoundedRect(QRectF(cx + 2.5, cy - 4.5, 1.8, 9.0), 0.6, 0.6)
        elif self.action_type == "prev":
            painter.setBrush(QBrush(icon_color))
            painter.setPen(Qt.PenStyle.NoPen)
            path = QPainterPath()
            path.moveTo(cx + 3.5, cy - 4.5)
            path.lineTo(cx - 1.5, cy)
            path.lineTo(cx + 3.5, cy + 4.5)
            path.closeSubpath()
            painter.drawPath(path)
            painter.drawRoundedRect(QRectF(cx - 4.3, cy - 4.5, 1.8, 9.0), 0.6, 0.6)


# ---------------------------------------------------------------------------
# PrivacyDot & NotificationBadge
# ---------------------------------------------------------------------------

class PrivacyDot(QWidget):
    def __init__(self, color: QColor, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.color = color
        self.setFixedSize(8, 8)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        halo = QColor(self.color.red(), self.color.green(), self.color.blue(), 105)
        painter.setBrush(QBrush(halo))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, 3.8, 3.8)
        core = QColor(max(self.color.red(), 225), max(self.color.green(), 225), max(self.color.blue(), 232))
        painter.setBrush(QBrush(core))
        painter.drawEllipse(center, 2.5, 2.5)


class NotificationBadge(QWidget):
    """Small glowing iOS-style red notification badge dot on compact island."""
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(10, 10)
        self.setVisible(False)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        # Soft outer red glow
        painter.setBrush(QBrush(QColor(242, 243, 248, 65)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, 4.5, 4.5)
        # Core glowing red dot
        painter.setBrush(QBrush(QColor(244, 245, 250, 225)))
        painter.drawEllipse(center, 2.8, 2.8)


# ---------------------------------------------------------------------------
# CapsBadgeWidget & Compact Volume Micro-Bar
# ---------------------------------------------------------------------------

class CapsBadgeWidget(QWidget):
    """
    Crisp monochrome Caps Lock indicator badge.
    Dedicated layout element so it NEVER overlaps visualizer dots or audio waves.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(14, 14)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = float(self.width())
        h = float(self.height())
        cx = w / 2.0
        cy = h / 2.0

        # Subtle badge background pill
        painter.setBrush(QBrush(QColor(255, 255, 255, 28)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(0.5, 0.5, w - 1.0, h - 1.0), 3.5, 3.5)

        # Crisp upward arrow
        painter.setPen(QPen(QColor(248, 249, 250), 1.5, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        arrow = QPainterPath()
        arrow.moveTo(cx - 3.2, cy + 2.0)
        arrow.lineTo(cx, cy - 2.0)
        arrow.lineTo(cx + 3.2, cy + 2.0)
        painter.drawPath(arrow)


class CompactMicroProgressBar(QWidget):
    """
    Fluid animated 42px x 4px pill progress bar for the compact Dynamic Island.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(42, 12)
        self._value: float = 0.0
        self._anim: Optional[QPropertyAnimation] = None

    @pyqtProperty(float)
    def progress(self) -> float:
        return self._value

    @progress.setter
    def progress(self, val: float) -> None:
        self._value = max(0.0, min(100.0, val))
        self.update()

    def set_value(self, val: float, animated: bool = True) -> None:
        val = max(0.0, min(100.0, float(val)))
        if animated:
            if self._anim is not None:
                self._anim.stop()
            self._anim = QPropertyAnimation(self, b"progress", self)
            self._anim.setDuration(120)
            self._anim.setStartValue(self._value)
            self._anim.setEndValue(val)
            self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._anim.start()
        else:
            self._value = val
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = float(self.width())
        h = 4.0
        y = (float(self.height()) - h) / 2.0

        # Background track
        painter.setBrush(QBrush(QColor(255, 255, 255, 45)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(0.0, y, w, h), 2.0, 2.0)

        # Active progress fill
        fill_w = (w * self._value) / 100.0
        if fill_w > 0:
            painter.setBrush(QBrush(QColor(56, 189, 248)))  # Cyan / Ice Blue
            painter.drawRoundedRect(QRectF(0.0, y, fill_w, h), 2.0, 2.0)


class CompactVolumeWidget(QWidget):
    """
    Inline volume indicator shown inside the compact Dynamic Island capsule.
    Displays: [Vector Speaker Icon] [Fluid Progress Bar] [%24]
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon = VectorIcon("speaker", size=12, color=Palette.TEXT_PRIMARY)
        layout.addWidget(self.icon)

        self.bar = CompactMicroProgressBar()
        layout.addWidget(self.bar)

        self.lbl_pct = QLabel("%0")
        self.lbl_pct.setStyleSheet("color: #D0D3D7; font-weight: 700; font-size: 11px; font-family: 'Segoe UI Semibold', 'Segoe UI', 'Segoe UI', sans-serif;")
        layout.addWidget(self.lbl_pct)
        self._percent = 0
        self._muted = False
        I18nManager.get_instance().language_changed.connect(self._on_language_changed)

    def _on_language_changed(self, _lang: str) -> None:
        self.set_volume(self._percent, self._muted)

    def set_volume(self, percent: int, is_muted: bool) -> None:
        self._percent = percent
        self._muted = is_muted
        if is_muted:
            self.icon.set_type("speaker_mute")
            self.bar.set_value(0)
            self.lbl_pct.setText(t("muted_label"))
            self.lbl_pct.setStyleSheet("color: #F87171; font-weight: 700; font-size: 11px; font-family: 'Segoe UI Semibold', 'Segoe UI', 'Segoe UI', sans-serif;")
        else:
            self.icon.set_type("speaker")
            self.bar.set_value(percent)
            self.lbl_pct.setText(f"%{percent}")
            self.lbl_pct.setStyleSheet("color: #D0D3D7; font-weight: 700; font-size: 11px; font-family: 'Segoe UI Semibold', 'Segoe UI', 'Segoe UI', sans-serif;")


# ---------------------------------------------------------------------------
# CompactCapsuleWidget — Clean Apple Aesthetic (No crowded static pet!)
# ---------------------------------------------------------------------------

class CompactCapsuleWidget(QWidget):
    """
    Sleek minimalist hardware pill (~180px x 32px).
    Features: Camera Cutout Lens · Status/Venv Title · Red Notification Badge · Visualizer · Inline Volume Scrubber · Caps Badge
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_track_title: str = ""
        self._is_playing: bool = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(6)

        # Hardware Camera Cutout Lens
        self.lens = VectorIcon("camera_lens", size=11)
        layout.addWidget(self.lens)

        # Privacy Dots
        self.dot_mic = PrivacyDot(Palette.TEXT_SECONDARY)
        self.dot_mic.setVisible(False)
        self.dot_cam = PrivacyDot(Palette.TEXT_SECONDARY)
        self.dot_cam.setVisible(False)
        layout.addWidget(self.dot_mic)
        layout.addWidget(self.dot_cam)

        # Center Container (Stacked: Page 0: Normal status/title, Page 1: Volume progress bar)
        self.center_stack = QStackedWidget(self)
        self.center_stack.setContentsMargins(0, 0, 0, 0)

        # Page 0: Normal Center Status Title
        self.lbl_center = QLabel("")
        self.lbl_center.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_center.setStyleSheet("color: #E4E4E7; font-weight: 600; font-size: 11px; font-family: 'Segoe UI Semibold', 'Segoe UI', 'Segoe UI', sans-serif;")
        self.center_stack.addWidget(self.lbl_center)

        # Page 1: Fluid Volume Scrubber Widget
        self.vol_widget = CompactVolumeWidget()
        self.center_stack.addWidget(self.vol_widget)

        layout.addWidget(self.center_stack, stretch=1)

        # Bluetooth connected icon
        self.bt_icon = VectorIcon("bluetooth", size=12)
        self.bt_icon.setVisible(False)
        layout.addWidget(self.bt_icon)

        # iOS-style Smart Notification Badge Dot
        self.badge = NotificationBadge(parent=self)
        layout.addWidget(self.badge)

        # Audio Visualizer
        self.visualizer = AudioVisualizer(bar_count=3)
        layout.addWidget(self.visualizer)

        # Caps Lock Indicator (Dedicated child widget - zero overlap!)
        self.caps_badge = CapsBadgeWidget()
        self.caps_badge.setVisible(False)
        layout.addWidget(self.caps_badge)

        # Auto-revert timer for inline volume bar
        self._vol_timer = QTimer(self)
        self._vol_timer.setSingleShot(True)
        self._vol_timer.timeout.connect(self._on_volume_timeout)

    def set_playing(self, is_playing: bool, title: str = "") -> None:
        self._is_playing = is_playing
        self._current_track_title = title
        self.visualizer.set_active(is_playing)
        # If volume widget is currently active, don't overwrite until volume timer finishes
        if self.center_stack.currentWidget() == self.vol_widget:
            return
        if is_playing and title:
            clean = title if len(title) <= 14 else title[:12] + ".."
            self.lbl_center.setText(clean)
        else:
            self.lbl_center.setText("")

    def set_bluetooth_active(self, active: bool) -> None:
        self.bt_icon.setVisible(active)

    def set_privacy(self, mic_active: bool, cam_active: bool) -> None:
        self.dot_mic.setVisible(mic_active)
        self.dot_cam.setVisible(cam_active)

    def set_caps_lock(self, active: bool) -> None:
        self.caps_badge.setVisible(active)

    def flash_charging(self, percent: int, plugged: bool) -> None:
        """Instant zero-latency visual charging indicator right in the compact pill."""
        if plugged:
            self.lbl_center.setText(f"%{percent}")
            self.lbl_center.setStyleSheet("color: #E0E3E6; font-weight: 700; font-size: 11px; font-family: 'Segoe UI Semibold', 'Segoe UI', 'Segoe UI', sans-serif;")
        else:
            self.lbl_center.setText(f" %{percent}")
            self.lbl_center.setStyleSheet("color: #94A3B8; font-weight: 600; font-size: 11px; font-family: 'Segoe UI Semibold', 'Segoe UI', 'Segoe UI', sans-serif;")
        self.center_stack.setCurrentWidget(self.lbl_center)
        QTimer.singleShot(2400, self._restore_center_title)

    def show_volume_bar(self, percent: int, is_muted: bool) -> None:
        """Fluid volume progress bar inside compact island. Reverts cleanly after 1300ms."""
        self.vol_widget.set_volume(percent, is_muted)
        self.center_stack.setCurrentWidget(self.vol_widget)
        self._vol_timer.stop()
        self._vol_timer.start(1300)

    def _on_volume_timeout(self) -> None:
        self.center_stack.setCurrentWidget(self.lbl_center)
        self._restore_center_title()

    def _restore_center_title(self) -> None:
        if self._is_playing and self._current_track_title:
            clean = self._current_track_title if len(self._current_track_title) <= 14 else self._current_track_title[:12] + ".."
            self.lbl_center.setText(clean)
        else:
            self.lbl_center.setText("")
        self.lbl_center.setStyleSheet("color: #E4E4E7; font-weight: 600; font-size: 11px; font-family: 'Segoe UI Semibold', 'Segoe UI', 'Segoe UI', sans-serif;")

    def set_notification_badge(self, visible: bool) -> None:
        self.badge.setVisible(visible)

    def clear_for_transition(self) -> None:
        self._vol_timer.stop()
        self.center_stack.setCurrentWidget(self.lbl_center)
        self.lbl_center.setText("")
        self.visualizer.set_active(False)


# ---------------------------------------------------------------------------
# NavIconButton & BackButton & SectionTileButton (Ultra-Modern Animated)
# ---------------------------------------------------------------------------

class NavIconButton(QPushButton):
    """
    Modern monochrome top navigation icon button with smooth hover animation,
    illuminated active state, and spring press feedback.
    """
    def __init__(self, icon_type: str, tooltip: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.icon_type = icon_type
        self.setFixedSize(36, 34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)
        self.setCheckable(True)
        self.setStyleSheet("QPushButton { border: none; background: transparent; }")

        self._hover_progress: float = 0.0
        self._press_offset: float = 0.0
        self._hover_anim: Optional[QPropertyAnimation] = None

    @pyqtProperty(float)
    def hoverProgress(self) -> float:
        return self._hover_progress

    @hoverProgress.setter
    def hoverProgress(self, val: float) -> None:
        self._hover_progress = val
        self.update()

    def enterEvent(self, event) -> None:
        if self._hover_anim is not None:
            self._hover_anim.stop()
        self._hover_anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_anim.setDuration(130)
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self._hover_anim is not None:
            self._hover_anim.stop()
        self._hover_anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_anim.setDuration(160)
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_offset = 1.0
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._press_offset = 0.0
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = float(self.width())
        h = float(self.height())
        cx = w / 2.0
        cy = h / 2.0 + self._press_offset
        painter.translate(cx, cy)
        painter.scale(1.18, 1.18)
        painter.translate(-cx, -cy)
        p = self._hover_progress
        checked = self.isChecked()

        rect = QRectF(0.5, 0.5 + self._press_offset, w - 1.0, h - 1.0)

        # Dynamic animated background & border (Apple squircle aesthetic)
        if checked:
            painter.setBrush(QBrush(QColor(255, 255, 255, 42)))
            painter.setPen(QPen(QColor(255, 255, 255, 75), 1.0))
            painter.drawRoundedRect(rect, 8.0, 8.0)
            icon_color = QColor(255, 255, 255)
        else:
            bg_alpha = int(8 + 22 * p)
            border_alpha = int(14 + 32 * p)
            painter.setBrush(QBrush(QColor(255, 255, 255, bg_alpha)))
            painter.setPen(QPen(QColor(255, 255, 255, border_alpha), 1.0))
            painter.drawRoundedRect(rect, 8.0, 8.0)
            ic_v = int(190 + 65 * p)
            icon_color = QColor(ic_v, ic_v, ic_v)

        # Vector icon drawing
        if self.icon_type == "control_center":
            painter.setPen(QPen(icon_color, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(QPointF(cx - 5.5, cy - 3.2), QPointF(cx + 5.5, cy - 3.2))
            painter.setBrush(QBrush(icon_color))
            painter.drawEllipse(QPointF(cx - 1.5, cy - 3.2), 1.8, 1.8)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawLine(QPointF(cx - 5.5, cy + 3.2), QPointF(cx + 5.5, cy + 3.2))
            painter.setBrush(QBrush(icon_color))
            painter.drawEllipse(QPointF(cx + 1.8, cy + 3.2), 1.8, 1.8)

        elif self.icon_type == "media_sound":
            painter.setPen(QPen(icon_color, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.setBrush(QBrush(icon_color))
            painter.drawEllipse(QPointF(cx - 3.5, cy + 3.5), 2.0, 1.6)
            painter.drawLine(QPointF(cx - 2.0, cy + 3.5), QPointF(cx - 2.0, cy - 4.5))
            painter.drawEllipse(QPointF(cx + 3.0, cy + 1.5), 2.0, 1.6)
            painter.drawLine(QPointF(cx + 4.5, cy + 1.5), QPointF(cx + 4.5, cy - 6.5))
            painter.setPen(QPen(icon_color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(cx - 2.0, cy - 4.5), QPointF(cx + 4.5, cy - 6.5))

        elif self.icon_type == "pixel":
            painter.setPen(QPen(icon_color, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            path = QPainterPath()
            path.moveTo(cx - 5.5, cy + 3.5)
            path.lineTo(cx - 5.5, cy - 1.0)
            path.lineTo(cx - 4.0, cy - 5.2)
            path.lineTo(cx - 1.5, cy - 2.0)
            path.lineTo(cx + 1.5, cy - 2.0)
            path.lineTo(cx + 4.0, cy - 5.2)
            path.lineTo(cx + 5.5, cy - 1.0)
            path.lineTo(cx + 5.5, cy + 3.5)
            path.quadTo(cx, cy + 5.5, cx - 5.5, cy + 3.5)
            painter.drawPath(path)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(icon_color))
            painter.drawEllipse(QPointF(cx - 2.5, cy + 1.2), 0.9, 0.9)
            painter.drawEllipse(QPointF(cx + 2.5, cy + 1.2), 0.9, 0.9)

        elif self.icon_type == "calendar":
            painter.setPen(QPen(icon_color, 1.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(cx - 5.5, cy - 4.5, 11, 10), 2.0, 2.0)
            painter.drawLine(QPointF(cx - 5.5, cy - 1.5), QPointF(cx + 5.5, cy - 1.5))
            painter.drawLine(QPointF(cx - 3.0, cy - 6.0), QPointF(cx - 3.0, cy - 4.5))
            painter.drawLine(QPointF(cx + 3.0, cy - 6.0), QPointF(cx + 3.0, cy - 4.5))
            painter.setBrush(QBrush(icon_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(cx, cy + 2.0), 1.2, 1.2)


class BackButton(QPushButton):
    """
    Modern animated monochrome back button (←) with smooth hover slide
    and tactile click feedback.
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(26, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(t("back_to_main"))
        self.setStyleSheet("QPushButton { border: none; background: transparent; }")

        self._arrow_slide: float = 0.0
        self._press_offset: float = 0.0
        self._slide_anim: Optional[QPropertyAnimation] = None

    @pyqtProperty(float)
    def arrowSlide(self) -> float:
        return self._arrow_slide

    @arrowSlide.setter
    def arrowSlide(self, val: float) -> None:
        self._arrow_slide = val
        self.update()

    def enterEvent(self, event) -> None:
        if self._slide_anim is not None:
            self._slide_anim.stop()
        self._slide_anim = QPropertyAnimation(self, b"arrowSlide", self)
        self._slide_anim.setDuration(140)
        self._slide_anim.setStartValue(self._arrow_slide)
        self._slide_anim.setEndValue(1.0)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self._slide_anim is not None:
            self._slide_anim.stop()
        self._slide_anim = QPropertyAnimation(self, b"arrowSlide", self)
        self._slide_anim.setDuration(160)
        self._slide_anim.setStartValue(self._arrow_slide)
        self._slide_anim.setEndValue(0.0)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._slide_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_offset = 1.0
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._press_offset = 0.0
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = float(self.width())
        h = float(self.height())
        s = self._arrow_slide
        cx = w / 2.0 - (s * 1.5)
        cy = h / 2.0 + self._press_offset
        rect = QRectF(0.5, 0.5 + self._press_offset, w - 1.0, h - 1.0)

        bg_a = int(12 + 22 * s)
        bd_a = int(24 + 44 * s)
        painter.setBrush(QBrush(QColor(255, 255, 255, bg_a)))
        painter.setPen(QPen(QColor(255, 255, 255, bd_a), 1.0))
        painter.drawRoundedRect(rect, 7.5, 7.5)

        c_val = int(210 + 45 * s)
        color = QColor(c_val, c_val, c_val)
        painter.setPen(QPen(color, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawLine(QPointF(cx + 3.5, cy), QPointF(cx - 3.5, cy))
        path = QPainterPath()
        path.moveTo(cx - 0.5, cy - 3.5)
        path.lineTo(cx - 3.5, cy)
        path.lineTo(cx - 0.5, cy + 3.5)
        painter.drawPath(path)


class SectionTileButton(QPushButton):
    """
    Ultra-modern animated dark glass action tile for Dynamic Island sections.
    Features:
    - Multi-stop obsidian glass gradient with specular edge highlight
    - Micro-animated hover glow (QPropertyAnimation)
    - Elastic tactile click press response
    - Frosted tinted vector icon pill on the left (zero emojis)
    - Bold white modern typography
    - Subtle illuminated right chevron
    """
    def __init__(self, text: str, tooltip: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.raw_text = text
        self.setToolTip(tooltip or text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(32)
        self.setMinimumWidth(180)
        self.setStyleSheet("QPushButton { border: none; background: transparent; }")

        # Labels are plain text; action symbols are drawn as vector icons.
        self.title_text = text.strip()

        # Deduce vector icon type from keyword
        t_lower = text.lower()
        if "önceki" in t_lower:
            self.icon_type = "prev"
        elif "oynat" in t_lower:
            self.icon_type = "play"
        elif "sonraki" in t_lower:
            self.icon_type = "next"
        elif "ses" in t_lower:
            self.icon_type = "sound"
        elif "müzik" in t_lower:
            self.icon_type = "music"
        elif "kutla" in t_lower:
            self.icon_type = "star"
        elif "animasyon" in t_lower:
            self.icon_type = "sparkle"
        elif "su" in t_lower:
            self.icon_type = "water"
        elif "mola" in t_lower:
            self.icon_type = "coffee"
        elif "form" in t_lower:
            self.icon_type = "pet"
        elif "çanta" in t_lower or "temizle" in t_lower:
            self.icon_type = "trash"
        else:
            self.icon_type = "star"

        # Animation states
        self._hover_progress: float = 0.0
        self._press_offset: float = 0.0
        self._hover_anim: Optional[QPropertyAnimation] = None

    def set_texts(self, title: str, tooltip: str) -> None:
        self.raw_text = title
        self.title_text = title.strip()
        self.setToolTip(tooltip)
        self.update()

    @pyqtProperty(float)
    def hoverProgress(self) -> float:
        return self._hover_progress

    @hoverProgress.setter
    def hoverProgress(self, val: float) -> None:
        self._hover_progress = val
        self.update()

    def enterEvent(self, event) -> None:
        if self._hover_anim is not None:
            self._hover_anim.stop()
        self._hover_anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_anim.setDuration(140)
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self._hover_anim is not None:
            self._hover_anim.stop()
        self._hover_anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_anim.setDuration(160)
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_offset = 1.0
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._press_offset = 0.0
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        w = float(self.width())
        h = float(self.height())
        p = self._hover_progress
        po = self._press_offset

        rect = QRectF(0.5, 0.5 + po, w - 1.0, h - 1.0)
        r = 8.5

        # 1. Glass background gradient
        grad = QLinearGradient(0, po, 0, h + po)
        top_alpha = int(18 + 26 * p)
        bot_alpha = int(8 + 16 * p)
        grad.setColorAt(0.0, QColor(255, 255, 255, top_alpha))
        grad.setColorAt(1.0, QColor(255, 255, 255, bot_alpha))
        painter.setBrush(QBrush(grad))

        # 2. Border with specular edge highlight
        border_alpha = int(24 + 48 * p)
        border_pen = QPen(QColor(255, 255, 255, border_alpha), 1.0)
        painter.setPen(border_pen)
        painter.drawRoundedRect(rect, r, r)

        # 3. Specular top light rim
        if p > 0.05:
            spec_path = QPainterPath()
            spec_path.addRoundedRect(QRectF(1.5, 1.0 + po, w - 3.0, 1.2), 0.6, 0.6)
            painter.fillPath(spec_path, QBrush(QColor(255, 255, 255, int(40 * p))))

        # 4. Icon Badge on Left with Pure Vector Drawing
        x_cursor = 8.0
        badge_rect = QRectF(x_cursor, 4.5 + po, 23.0, 23.0)
        badge_alpha = int(20 + 25 * p)
        painter.setBrush(QBrush(QColor(255, 255, 255, badge_alpha)))
        painter.setPen(QPen(QColor(255, 255, 255, int(25 + 35 * p)), 0.8))
        painter.drawRoundedRect(badge_rect, 6.0, 6.0)

        bx = badge_rect.center().x()
        by = badge_rect.center().y()
        ic = QColor(255, 255, 255, int(210 + 45 * p))
        painter.setPen(QPen(ic, 1.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if self.icon_type == "prev":
            path = QPainterPath()
            path.moveTo(bx + 2.5, by - 3.5)
            path.lineTo(bx - 2.0, by)
            path.lineTo(bx + 2.5, by + 3.5)
            painter.drawPath(path)
            painter.drawLine(int(bx - 3.5), int(by - 3.5), int(bx - 3.5), int(by + 3.5))
        elif self.icon_type == "next":
            path = QPainterPath()
            path.moveTo(bx - 2.5, by - 3.5)
            path.lineTo(bx + 2.0, by)
            path.lineTo(bx - 2.5, by + 3.5)
            painter.drawPath(path)
            painter.drawLine(int(bx + 3.5), int(by - 3.5), int(bx + 3.5), int(by + 3.5))
        elif self.icon_type == "play":
            path = QPainterPath()
            path.moveTo(bx - 3.0, by - 4.0)
            path.lineTo(bx + 4.0, by)
            path.lineTo(bx - 3.0, by + 4.0)
            path.closeSubpath()
            painter.setBrush(QBrush(ic))
            painter.drawPath(path)
        elif self.icon_type == "sound":
            painter.drawArc(QRectF(bx - 4.0, by - 3.5, 4.0, 7.0), -60 * 16, 120 * 16)
            painter.drawArc(QRectF(bx - 2.0, by - 5.0, 5.5, 10.0), -60 * 16, 120 * 16)
        elif self.icon_type == "music":
            painter.drawEllipse(QPointF(bx - 2.5, by + 2.5), 1.6, 1.3)
            painter.drawEllipse(QPointF(bx + 2.5, by + 1.0), 1.6, 1.3)
            painter.drawLine(QPointF(bx - 1.0, by + 2.5), QPointF(bx - 1.0, by - 3.5))
            painter.drawLine(QPointF(bx + 4.0, by + 1.0), QPointF(bx + 4.0, by - 5.0))
            painter.drawLine(QPointF(bx - 1.0, by - 3.5), QPointF(bx + 4.0, by - 5.0))
        elif self.icon_type == "water":
            drop = QPainterPath()
            drop.moveTo(bx, by - 4.5)
            drop.quadTo(bx + 4.0, by + 1.0, bx, by + 4.5)
            drop.quadTo(bx - 4.0, by + 1.0, bx, by - 4.5)
            painter.setBrush(QBrush(QColor(56, 189, 248, 200)))
            painter.drawPath(drop)
        elif self.icon_type == "coffee":
            painter.drawRoundedRect(QRectF(bx - 3.5, by - 2.0, 7.0, 6.0), 1.0, 1.0)
            painter.drawArc(QRectF(bx + 2.0, by - 1.5, 3.0, 4.0), -90 * 16, 180 * 16)
        elif self.icon_type == "trash":
            painter.drawRoundedRect(QRectF(bx - 3.5, by - 2.5, 7.0, 7.0), 1.0, 1.0)
            painter.drawLine(QPointF(bx - 4.5, by - 2.5), QPointF(bx + 4.5, by - 2.5))
        else:
            # Star / sparkle
            sp = QPainterPath()
            sp.moveTo(bx, by - 4.5)
            sp.quadTo(bx, by, bx + 4.5, by)
            sp.quadTo(bx, by, bx, by + 4.5)
            sp.quadTo(bx, by, bx - 4.5, by)
            sp.quadTo(bx, by, bx, by - 4.5)
            painter.setBrush(QBrush(ic))
            painter.drawPath(sp)

        x_cursor += 31.0

        # 5. Title Text: Crisp bold Apple typography
        text_rect = QRectF(x_cursor, po, w - x_cursor - 18.0, h)
        t_font = QFont("Segoe UI Semibold", 9, QFont.Weight.Bold)
        painter.setFont(t_font)
        text_color = QColor(255, 255, 255) if p > 0.4 else QColor(235, 238, 245)
        painter.setPen(text_color)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.title_text)

        # 6. Right Chevron › with hover illumination
        chev_rect = QRectF(w - 18.0, po, 12.0, h)
        c_font = QFont("Segoe UI Semibold", 10, QFont.Weight.Bold)
        painter.setFont(c_font)
        chev_color = QColor(255, 255, 255, int(120 + 135 * p))
        painter.setPen(chev_color)
        painter.drawText(chev_rect, Qt.AlignmentFlag.AlignCenter, "›")


# ---------------------------------------------------------------------------
# HorizontalAlertWidget — Perfectly Centered Symmetrical Alert Pill
# ---------------------------------------------------------------------------

class HorizontalAlertWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(8)

        # Left Icon / Media Art (Size 22 for crisp, prominent battery visibility)
        self.icon = VectorIcon("battery", size=22)
        self.thumb = MediaThumbnail(size=24)
        self.thumb.setVisible(False)
        layout.addWidget(self.icon)
        layout.addWidget(self.thumb)

        # Centered Alert Text (High clarity, bold modern typography)
        self.lbl_text = QLabel("")
        self.lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_text.setStyleSheet("color: #FFFFFF; font-weight: 700; font-size: 12px; font-family: 'Segoe UI Semibold', 'Segoe UI', 'Segoe UI', sans-serif;")
        layout.addWidget(self.lbl_text, stretch=1)

        # Right side balancer container (visualizer or symmetric spacer for true center alignment)
        self.right_container = QWidget()
        self.right_layout = QHBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)
        self.visualizer = AudioVisualizer(bar_count=3)
        self.visualizer.setVisible(False)
        self.right_spacer = QWidget()
        self.right_spacer.setFixedSize(22, 22)
        self.right_layout.addWidget(self.visualizer)
        self.right_layout.addWidget(self.right_spacer)
        layout.addWidget(self.right_container)

    def display(self, title: str, subtitle: str = "", icon_type: str = "battery",
                pixmap: Optional[QPixmap] = None, show_visualizer: bool = False,
                battery_pct: float = 100.0) -> None:
        clean_title = title.strip()
        clean_sub = subtitle.strip()
        display_text = f"{clean_title} · {clean_sub}" if clean_sub else clean_title
        self.lbl_text.setText(display_text)

        if pixmap and not pixmap.isNull():
            self.thumb.set_pixmap(pixmap)
            self.thumb.setVisible(True)
            self.icon.setVisible(False)
        else:
            self.thumb.setVisible(False)
            self.icon.setVisible(True)
            self.icon.value_percent = battery_pct
            self.icon.set_type(icon_type)

        if show_visualizer:
            self.visualizer.setVisible(True)
            self.visualizer.set_active(True)
            self.right_spacer.setVisible(False)
        else:
            self.visualizer.setVisible(False)
            self.visualizer.set_active(False)
            self.right_spacer.setVisible(True)

    def clear_for_transition(self) -> None:
        self.lbl_text.setText("")
        self.visualizer.set_active(False)
        self.visualizer.setVisible(False)
        self.right_spacer.setVisible(True)


class HoverPreviewWidget(QWidget):
    """Lightweight horizontal summary shown on hover; clicks pass to the island."""
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(8)

        self.lbl_time = QLabel(self)
        self.lbl_time.setStyleSheet("color:#F8F9FA;font-size:12px;font-weight:700;font-family:'Segoe UI Semibold','Segoe UI',sans-serif")
        layout.addWidget(self.lbl_time)
        self.lbl_date = QLabel(self)
        self.lbl_date.setStyleSheet("color:#A1A1AA;font-size:10px;font-weight:700;font-family:'Segoe UI Semibold','Segoe UI',sans-serif")
        layout.addWidget(self.lbl_date)
        layout.addStretch(1)

        self.system_icon = VectorIcon("system_chip", size=14, color=Palette.TEXT_SECONDARY)
        layout.addWidget(self.system_icon)
        self.lbl_system = QLabel("CPU —% · RAM —%", self)
        self.lbl_system.setStyleSheet("color:#D4D4D8;font-size:9px;font-weight:700;font-family:'Segoe UI Semibold','Segoe UI',sans-serif")
        layout.addWidget(self.lbl_system)

        self.battery_icon = VectorIcon("battery", size=16, color=Palette.TEXT_SECONDARY)
        layout.addWidget(self.battery_icon)
        self.lbl_battery = QLabel("—", self)
        self.lbl_battery.setStyleSheet("color:#E4E4E7;font-size:11px;font-weight:700;font-family:'Segoe UI Semibold','Segoe UI',sans-serif")
        layout.addWidget(self.lbl_battery)
        self.lbl_weather = QLabel("", self)
        self.lbl_weather.setStyleSheet("color:#D4D4D8;font-size:11px;font-weight:700;font-family:'Segoe UI Semibold','Segoe UI',sans-serif")
        self.weather_icon = VectorIcon("weather_sun", size=14, color=Palette.TEXT_SECONDARY)
        layout.addWidget(self.weather_icon)
        layout.addWidget(self.lbl_weather)
        self.tasks_icon = VectorIcon("calendar", size=14, color=Palette.TEXT_SECONDARY)
        layout.addWidget(self.tasks_icon)
        self.lbl_tasks = QLabel("", self)
        self.lbl_tasks.setStyleSheet("color:#D4D4D8;font-size:11px;font-weight:700;font-family:'Segoe UI Semibold','Segoe UI',sans-serif")
        layout.addWidget(self.lbl_tasks)

        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._update_clock)
        self._update_clock()
        manager = TodoManager.get_instance()
        manager.todos_changed.connect(self.update_tasks)
        I18nManager.get_instance().language_changed.connect(self._on_language_changed)
        self._settings = SettingsManager.get_instance()
        self._settings.settings_changed.connect(self._sync_indicators)
        self._sync_indicators({})
        self.update_tasks()

    def _sync_indicators(self, _settings: dict) -> None:
        show_system = bool(self._settings.get("show_system_telemetry", True))
        self.system_icon.setVisible(show_system)
        self.lbl_system.setVisible(show_system)
        self.battery_icon.setVisible(bool(self._settings.get("show_battery_indicator", True)))
        self.lbl_battery.setVisible(bool(self._settings.get("show_battery_indicator", True)))
        self.weather_icon.setVisible(bool(self._settings.get("show_weather_indicator", True)))
        self.lbl_weather.setVisible(bool(self._settings.get("show_weather_indicator", True)))
        self.tasks_icon.setVisible(bool(self._settings.get("show_task_indicator", True)))
        self.lbl_tasks.setVisible(bool(self._settings.get("show_task_indicator", True)))

    def _update_clock(self) -> None:
        from PyQt6.QtCore import QDate, QTime, QLocale
        lang = I18nManager.get_instance().current_language
        locale = QLocale("tr_TR" if lang == "tr" else "en_US")
        self.lbl_time.setText(QTime.currentTime().toString("HH:mm"))
        self.lbl_date.setText(locale.toString(QDate.currentDate(), "ddd, d MMM"))

    def update_tasks(self, *_args) -> None:
        completed, total = TodoManager.get_instance().get_counts()
        pending = max(0, total - completed)
        self.lbl_tasks.setText(t("tasks_pending", count=pending) if pending else t("tasks_none"))

    def update_telemetry(self, cpu: float, ram: float) -> None:
        self.lbl_system.setText(f"CPU {int(cpu)}% · RAM {int(ram)}%")

    def _on_language_changed(self, _lang: str) -> None:
        self._update_clock()
        self.update_tasks()

    def update_battery(self, pct: int, plugged: bool = False, has_battery: bool = True) -> None:
        self.battery_icon.setVisible(has_battery)
        lang = I18nManager.get_instance().current_language
        percent = f"%{pct}" if lang == "tr" else f"{pct}%"
        self.lbl_battery.setText(percent if has_battery else "")
        self.battery_icon.value_percent = float(pct)
        self.battery_icon.set_type("battery_charging" if plugged else "battery")

    def update_weather(self, temp: str, icon_type: str = "weather_sun") -> None:
        self.lbl_weather.setText(temp.strip())
        self.weather_icon.set_type(icon_type)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._update_clock()
        if not self._clock_timer.isActive():
            self._clock_timer.start()

    def hideEvent(self, event) -> None:
        self._clock_timer.stop()
        super().hideEvent(event)


# ---------------------------------------------------------------------------
# ModernClockWidget — Sleek Bold Digital Clock
# ---------------------------------------------------------------------------

class ModernClockWidget(QWidget):
    """
    Crisp Apple-style digital clock for the Dynamic Island header.
    Features bold white typography ('Segoe UI Semibold', weight 700).
    Clicking navigates directly to the Calendar & Todo view.
    """
    clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(t("clock_tooltip"))
        self.setFixedSize(84, 26)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_time = QLabel(self)
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_time.setFixedWidth(40)
        self.lbl_time.setStyleSheet(
            "color: #FFFFFF; font-size: 11.5px; font-weight: 700; "
            "font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif;"
        )
        layout.addWidget(self.lbl_time)

        self.lbl_date = QLabel(self)
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_date.setFixedWidth(34)
        self.lbl_date.setStyleSheet("color: #AEB3B9; font-size: 8.5px; font-weight: 700; font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif;")
        layout.addWidget(self.lbl_date)

        self.setStyleSheet("""
            ModernClockWidget {
                background: rgba(255, 255, 255, 10);
                border: 1px solid rgba(255, 255, 255, 14);
                border-radius: 8px;
            }
            ModernClockWidget:hover {
                background: rgba(255, 255, 255, 22);
                border: 1px solid rgba(255, 255, 255, 28);
            }
        """)

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._update_clock)
        self._update_clock()
        I18nManager.get_instance().language_changed.connect(lambda _lang: self.setToolTip(t("clock_tooltip")))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._update_clock()
        if not self._timer.isActive():
            self._timer.start()

    def hideEvent(self, event) -> None:
        self._timer.stop()
        super().hideEvent(event)

    def _update_clock(self) -> None:
        from PyQt6.QtCore import QDate, QTime, QLocale
        from modules.i18n import I18nManager
        lang = I18nManager.get_instance().current_language
        locale = QLocale("tr_TR" if lang == "tr" else "en_US")
        self.lbl_time.setText(QTime.currentTime().toString("HH:mm"))
        self.lbl_date.setText(locale.toString(QDate.currentDate(), "d MMM"))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
# WeatherPillWidget — Sleek Monochrome Weather Pill in Expanded Island
# ---------------------------------------------------------------------------

class WeatherPillWidget(QWidget):
    """
    Sleek minimal monochrome weather widget for the Expanded Dynamic Island header.
    Displays: [Monochrome Weather Icon] [Temp, e.g. 9°C]
    """
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(76, 30)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 8, 3)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon = VectorIcon("weather_sun", size=17, color=Palette.TEXT_PRIMARY)
        layout.addWidget(self.icon)

        self.lbl_temp = QLabel("--°")
        self.lbl_temp.setFixedWidth(36)
        self.lbl_temp.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.lbl_temp.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 700; font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif;")
        layout.addWidget(self.lbl_temp)

        self.setStyleSheet("""
            WeatherPillWidget {
                background: rgba(255, 255, 255, 10);
                border: 1px solid rgba(255, 255, 255, 14);
                border-radius: 10px;
            }
            WeatherPillWidget:hover {
                background: rgba(255, 255, 255, 22);
                border: 1px solid rgba(255, 255, 255, 28);
            }
        """)
        self.setToolTip(t("weather_loading"))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._weather_label_key = "weather_clear"
        self._temperature = "--°"
        I18nManager.get_instance().language_changed.connect(self._refresh_tooltip)

    def update_weather(self, temp: str, _condition: str, icon_type: str) -> None:
        self._temperature = temp
        self._weather_label_key = {
            "weather_cloud": "weather_cloudy",
            "weather_partly_cloudy": "weather_partly_cloudy_label",
            "weather_rain": "weather_rainy",
            "weather_snow": "weather_snowy",
        }.get(icon_type, "weather_clear")
        self.lbl_temp.setText(temp)
        self.icon.set_type(icon_type)
        self._refresh_tooltip()

    def _refresh_tooltip(self, *_args) -> None:
        self.setToolTip(f"{t('weather_label')}: {t(self._weather_label_key)} · {self._temperature}")


# ---------------------------------------------------------------------------
# PocketButton — Supports dragging files OUT of the island!
# ---------------------------------------------------------------------------

class PocketButton(ActionButton):
    """Button showing stored pocket files and supporting drag-out to other apps."""
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("clipboard", "Pocket", parent)
        self._files: List[str] = []
        self._drag_start_pos: Optional[QPointF] = None
        I18nManager.get_instance().language_changed.connect(lambda _lang: self.set_files(self._files))
        self.set_files([])

    def set_files(self, files: List[str]) -> None:
        self._files = files
        count = len(files)
        base = "Çanta" if I18nManager.get_instance().current_language == "tr" else "Pocket"
        self.label = f"{base} ({count})" if count > 0 else base
        self.update()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_start_pos and self._files:
            dist = (event.position() - self._drag_start_pos).manhattanLength()
            if dist > 8:
                # Initiate QDrag to drag out file into Discord, Photoshop, Explorer
                drag = QDrag(self)
                mime = QMimeData()
                urls = [QUrl.fromLocalFile(p) for p in self._files if os.path.exists(p)]
                if urls:
                    mime.setUrls(urls)
                    drag.setMimeData(mime)
                    drag.exec(Qt.DropAction.CopyAction)
                    self._drag_start_pos = None
                    return
        super().mouseMoveEvent(event)


# ---------------------------------------------------------------------------
# VectorMoreButton — 3-dot (•••) Options Button
# ---------------------------------------------------------------------------

class VectorMoreButton(QPushButton):
    """Sleek minimalist 3-dot options button with smooth hover animation and tactile press feedback."""
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(26, 26)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(t("quick_options_tooltip"))
        I18nManager.get_instance().language_changed.connect(lambda _lang: self.setToolTip(t("quick_options_tooltip")))
        self._hover_progress: float = 0.0
        self._press_offset: float = 0.0
        self._hover_anim: Optional[QPropertyAnimation] = None

    @pyqtProperty(float)
    def hoverProgress(self) -> float:
        return self._hover_progress

    @hoverProgress.setter
    def hoverProgress(self, val: float) -> None:
        self._hover_progress = val
        self.update()

    def enterEvent(self, event) -> None:
        if self._hover_anim is not None:
            self._hover_anim.stop()
        self._hover_anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_anim.setDuration(130)
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self._hover_anim is not None:
            self._hover_anim.stop()
        self._hover_anim = QPropertyAnimation(self, b"hoverProgress", self)
        self._hover_anim.setDuration(160)
        self._hover_anim.setStartValue(self._hover_progress)
        self._hover_anim.setEndValue(0.0)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._hover_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_offset = 1.0
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._press_offset = 0.0
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        p = self._hover_progress
        po = self._press_offset
        w = float(self.width())
        h = float(self.height())
        rect = QRectF(1.0, 1.0 + po, w - 2.0, h - 2.0)

        bg_a = int(10 + 26 * p)
        bd_a = int(18 + 42 * p)
        painter.setBrush(QBrush(QColor(255, 255, 255, bg_a)))
        painter.setPen(QPen(QColor(255, 255, 255, bd_a), 1.0))
        painter.drawRoundedRect(rect, 7.5, 7.5)

        c_val = int(200 + 55 * p)
        painter.setBrush(QBrush(QColor(c_val, c_val, c_val)))
        painter.setPen(Qt.PenStyle.NoPen)
        cx = w / 2.0
        cy = h / 2.0 + po
        r = 1.6
        painter.drawEllipse(QPointF(cx - 5.5, cy), r, r)
        painter.drawEllipse(QPointF(cx, cy), r, r)
        painter.drawEllipse(QPointF(cx + 5.5, cy), r, r)


# ---------------------------------------------------------------------------
# QuickDockWidget — Sleek Apple-Style Telemetry & Quick Utilities Dock
# ---------------------------------------------------------------------------

class QuickDockWidget(QWidget):
    """
    Sleek Apple-style telemetry & core action dock.
    Left: Mini telemetry chips (CPU, RAM).
    Right: Core actions: AI Ask, Pocket Satchel, Lock PC.
    """
    ai_clicked = pyqtSignal()
    lock_clicked = pyqtSignal()
    calendar_clicked = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(28)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(8)

        # Left: CPU & RAM status pill
        self.telemetry_pill = QWidget(self)
        t_layout = QHBoxLayout(self.telemetry_pill)
        t_layout.setContentsMargins(10, 0, 10, 0)
        t_layout.setSpacing(8)
        self.telemetry_pill.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 8px;
            }
        """)

        self.lbl_cpu = QLabel("CPU %0", self)
        self.lbl_cpu.setStyleSheet("color: #D0D3D7; font-size: 10.5px; font-weight: 700; border: none; font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif;")
        t_layout.addWidget(self.lbl_cpu)

        dot = QLabel("·", self)
        dot.setStyleSheet("color: rgba(255, 255, 255, 0.35); font-size: 10px; font-weight: 700; border: none;")
        t_layout.addWidget(dot)

        self.lbl_ram = QLabel("RAM %0", self)
        self.lbl_ram.setStyleSheet("color: #AEB3B9; font-size: 10.5px; font-weight: 700; border: none; font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif;")
        t_layout.addWidget(self.lbl_ram)

        layout.addWidget(self.telemetry_pill)

        self.btn_calendar = ActionButton("calendar", "", self)
        self.btn_calendar.setFixedWidth(96)
        self.btn_calendar.setToolTip(t("calendar_summary_tooltip"))
        self.btn_calendar.clicked.connect(self.calendar_clicked.emit)
        layout.addWidget(self.btn_calendar)
        layout.addStretch(1)

        # Right: 3 Core Apple Actions
        self.btn_ai = ActionButton("ai_sparkle", t("ai_label"), self)
        self.btn_ai.setFixedWidth(88)
        self.btn_ai.clicked.connect(self.ai_clicked.emit)
        layout.addWidget(self.btn_ai)

        self.btn_pocket = PocketButton(self)
        self.btn_pocket.setFixedWidth(80)
        layout.addWidget(self.btn_pocket)

        self.btn_lock = ActionButton("lock", t("lock_label"), self)
        self.btn_lock.setFixedWidth(66)
        self.btn_lock.clicked.connect(self.lock_clicked.emit)
        layout.addWidget(self.btn_lock)

        todo_manager = TodoManager.get_instance()
        todo_manager.todos_changed.connect(self.update_task_summary)
        I18nManager.get_instance().language_changed.connect(self._on_language_changed)
        self._settings = SettingsManager.get_instance()
        self._settings.settings_changed.connect(self._sync_indicators)
        self._sync_indicators({})
        self.update_task_summary()

    def _sync_indicators(self, _settings: dict) -> None:
        self.telemetry_pill.setVisible(bool(self._settings.get("show_system_telemetry", True)))
        self.update_task_summary()

    def _on_language_changed(self, _lang: str) -> None:
        self.btn_ai.set_label(t("ai_label"))
        self.btn_lock.set_label(t("lock_label"))
        self.btn_calendar.setToolTip(t("calendar_summary_tooltip"))
        self.update_task_summary()

    def update_task_summary(self, *_args) -> None:
        completed, total = TodoManager.get_instance().get_counts()
        pending = max(0, total - completed)
        if self._settings.get("show_task_indicator", True):
            self.btn_calendar.set_label(t("tasks_pending", count=pending) if pending else t("tasks_none"))
        else:
            self.btn_calendar.set_label("")
        self.btn_calendar.setToolTip(t("calendar_summary_tooltip"))
        self.btn_calendar.update()

    def update_telemetry(self, cpu: float, ram: float) -> None:
        self.lbl_cpu.setText(f"CPU %{int(cpu)}")
        self.lbl_ram.setText(f"RAM %{int(ram)}")


# ---------------------------------------------------------------------------
# ExpandedDashboard
# ---------------------------------------------------------------------------

class ExpandedDashboard(QWidget):
    play_pause_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    prev_clicked = pyqtSignal()
    seek_requested = pyqtSignal(float)
    volume_changed = pyqtSignal(int)
    mute_toggled = pyqtSignal()
    ai_ask_requested = pyqtSignal(str)
    ai_drawer_toggled = pyqtSignal(bool)
    pomodoro_toggled = pyqtSignal()
    bring_music_clicked = pyqtSignal()
    dnd_toggled = pyqtSignal()
    clear_pocket_clicked = pyqtSignal()
    sound_settings_clicked = pyqtSignal()
    optimize_ram_clicked = pyqtSignal()
    take_screenshot_clicked = pyqtSignal()
    power_mode_clicked = pyqtSignal()
    open_settings_requested = pyqtSignal()
    section_height_changed = pyqtSignal(int)
    sidebar_requested = pyqtSignal()
    sidebar_page_requested = pyqtSignal(int)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setMinimumSize(0, 0)
        self._duration_sec = 0.0
        self._current_section_index: int = -1
        self._fade_anim: Optional[QPropertyAnimation] = None
        self._last_play_toggle_time: float = 0.0  # debounce latch for play/pause
        self._setup_ui()
        I18nManager.get_instance().language_changed.connect(self._on_language_changed)
        self._on_language_changed(I18nManager.get_instance().current_language)

    def _on_language_changed(self, _lang: str) -> None:
        self.lbl_sec_1.setText(t("nav_cc_title"))
        self.lbl_sec_2.setText(t("nav_cal_title"))
        self.lbl_sec_3.setText(t("nav_media_title"))
        if self.lbl_title.text() in ("Medya Çalmıyor", "No Media Playing"):
            self.lbl_title.setText(t("media_idle_title"))
        if self.lbl_artist.text() in ("Medyayı oynatın", "Play some music"):
            self.lbl_artist.setText(t("media_idle_artist"))
        self.btn_nav_cc.setToolTip(t("nav_cc_title"))
        self.btn_nav_cal.setToolTip(t("nav_cal_title"))
        self.btn_nav_media.setToolTip(t("nav_media_title"))
        self.lbl_media_volume.setText(t("volume_label"))
        localized_tiles = (
            (self.btn_m_prev, "media_prev", "media_prev_desc"),
            (self.btn_m_play, "media_toggle", "media_toggle_desc"),
            (self.btn_m_next, "media_next", "media_next_desc"),
            (self.btn_m_sound, "windows_sound", "windows_sound_desc"),
            (self.btn_m_app, "music_app", "music_app_desc"),
            (self.btn_p_flip, "pixel_celebrate", "pixel_celebrate_desc"),
            (self.btn_p_anim, "pixel_animations", "pixel_animations_desc"),
            (self.btn_p_water, "pixel_water", "pixel_water_desc"),
            (self.btn_p_break, "eye_break", "eye_break_desc"),
            (self.btn_p_species, "pixel_species", "pixel_species_desc"),
            (self.btn_p_clear, "clear_pocket", "clear_pocket_desc"),
        )
        for button, title_key, tip_key in localized_tiles:
            button.set_texts(t(title_key), t(tip_key))
        for button in self.findChildren(VectorMoreButton):
            button.setToolTip(t("quick_options_tooltip"))
        for button in self.findChildren(BackButton):
            button.setToolTip(t("back_to_main"))
        if hasattr(self, "ai_input"):
            self.ai_input.setPlaceholderText(t("ai_placeholder"))

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 8, 12, 8)
        outer.setSpacing(5)
        outer.setSizeConstraint(QVBoxLayout.SizeConstraint.SetNoConstraint)

        # ── Persistent Top Header Row ────────────────────────────────────
        self.header_row = QWidget(self)
        self.header_row.setFixedHeight(40)
        header_layout = QHBoxLayout(self.header_row)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        # 1. Left Header Stack (Page 0: Media Info | Pages 1,2,3,4: Back Button + Section Title)
        self.header_left_stack = QStackedWidget(self)
        self.header_left_stack.setFixedSize(160, 40)

        # Page 0 Left: Thumbnail & Title/Artist
        page0_left = QWidget()
        page0_left_layout = QHBoxLayout(page0_left)
        page0_left_layout.setContentsMargins(0, 0, 0, 0)
        page0_left_layout.setSpacing(8)

        self.thumb = MediaThumbnail(size=36)
        page0_left_layout.addWidget(self.thumb)

        info = QVBoxLayout()
        info.setSpacing(1)
        info.setContentsMargins(0, 2, 0, 2)
        self.lbl_title = QLabel("Medya Çalmıyor")
        self.lbl_title.setStyleSheet("color: #FFFFFF; font-weight: 700; font-size: 11.5px; font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif;")
        self.lbl_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.lbl_artist = QLabel("WinIsland")
        self.lbl_artist.setStyleSheet("color: #A1A1AA; font-size: 9.5px; font-weight: 500; font-family: 'Segoe UI', 'Segoe UI', sans-serif;")
        self.lbl_artist.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        info.addWidget(self.lbl_title)
        info.addWidget(self.lbl_artist)
        page0_left_layout.addLayout(info, stretch=1)
        self.header_left_stack.addWidget(page0_left)

        # Page 1 Left: Back + "Kontrol Merkezi"
        page1_left = QWidget()
        page1_left_layout = QHBoxLayout(page1_left)
        page1_left_layout.setContentsMargins(0, 0, 0, 0)
        page1_left_layout.setSpacing(8)
        btn_back_1 = BackButton()
        btn_back_1.clicked.connect(lambda: self.show_section(-1))
        self.lbl_sec_1 = QLabel("Kontrol Merkezi")
        self.lbl_sec_1.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 700; font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif;")
        page1_left_layout.addWidget(btn_back_1)
        page1_left_layout.addWidget(self.lbl_sec_1)
        page1_left_layout.addStretch(1)
        self.header_left_stack.addWidget(page1_left)

        # Page 2 Left: Back + "Takvim ve Görevler"
        page2_left = QWidget()
        page2_left_layout = QHBoxLayout(page2_left)
        page2_left_layout.setContentsMargins(0, 0, 0, 0)
        page2_left_layout.setSpacing(8)
        btn_back_2 = BackButton()
        btn_back_2.clicked.connect(lambda: self.show_section(-1))
        self.lbl_sec_2 = QLabel("Takvim & Görevler")
        self.lbl_sec_2.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 700; font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif;")
        page2_left_layout.addWidget(btn_back_2)
        page2_left_layout.addWidget(self.lbl_sec_2)
        page2_left_layout.addStretch(1)
        self.header_left_stack.addWidget(page2_left)

        # Page 3 Left: Back + "Medya ve Ses"
        page3_left = QWidget()
        page3_left_layout = QHBoxLayout(page3_left)
        page3_left_layout.setContentsMargins(0, 0, 0, 0)
        page3_left_layout.setSpacing(8)
        btn_back_3 = BackButton()
        btn_back_3.clicked.connect(lambda: self.show_section(-1))
        self.lbl_sec_3 = QLabel("Medya ve Ses")
        self.lbl_sec_3.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 700; font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif;")
        page3_left_layout.addWidget(btn_back_3)
        page3_left_layout.addWidget(self.lbl_sec_3)
        page3_left_layout.addStretch(1)
        self.header_left_stack.addWidget(page3_left)

        # Page 4 Left: Back + "Pixel"
        page4_left = QWidget()
        page4_left_layout = QHBoxLayout(page4_left)
        page4_left_layout.setContentsMargins(0, 0, 0, 0)
        page4_left_layout.setSpacing(8)
        btn_back_4 = BackButton()
        btn_back_4.clicked.connect(lambda: self.show_section(-1))
        self.lbl_sec_4 = QLabel("Pixel")
        self.lbl_sec_4.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 700; font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif;")
        page4_left_layout.addWidget(btn_back_4)
        page4_left_layout.addWidget(self.lbl_sec_4)
        page4_left_layout.addStretch(1)
        self.header_left_stack.addWidget(page4_left)

        header_layout.addWidget(self.header_left_stack)
        header_layout.addStretch(1)

        # 2. Middle: Centered Navigation Bar (Clock, Weather & Tabs)
        self.nav_container = QWidget(self)
        self.nav_container.setFixedSize(336, 34)
        nav_layout = QHBoxLayout(self.nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(4)
        nav_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.clock_pill = ModernClockWidget(self)
        self.clock_pill.clicked.connect(lambda: self.show_section(1))
        nav_layout.addWidget(self.clock_pill)

        self.weather_pill = WeatherPillWidget(self)
        nav_layout.addWidget(self.weather_pill)

        self.btn_nav_cc = NavIconButton("control_center", "Kontrol Merkezi")
        self.btn_nav_cc.clicked.connect(lambda: self.show_section(0))
        self.btn_nav_cal = NavIconButton("calendar", "Takvim & Görevler")
        self.btn_nav_cal.clicked.connect(lambda: self.show_section(1))
        self.btn_nav_media = NavIconButton("media_sound", "Medya ve Ses")
        self.btn_nav_media.clicked.connect(lambda: self.show_section(2))
        self.btn_nav_pixel = NavIconButton("pixel", "Pixel")
        self.btn_nav_pixel.clicked.connect(lambda: self.show_section(3))

        self.nav_buttons = [self.btn_nav_cc, self.btn_nav_cal, self.btn_nav_media, self.btn_nav_pixel]
        nav_layout.addWidget(self.btn_nav_cc)
        nav_layout.addWidget(self.btn_nav_cal)
        nav_layout.addWidget(self.btn_nav_media)
        nav_layout.addWidget(self.btn_nav_pixel)

        header_layout.addWidget(self.nav_container)
        header_layout.addStretch(1)

        # 3. Right Header Stack (Anchored with fixed width)
        self.header_right_stack = QStackedWidget(self)
        self.header_right_stack.setFixedSize(130, 40)

        # Page 0 Right: Controls (More, Prev, Play/Pause, Next)
        page0_right = QWidget()
        page0_right_layout = QHBoxLayout(page0_right)
        page0_right_layout.setContentsMargins(0, 0, 0, 0)
        page0_right_layout.setSpacing(5)
        page0_right_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.btn_more = VectorMoreButton()
        self.btn_more.clicked.connect(self._show_options_menu)
        page0_right_layout.addWidget(self.btn_more)

        self.btn_prev = VectorMediaButton("prev", is_primary=False)
        self.btn_prev.clicked.connect(self.prev_clicked.emit)
        self.btn_play = VectorMediaButton("play", is_primary=True)
        self.btn_play.clicked.connect(self._optimistic_play_toggle)
        self.btn_next = VectorMediaButton("next", is_primary=False)
        self.btn_next.clicked.connect(self.next_clicked.emit)

        page0_right_layout.addWidget(self.btn_prev)
        page0_right_layout.addWidget(self.btn_play)
        page0_right_layout.addWidget(self.btn_next)
        self.header_right_stack.addWidget(page0_right)

        # Pages 1-4 Right: Settings & Quick Options
        for _ in range(4):
            page_sub_right = QWidget()
            page_sub_layout = QHBoxLayout(page_sub_right)
            page_sub_layout.setContentsMargins(0, 0, 0, 0)
            page_sub_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            btn_sub_settings = VectorMoreButton()
            btn_sub_settings.clicked.connect(self.open_settings_requested.emit)
            btn_sub_settings.setToolTip(t("open_settings"))
            page_sub_layout.addWidget(btn_sub_settings)
            self.header_right_stack.addWidget(page_sub_right)

        header_layout.addWidget(self.header_right_stack)
        outer.addWidget(self.header_row)

        # ── Body Stack (Smooth in-island transitions) ─────────────────────
        self.body_stack = QStackedWidget(self)
        self.body_stack.setContentsMargins(0, 0, 0, 0)

        # ── Page 0: Default Media Dashboard Body ──────────────────────
        self.default_page = QWidget()
        def_layout = QVBoxLayout(self.default_page)
        def_layout.setContentsMargins(0, 2, 0, 0)
        def_layout.setSpacing(6)

        # Row 2: Timeline Scrubber
        row2 = QHBoxLayout()
        row2.setSpacing(6)

        self.lbl_time_cur = QLabel("0:00")
        self.lbl_time_cur.setStyleSheet("color: #71717A; font-size: 9px; font-weight: 600; font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif;")
        self.lbl_time_cur.setFixedWidth(28)

        self.scrubber = ModernSlider(is_range_100=False, accent_color=Palette.ACCENT_MEDIA)
        self.scrubber.valueChanged.connect(self._on_scrubber_changed)

        self.lbl_time_tot = QLabel("0:00")
        self.lbl_time_tot.setStyleSheet("color: #71717A; font-size: 9px; font-weight: 600; font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif;")
        self.lbl_time_tot.setFixedWidth(28)
        self.lbl_time_tot.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        row2.addWidget(self.lbl_time_cur)
        row2.addWidget(self.scrubber, stretch=1)
        row2.addWidget(self.lbl_time_tot)

        def_layout.addLayout(row2)

        # Row 3: Expansive Master Volume Slider + Battery Pill
        row3 = QHBoxLayout()
        row3.setSpacing(8)

        self.btn_speaker = QPushButton()
        self.btn_speaker.setFixedSize(22, 22)
        self.btn_speaker.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_speaker.setStyleSheet("background: transparent; border: none;")
        self.speaker_icon = VectorIcon("speaker", size=18, color=Palette.TEXT_PRIMARY, parent=self.btn_speaker)
        self.btn_speaker.clicked.connect(self.mute_toggled.emit)
        row3.addWidget(self.btn_speaker)

        self.vol_slider = ModernSlider(is_range_100=True, accent_color=Palette.ACCENT_CPU)
        self.vol_slider.setFixedHeight(14)
        self.vol_slider.valueChanged.connect(lambda v: self.volume_changed.emit(int(v)))
        row3.addWidget(self.vol_slider, stretch=1)

        self.battery_pill = BatteryPill()
        row3.addWidget(self.battery_pill)

        def_layout.addLayout(row3)

        # AI Interactive Drawer
        self.ai_panel = QWidget()
        self.ai_panel.setVisible(False)
        self.ai_panel.setMinimumSize(0, 0)
        ai_layout = QVBoxLayout(self.ai_panel)
        ai_layout.setContentsMargins(0, 2, 0, 2)
        ai_layout.setSpacing(4)

        input_row = QHBoxLayout()
        input_row.setSpacing(6)
        self.ai_input = QLineEdit()
        self.ai_input.setPlaceholderText(t("ai_placeholder"))
        self.ai_input.setStyleSheet(
            "QLineEdit { background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(56, 189, 248, 0.35); "
            "border-radius: 12px; padding: 4px 10px; color: #FFFFFF; font-size: 11px; font-family: 'Segoe UI', 'Segoe UI', sans-serif; }"
            "QLineEdit:focus { border: 1px solid rgba(56, 189, 248, 0.85); background: rgba(255, 255, 255, 0.12); }"
        )
        self.ai_input.returnPressed.connect(self._on_ai_submit)
        input_row.addWidget(self.ai_input, stretch=1)

        btn_send_ai = QPushButton("Sor")
        btn_send_ai.setFixedSize(40, 24)
        btn_send_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_send_ai.setStyleSheet(
            "QPushButton { background: rgba(56, 189, 248, 0.25); color: #E0F2FE; font-weight: 600; border-radius: 12px; font-size: 11px; border: 1px solid rgba(56, 189, 248, 0.45); font-family: 'Segoe UI', 'Segoe UI', sans-serif; }"
            "QPushButton:hover { background: rgba(56, 189, 248, 0.55); color: #FFFFFF; }"
        )
        btn_send_ai.clicked.connect(self._on_ai_submit)
        input_row.addWidget(btn_send_ai)

        self.btn_close_ai = QPushButton("✕")
        self.btn_close_ai.setFixedSize(24, 24)
        self.btn_close_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close_ai.setToolTip(t("close_ai"))
        self.btn_close_ai.setStyleSheet(
            "QPushButton { background: rgba(255, 255, 255, 0.08); color: #94A3B8; font-weight: bold; border-radius: 12px; font-size: 11px; border: 1px solid rgba(255, 255, 255, 0.12); }"
            "QPushButton:hover { background: rgba(239, 68, 68, 0.35); color: #FFFFFF; border-color: rgba(239, 68, 68, 0.5); }"
        )
        self.btn_close_ai.clicked.connect(self.close_ai_drawer)
        input_row.addWidget(self.btn_close_ai)
        ai_layout.addLayout(input_row)

        self.ai_scroll = QScrollArea()
        self.ai_scroll.setWidgetResizable(True)
        self.ai_scroll.setFixedHeight(72)
        self.ai_scroll.setStyleSheet("""
            QScrollArea {
                background: rgba(14, 16, 22, 0.70);
                border: 1px solid rgba(56, 189, 248, 0.28);
                border-radius: 10px;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 5px;
                margin: 2px 2px 2px 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.28);
                min-height: 14px;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(56, 189, 248, 0.65);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        self.lbl_ai_response = QLabel("")
        self.lbl_ai_response.setWordWrap(True)
        self.lbl_ai_response.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lbl_ai_response.setStyleSheet("color: #F0F9FF; font-size: 10.5px; font-weight: 500; padding: 4px 6px; background: transparent; font-family: 'Segoe UI', 'Segoe UI', sans-serif;")
        self.ai_scroll.setWidget(self.lbl_ai_response)
        self.ai_scroll.setVisible(False)
        ai_layout.addWidget(self.ai_scroll)
        def_layout.addWidget(self.ai_panel)

        # Row 4: Apple-Style Telemetry & Core Action Dock
        self.quick_dock = QuickDockWidget(self)
        self.btn_ai = self.quick_dock.btn_ai
        self.btn_pocket = self.quick_dock.btn_pocket
        self.btn_lock = self.quick_dock.btn_lock
        self.quick_dock.ai_clicked.connect(self._toggle_ai_input)
        self.quick_dock.lock_clicked.connect(self._trigger_lock_pc)
        self.quick_dock.calendar_clicked.connect(lambda: self.show_section(1))
        def_layout.addWidget(self.quick_dock)

        # Companion Lounge widget instance retained for dedicated Pixel page
        self.pet_lounge = PetLoungeWidget()

        self.body_stack.addWidget(self.default_page)

        # ── Page 1: Apple iOS Control Center Pro Body ──────────────────
        self.page_cc = IOSControlCenterWidget(self)
        self.page_cc.volume_changed.connect(self.volume_changed.emit)
        self.page_cc.open_settings_requested.connect(self.open_settings_requested.emit)
        self.page_cc.lock_pc_requested.connect(self._trigger_lock_pc)
        self.page_cc.take_screenshot_requested.connect(self.take_screenshot_clicked.emit)
        self.page_cc.dnd_toggled.connect(self.dnd_toggled.emit)
        self.body_stack.addWidget(self.page_cc)

        # ── Page 2: Apple Calendar & To-Do List Body ───────────────────
        self.page_cal = CalendarTodoWidget(self)
        self.body_stack.addWidget(self.page_cal)

        # ── Page 3: Medya ve Ses Body ──────────────────────────────────
        self.page_media = QWidget()
        media_layout = QVBoxLayout(self.page_media)
        media_layout.setContentsMargins(0, 4, 0, 2)
        media_layout.setSpacing(6)

        mr1 = QHBoxLayout(); mr1.setSpacing(8)
        self.btn_m_prev = SectionTileButton(t("media_prev"), t("media_prev_desc"))
        self.btn_m_prev.clicked.connect(self.prev_clicked.emit)
        self.btn_m_play = SectionTileButton(t("media_toggle"), t("media_toggle_desc"))
        self.btn_m_play.clicked.connect(self._optimistic_play_toggle)
        self.btn_m_next = SectionTileButton(t("media_next"), t("media_next_desc"))
        self.btn_m_next.clicked.connect(self.next_clicked.emit)
        mr1.addWidget(self.btn_m_prev)
        mr1.addWidget(self.btn_m_play)
        mr1.addWidget(self.btn_m_next)
        media_layout.addLayout(mr1)

        mr2 = QHBoxLayout(); mr2.setSpacing(8)
        self.btn_m_sound = SectionTileButton(t("windows_sound"), t("windows_sound_desc"))
        self.btn_m_sound.clicked.connect(self.sound_settings_clicked.emit)
        self.btn_m_app = SectionTileButton(t("music_app"), t("music_app_desc"))
        self.btn_m_app.clicked.connect(self.bring_music_clicked.emit)
        mr2.addWidget(self.btn_m_sound)
        mr2.addWidget(self.btn_m_app)
        media_layout.addLayout(mr2)

        mr3 = QHBoxLayout(); mr3.setSpacing(8)
        self.lbl_media_volume = QLabel(t("volume_label"))
        self.lbl_media_volume.setStyleSheet("color: #A1A1AA; font-size: 11px; font-weight: 500; font-family: 'Segoe UI', 'Segoe UI', sans-serif;")
        self.lbl_media_volume.setFixedWidth(64)
        mr3.addWidget(self.lbl_media_volume)
        self.vol_slider_media = ModernSlider(is_range_100=True, accent_color=Palette.ACCENT_CPU)
        self.vol_slider_media.setFixedHeight(14)
        self.vol_slider_media.valueChanged.connect(lambda v: self.volume_changed.emit(int(v)))
        mr3.addWidget(self.vol_slider_media, stretch=1)
        media_layout.addLayout(mr3)

        self.body_stack.addWidget(self.page_media)

        # ── Page 4: Pixel Body ─────────────────────────────────────────
        self.page_pixel = QWidget()
        pixel_layout = QVBoxLayout(self.page_pixel)
        pixel_layout.setContentsMargins(0, 4, 0, 2)
        pixel_layout.setSpacing(6)
        pixel_layout.addWidget(self.pet_lounge)

        pr1 = QHBoxLayout(); pr1.setSpacing(8)
        self.btn_p_flip = SectionTileButton(t("pixel_celebrate"), t("pixel_celebrate_desc"))
        self.btn_p_flip.clicked.connect(self.pet_lounge.pet_avatar.trigger_happy_flip)
        self.btn_p_anim = SectionTileButton(t("pixel_animations"), t("pixel_animations_desc"))
        self.btn_p_anim.clicked.connect(self._toggle_pixel_animations)
        pr1.addWidget(self.btn_p_flip)
        pr1.addWidget(self.btn_p_anim)
        pixel_layout.addLayout(pr1)

        pr2 = QHBoxLayout(); pr2.setSpacing(8)
        self.btn_p_water = SectionTileButton(t("pixel_water"), t("pixel_water_desc"))
        self.btn_p_water.clicked.connect(self.pet_lounge.water_clicked.emit)
        self.btn_p_break = SectionTileButton(t("eye_break"), t("eye_break_desc"))
        self.btn_p_break.clicked.connect(self.pet_lounge.break_clicked.emit)
        pr2.addWidget(self.btn_p_water)
        pr2.addWidget(self.btn_p_break)
        pixel_layout.addLayout(pr2)

        pr3 = QHBoxLayout(); pr3.setSpacing(8)
        self.btn_p_species = SectionTileButton(t("pixel_species"), t("pixel_species_desc"))
        self.btn_p_species.clicked.connect(self.pet_lounge._on_avatar_clicked)
        self.btn_p_clear = SectionTileButton(t("clear_pocket"), t("clear_pocket_desc"))
        self.btn_p_clear.clicked.connect(self.clear_pocket_clicked.emit)
        pr3.addWidget(self.btn_p_species)
        pr3.addWidget(self.btn_p_clear)
        pixel_layout.addLayout(pr3)

        self.body_stack.addWidget(self.page_pixel)

        outer.addWidget(self.body_stack, 1)

        # ── Apple iOS Page Indicator Dots ────────────────────────────────
        self.page_dots = PageDotsIndicator(count=5, parent=self)
        self.page_dots.page_selected.connect(self._on_dot_selected)
        outer.addWidget(self.page_dots, 0, Qt.AlignmentFlag.AlignCenter)

    def _on_dot_selected(self, page_idx: int) -> None:
        self.show_section(page_idx - 1)

    def next_section(self) -> None:
        curr_page = 0 if self._current_section_index < 0 else (self._current_section_index + 1)
        next_page = (curr_page + 1) % 5
        self.show_section(next_page - 1)

    def prev_section(self) -> None:
        curr_page = 0 if self._current_section_index < 0 else (self._current_section_index + 1)
        prev_page = (curr_page - 1 + 5) % 5
        self.show_section(prev_page - 1)

    def _toggle_pixel_animations(self) -> None:
        """Toggles Pixel's motion animations and displays a brief visual feedback."""
        enabled = self.pet_lounge.pet_avatar.toggle_animations()
        self.pet_lounge.show_notification_bubble(t("pixel_anim_on") if enabled else t("pixel_anim_off"))

    def show_section(self, index: int) -> None:
        """
        Switches between the default media dashboard (-1) and the selected section (0, 1, 2)
        with a fluid in-island opacity transition without shifting window geometry.
        """
        # If user clicks the currently active section button again, toggle back to main (-1)
        if index >= 0 and self._current_section_index == index:
            index = -1
        self._current_section_index = index

        page_idx = 0 if index < 0 else (index + 1)

        # Update nav button states
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

        if hasattr(self, 'page_dots'):
            self.page_dots.set_active_index(page_idx)

        # Dynamic morphing height per page
        from core.config import Dimensions
        if page_idx == 1:
            target_h = Dimensions.EXPANDED_CC_HEIGHT
        elif page_idx == 2:
            target_h = Dimensions.EXPANDED_CAL_HEIGHT
        elif page_idx == 4:
            target_h = Dimensions.EXPANDED_PIXEL_HEIGHT
        else:
            target_h = Dimensions.EXPANDED_HEIGHT
        self.section_height_changed.emit(target_h)

        # Switch header left & right stacks
        self.header_left_stack.setCurrentIndex(page_idx)
        self.header_right_stack.setCurrentIndex(page_idx)

        # Switch body stack with smooth fluid crossfade animation
        old_widget = self.body_stack.currentWidget()
        new_widget = self.body_stack.widget(page_idx)
        if new_widget and old_widget != new_widget:
            self.body_stack.setCurrentWidget(new_widget)
            effect = QGraphicsOpacityEffect(new_widget)
            new_widget.setGraphicsEffect(effect)
            if self._fade_anim is not None:
                self._fade_anim.stop()
            self._fade_anim = QPropertyAnimation(effect, b"opacity", self)
            self._fade_anim.setDuration(160)
            self._fade_anim.setStartValue(0.1)
            self._fade_anim.setEndValue(1.0)
            self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._fade_anim.start()

    # ── Slots & Actions ────────────────────────────────────────────────

    def _show_options_menu(self) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: rgba(10, 11, 15, 0.98);
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 12px;
                padding: 6px;
                color: #FFFFFF;
                font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif;
                font-size: 11.5px;
                font-weight: 600;
            }
            QMenu::item {
                padding: 6px 14px 6px 10px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background: rgba(255, 255, 255, 0.15);
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.09);
                margin: 4px 6px;
            }
        """)

        act_ram = menu.addAction(t("menu_ram"))
        act_ram.triggered.connect(self.optimize_ram_clicked.emit)

        act_shot = menu.addAction(t("menu_screenshot"))
        act_shot.triggered.connect(self.take_screenshot_clicked.emit)

        act_perf = menu.addAction(t("menu_performance"))
        act_perf.triggered.connect(self.power_mode_clicked.emit)

        menu.addSeparator()

        act_pomodoro = menu.addAction(t("menu_focus"))
        act_pomodoro.triggered.connect(self.pomodoro_toggled.emit)

        act_music = menu.addAction(t("music_app"))
        act_music.triggered.connect(self.bring_music_clicked.emit)

        act_dnd = menu.addAction(t("menu_dnd"))
        act_dnd.triggered.connect(self.dnd_toggled.emit)

        menu.addSeparator()

        act_clear_pocket = menu.addAction(t("menu_clear_pocket"))
        act_clear_pocket.triggered.connect(self.clear_pocket_clicked.emit)

        act_sound = menu.addAction(t("menu_open_sound"))
        act_sound.triggered.connect(self.sound_settings_clicked.emit)

        menu.addSeparator()

        act_settings = menu.addAction(t("tray_settings"))
        act_settings.triggered.connect(self.open_settings_requested.emit)

        pos = self.btn_more.mapToGlobal(self.btn_more.rect().bottomLeft())
        menu.exec(pos)

    def _toggle_ai_input(self) -> None:
        is_visible = not self.ai_panel.isVisible()
        self.ai_panel.setVisible(is_visible)
        self.ai_drawer_toggled.emit(is_visible)
        if is_visible:
            self.ai_input.setFocus()

    def close_ai_drawer(self) -> None:
        self.ai_panel.setVisible(False)
        self.ai_scroll.setVisible(False)
        self.lbl_ai_response.setVisible(False)
        self.ai_drawer_toggled.emit(False)

    def _on_ai_submit(self) -> None:
        text = self.ai_input.text().strip()
        if text:
            self.ai_input.clear()  # Mesaj text alanından anında temizlenir
            self.lbl_ai_response.setText(t("ai_thinking"))
            self.ai_scroll.setVisible(True)
            self.lbl_ai_response.setVisible(True)
            self.ai_ask_requested.emit(text)

    def display_ai_response(self, text: str) -> None:
        self.lbl_ai_response.setText(f"{text}")
        self.ai_scroll.setVisible(True)
        self.lbl_ai_response.setVisible(True)
        self.ai_panel.setVisible(True)
        self.ai_drawer_toggled.emit(True)

    def set_pocket_files(self, files: List[str]) -> None:
        self.btn_pocket.set_files(files)
        self.pet_lounge.pet_avatar.set_pocket_active(len(files) > 0)

    def _on_scrubber_changed(self, ratio: float) -> None:
        if self._duration_sec > 0:
            self.seek_requested.emit(ratio * self._duration_sec)

    @staticmethod
    def _format_time(sec: float) -> str:
        s = int(max(0.0, sec))
        return f"{s // 60}:{s % 60:02d}"

    def update_media(self, title: str, artist: str, is_playing: bool,
                     pixmap: Optional[QPixmap],
                     pos_sec: float = 0.0, dur_sec: float = 0.0) -> None:
        import time
        self.lbl_title.setText(title or t("media_idle_title"))
        self.lbl_artist.setText(artist or (t("media_idle_artist") if not title else "WinIsland"))
        # Debounce: skip play/pause glyph updates within 400ms of a user toggle
        # to avoid stale GSMTC async events reverting the optimistic icon
        if time.monotonic() - self._last_play_toggle_time > 0.4:
            self.btn_play.set_action("pause" if is_playing else "play")
        self.thumb.set_pixmap(pixmap)
        self._duration_sec = dur_sec
        self.lbl_time_cur.setText(self._format_time(pos_sec))
        self.lbl_time_tot.setText(self._format_time(dur_sec))
        if dur_sec > 0:
            self.scrubber.set_value(max(0.0, min(1.0, pos_sec / dur_sec)))
        else:
            self.scrubber.set_value(0.0)

    def _optimistic_play_toggle(self) -> None:
        """
        Update the play glyph immediately while Windows handles the media command.
        400ms debounce prevents stale GSMTC async events from reverting the icon.
        """
        import time
        self._last_play_toggle_time = time.monotonic()
        next_action = "play" if self.btn_play.action_type == "pause" else "pause"
        self.btn_play.set_action(next_action)
        self.play_pause_clicked.emit()

    def update_volume(self, percent: int, is_muted: bool) -> None:
        self.vol_slider.set_value(float(percent))
        self.speaker_icon.set_type("speaker_mute" if is_muted else "speaker")

    def update_weather(self, temp: str, condition: str, icon_type: str) -> None:
        """Update the weather pill in the expanded header."""
        self.weather_pill.update_weather(temp, condition, icon_type)

    def update_telemetry(self, cpu: float, ram: float, ram_used: float, ram_tot: float,
                         bat_pct: int, plugged: bool, has_bat: bool) -> None:
        self.battery_pill.update_battery(bat_pct, plugged, has_bat)
        if hasattr(self, 'quick_dock'):
            self.quick_dock.update_telemetry(cpu, ram)

    def update_pet(self, state, stats=None) -> None:
        self.pet_lounge.update_pet(state, stats)

    @staticmethod
    def _trigger_lock_pc() -> None:
        try:
            ctypes.windll.user32.LockWorkStation()
        except Exception:
            pass
