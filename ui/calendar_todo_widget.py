"""
WinIsland - Apple iOS / macOS Style Calendar & To-Do List Widget
Clean, zero-emoji, elegant vector checkmarks, responsive scroll layout.
"""

import calendar
from datetime import datetime
from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal, QDate
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPainterPath, QPalette
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QLineEdit,
    QScrollArea, QFrame, QSizePolicy, QGridLayout
)

from core.config import Palette, Typography
from modules.i18n import t, I18nManager
from modules.todo_manager import TodoManager, TodoItem


class IOSCheckmarkButton(QPushButton):
    """Circular Apple Reminders checkmark button with smooth toggle feedback."""
    toggled_state = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked: bool = checked
        # Commit on click/release rather than mouse-down. The task manager
        # rebuilds the list in response to this signal, so emitting during a
        # press can replace the row while Qt is still dispatching that press.
        self.clicked.connect(self._on_clicked)

    def is_checked(self) -> bool:
        return self._checked

    def set_checked(self, val: bool) -> None:
        if self._checked != val:
            self._checked = val
            self.update()

    def _on_clicked(self, _checked: bool = False) -> None:
        self._checked = not self._checked
        self.update()
        self.toggled_state.emit(self._checked)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        cx = rect.width() / 2.0
        cy = rect.height() / 2.0
        radius = 7.5

        if self._checked:
            painter.setBrush(QBrush(QColor(226, 228, 231)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))

            painter.setPen(QPen(QColor(17, 18, 20), 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            path = QPainterPath()
            path.moveTo(cx - 3.5, cy - 0.2)
            path.lineTo(cx - 1.0, cy + 2.5)
            path.lineTo(cx + 4.0, cy - 2.5)
            painter.drawPath(path)
        else:
            painter.setBrush(QBrush(QColor(255, 255, 255, 10)))
            painter.setPen(QPen(QColor(255, 255, 255, 60), 1.4))
            painter.drawEllipse(int(cx - radius), int(cy - radius), int(radius * 2), int(radius * 2))
        painter.end()


class TodoRowWidget(QWidget):
    """Single row representing a task item with interactive check & delete."""
    item_toggled = pyqtSignal(str)
    item_deleted = pyqtSignal(str)

    def __init__(self, item: TodoItem, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.item_id = item.id
        self._item = item
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("""
            TodoRowWidget {
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 7px;
            }
            TodoRowWidget:hover {
                background: rgba(255, 255, 255, 0.09);
                border: 1px solid rgba(255, 255, 255, 0.14);
            }
        """)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)

        self.btn_check = IOSCheckmarkButton(self._item.completed, self)
        self.btn_check.toggled_state.connect(self._on_toggled)
        layout.addWidget(self.btn_check)

        self.lbl_text = QLabel(self._item.text, self)
        self.lbl_text.setFont(QFont("Segoe UI Semibold", 10, QFont.Weight.DemiBold))
        self.lbl_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._apply_text_style()
        layout.addWidget(self.lbl_text, stretch=1)

        self.btn_del = QPushButton("×", self)
        self.btn_del.setFixedSize(16, 16)
        self.btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_del.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: rgba(255, 255, 255, 0.40);
                font-size: 14px;
                font-weight: 700;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: rgba(239, 68, 68, 0.25);
                color: #EF4444;
            }
        """)
        self.btn_del.clicked.connect(lambda: self.item_deleted.emit(self.item_id))
        layout.addWidget(self.btn_del)

    def _on_toggled(self, checked: bool) -> None:
        # TodoManager owns the canonical state and emits todos_changed, which
        # rebuilds this row. Mutating locally here caused a double toggle.
        self.item_toggled.emit(self.item_id)

    def _apply_text_style(self) -> None:
        if self._item.completed:
            self.lbl_text.setStyleSheet("color: rgba(255, 255, 255, 0.35); text-decoration: line-through; font-weight: 600; font-size: 10.5px; font-family: 'Segoe UI Semibold', sans-serif; background: transparent; border: none;")
        else:
            self.lbl_text.setStyleSheet("color: #FFFFFF; text-decoration: none; font-weight: 600; font-size: 10.5px; font-family: 'Segoe UI Semibold', sans-serif; background: transparent; border: none;")


class MiniCalendarWidget(QWidget):
    """Sleek iOS-inspired mini monthly calendar widget."""
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        now = datetime.now()
        self.year = now.year
        self.month = now.month
        self.today_day = now.day
        self.today_month = now.month
        self.today_year = now.year
        self.setFixedWidth(205)
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(4, 2, 6, 2)
        self.main_layout.setSpacing(4)

        # Header: < Month Year >
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(4)

        self.btn_prev = QPushButton("‹", self)
        self.btn_prev.setFixedSize(20, 20)
        self.btn_prev.setStyleSheet(self._nav_btn_style())
        self.btn_prev.clicked.connect(self._prev_month)
        header.addWidget(self.btn_prev)

        self.lbl_title = QLabel(self)
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 800; font-family: 'Segoe UI Semibold', -apple-system, sans-serif;")
        header.addWidget(self.lbl_title, stretch=1)

        self.btn_next = QPushButton("›", self)
        self.btn_next.setFixedSize(20, 20)
        self.btn_next.setStyleSheet(self._nav_btn_style())
        self.btn_next.clicked.connect(self._next_month)
        header.addWidget(self.btn_next)

        self.main_layout.addLayout(header)

        # Calendar Grid Container
        self.grid_container = QWidget(self)
        self.main_layout.addWidget(self.grid_container, stretch=1)
        self.update_calendar()

    def _nav_btn_style(self) -> str:
        return """
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: rgba(255, 255, 255, 0.90);
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.22);
                color: #FFFFFF;
            }
        """

    def _prev_month(self) -> None:
        if self.month == 1:
            self.month = 12
            self.year -= 1
        else:
            self.month -= 1
        self.update_calendar()

    def _next_month(self) -> None:
        if self.month == 12:
            self.month = 1
            self.year += 1
        else:
            self.month += 1
        self.update_calendar()

    def update_calendar(self) -> None:
        m_key = f"month_{self.month}"
        month_name = t(m_key)
        self.lbl_title.setText(f"{month_name} {self.year}")

        if self.grid_container.layout():
            QWidget().setLayout(self.grid_container.layout())

        grid = QGridLayout(self.grid_container)
        grid.setContentsMargins(0, 2, 0, 0)
        grid.setSpacing(2)

        day_keys = ["day_mon", "day_tue", "day_wed", "day_thu", "day_fri", "day_sat", "day_sun"]
        for col, dk in enumerate(day_keys):
            d_lbl = QLabel(t(dk)[:2].upper(), self)
            d_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            d_lbl.setStyleSheet("color: rgba(255, 255, 255, 0.60); font-size: 9px; font-weight: 700; font-family: 'Segoe UI Semibold', sans-serif;")
            grid.addWidget(d_lbl, 0, col)

        cal = calendar.monthcalendar(self.year, self.month)
        for r_idx, week in enumerate(cal):
            for c_idx, day_num in enumerate(week):
                if day_num == 0:
                    continue
                day_btn = QLabel(str(day_num), self)
                day_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
                day_btn.setFixedSize(22, 18)

                is_today = (
                    day_num == self.today_day and
                    self.month == self.today_month and
                    self.year == self.today_year
                )

                if is_today:
                    day_btn.setStyleSheet("""
                        background: #E2E4E7;
                        color: #111214;
                        font-weight: 800;
                        font-size: 10px;
                        border-radius: 9px;
                        font-family: 'Segoe UI Semibold', sans-serif;
                    """)
                else:
                    day_btn.setStyleSheet("""
                        color: #F4F4F5;
                        font-size: 10px;
                        font-weight: 600;
                        font-family: 'Segoe UI Semibold', sans-serif;
                    """)
                grid.addWidget(day_btn, r_idx + 1, c_idx)


class CalendarTodoWidget(QWidget):
    """WinIsland Combined Apple-Style Calendar & Reminders view."""
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._todo_mgr = TodoManager.get_instance()
        self._todo_mgr.todos_changed.connect(self._refresh_todos)
        I18nManager.get_instance().language_changed.connect(self._on_language_changed)
        self._setup_ui()

    def _setup_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(6, 4, 6, 6)
        outer.setSpacing(14)

        # ── Left: Mini Calendar ──────────────────────────────────────────
        self.cal_widget = MiniCalendarWidget(self)
        outer.addWidget(self.cal_widget)

        # Subtle vertical separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: rgba(255, 255, 255, 0.1);")
        outer.addWidget(sep)

        # ── Right: Task & Reminders Panel ────────────────────────────────
        right_panel = QWidget(self)
        r_layout = QVBoxLayout(right_panel)
        r_layout.setContentsMargins(0, 0, 0, 0)
        r_layout.setSpacing(5)

        # Header & Status counter
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)

        self.lbl_heading = QLabel(t("todo_title"), right_panel)
        self.lbl_heading.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: 800; font-family: 'Segoe UI Semibold', -apple-system, sans-serif;")
        top_bar.addWidget(self.lbl_heading)

        self.lbl_counter = QLabel("", right_panel)
        self.lbl_counter.setStyleSheet("color: #D0D3D7; font-size: 10px; font-weight: 700; font-family: 'Segoe UI Semibold', sans-serif;")
        top_bar.addWidget(self.lbl_counter, alignment=Qt.AlignmentFlag.AlignRight)
        r_layout.addLayout(top_bar)

        # Input field for fast addition
        self.txt_new_task = QLineEdit(right_panel)
        self.txt_new_task.setPlaceholderText(t("todo_placeholder"))
        self.txt_new_task.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 9px;
                padding: 5px 9px;
                color: #FFFFFF;
                font-size: 10px;
                font-weight: 500;
                font-family: 'Segoe UI Semibold', -apple-system, sans-serif;
            }
            QLineEdit:focus {
                border: 1px solid rgba(255, 255, 255, 0.48);
                background: rgba(255, 255, 255, 0.14);
            }
        """)
        self.txt_new_task.returnPressed.connect(self._add_task)
        r_layout.addWidget(self.txt_new_task)

        # Scrollable Task List (Zero ugly horizontal scrollbar, 100% transparent background)
        self.scroll = QScrollArea(right_panel)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.scroll.viewport().setAutoFillBackground(False)
        p = self.scroll.palette()
        p.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.transparent)
        p.setColor(QPalette.ColorRole.Window, Qt.GlobalColor.transparent)
        self.scroll.setPalette(p)
        self.scroll.viewport().setPalette(p)
        self.scroll.setStyleSheet("""
            QScrollArea, QScrollArea * {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 4px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.25);
                border-radius: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.list_container = QWidget()
        self.list_container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.list_container.setAutoFillBackground(False)
        self.list_container.setStyleSheet("background: transparent !important; border: none;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 4, 0)
        self.list_layout.setSpacing(4)
        self.list_layout.addStretch(1)

        self.scroll.setWidget(self.list_container)
        r_layout.addWidget(self.scroll, stretch=1)

        outer.addWidget(right_panel, stretch=1)
        self._refresh_todos()

    def _add_task(self) -> None:
        text = self.txt_new_task.text().strip()
        if text:
            self._todo_mgr.add_todo(text)
            self.txt_new_task.clear()

    def _refresh_todos(self) -> None:
        while self.list_layout.count() > 1:
            child = self.list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        items = self._todo_mgr.get_all()
        for it in items:
            row = TodoRowWidget(it, self.list_container)
            row.item_toggled.connect(self._on_item_toggled)
            row.item_deleted.connect(self._on_item_deleted)
            self.list_layout.insertWidget(self.list_layout.count() - 1, row)

        comp, total = self._todo_mgr.get_counts()
        self.lbl_counter.setText(t("todo_count", completed=comp, total=total))

    def _on_item_toggled(self, item_id: str) -> None:
        self._todo_mgr.toggle_todo(item_id)

    def _on_item_deleted(self, item_id: str) -> None:
        self._todo_mgr.delete_todo(item_id)

    def _on_language_changed(self, lang: str) -> None:
        self.lbl_heading.setText(t("todo_title"))
        self.txt_new_task.setPlaceholderText(t("todo_placeholder"))
        self.cal_widget.update_calendar()
        comp, total = self._todo_mgr.get_counts()
        self.lbl_counter.setText(t("todo_count", completed=comp, total=total))
