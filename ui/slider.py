"""
WinIsland - Modern Sleek Sliders (Volume, Brightness, Scrubber)
"""

from typing import Optional
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QBrush
from PyQt6.QtWidgets import QWidget
from core.config import Palette


class ModernSlider(QWidget):
    valueChanged = pyqtSignal(float)

    def __init__(self, is_range_100: bool = False,
                 accent_color: QColor = Palette.TEXT_PRIMARY,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_range_100 = is_range_100
        self.accent_color = accent_color
        self._value = 0.0
        self._hovered = False
        self._dragging = False
        self.setFixedHeight(16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_value(self, val: float) -> None:
        if not self._dragging:
            self._value = max(0.0, min(100.0 if self.is_range_100 else 1.0, float(val)))
            self.update()

    def setValue(self, val: float) -> None:
        self.set_value(val)

    def get_value(self) -> float:
        return self._value

    def value(self) -> float:
        return self._value

    def enterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._update_from_mouse(event.pos().x())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._dragging:
            self._update_from_mouse(event.pos().x())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.valueChanged.emit(self._value)
        super().mouseReleaseEvent(event)

    def _update_from_mouse(self, x: float) -> None:
        w = max(1.0, float(self.width()))
        ratio = max(0.0, min(1.0, x / w))
        self._value = ratio * 100.0 if self.is_range_100 else ratio
        self.valueChanged.emit(self._value)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = float(self.width())
        h = float(self.height())
        track_h = 4.0 if not (self._hovered or self._dragging) else 5.5
        track_y = (h - track_h) / 2.0
        painter.setBrush(QBrush(QColor(255, 255, 255, 25)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(0, track_y, w, track_h), track_h / 2.0, track_h / 2.0)
        ratio = (self._value / 100.0) if self.is_range_100 else self._value
        fill_w = ratio * w
        if fill_w > 0:
            painter.setBrush(QBrush(self.accent_color))
            painter.drawRoundedRect(QRectF(0, track_y, fill_w, track_h), track_h / 2.0, track_h / 2.0)
        if self._hovered or self._dragging:
            thumb_r = 5.0
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(QRectF(max(0.0, fill_w - thumb_r), (h - thumb_r * 2) / 2.0, thumb_r * 2, thumb_r * 2))
        painter.end()
