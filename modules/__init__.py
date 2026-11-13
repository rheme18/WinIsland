"""
WinIsland modules package.
All subsystem imports centralized here for clean access.
"""

from modules.media import MediaWorker, MediaTrackData
from modules.system_stats import SystemStatsWorker, SystemStatsData
from modules.clipboard import ClipboardWatcher
from modules.ipc_server import IPCServer
from modules.volume import VolumeManager
from modules.bluetooth_monitor import BluetoothMonitor
from modules.screen_recording import ScreenRecordingMonitor
from modules.wpm_tracker import WPMTracker
from modules.venv_detector import VenvDetector
from modules.ai_client import AIClient
from modules.pet import PetManager, PetState, PetEvolution

__all__ = [
    "MediaWorker", "MediaTrackData",
    "SystemStatsWorker", "SystemStatsData",
    "ClipboardWatcher",
    "IPCServer",
    "VolumeManager",
    "BluetoothMonitor",
    "ScreenRecordingMonitor",
    "WPMTracker",
    "VenvDetector",
    "AIClient",
    "PetManager", "PetState", "PetEvolution",
]
