"""
WinIsland - AI Quick Input Client
Uses google-genai (Gemini API) to answer questions directly in the Dynamic Island.
Features auto-model fallback: gemini-2.5-flash -> gemini-2.5-flash-lite -> gemini-1.5-flash.
"""

import json
import os
from typing import Optional, List
from PyQt6.QtCore import QObject, QThread, pyqtSignal

try:
    import google.genai as genai
    _GENAI_OK = True
except ImportError:
    _GENAI_OK = False

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_CONFIG = os.path.join(PROJECT_DIR, "config.json")
LOCAL_ENV = os.path.join(PROJECT_DIR, ".env")
APPDATA_ROOT = os.environ.get("APPDATA", os.path.expanduser("~"))
APPDATA_CONFIG = os.path.join(APPDATA_ROOT, "WinIsland", "config.json")
LEGACY_APPDATA_CONFIG = os.path.join(APPDATA_ROOT, "RhemeIsland", "config.json")

CANDIDATE_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-1.5-flash",
    "gemini-3.8-flash"
]


def _load_api_key() -> Optional[str]:
    """Load Gemini API key from local config, .env, appdata, or env vars."""
    for path in (LOCAL_CONFIG, APPDATA_CONFIG, LEGACY_APPDATA_CONFIG):
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    key = data.get("gemini_api_key") or data.get("api_key")
                    if key and key.strip() and not key.startswith("BURAYA"):
                        return key.strip()
        except Exception:
            pass

    try:
        if os.path.exists(LOCAL_ENV):
            with open(LOCAL_ENV, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY=") or line.startswith("GOOGLE_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val and not val.startswith("BURAYA"):
                            return val
    except Exception:
        pass

    env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    return None


def save_api_key(key: str) -> None:
    try:
        data = {}
        if os.path.exists(LOCAL_CONFIG):
            with open(LOCAL_CONFIG, "r", encoding="utf-8") as f:
                data = json.load(f)
        data["gemini_api_key"] = key.strip()
        with open(LOCAL_CONFIG, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


class AIWorker(QThread):
    """Background thread for Gemini API call with auto-fallback."""
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, prompt: str, api_key: str, parent=None):
        super().__init__(parent)
        self._prompt = prompt
        self._api_key = api_key

    def run(self) -> None:
        if not _GENAI_OK:
            self.error_occurred.emit("google-genai kütüphanesi yüklü değil.")
            return

        last_error = ""
        try:
            client = genai.Client(api_key=self._api_key)
            for model_name in CANDIDATE_MODELS:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=self._prompt
                    )
                    text = (response.text or "").strip()
                    if text:
                        self.response_ready.emit(text)
                        return
                except Exception as ex:
                    last_error = str(ex)
                    continue

            self.error_occurred.emit(f"AI Yanıtı Alınamadı: {last_error[:80]}")
        except Exception as e:
            self.error_occurred.emit(f"Bağlantı Hatası: {e}")


class AIClient(QObject):
    """Public interface for AI quick input."""
    response_complete = pyqtSignal(str)
    response_error = pyqtSignal(str)
    thinking = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[AIWorker] = None

    def is_available(self) -> bool:
        return _GENAI_OK and bool(_load_api_key())

    def get_api_key(self) -> Optional[str]:
        return _load_api_key()

    def ask(self, prompt: str) -> None:
        api_key = _load_api_key()
        if not api_key:
            self.response_error.emit("API anahtarı bulunamadı! config.json dosyasına gemini_api_key ekleyin.")
            return

        if self._worker and self._worker.isRunning():
            self._worker.terminate()

        self.thinking.emit()
        self._worker = AIWorker(prompt, api_key, self)
        self._worker.response_ready.connect(self.response_complete)
        self._worker.error_occurred.connect(self.response_error)
        self._worker.start()
