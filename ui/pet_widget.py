"""
WinIsland - Pixel the Tamagotchi Desktop Pet
Pure QPainter vector animated pet named Pixel (Adorable Kitten & Baby Dragon).
12 real-time reactive states based on system load, coding cadence, battery & music.
Includes Pocket Mode (holding a cute satchel when files are stored).
"""

import math
import random
import time
from typing import Optional
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush, QPainterPath, QLinearGradient
)
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton

from core.config import Palette, Typography
from modules.pet import PetState, PetStats
from modules.i18n import I18nManager


class PetSpecies:
    CAT = "cat"
    DRAGON = "dragon"


class PetWidget(QWidget):
    """
    Pixel - The Interactive Desktop Companion.
    Supports Yavru Kedi (Kitten) and Yavru Ejderha (Baby Dragon) forms.
    """
    clicked = pyqtSignal()

    def __init__(self, size: int = 42, species: str = PetSpecies.CAT, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._size = size
        self.species = species
        self.setFixedSize(size, size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._state: PetState = PetState.IDLE
        self._stats: Optional[PetStats] = None
        self._xp: int = 150
        self.has_pocket: bool = False  # True when files are stored in backpack

        # Animation states
        self._phase: float = 0.0
        self._flip_angle: float = 0.0
        self._is_flipping: bool = False
        self._blink_counter: int = 0
        self._is_blinking: bool = False
        self._animations_enabled: bool = True

        # 30 FPS animation loop
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._on_tick)
        self._update_tooltip()
        I18nManager.get_instance().language_changed.connect(lambda _lang: self._update_tooltip())

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._animations_enabled and not self._timer.isActive():
            self._timer.start()

    def hideEvent(self, event) -> None:
        self._timer.stop()
        super().hideEvent(event)

    def set_species(self, species: str) -> None:
        self.species = species
        self._update_tooltip()
        self.update()

    def toggle_animations(self) -> bool:
        self._animations_enabled = not self._animations_enabled
        if self._animations_enabled:
            if self.isVisible():
                self._timer.start()
        else:
            self._timer.stop()
            self._is_flipping = False
            self._is_blinking = False
            self._phase = 0.0
        self.update()
        return self._animations_enabled

    def toggle_species(self) -> str:
        self.species = PetSpecies.DRAGON if self.species == PetSpecies.CAT else PetSpecies.CAT
        self._update_tooltip()
        self.update()
        return self.species

    def set_pet_state(self, state: PetState) -> None:
        if state == PetState.HAPPY and not self._is_flipping:
            self._is_flipping = True
            self._flip_angle = 0.0
        self._state = state
        self._update_tooltip()
        self.update()

    def set_stats(self, stats: PetStats) -> None:
        self._stats = stats
        self._xp = stats.xp
        self._update_tooltip()
        self.update()

    def set_pocket_active(self, active: bool) -> None:
        self.has_pocket = active
        self._update_tooltip()
        self.update()

    def trigger_happy_flip(self) -> None:
        """Trigger a joyous 360-degree backflip with hearts."""
        self._is_flipping = True
        self._flip_angle = 0.0
        self._state = PetState.HAPPY
        self.update()

    def _update_tooltip(self) -> None:
        english = I18nManager.get_instance().current_language == "en"
        if english:
            names = {PetSpecies.CAT: "Pixel (Kitten)", PetSpecies.DRAGON: "Pixel (Baby Dragon)"}
            state_names = {
                PetState.IDLE: "Resting calmly", PetState.SLEEPING: "Sleeping",
                PetState.HAPPY: "Happy and doing a flip", PetState.PANICKING: "CPU above 95%; panicking",
                PetState.BLOATED: "RAM is full", PetState.FLYING: "Surfing the breeze",
                PetState.CODING: "Coding quickly", PetState.SHOCKED: "Power connected",
                PetState.PEEKING_LEFT: "Peeking from the side", PetState.PEEKING_RIGHT: "Peeking from the side",
                PetState.DANCING: "Dancing to music", PetState.HIDING: "Low on energy, hiding",
            }
            status = state_names.get(self._state, "Happy")
            pocket = "\nFiles in pocket (drag to take them out)" if self.has_pocket else ""
            self.setToolTip(f"{names[self.species]}\nStatus: {status}\nXP: {self._xp}{pocket}\nClick to change form")
            return
        name_str = "Pixel (Yavru Kedi)" if self.species == PetSpecies.CAT else "Pixel (Yavru Ejderha)"
        state_names = {
            PetState.IDLE: "Sakin dinleniyor",
            PetState.SLEEPING: "Mışıl mışıl uyuyor (Zzz)",
            PetState.HAPPY: "Çok mutlu! Takla atıyor ",
            PetState.PANICKING: "CPU > %95! Terliyor ve panikliyor ",
            PetState.BLOATED: "RAM Dolu! Yanakları şişti ",
            PetState.FLYING: "Rüzgarda sörf yapıyor ",
            PetState.CODING: "Hızlı kod yazıyor! ",
            PetState.SHOCKED: "Şarj takıldı! Elektrik efekti ",
            PetState.PEEKING_LEFT: "Kenardan dikizliyor ",
            PetState.PEEKING_RIGHT: "Kenardan dikizliyor ",
            PetState.DANCING: "Müzikle kafa sallıyor ",
            PetState.HIDING: "Enerjisi azaldı, saklanıyor...",
        }
        status_txt = state_names.get(self._state, "Mutlu")
        pocket_txt = "\n Çantada dosya var (Sürükleyip çıkarabilirsin!)" if self.has_pocket else ""
        self.setToolTip(f"{name_str}\nDurum: {status_txt}\nXP: {self._xp}{pocket_txt}\n(Tıkla: Form Değiştir)")

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def _on_tick(self) -> None:
        self._phase += 0.12

        # Blinking logic
        self._blink_counter += 1
        if self._blink_counter > 85:
            self._is_blinking = True
            if self._blink_counter > 92:
                self._is_blinking = False
                self._blink_counter = random.randint(0, 30)

        # Backflip logic
        if self._is_flipping:
            self._flip_angle += 24.0
            if self._flip_angle >= 360.0:
                self._flip_angle = 0.0
                self._is_flipping = False
                if self._state == PetState.HAPPY:
                    self._state = PetState.IDLE

        self.update()

    # ── Master Paint Dispatcher ──────────────────────────────────────────

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())
        cx = w / 2.0
        cy = h / 2.0

        bounce = 0.0
        squash_x = 1.0
        squash_y = 1.0

        if self._state == PetState.DANCING:
            bounce = math.sin(self._phase * 2.2) * 3.0
            squash_x = 1.0 + math.sin(self._phase * 2.2) * 0.12
            squash_y = 1.0 - math.sin(self._phase * 2.2) * 0.12
        elif self._state == PetState.CODING:
            bounce = math.sin(self._phase * 4.5) * 1.8
            squash_x = 1.06
            squash_y = 0.96
        elif self._state == PetState.PANICKING:
            cx += (random.random() - 0.5) * 3.5
            cy += (random.random() - 0.5) * 3.5
        elif self._state == PetState.SLEEPING:
            bounce = math.sin(self._phase * 0.6) * 1.0
            squash_y = 0.82
            squash_x = 1.12
        elif self._state == PetState.BLOATED:
            squash_x = 1.40
            squash_y = 1.20
        elif self._state == PetState.FLYING:
            bounce = math.sin(self._phase * 3.0) * 3.5
        else:
            bounce = math.sin(self._phase) * 1.2

        painter.save()
        painter.translate(cx, cy + bounce)

        if self._is_flipping:
            painter.rotate(self._flip_angle)

        painter.scale(squash_x, squash_y)

        # Scale according to widget dimensions
        base_scale = self._size / 42.0
        painter.scale(base_scale, base_scale)

        if self.species == PetSpecies.DRAGON:
            self._draw_pixel_dragon(painter)
        else:
            self._draw_pixel_cat(painter)

        # Draw Pocket satchel if holding files
        if self.has_pocket:
            self._draw_satchel(painter)

        painter.restore()
        self._draw_overlays(painter, w, h)

    def _draw_satchel(self, p: QPainter) -> None:
        """Tiny cute leather satchel backpack hanging on Pixel's shoulder."""
        p.setPen(QPen(QColor(160, 95, 40), 1.0))
        p.setBrush(QBrush(QColor(195, 120, 55)))
        p.drawRoundedRect(QRectF(-14, 2, 7, 8), 2, 2)
        # Strap
        p.setPen(QPen(QColor(140, 80, 30), 1.2))
        p.drawLine(-11, 2, -5, -4)
        # Golden buckle
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(255, 215, 60)))
        p.drawEllipse(QRectF(-11.5, 5, 2, 2))

    # ── Pixel The Kitten (Yavru Kedi) ────────────────────────────────────

    def _draw_pixel_cat(self, p: QPainter) -> None:
        grad = QLinearGradient(0, -13, 0, 13)
        if self._state == PetState.PANICKING:
            grad.setColorAt(0.0, QColor(255, 130, 90))
            grad.setColorAt(1.0, QColor(220, 60, 40))
        elif self._state == PetState.SHOCKED:
            grad.setColorAt(0.0, QColor(255, 235, 90))
            grad.setColorAt(1.0, QColor(235, 175, 25))
        else:
            grad.setColorAt(0.0, QColor(62, 66, 85))
            grad.setColorAt(1.0, QColor(30, 32, 45))

        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor(255, 255, 255, 50), 1.0))

        # Pointy cute ears with twitching motion
        twitch = math.sin(self._phase * 1.8) * 1.2
        ear_l = QPainterPath()
        ear_l.moveTo(-9, -7)
        ear_l.lineTo(-13 + twitch, -17)
        ear_l.lineTo(-4, -11)
        p.drawPath(ear_l)

        ear_r = QPainterPath()
        ear_r.moveTo(9, -7)
        ear_r.lineTo(13 - twitch, -17)
        ear_r.lineTo(4, -11)
        p.drawPath(ear_r)

        # Soft pink inner ears
        p.setBrush(QBrush(QColor(255, 160, 185, 220)))
        p.setPen(Qt.PenStyle.NoPen)
        inner_l = QPainterPath()
        inner_l.moveTo(-8.5, -8)
        inner_l.lineTo(-12 + twitch, -15)
        inner_l.lineTo(-5, -11)
        p.drawPath(inner_l)
        inner_r = QPainterPath()
        inner_r.moveTo(8.5, -8)
        inner_r.lineTo(12 - twitch, -15)
        inner_r.lineTo(5, -11)
        p.drawPath(inner_r)

        # Round chubby head & body
        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor(255, 255, 255, 55), 1.0))
        p.drawRoundedRect(QRectF(-13, -11, 26, 23), 10, 10)

        # Swishing tail
        tail = QPainterPath()
        tail.moveTo(11, 8)
        tail_swish = math.sin(self._phase * 2.2) * 5.0
        tail.quadTo(19 + tail_swish, 5, 18 + tail_swish, -4)
        p.setPen(QPen(QColor(70, 75, 98), 2.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(tail)

        # Whiskers
        p.setPen(QPen(QColor(255, 255, 255, 140), 1.0))
        p.drawLine(-15, 0, -9, -1)
        p.drawLine(-15, 4, -9, 3)
        p.drawLine(15, 0, 9, -1)
        p.drawLine(15, 4, 9, 3)

        # Cute Paws
        p.setBrush(QBrush(QColor(48, 52, 68)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(-9, 9, 6, 4))
        p.drawEllipse(QRectF(3, 9, 6, 4))

        # Face
        self._draw_cat_face(p)

    def _draw_cat_face(self, p: QPainter) -> None:
        p.setPen(Qt.PenStyle.NoPen)

        # Sleeping or Blinking
        if self._is_blinking or self._state == PetState.SLEEPING:
            p.setPen(QPen(QColor(230, 235, 250), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(-8, -2, -3, -2)
            p.drawLine(3, -2, 8, -2)
            p.drawArc(QRectF(-3, 1, 6, 4), 180 * 16, 180 * 16)
            return

        # Panicking wide eyes
        if self._state == PetState.PANICKING:
            p.setBrush(QBrush(QColor(255, 255, 255)))
            p.drawEllipse(QRectF(-9, -5, 7, 7))
            p.drawEllipse(QRectF(2, -5, 7, 7))
            p.setBrush(QBrush(QColor(20, 20, 30)))
            p.drawEllipse(QRectF(-7, -3, 3, 3))
            p.drawEllipse(QRectF(4, -3, 3, 3))
            p.setBrush(QBrush(QColor(230, 60, 70)))
            p.drawEllipse(QRectF(-2.5, 2, 5, 5))
            return

        # Happy crescent eyes
        if self._state in (PetState.HAPPY, PetState.DANCING):
            p.setPen(QPen(QColor(240, 245, 255), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(QRectF(-8, -5, 6, 6), 0, 180 * 16)
            p.drawArc(QRectF(2, -5, 6, 6), 0, 180 * 16)
            p.setBrush(QBrush(QColor(255, 120, 140)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QRectF(-2.5, 2, 5, 3.5))
            return

        # Big kawaii anime kitten eyes
        p.setBrush(QBrush(QColor(30, 215, 160)))
        p.drawEllipse(QRectF(-8.5, -4, 6, 6.5))
        p.drawEllipse(QRectF(2.5, -4, 6, 6.5))

        # Pupils
        p.setBrush(QBrush(QColor(10, 20, 25)))
        p.drawEllipse(QRectF(-7.5, -3, 4.0, 5.0))
        p.drawEllipse(QRectF(3.5, -3, 4.0, 5.0))

        # Sparkle catchlights
        p.setBrush(QBrush(QColor(255, 255, 255)))
        p.drawEllipse(QRectF(-7.5, -3.5, 2.4, 2.4))
        p.drawEllipse(QRectF(3.5, -3.5, 2.4, 2.4))
        p.drawEllipse(QRectF(-5.5, 0.5, 1.2, 1.2))
        p.drawEllipse(QRectF(5.5, 0.5, 1.2, 1.2))

        # Soft pink blush
        p.setBrush(QBrush(QColor(255, 130, 160, 140)))
        p.drawEllipse(QRectF(-11, 1.5, 4, 2.5))
        p.drawEllipse(QRectF(7, 1.5, 4, 2.5))

        # Cute pink nose :3
        p.setBrush(QBrush(QColor(255, 150, 180)))
        p.drawEllipse(QRectF(-1.2, 0.5, 2.4, 1.8))
        p.setPen(QPen(QColor(200, 210, 230), 1.1))
        p.drawArc(QRectF(-3.5, 1.5, 3.5, 3.0), 180 * 16, 180 * 16)
        p.drawArc(QRectF(0, 1.5, 3.5, 3.0), 180 * 16, 180 * 16)

    # ── Pixel The Baby Dragon (Yavru Ejderha) ─────────────────────────────

    def _draw_pixel_dragon(self, p: QPainter) -> None:
        grad = QLinearGradient(0, -13, 0, 13)
        if self._state == PetState.PANICKING:
            grad.setColorAt(0.0, QColor(255, 110, 80))
            grad.setColorAt(1.0, QColor(190, 40, 50))
        else:
            grad.setColorAt(0.0, QColor(170, 95, 235))
            grad.setColorAt(1.0, QColor(95, 40, 165))

        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor(255, 255, 255, 60), 1.0))

        # Golden Horns
        p.setBrush(QBrush(QColor(255, 215, 60)))
        horn_l = QPainterPath()
        horn_l.moveTo(-7, -8)
        horn_l.lineTo(-12, -17)
        horn_l.lineTo(-4, -11)
        p.drawPath(horn_l)
        horn_r = QPainterPath()
        horn_r.moveTo(7, -8)
        horn_r.lineTo(12, -17)
        horn_r.lineTo(4, -11)
        p.drawPath(horn_r)

        # Flapping Wings
        wing_flap = math.sin(self._phase * 3.5) * 5.0
        p.setBrush(QBrush(QColor(210, 150, 255)))
        wing_l = QPainterPath()
        wing_l.moveTo(-9, 0)
        wing_l.lineTo(-18, -8 + wing_flap)
        wing_l.lineTo(-11, 6)
        p.drawPath(wing_l)
        wing_r = QPainterPath()
        wing_r.moveTo(9, 0)
        wing_r.lineTo(18, -8 - wing_flap)
        wing_r.lineTo(11, 6)
        p.drawPath(wing_r)

        # Body
        p.setBrush(QBrush(grad))
        p.drawRoundedRect(QRectF(-12, -11, 24, 23), 8, 8)

        # Golden dragon eyes
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(255, 215, 50)))
        p.drawEllipse(QRectF(-8, -3, 5.5, 5.5))
        p.drawEllipse(QRectF(2.5, -3, 5.5, 5.5))

        # Slit pupils
        p.setBrush(QBrush(QColor(30, 10, 45)))
        p.drawRect(QRectF(-6.0, -3, 1.6, 5.5))
        p.drawRect(QRectF(4.4, -3, 1.6, 5.5))

        # Tiny friendly flame puff if coding/happy
        if self._state in (PetState.HAPPY, PetState.CODING, PetState.DANCING):
            p.setBrush(QBrush(QColor(255, 120, 20)))
            p.drawEllipse(QRectF(5, 6, 5.5, 4.0))
            p.setBrush(QBrush(QColor(255, 220, 50)))
            p.drawEllipse(QRectF(6, 6.5, 2.8, 2.8))

    # ── State Overlays ───────────────────────────────────────────────────

    def _draw_overlays(self, p: QPainter, w: float, h: float) -> None:
        if self._state == PetState.SLEEPING:
            font = QFont("Segoe UI", 8, QFont.Weight.Bold)
            p.setFont(font)
            p.setPen(QColor(160, 210, 255, int(190 + math.sin(self._phase) * 55)))
            drift = math.sin(self._phase * 0.9) * 2.0
            p.drawText(QPointF(w - 11 + drift, 12), "z")
            p.drawText(QPointF(w - 7 + drift, 7), "Z")

        elif self._state == PetState.PANICKING:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(90, 195, 255, 230)))
            drop = QPainterPath()
            drop.moveTo(w - 7, 5)
            drop.quadTo(w - 4, 10, w - 7, 11)
            drop.quadTo(w - 10, 10, w - 7, 5)
            p.drawPath(drop)

        elif self._state == PetState.HAPPY or self._is_flipping:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(255, 75, 110)))
            hx = w - 9.0
            hy = 7.0 + math.sin(self._phase * 3.0) * 2.5
            heart = QPainterPath()
            heart.moveTo(hx, hy + 3.5)
            heart.cubicTo(hx - 3.5, hy, hx - 3.5, hy - 3.5, hx, hy - 2)
            heart.cubicTo(hx + 3.5, hy - 3.5, hx + 3.5, hy, hx, hy + 3.5)
            p.drawPath(heart)

        elif self._state == PetState.DANCING:
            note_y = 11 + math.sin(self._phase * 2.8) * 2.5
            p.setPen(QPen(QColor(230, 232, 235), 1.4, Qt.PenStyle.SolidLine,
                          Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.drawLine(QPointF(w - 8, note_y - 5), QPointF(w - 8, note_y + 1))
            p.drawLine(QPointF(w - 8, note_y - 5), QPointF(w - 4, note_y - 6))
            p.setBrush(QBrush(QColor(230, 232, 235)))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(w - 10, note_y + 2), 2.2, 1.7)

        elif self._state == PetState.CODING:
            p.setPen(QPen(QColor(255, 255, 255, 140), 0.8))
            p.setBrush(QBrush(QColor(35, 40, 52)))
            p.drawRoundedRect(QRectF(w / 2.0 - 9, h - 6, 18, 5), 1.2, 1.2)
            p.setPen(QPen(QColor(0, 229, 255), 1.2))
            p.drawPoint(int(w / 2.0 - 5), int(h - 3.5))
            p.drawPoint(int(w / 2.0), int(h - 3.5))
            p.drawPoint(int(w / 2.0 + 5), int(h - 3.5))

        elif self._state == PetState.SHOCKED:
            p.setPen(QPen(QColor(255, 235, 45), 1.8))
            p.drawLine(int(w - 7), 2, int(w - 12), 7)
            p.drawLine(int(w - 12), 7, int(w - 7), 7)
            p.drawLine(int(w - 7), 7, int(w - 11), 14)


class PetLoungeWidget(QWidget):
    """
    Spacious Companion Lounge row in Expanded Island:
    Includes:
    - Pixel Avatar (42px rich detail, click to toggle species Kitten <-> Dragon)
    - Live Status Speech Bubble
    - ` Su Ver` button
    - ` Mola Ver` button
    - Kedi / Ejderha form toggle
    """
    water_clicked = pyqtSignal()
    break_clicked = pyqtSignal()
    species_toggled = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self._current_state = PetState.IDLE
        self._current_stats = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(8)

        # Pixel Avatar (42px detailed)
        self.pet_avatar = PetWidget(size=40, species=PetSpecies.CAT, parent=self)
        self.pet_avatar.clicked.connect(self._on_avatar_clicked)
        layout.addWidget(self.pet_avatar)

        # Live Status Speech Label
        self.lbl_status = QLabel("Pixel: Dinleniyor ")
        self.lbl_status.setStyleSheet("color: #E4E4E7; font-size: 11px; font-weight: 600; font-family: 'Segoe UI', 'Segoe UI', sans-serif;")
        layout.addWidget(self.lbl_status, stretch=1)

        # Action 1: Water Button
        self.btn_water = QPushButton(" Su Ver")
        self.btn_water.setFixedSize(68, 24)
        self.btn_water.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_water.setToolTip("Pixel'e su ver & kullanıcının su içmesini hatırla (+15 XP)")
        self.btn_water.setStyleSheet(
            "QPushButton { background: rgba(255, 255, 255, 0.06); color: #E2E4E7; font-size: 10px; font-weight: 700; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.12); font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif; }"
            "QPushButton:hover { background: rgba(255, 255, 255, 0.14); color: #FFFFFF; }"
        )
        self.btn_water.clicked.connect(self.water_clicked.emit)
        layout.addWidget(self.btn_water)

        # Action 2: Coffee / Break Button
        self.btn_break = QPushButton(" Mola Ver")
        self.btn_break.setFixedSize(72, 24)
        self.btn_break.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_break.setToolTip("20-20-20 Göz Dinlendirme Kuralı (+10 XP)")
        self.btn_break.setStyleSheet(
            "QPushButton { background: rgba(255, 255, 255, 0.06); color: #E2E4E7; font-size: 10px; font-weight: 700; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.12); font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif; }"
            "QPushButton:hover { background: rgba(255, 255, 255, 0.14); color: #FFFFFF; }"
        )
        self.btn_break.clicked.connect(self.break_clicked.emit)
        layout.addWidget(self.btn_break)

        # Species Switch Pill
        self.btn_species = QPushButton("Kedi")
        self.btn_species.setFixedSize(62, 24)
        self.btn_species.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_species.setToolTip("Pixel'in Formunu Değiştir (Kedi ↔ Ejderha)")
        self.btn_species.setStyleSheet(
            "QPushButton { background: rgba(255, 255, 255, 0.06); color: #E2E4E7; font-size: 10px; font-weight: 700; border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.12); font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif; }"
            "QPushButton:hover { background: rgba(255, 255, 255, 0.14); color: #FFFFFF; }"
        )
        self.btn_species.clicked.connect(self._on_avatar_clicked)
        layout.addWidget(self.btn_species)
        I18nManager.get_instance().language_changed.connect(self._on_language_changed)
        self._on_language_changed(I18nManager.get_instance().current_language)

    def _on_avatar_clicked(self) -> None:
        new_species = self.pet_avatar.toggle_species()
        is_en = I18nManager.get_instance().current_language == "en"
        self.btn_species.setText(("Dragon" if new_species == PetSpecies.DRAGON else "Cat") if is_en else ("Ejderha" if new_species == PetSpecies.DRAGON else "Kedi"))
        self.species_toggled.emit(new_species)

    def _on_language_changed(self, lang: str) -> None:
        is_en = lang == "en"
        self.btn_water.setText("Give water" if is_en else "Su Ver")
        self.btn_water.setToolTip("Give Pixel water and remember to drink (+15 XP)" if is_en else "Pixel'e su ver ve su içmeyi hatırla (+15 XP)")
        self.btn_break.setText("Take a break" if is_en else "Mola Ver")
        self.btn_break.setToolTip("20-20-20 eye rest rule (+10 XP)" if is_en else "20-20-20 göz dinlendirme kuralı (+10 XP)")
        self.btn_species.setToolTip("Change Pixel's form (Cat ↔ Dragon)" if is_en else "Pixel'in formunu değiştir (Kedi ↔ Ejderha)")
        self._on_avatar_clicked_language_refresh()
        self.update_pet(self._current_state, self._current_stats)

    def _on_avatar_clicked_language_refresh(self) -> None:
        is_en = I18nManager.get_instance().current_language == "en"
        self.btn_species.setText(("Dragon" if self.pet_avatar.species == PetSpecies.DRAGON else "Cat") if is_en else ("Ejderha" if self.pet_avatar.species == PetSpecies.DRAGON else "Kedi"))

    def show_notification_bubble(self, message: str) -> None:
        """Display an unread reminder bubble on Pixel's speech line."""
        self.lbl_status.setText(message)

    def update_pet(self, state: PetState, stats: Optional[PetStats] = None) -> None:
        self._current_state, self._current_stats = state, stats
        self.pet_avatar.set_pet_state(state)
        if I18nManager.get_instance().current_language == "en":
            state_msgs = {
                PetState.IDLE: "Pixel: Calm and content", PetState.SLEEPING: "Pixel: Sleeping",
                PetState.HAPPY: "Pixel: Great work!", PetState.PANICKING: "Pixel: CPU is above 95%",
                PetState.BLOATED: "Pixel: RAM is full", PetState.CODING: "Pixel: Coding quickly",
                PetState.DANCING: "Pixel: Dancing to music", PetState.SHOCKED: "Pixel: Power connected",
            }
            msg = state_msgs.get(state, "Pixel: Active and happy")
            xp_str = f" · {stats.xp} XP" if stats else ""
            self.lbl_status.setText(f"{msg}{xp_str}")
            if stats:
                self.pet_avatar.set_stats(stats)
            return
        state_msgs = {
            PetState.IDLE: "Pixel: Keyifli ve sakin ",
            PetState.SLEEPING: "Pixel: Mışıl mışıl uyuyor ",
            PetState.HAPPY: "Pixel: Harika iş! Kalp fırlatıyor ",
            PetState.PANICKING: "Pixel: Çok sıcak! CPU > %95 ",
            PetState.BLOATED: "Pixel: RAM doldu, şiştim! ",
            PetState.CODING: "Pixel: Hızlı kodlama modunda! ",
            PetState.DANCING: "Pixel: Müzikle dans ediyor ",
            PetState.SHOCKED: "Pixel: Şarj takıldı! Enerji dolu ",
        }
        msg = state_msgs.get(state, "Pixel: Aktif ve mutlu ")
        xp_str = f" · {stats.xp}XP" if stats else ""
        self.lbl_status.setText(f"{msg}{xp_str}")
        if stats:
            self.pet_avatar.set_stats(stats)
