"""
WinIsland - Python Virtual Environment Detector
Scans running processes to find active Python venvs (VS Code, terminal, etc).
Also checks the VIRTUAL_ENV environment variable of child processes.
"""

import os
import re
from typing import Optional
from PyQt6.QtCore import QThread, pyqtSignal

try:
    import psutil
    _PSUTIL_OK = True
except ImportError:
    _PSUTIL_OK = False

POLL_INTERVAL_MS = 5000


def _extract_venv_info(exe_path: str) -> Optional[tuple[str, str]]:
    """
    Given a python.exe path, check if it is inside a venv (has 'Scripts' parent).
    Returns (venv_name, python_version) or None.
    """
    try:
        norm = exe_path.replace("\\", "/")
        # Windows venv layout: <venv_root>/Scripts/python.exe
        match = re.search(r"/([^/]+)/Scripts/python", norm, re.IGNORECASE)
        if not match:
            return None
        venv_name = match.group(1)
        # Try to get Python version
        import subprocess
        result = subprocess.run(
            [exe_path, "--version"],
            capture_output=True, text=True, timeout=3
        )
        version_str = (result.stdout + result.stderr).strip()
        # e.g. "Python 3.11.4"
        ver_match = re.search(r"Python (\d+\.\d+)", version_str)
        py_ver = ver_match.group(1) if ver_match else "3.x"
        return venv_name, py_ver
    except Exception:
        return None


class VenvDetector(QThread):
    """
    Scans for active Python venv processes every 5 s.
    Signals:
        venv_activated(name: str, py_version: str)
        venv_deactivated()
    """
    venv_activated = pyqtSignal(str, str)
    venv_deactivated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._active_venv: Optional[str] = None  # current venv name

    def stop(self) -> None:
        self._running = False
        self.wait(2000)

    def run(self) -> None:
        if not _PSUTIL_OK:
            return

        while self._running:
            self.msleep(POLL_INTERVAL_MS)
            try:
                detected: Optional[tuple[str, str]] = None

                for proc in psutil.process_iter(["name", "exe", "environ"]):
                    try:
                        name = (proc.info.get("name") or "").lower()
                        if "python" not in name:
                            continue
                        exe = proc.info.get("exe") or ""
                        if not exe:
                            continue

                        # Check exe path for venv pattern
                        info = _extract_venv_info(exe)
                        if info:
                            detected = info
                            break

                        # Also check VIRTUAL_ENV env var if accessible
                        try:
                            env = proc.environ()
                            venv_path = env.get("VIRTUAL_ENV", "")
                            if venv_path:
                                venv_name = os.path.basename(venv_path)
                                info2 = _extract_venv_info(exe)
                                py_ver = info2[1] if info2 else "3.x"
                                detected = (venv_name, py_ver)
                                break
                        except (psutil.AccessDenied, psutil.ZombieProcess):
                            pass

                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                current_name = detected[0] if detected else None

                if current_name and current_name != self._active_venv:
                    self._active_venv = current_name
                    self.venv_activated.emit(detected[0], detected[1])  # type: ignore
                elif not current_name and self._active_venv is not None:
                    self._active_venv = None
                    self.venv_deactivated.emit()

            except Exception:
                pass
