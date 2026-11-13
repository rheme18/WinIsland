"""
WinIsland - To-Do & Reminder Storage Manager
Local JSON persistence for fast, lightweight iOS Reminders-style task management.
"""

import json
import os
import uuid
import time
import sys
from typing import List, Dict, Any, Optional
from PyQt6.QtCore import QObject, pyqtSignal


if getattr(sys, "frozen", False):
    DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "WinIsland")
else:
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
TODOS_FILE = os.path.join(DATA_DIR, "todos.json")


class TodoItem:
    def __init__(self, id_str: str, text: str, completed: bool = False, created_at: float = None):
        self.id = id_str
        self.text = text
        self.completed = completed
        self.created_at = created_at or time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "completed": self.completed,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TodoItem":
        return cls(
            id_str=d.get("id", str(uuid.uuid4())[:8]),
            text=d.get("text", ""),
            completed=d.get("completed", False),
            created_at=d.get("created_at", time.time())
        )


class TodoManager(QObject):
    """Singleton task and reminder persistence manager."""
    todos_changed = pyqtSignal()

    _instance = None

    def __init__(self):
        super().__init__()
        self._items: List[TodoItem] = []
        self._ensure_storage()
        self.load()

    @classmethod
    def get_instance(cls) -> "TodoManager":
        if cls._instance is None:
            cls._instance = TodoManager()
        return cls._instance

    def _ensure_storage(self) -> None:
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR, exist_ok=True)

    def load(self) -> None:
        if os.path.exists(TODOS_FILE):
            try:
                with open(TODOS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._items = [TodoItem.from_dict(d) for d in data]
            except Exception as e:
                print(f"[TodoManager] Load error: {e}")
                self._items = []
        else:
            # Default welcome tasks
            self._items = [
                TodoItem(str(uuid.uuid4())[:8], "WinIsland'i keşfet", completed=True),
                TodoItem(str(uuid.uuid4())[:8], "Su iç ve kısa bir mola ver", completed=False),
                TodoItem(str(uuid.uuid4())[:8], "Bugünkü yapılacakları tamamla", completed=False)
            ]
            self.save()

    def save(self) -> None:
        try:
            with open(TODOS_FILE, "w", encoding="utf-8") as f:
                json.dump([item.to_dict() for item in self._items], f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[TodoManager] Save error: {e}")

    def get_all(self) -> List[TodoItem]:
        return list(self._items)

    def add_todo(self, text: str) -> Optional[TodoItem]:
        clean_text = text.strip()
        if not clean_text:
            return None
        item = TodoItem(
            id_str=str(uuid.uuid4())[:8],
            text=clean_text,
            completed=False
        )
        self._items.insert(0, item)
        self.save()
        self.todos_changed.emit()
        return item

    def toggle_todo(self, item_id: str) -> bool:
        for item in self._items:
            if item.id == item_id:
                item.completed = not item.completed
                self.save()
                self.todos_changed.emit()
                return item.completed
        return False

    def delete_todo(self, item_id: str) -> bool:
        initial_len = len(self._items)
        self._items = [it for it in self._items if it.id != item_id]
        if len(self._items) != initial_len:
            self.save()
            self.todos_changed.emit()
            return True
        return False

    def get_counts(self) -> (int, int):
        completed = sum(1 for it in self._items if it.completed)
        return completed, len(self._items)
