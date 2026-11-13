"""
WinIsland - Process Watcher IPC Server (Named Pipes / Local Socket)
Receives notifications from external processes, terminal scripts, or build tools.
"""

import json
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from core.config import IPC_PIPE_NAME, LEGACY_IPC_PIPE_NAME, Timing
from modules.i18n import t


class IPCServer(QObject):
    """
    QLocalServer that listens for external process notification events.
    """
    notification_received = pyqtSignal(str, str, str, int)  # (title, message, type, duration_ms)

    def __init__(self, parent: Optional[QObject] = None, pipe_name: str = IPC_PIPE_NAME):
        super().__init__(parent)
        self._servers = []
        names = dict.fromkeys((pipe_name, LEGACY_IPC_PIPE_NAME))
        for name in names:
            server = QLocalServer(self)
            server.newConnection.connect(lambda server=server: self._on_new_connection(server))
            self._servers.append((name, server))
        self._start_server()

    def _start_server(self) -> None:
        # Clear stale socket/pipe from prior crash if any
        for name, server in self._servers:
            QLocalServer.removeServer(name)
            server.listen(name)

    def stop(self) -> None:
        for name, server in self._servers:
            if server.isListening():
                server.close()
                QLocalServer.removeServer(name)

    def _on_new_connection(self, server: QLocalServer) -> None:
        client: Optional[QLocalSocket] = server.nextPendingConnection()
        if not client:
            return

        def read_data():
            try:
                data = client.readAll().data().decode("utf-8").strip()
                if not data:
                    return

                # Attempt to parse as JSON payload
                try:
                    payload = json.loads(data)
                    title = payload.get("title", t("terminal_notification"))
                    message = payload.get("message", "")
                    n_type = payload.get("type", "info")
                    duration = int(payload.get("duration", Timing.BANNER_TIMEOUT_MS))
                except json.JSONDecodeError:
                    # Treat raw text payload gracefully
                    parts = data.split(":", 1)
                    if len(parts) == 2:
                        title = parts[0].strip()
                        message = parts[1].strip()
                    else:
                        title = t("process_notification")
                        message = data
                    n_type = "info"
                    duration = Timing.BANNER_TIMEOUT_MS

                self.notification_received.emit(title, message, n_type, duration)
            except Exception:
                pass
            finally:
                client.disconnectFromServer()

        client.readyRead.connect(read_data)
