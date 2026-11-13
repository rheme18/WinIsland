"""
WinIsland - Apple-Style Interactive Page Dots Indicator
Displays smooth iOS-style capsule/dot indicators for carousel dashboard navigation.
"""

from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen
from PyQt6.QtWidgets import QWidget


class PageDotsIndicator(QWidget):
    """
    Renders iOS home screen / carousel style navigation dots.
    The active index smoothly morphs into an elongated pill.
    Clicking a dot navigates directly to that page.
    """
    page_selected = pyqtSignal(int)

    def __init__(self, count: int = 5, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._count = count
        self._active_index = 0
        self._pill_pos = 0.0  # Animated position
        self.setFixedHeight(12)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"pillPosition", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    @pyqtProperty(float)
    def pillPosition(self) -> float:
        return self._pill_pos

    @pillPosition.setter
    def pillPosition(self, val: float) -> None:
        self._pill_pos = val
        self.update()

    def set_count(self, count: int) -> None:
        self._count = max(1, count)
        self.update()

    def set_active_index(self, index: int) -> None:
        if 0 <= index < self._count and index != self._active_index:
            self._active_index = index
            self._anim.stop()
            self._anim.setStartValue(self._pill_pos)
            self._anim.setEndValue(float(index))
            self._anim.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            w = self.width()
            step = 16
            total_w = self._count * step + 8
            start_x = (w - total_w) / 2.0
            click_x = event.position().x()
            rel_x = click_x - start_x
            if 0 <= rel_x <= total_w:
                idx = int(rel_x // step)
                idx = max(0, min(self._count - 1, idx))
                self.set_active_index(idx)
                self.page_selected.emit(idx)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        dot_diam = 4.0
        pill_w = 14.0
        step = 16.0
        total_w = (self._count - 1) * step + pill_w
        start_x = (self.width() - total_w) / 2.0
        cy = self.height() / 2.0

        # Draw inactive background dots
        painter.setPen(Qt.PenStyle.NoPen)
        for i in range(self._count):
            # calculate center for dot i
            cx = start_x + (i * step) + (dot_diam / 2.0)
            painter.setBrush(QBrush(QColor(255, 255, 255, 60)))
            painter.drawEllipse(QRectF(cx - dot_diam / 2.0, cy - dot_diam / 2.0, dot_diam, dot_diam))

        # Draw active pill sliding smoothly
        active_x = start_x + (self._pill_pos * step)
        painter.setBrush(QBrush(QColor(255, 255, 255, 220)))
        painter.drawRoundedRect(QRectF(active_x, cy - dot_diam / 2.0, pill_w, dot_diam), dot_diam / 2.0, dot_diam / 2.0)

        painter.end()
