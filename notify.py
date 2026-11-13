"""
WinIsland - IPC Notification Client (CLI Tool)
Send notifications to WinIsland from terminal, bash, PowerShell or git hooks.

Usage:
    python notify.py "Build Başarılı" --message "Webpack bundle 1.4s" --type success
    python notify.py "Git Push" -m "origin main push finished" -t info
    python notify.py "Kritik Hata" -m "Segmentasyon hatası" -t error --duration 5000
"""

import sys
import json
import argparse
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtNetwork import QLocalSocket

from core.config import IPC_PIPE_NAME, LEGACY_IPC_PIPE_NAME


def send_notification(title: str, message: str, n_type: str = "info", duration: int = 3800) -> bool:
    app = QCoreApplication(sys.argv)
    socket = None
    for pipe_name in dict.fromkeys((IPC_PIPE_NAME, LEGACY_IPC_PIPE_NAME)):
        candidate = QLocalSocket()
        candidate.connectToServer(pipe_name)
        if candidate.waitForConnected(1000):
            socket = candidate
            break

    if socket is None:
        print(f"[WinIsland CLI] Uyarı: Ada uygulaması çalışmıyor veya pipe ({IPC_PIPE_NAME}) bulunamadı.")
        return False

    payload = json.dumps({
        "title": title,
        "message": message,
        "type": n_type,
        "duration": duration
    })

    socket.write(payload.encode("utf-8"))
    socket.flush()
    socket.waitForBytesWritten(1000)
    socket.disconnectFromServer()
    print(f"[WinIsland CLI] Bildirim gönderildi -> {title}: {message}")
    return True


def main():
    parser = argparse.ArgumentParser(description="WinIsland Terminal IPC Bildirim Aracı")
    parser.add_argument("title", type=str, help="Bildirim başlığı")
    parser.add_argument("-m", "--message", type=str, default="", help="Bildirim alt metni / detay")
    parser.add_argument("-t", "--type", type=str, default="info", choices=["info", "success", "warning", "error"], help="Bildirim türü")
    parser.add_argument("-d", "--duration", type=int, default=3800, help="Görünüm süresi (ms)")

    args = parser.parse_args()
    send_notification(args.title, args.message, args.type, args.duration)


if __name__ == "__main__":
    main()
