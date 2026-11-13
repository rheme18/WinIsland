"""
WinIsland - Native Dynamic Island Application for Windows
Main application entry point, lifecycle management and subsystem wiring.
Features:
- Windows Native Acrylic/Blur-Behind Glass
- Media controls, Volume, Fast Telemetry
- Bluetooth, Screen recording, WPM & Caps Lock, Python venv
- AI Quick Ask with In-Island Answering
- Pocket Mode (drag-in & drag-out file storage)
- Smart Notification Badge & Pixel the Companion
"""

import sys
import ctypes
import os
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

from core.window import DynamicIslandWindow, IslandState
from modules.i18n import I18nManager, t
from modules.media import MediaWorker
from modules.system_stats import SystemStatsWorker
from modules.clipboard import ClipboardWatcher
from modules.ipc_server import IPCServer
from modules.volume import VolumeManager
from modules.bluetooth_monitor import BluetoothMonitor
from modules.screen_recording import ScreenRecordingMonitor
from modules.wpm_tracker import WPMTracker
from modules.venv_detector import VenvDetector
from modules.pet import PetManager
from modules.ai_client import AIClient
from modules.weather import WeatherWorker
from modules.hardware_monitor import HardwareMonitor
from modules.brightness import BrightnessManager


def create_tray_icon() -> QIcon:
    """Generate a clean procedural tray icon."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(18, 18, 22))
    painter.setPen(QColor(255, 255, 255, 40))
    painter.drawRoundedRect(2, 6, 28, 20, 10, 10)
    painter.setBrush(QColor(235, 237, 240))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(13, 13, 6, 6)
    painter.end()
    return QIcon(pixmap)


def main():
    # Source launches from PowerShell inherit its console by default. Detach
    # the GUI process so closing that shell cannot send it a console-close
    # event (which looks like WinIsland randomly exiting).
    if os.name == "nt":
        try:
            ctypes.windll.kernel32.FreeConsole()
        except (AttributeError, OSError):
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("WinIsland")
    app.setApplicationDisplayName("WinIsland")
    app.setQuitOnLastWindowClosed(False)

    # Apply modern system font globally (subtle, clean — Segoe UI)
    _app_font = QFont("Segoe UI Semibold", 10, QFont.Weight.DemiBold)
    _app_font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(_app_font)

    # ── 1. Primary Dynamic Island Window ─────────────────────────────────
    window = DynamicIslandWindow()
    window.show()

    # ── 2. Windows Media Transport Controls (GSMTC) ──────────────────────
    media_worker = MediaWorker()
    media_worker.media_updated.connect(window.on_media_updated)
    media_worker.track_changed.connect(window.on_track_changed)
    media_worker.media_idle.connect(window.on_media_idle)

    # Wire GUI media controls back to worker
    window.view_expanded.play_pause_clicked.connect(media_worker.request_toggle_play)
    window.view_expanded.next_clicked.connect(media_worker.request_next)
    window.view_expanded.prev_clicked.connect(media_worker.request_previous)
    window.view_expanded.seek_requested.connect(media_worker.request_seek)
    media_worker.start()

    # ── 3. Master Volume Manager ─────────────────────────────────────────
    volume_manager = VolumeManager()
    volume_manager.volume_changed.connect(window.on_volume_changed)
    window.view_expanded.volume_changed.connect(volume_manager.set_volume)
    window.view_expanded.mute_toggled.connect(volume_manager.toggle_mute)
    window.on_volume_changed(volume_manager.get_volume(), volume_manager.is_muted())
    brightness_manager = BrightnessManager.get_instance()
    brightness_manager.brightness_changed.connect(window.on_brightness_changed)

    # ── 4. System telemetry worker (battery + CPU/RAM + privacy) ─────────
    stats_worker = SystemStatsWorker()
    stats_worker.stats_updated.connect(window.on_telemetry_updated)
    stats_worker.critical_state_changed.connect(window.on_critical_state_changed)
    stats_worker.battery_event.connect(window.on_battery_event)
    stats_worker.privacy_changed.connect(window.on_privacy_changed)
    stats_worker.start()

    # ── 5. Smart Clipboard Watcher (Silent mode — disabled popups per user request) ──
    clipboard_watcher = ClipboardWatcher()
    clipboard_watcher.disable()

    # ── 6. IPC Server (Named Pipes) ──────────────────────────────────────
    ipc_server = IPCServer()
    ipc_server.notification_received.connect(window.on_ipc_notification)

    # ── 7. Bluetooth Audio Device Monitor ────────────────────────────────
    bt_monitor = BluetoothMonitor()
    bt_monitor.audio_device_changed.connect(window.on_bt_audio_changed)
    bt_monitor.start()

    # ── 8. Screen Recording Detector (OBS, Bandicam, etc.) ───────────────
    rec_monitor = ScreenRecordingMonitor()
    rec_monitor.recording_started.connect(window.on_recording_started)
    rec_monitor.recording_stopped.connect(window.on_recording_stopped)
    rec_monitor.start()

    # ── 9. WPM Tracker & Caps Lock Monitor ───────────────────────────────
    wpm_tracker = WPMTracker()
    wpm_tracker.caps_lock_changed.connect(window.on_caps_lock_changed)
    wpm_tracker.start()

    # ── 10. Python Venv Detector ─────────────────────────────────────────
    venv_detector = VenvDetector()
    venv_detector.venv_activated.connect(window.on_venv_activated)
    venv_detector.venv_deactivated.connect(window.on_venv_deactivated)
    venv_detector.start()

    # ── 11. AI Quick Question Client (Gemini 2.5 Flash) ──────────────────
    ai_client = AIClient()

    def on_ai_ask(query: str):
        ai_client.ask(query)

    def on_ai_complete(response: str):
        # 1. Display directly in expanded island
        window.view_expanded.display_ai_response(response)
        # 2. Copy to clipboard
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(response)
        # 3. Pixel celebrates
        window.view_expanded.pet_lounge.pet_avatar.trigger_happy_flip()

    def on_ai_error(error_msg: str):
        window.view_expanded.lbl_ai_response.setText(f"{error_msg}")
        window.view_expanded.lbl_ai_response.setVisible(True)

    window.view_expanded.ai_ask_requested.connect(on_ai_ask)
    ai_client.response_complete.connect(on_ai_complete)
    ai_client.response_error.connect(on_ai_error)

    # ── 12. Pixel the Tamagotchi Desktop Companion ───────────────────────
    pet_manager = PetManager()
    stats_worker.stats_updated.connect(pet_manager.on_telemetry_updated)
    media_worker.media_updated.connect(pet_manager.on_media_updated)
    wpm_tracker.activity_detected.connect(pet_manager.on_key_pressed)
    wpm_tracker.wpm_updated.connect(pet_manager.on_wpm_updated)

    # Pocket Mode (file dropped onto island -> stored in pouch + awards XP)
    window.file_pocket_updated.connect(pet_manager.on_file_dropped)

    # Pet state & Smart Notification Badge
    pet_manager.state_changed.connect(window.on_pet_state_changed)
    pet_manager.reminder_triggered.connect(window.on_pet_reminder)

    # Interactive Water & Break Buttons
    window.view_expanded.pet_lounge.water_clicked.connect(lambda: pet_manager.on_reminder_acknowledged("water"))
    window.view_expanded.pet_lounge.break_clicked.connect(lambda: pet_manager.on_reminder_acknowledged("break"))

    # Initial state sync
    window.on_pet_state_changed(pet_manager.current_state, pet_manager.current_evolution)

    # ── 13. Weather Service ───────────────────────────────────────────────
    weather_worker = WeatherWorker()
    weather_worker.weather_updated.connect(window.on_weather_updated)
    weather_worker.start()

    # ── 14. Hardware / USB Monitor ────────────────────────────────────────
    hardware_monitor = HardwareMonitor()
    hardware_monitor.device_event.connect(window.on_hardware_device_event)
    hardware_monitor.start()

    # ── 15. System Tray Integration ──────────────────────────────────────
    tray_icon = QSystemTrayIcon(create_tray_icon(), app)
    tray_menu = QMenu()

    action_expand = QAction(t("tray_expand"), tray_menu)
    action_expand.triggered.connect(lambda: window.transition_to(IslandState.EXPANDED))
    tray_menu.addAction(action_expand)

    action_compact = QAction(t("tray_compact"), tray_menu)
    action_compact.triggered.connect(lambda: window.transition_to(IslandState.COMPACT))
    tray_menu.addAction(action_compact)

    tray_menu.addSeparator()

    action_clip_toggle = QAction(t("tray_clip_on"), tray_menu, checkable=True)
    action_clip_toggle.setChecked(False)

    def toggle_clipboard(checked: bool):
        action_clip_toggle.setText(t("tray_clip_off") if checked else t("tray_clip_on"))
        if checked:
            clipboard_watcher.enable()
        else:
            clipboard_watcher.disable()

    action_clip_toggle.toggled.connect(toggle_clipboard)
    tray_menu.addAction(action_clip_toggle)

    action_settings = QAction(t("tray_settings"), tray_menu)
    action_settings.triggered.connect(window.open_settings_dialog)
    tray_menu.addAction(action_settings)

    tray_menu.addSeparator()

    action_quit = QAction(t("tray_exit"), tray_menu)
    action_quit.triggered.connect(app.quit)
    tray_menu.addAction(action_quit)

    tray_icon.setContextMenu(tray_menu)
    tray_icon.setToolTip(t("tray_tooltip"))

    def refresh_tray_language(_lang: str) -> None:
        action_expand.setText(t("tray_expand"))
        action_compact.setText(t("tray_compact"))
        action_clip_toggle.setText(t("tray_clip_off") if action_clip_toggle.isChecked() else t("tray_clip_on"))
        action_settings.setText(t("tray_settings"))
        action_quit.setText(t("tray_exit"))
        tray_icon.setToolTip(t("tray_tooltip"))

    I18nManager.get_instance().language_changed.connect(refresh_tray_language)
    tray_icon.show()

    # ── Clean Shutdown Hook ──────────────────────────────────────────────
    def shutdown():
        tray_icon.hide()
        media_worker.stop()
        stats_worker.stop()
        ipc_server.stop()
        bt_monitor.stop()
        rec_monitor.stop()
        wpm_tracker.stop()
        venv_detector.stop()
        pet_manager.stop()
        weather_worker.stop()
        hardware_monitor.stop()

    app.aboutToQuit.connect(shutdown)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
