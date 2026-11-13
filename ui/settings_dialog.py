"""
WinIsland - Apple macOS / iOS Style Modern Multi-Page Settings Window
Frameless, dark acrylic glass aesthetic, instant multi-language switching (TR/EN),
and registry-backed system startup options.
"""

import math
from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QPointF, QSize, QRectF
from PyQt6.QtGui import QFont, QColor, QPainter, QBrush, QPen, QPainterPath, QPixmap, QIcon
from PyQt6.QtWidgets import (
    QDialog, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QStackedWidget, QListWidget, QListWidgetItem, QFrame, QCheckBox,
    QComboBox, QGraphicsDropShadowEffect, QSizePolicy, QApplication
)

from core.config import Palette, Typography
from modules.i18n import t, I18nManager
from modules.settings_manager import SettingsManager


class IOSToggleSwitch(QWidget):
    """Apple iOS style green pill toggle switch."""
    state_changed = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(40, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked: bool = checked

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, val: bool) -> None:
        if self._checked != val:
            self._checked = val
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._checked = not self._checked
            self.update()
            self.state_changed.emit(self._checked)
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        h = rect.height()
        w = rect.width()
        radius = h / 2.0

        if self._checked:
            # Apple emerald green
            painter.setBrush(QBrush(QColor(52, 199, 89)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(0, 0, w, h, radius, radius)
            # Knob on right
            knob_x = w - h + 2
        else:
            # Dark grey surface
            painter.setBrush(QBrush(QColor(255, 255, 255, 30)))
            painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
            painter.drawRoundedRect(0, 0, w, h, radius, radius)
            # Knob on left
            knob_x = 2

        # White Knob
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.setPen(Qt.PenStyle.NoPen)
        knob_size = h - 4
        painter.drawEllipse(int(knob_x), 2, int(knob_size), int(knob_size))
        painter.end()


class SettingRowCard(QWidget):
    """Apple macOS style settings card row with title, description, and action widget."""
    def __init__(self, title_key: str, desc_key: str = "", control_widget: Optional[QWidget] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.title_key = title_key
        self.desc_key = desc_key
        self.control_widget = control_widget
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setStyleSheet("""
            SettingRowCard {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        self.lbl_title = QLabel(t(self.title_key), self)
        self.lbl_title.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 600; font-family: 'Segoe UI', sans-serif;")
        info_layout.addWidget(self.lbl_title)

        if self.desc_key:
            self.lbl_desc = QLabel(t(self.desc_key), self)
            self.lbl_desc.setStyleSheet("color: rgba(255, 255, 255, 0.5); font-size: 10px; font-family: 'Segoe UI', sans-serif;")
            self.lbl_desc.setWordWrap(True)
            info_layout.addWidget(self.lbl_desc)

        layout.addLayout(info_layout, stretch=1)

        if self.control_widget:
            layout.addWidget(self.control_widget, alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def refresh_texts(self) -> None:
        self.lbl_title.setText(t(self.title_key))
        if hasattr(self, "lbl_desc") and self.desc_key:
            self.lbl_desc.setText(t(self.desc_key))


class ModernSettingsDialog(QDialog):
    """Standalone macOS/iOS-like comprehensive Settings Window."""
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(660, 500)

        self._drag_pos = QPoint()
        self._settings = SettingsManager.get_instance()
        self._i18n = I18nManager.get_instance()
        self._i18n.language_changed.connect(self._on_language_changed)

        self._cards = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)

        # Container Window with obsidian dark background and subtle border
        self.container = QWidget(self)
        self.container.setStyleSheet("""
            QWidget#SettingsContainer {
                background-color: #090A0B;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 16px;
            }
        """)
        self.container.setObjectName("SettingsContainer")

        c_layout = QVBoxLayout(self.container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(0)

        # Top Title Bar with Window Controls
        title_bar = QWidget(self.container)
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet("border-bottom: 1px solid rgba(255, 255, 255, 0.08);")
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(14, 0, 14, 0)

        # Minimal monochrome window controls.
        btn_close = QPushButton(title_bar)
        btn_close.setFixedSize(12, 12)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #25272A;
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #45484D;
            }
        """)
        btn_close.clicked.connect(self.close)
        tb_layout.addWidget(btn_close)

        btn_min = QPushButton(title_bar)
        btn_min.setFixedSize(12, 12)
        btn_min.setStyleSheet("""
            QPushButton {
                background-color: #25272A;
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 6px;
            }
        """)
        btn_min.clicked.connect(self.showMinimized)
        tb_layout.addWidget(btn_min)

        self.lbl_win_title = QLabel(t("settings_title"), title_bar)
        self.lbl_win_title.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: 600; font-family: 'Segoe UI', sans-serif;")
        tb_layout.addSpacing(12)
        tb_layout.addWidget(self.lbl_win_title)
        tb_layout.addStretch(1)

        c_layout.addWidget(title_bar)

        # Main Body: Left Sidebar + Right Pages Stack
        body = QWidget(self.container)
        b_layout = QHBoxLayout(body)
        b_layout.setContentsMargins(10, 10, 10, 10)
        b_layout.setSpacing(12)

        # ── Left Sidebar Navigation ──────────────────────────────────────
        self.sidebar = QListWidget(body)
        self.sidebar.setFixedWidth(160)
        self.sidebar.setIconSize(QSize(18, 18))
        self.sidebar.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sidebar.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.sidebar.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                color: rgba(255, 255, 255, 0.7);
                padding: 8px 10px;
                border-radius: 8px;
                font-size: 11px;
                font-weight: 500;
                font-family: 'Segoe UI', sans-serif;
            }
            QListWidget::item:selected {
                background: rgba(255, 255, 255, 0.12);
                color: #FFFFFF;
                font-weight: 600;
            }
            QListWidget::item:hover:!selected {
                background: rgba(255, 255, 255, 0.06);
                color: #FFFFFF;
            }
        """)
        self._populate_sidebar()
        self.sidebar.currentRowChanged.connect(self._on_sidebar_changed)
        b_layout.addWidget(self.sidebar)

        # Separator line
        v_sep = QFrame()
        v_sep.setFrameShape(QFrame.Shape.VLine)
        v_sep.setStyleSheet("color: rgba(255, 255, 255, 0.08);")
        b_layout.addWidget(v_sep)

        # ── Right Pages Stack ────────────────────────────────────────────
        self.stack = QStackedWidget(body)
        self._init_pages()
        b_layout.addWidget(self.stack, stretch=1)

        c_layout.addWidget(body, stretch=1)
        root.addWidget(self.container)
        self.sidebar.setCurrentRow(0)

    def _populate_sidebar(self) -> None:
        current_row = max(0, self.sidebar.currentRow())
        self.sidebar.clear()
        categories = [
            ("general", "set_cat_general"),
            ("controls", "set_cat_control_center"),
            ("gestures", "set_cat_gestures"),
            ("appearance", "set_cat_appearance"),
            ("system", "set_cat_system"),
            ("about", "set_cat_about")
        ]
        for icon_name, title_key in categories:
            self.sidebar.addItem(QListWidgetItem(self._category_icon(icon_name), t(title_key)))
        self.sidebar.setCurrentRow(min(current_row, len(categories) - 1))

    @staticmethod
    def _category_icon(icon_name: str) -> QIcon:
        pixmap = QPixmap(18, 18)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = QColor(190, 194, 200)
        painter.setPen(QPen(color, 1.35, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if icon_name == "general":
            painter.drawEllipse(QRectF(5.5, 5.5, 7, 7))
            for angle in range(0, 360, 45):
                rad = math.radians(angle)
                painter.drawLine(QPointF(9 + math.cos(rad) * 5, 9 + math.sin(rad) * 5),
                                 QPointF(9 + math.cos(rad) * 7, 9 + math.sin(rad) * 7))
        elif icon_name == "controls":
            for y, knob_x in ((4, 7), (9, 12), (14, 6)):
                painter.drawLine(QPointF(2, y), QPointF(16, y))
                painter.setBrush(QBrush(QColor(9, 10, 11)))
                painter.drawEllipse(QPointF(knob_x, y), 1.8, 1.8)
                painter.setBrush(Qt.BrushStyle.NoBrush)
        elif icon_name == "gestures":
            painter.drawRoundedRect(QRectF(5, 1.5, 8, 15), 4, 4)
            painter.drawLine(QPointF(9, 3.5), QPointF(9, 7))
            painter.drawLine(QPointF(2, 10), QPointF(4.3, 10))
        elif icon_name == "appearance":
            painter.drawEllipse(QRectF(2, 2, 14, 14))
            painter.drawLine(QPointF(9, 2), QPointF(9, 16))
        elif icon_name == "system":
            painter.drawRoundedRect(QRectF(2, 3, 14, 11), 2, 2)
            painter.drawLine(QPointF(6, 16), QPointF(12, 16))
            painter.drawLine(QPointF(9, 14), QPointF(9, 16))
        else:
            painter.drawEllipse(QRectF(2, 2, 14, 14))
            painter.drawLine(QPointF(9, 8), QPointF(9, 13))
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPointF(9, 5), 0.8, 0.8)

        painter.end()
        return QIcon(pixmap)

    def _on_sidebar_changed(self, row: int) -> None:
        self.stack.setCurrentIndex(row)

    def _init_pages(self) -> None:
        # Page 0: General & Language
        p_gen = QWidget()
        p_gen_l = QVBoxLayout(p_gen)
        p_gen_l.setContentsMargins(4, 4, 4, 4)
        p_gen_l.setSpacing(8)

        # Language Selector Button Group
        lang_container = QWidget()
        lang_l = QHBoxLayout(lang_container)
        lang_l.setContentsMargins(0, 0, 0, 0)
        lang_l.setSpacing(6)

        self.btn_tr = QPushButton("Türkçe", lang_container)
        self.btn_en = QPushButton("English", lang_container)
        self._style_lang_buttons()

        self.btn_tr.clicked.connect(lambda: self._set_app_language("tr"))
        self.btn_en.clicked.connect(lambda: self._set_app_language("en"))
        lang_l.addWidget(self.btn_tr)
        lang_l.addWidget(self.btn_en)

        card_lang = SettingRowCard("set_language", "set_language_desc", lang_container, p_gen)
        self._cards.append(card_lang)
        p_gen_l.addWidget(card_lang)

        # Launch at startup Toggle
        self.sw_startup = IOSToggleSwitch(self._settings.get("launch_at_startup", False), p_gen)
        self.sw_startup.state_changed.connect(lambda val: self._settings.set("launch_at_startup", val))
        card_startup = SettingRowCard("set_startup", "set_startup_desc", self.sw_startup, p_gen)
        self._cards.append(card_startup)
        p_gen_l.addWidget(card_startup)

        p_gen_l.addStretch(1)
        self.stack.addWidget(p_gen)

        # Page 1: Control Center Settings
        p_cc = QWidget()
        p_cc_l = QVBoxLayout(p_cc)
        p_cc_l.setContentsMargins(4, 4, 4, 4)
        p_cc_l.setSpacing(8)

        self.lbl_cc_info = QLabel(t("settings_cc_info"), p_cc)
        self.lbl_cc_info.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 11px;")
        self.lbl_cc_info.setWordWrap(True)
        p_cc_l.addWidget(self.lbl_cc_info)
        p_cc_l.addStretch(1)
        self.stack.addWidget(p_cc)

        # Page 2: Gestures / Scroll
        p_gest = QWidget()
        p_gest_l = QVBoxLayout(p_gest)
        p_gest_l.setContentsMargins(4, 4, 4, 4)
        p_gest_l.setSpacing(8)

        # Scroll Action Switcher
        scroll_container = QWidget()
        scroll_l = QHBoxLayout(scroll_container)
        scroll_l.setContentsMargins(0, 0, 0, 0)
        self.combo_scroll = QComboBox(scroll_container)
        self.combo_scroll.addItem(t("set_scroll_pages"), "switch_page")
        self.combo_scroll.addItem(t("set_scroll_volume"), "volume")
        self.combo_scroll.setCurrentIndex(0 if self._settings.get("scroll_action") == "switch_page" else 1)
        self.combo_scroll.setStyleSheet("""
            QComboBox {
                background: rgba(255, 255, 255, 0.08);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QComboBox QAbstractItemView {
                background: #181920;
                color: #FFFFFF;
                selection-background-color: #3B3D41;
            }
        """)
        self.combo_scroll.currentIndexChanged.connect(
            lambda idx: self._settings.set("scroll_action", self.combo_scroll.itemData(idx))
        )
        scroll_l.addWidget(self.combo_scroll)

        card_scroll = SettingRowCard("set_scroll_behavior", "set_scroll_behavior_desc", scroll_container, p_gest)
        self._cards.append(card_scroll)
        p_gest_l.addWidget(card_scroll)
        p_gest_l.addStretch(1)
        self.stack.addWidget(p_gest)

        # Page 3: Appearance & Effects
        p_app = QWidget()
        p_app_l = QVBoxLayout(p_app)
        p_app_l.setContentsMargins(4, 4, 4, 4)
        p_app_l.setSpacing(8)

        # Page Dots Toggle
        self.sw_dots = IOSToggleSwitch(self._settings.get("show_page_dots", True), p_app)
        self.sw_dots.state_changed.connect(lambda val: self._settings.set("show_page_dots", val))
        card_dots = SettingRowCard("set_page_dots", "set_page_dots_desc", self.sw_dots, p_app)
        self._cards.append(card_dots)
        p_app_l.addWidget(card_dots)

        # Acrylic Blur Toggle
        self.sw_acrylic = IOSToggleSwitch(self._settings.get("acrylic_blur", False), p_app)
        self.sw_acrylic.state_changed.connect(lambda val: self._settings.set("acrylic_blur", val))
        card_acrylic = SettingRowCard("set_acrylic_blur", "set_acrylic_blur_desc", self.sw_acrylic, p_app)
        self._cards.append(card_acrylic)
        p_app_l.addWidget(card_acrylic)

        # Ambient Glow Toggle
        self.sw_glow = IOSToggleSwitch(self._settings.get("ambient_glow", True), p_app)
        self.sw_glow.state_changed.connect(lambda val: self._settings.set("ambient_glow", val))
        card_glow = SettingRowCard("set_ambient_glow", "set_ambient_glow_desc", self.sw_glow, p_app)
        self._cards.append(card_glow)
        p_app_l.addWidget(card_glow)

        self.sw_animations = IOSToggleSwitch(self._settings.get("animations_enabled", True), p_app)
        self.sw_animations.state_changed.connect(lambda val: self._settings.set("animations_enabled", val))
        card_animations = SettingRowCard("set_animations", "set_animations_desc", self.sw_animations, p_app)
        self._cards.append(card_animations)
        p_app_l.addWidget(card_animations)

        p_app_l.addStretch(1)
        self.stack.addWidget(p_app)

        # Page 4: Notifications and indicator visibility
        p_system = QWidget()
        p_system_l = QVBoxLayout(p_system)
        p_system_l.setContentsMargins(4, 4, 4, 4)
        p_system_l.setSpacing(7)

        system_options = (
            ("show_notifications", "set_notifications", "set_notifications_desc"),
            ("show_battery_indicator", "set_indicator_battery", "set_indicator_battery_desc"),
            ("show_weather_indicator", "set_indicator_weather", "set_indicator_weather_desc"),
            ("show_task_indicator", "set_indicator_tasks", "set_indicator_tasks_desc"),
            ("show_system_telemetry", "set_indicator_system", "set_indicator_system_desc"),
        )
        for setting_key, title_key, desc_key in system_options:
            toggle = IOSToggleSwitch(self._settings.get(setting_key, True), p_system)
            toggle.state_changed.connect(
                lambda value, key=setting_key: self._settings.set(key, value)
            )
            card = SettingRowCard(title_key, desc_key, toggle, p_system)
            self._cards.append(card)
            p_system_l.addWidget(card)
        p_system_l.addStretch(1)
        self.stack.addWidget(p_system)

        # Page 5: About
        p_abt = QWidget()
        p_abt_l = QVBoxLayout(p_abt)
        p_abt_l.setContentsMargins(12, 12, 12, 12)
        p_abt_l.setSpacing(6)

        lbl_app_logo = QLabel("WinIsland", p_abt)
        lbl_app_logo.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: 700; font-family: 'Segoe UI Semibold', sans-serif;")
        p_abt_l.addWidget(lbl_app_logo)

        self.lbl_about_desc = QLabel(t("about_desc"), p_abt)
        self.lbl_about_desc.setStyleSheet("color: rgba(255, 255, 255, 0.65); font-size: 11px;")
        self.lbl_about_desc.setWordWrap(True)
        p_abt_l.addWidget(self.lbl_about_desc)

        self.lbl_about_build = QLabel(t("about_build"), p_abt)
        self.lbl_about_build.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 10px; font-family: 'Cascadia Code', monospace;")
        p_abt_l.addSpacing(8)
        p_abt_l.addWidget(self.lbl_about_build)

        p_abt_l.addStretch(1)
        self.stack.addWidget(p_abt)

    def _style_lang_buttons(self) -> None:
        curr = self._i18n.current_language
        active_style = """
            QPushButton {
                background: #E2E4E7;
                color: #111214;
                border: none;
                border-radius: 8px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
        """
        inactive_style = """
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 4px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
                color: #FFFFFF;
            }
        """
        self.btn_tr.setStyleSheet(active_style if curr == "tr" else inactive_style)
        self.btn_en.setStyleSheet(active_style if curr == "en" else inactive_style)

    def _set_app_language(self, lang: str) -> None:
        self._settings.set("language", lang)
        self._style_lang_buttons()

    def _on_language_changed(self, lang: str) -> None:
        self.lbl_win_title.setText(t("settings_title"))
        self.lbl_about_desc.setText(t("about_desc"))
        self.lbl_about_build.setText(t("about_build"))
        self.lbl_cc_info.setText(t("settings_cc_info"))
        self._populate_sidebar()
        self._style_lang_buttons()
        for card in self._cards:
            card.refresh_texts()
        # Refresh combo
        self.combo_scroll.setItemText(0, t("set_scroll_pages"))
        self.combo_scroll.setItemText(1, t("set_scroll_volume"))

    # Draggable Frameless Window
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
