"""
WinIsland - Smart Clipboard Watcher Module
Monitors Windows clipboard events natively using Qt signals (Zero CPU idle).
"""

from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QClipboard, QPixmap
from PyQt6.QtWidgets import QApplication


class ClipboardWatcher(QObject):
    """
    Monitors Windows clipboard transitions.
    Triggers temporary horizontal island alert with character count or image stats.
    """
    clipboard_event = pyqtSignal(str, str, object, str)  # (title, subtitle, pixmap or None, icon_type)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._clipboard: QClipboard = QApplication.clipboard()
        self._last_text: Optional[str] = None
        self._is_active: bool = True

        self._clipboard.dataChanged.connect(self._on_clipboard_changed)

    def enable(self) -> None:
        self._is_active = True

    def disable(self) -> None:
        self._is_active = False

    def _on_clipboard_changed(self) -> None:
        if not self._is_active:
            return

        try:
            mime_data = self._clipboard.mimeData()
            if mime_data is None:
                return

            # Case 1: Image copied
            if mime_data.hasImage():
                image = self._clipboard.image()
                if not image.isNull():
                    pixmap = QPixmap.fromImage(image)
                    dims = f"{pixmap.width()}×{pixmap.height()} px"
                    self.clipboard_event.emit(
                        "Görsel Kopyalandı",
                        dims,
                        pixmap,
                        "image"
                    )
                    return

            # Case 2: Text copied
            if mime_data.hasText():
                text = self._clipboard.text().strip()
                if not text or text == self._last_text:
                    return

                self._last_text = text
                char_count = len(text)
                
                clean_preview = text.replace("\r", " ").replace("\n", " ")
                if len(clean_preview) > 28:
                    clean_preview = clean_preview[:25] + "..."

                title = f"Kopyalandı ({char_count} kr)"
                subtitle = f'"{clean_preview}"'
                self.clipboard_event.emit(title, subtitle, None, "clipboard")

        except Exception:
            pass
