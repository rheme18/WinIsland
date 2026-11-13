"""
WinIsland - Windows Media Transport Controls (GSMTC) Integration
Tracks Spotify, YouTube, Apple Music, VLC with timeline scrubber and HD album art.
"""

import asyncio
import queue
import urllib.request
import urllib.parse
import json
import re
from dataclasses import dataclass
from typing import Optional, Dict
from PyQt6.QtCore import QThread, pyqtSignal, pyqtSlot
from modules.i18n import t

try:
    import winsdk.windows.media.control as wmc
    import winsdk.windows.storage.streams as streams
    WINSDK_AVAILABLE = True
except ImportError:
    WINSDK_AVAILABLE = False


@dataclass
class MediaTrackData:
    title: str
    artist: str
    album: str
    app_id: str
    is_playing: bool
    thumbnail_bytes: Optional[bytes] = None
    position_sec: float = 0.0
    duration_sec: float = 0.0

    @property
    def is_valid(self) -> bool:
        return bool(self.title.strip() or self.artist.strip())

    @property
    def track_id(self) -> str:
        return f"{self.title.strip()}|{self.artist.strip()}".lower()


class MediaWorker(QThread):
    """
    Asynchronous Windows Media Controller worker.
    Runs an asyncio loop inside a dedicated QThread to safely interface with WinRT.
    Features timeline scrubber position tracking, seeking, and online HD album art fetching.
    """
    media_updated = pyqtSignal(object)       # Emits MediaTrackData
    track_changed = pyqtSignal(object)       # Emits MediaTrackData on song switch
    media_idle = pyqtSignal()                # Emits when no media is active

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._cmd_queue: queue.Queue = queue.Queue()
        self._last_track_id: Optional[str] = None
        self._last_is_playing: bool = False
        self._manager = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._command_event: Optional[asyncio.Event] = None
        self._art_cache: Dict[str, bytes] = {}
        self._fetching_art: set = set()

    def stop(self) -> None:
        self._running = False
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self.wait(1000)

    # Thread-safe slots callable from Qt GUI thread
    @pyqtSlot()
    def request_toggle_play(self) -> None:
        self._queue_command("toggle_play", None)

    @pyqtSlot()
    def request_next(self) -> None:
        self._queue_command("next", None)

    @pyqtSlot()
    def request_previous(self) -> None:
        self._queue_command("previous", None)

    @pyqtSlot(float)
    def request_seek(self, position_seconds: float) -> None:
        self._queue_command("seek", position_seconds)

    def _queue_command(self, command: str, payload) -> None:
        self._cmd_queue.put((command, payload))
        loop = self._loop
        event = self._command_event
        if loop and event and loop.is_running():
            loop.call_soon_threadsafe(event.set)

    def run(self) -> None:
        if not WINSDK_AVAILABLE:
            self.media_idle.emit()
            return

        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            self._loop.run_until_complete(self._media_loop())
        except Exception:
            pass
        finally:
            self._loop.close()

    async def _media_loop(self) -> None:
        self._command_event = asyncio.Event()
        try:
            self._manager = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
        except Exception:
            self._manager = None

        if not self._manager:
            self.media_idle.emit()
            return

        while self._running:
            await self._process_commands()

            try:
                session = self._manager.get_current_session()
                if session is None:
                    if self._last_track_id is not None:
                        self._last_track_id = None
                        self.media_idle.emit()
                else:
                    await self._update_session_data(session)
            except Exception:
                pass

            # Wake immediately for user input instead of waiting out the polling interval.
            try:
                await asyncio.wait_for(self._command_event.wait(), timeout=0.8)
            except asyncio.TimeoutError:
                pass
            self._command_event.clear()

    async def _process_commands(self) -> None:
        while not self._cmd_queue.empty():
            cmd_type, payload = self._cmd_queue.get_nowait()
            try:
                session = self._manager.get_current_session() if self._manager else None
                if not session:
                    continue

                if cmd_type == "toggle_play":
                    await session.try_toggle_play_pause_async()
                elif cmd_type == "next":
                    await session.try_skip_next_async()
                elif cmd_type == "previous":
                    await session.try_skip_previous_async()
                elif cmd_type == "seek" and payload is not None:
                    # Windows GSMTC seek position is in 100-nanosecond intervals (1 sec = 10,000,000 units)
                    target_units = int(float(payload) * 10_000_000)
                    await session.try_change_playback_position_async(target_units)
            except Exception:
                pass

    async def _update_session_data(self, session) -> None:
        try:
            props = await session.try_get_media_properties_async()
            if not props:
                return

            info = session.get_playback_info()
            is_playing = False
            if info:
                is_playing = (info.playback_status == wmc.GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING)

            title = props.title or ""
            artist = props.artist or ""
            album = props.album_title or ""
            app_id = session.source_app_user_model_id or "Media Player"

            friendly_app = app_id.split("!")[-1].split(".")[0].capitalize()
            track_key = f"{title.strip()}|{artist.strip()}".lower()

            # Timeline properties (position and duration)
            position_sec = 0.0
            duration_sec = 0.0
            try:
                timeline = session.get_timeline_properties()
                if timeline:
                    if timeline.position:
                        position_sec = timeline.position.total_seconds()
                    if timeline.end_time:
                        duration_sec = timeline.end_time.total_seconds()
            except Exception:
                pass

            # Thumbnail
            thumbnail_bytes = self._art_cache.get(track_key)
            if not thumbnail_bytes and props.thumbnail:
                try:
                    stream_ref = props.thumbnail
                    stream = await stream_ref.open_read_async()
                    size = stream.size
                    if 32 < size < 10 * 1024 * 1024:
                        reader = streams.DataReader(stream)
                        await reader.load_async(size)
                        buf = bytearray(size)
                        reader.read_bytes(buf)
                        raw = bytes(buf)
                        # Validate PNG and JPEG headers and EOF markers to prevent libpng stderr Read Errors
                        is_valid = False
                        if raw.startswith(b"\x89PNG\r\n\x1a\n"):
                            # PNG must contain IEND chunk
                            if b"IEND" in raw:
                                is_valid = True
                        elif raw.startswith(b"\xff\xd8"):
                            # JPEG must contain EOI marker near the end
                            if b"\xff\xd9" in raw[-32:]:
                                is_valid = True
                        elif len(raw) > 128:
                            # Other formats (WebP, BMP)
                            is_valid = True

                        if is_valid:
                            thumbnail_bytes = raw
                            self._art_cache[track_key] = thumbnail_bytes
                except Exception:
                    thumbnail_bytes = None

            # Fetch HD art online in background if missing
            if not thumbnail_bytes and title and track_key not in self._fetching_art:
                self._fetching_art.add(track_key)
                asyncio.create_task(self._fetch_cover_online(title, artist, track_key))

            track = MediaTrackData(
                title=title.strip() or t("unknown_track"),
                artist=artist.strip() or friendly_app,
                album=album.strip(),
                app_id=friendly_app,
                is_playing=is_playing,
                thumbnail_bytes=thumbnail_bytes,
                position_sec=position_sec,
                duration_sec=duration_sec
            )

            # Detect song switch
            if track_key != self._last_track_id:
                old_id = self._last_track_id
                self._last_track_id = track_key
                self._last_is_playing = is_playing

                if old_id is not None and (track.title or track.artist):
                    self.track_changed.emit(track)
            elif is_playing != self._last_is_playing:
                self._last_is_playing = is_playing

            self.media_updated.emit(track)

        except Exception:
            pass

    async def _fetch_cover_online(self, title: str, artist: str, track_key: str) -> None:
        try:
            loop = asyncio.get_event_loop()
            art_bytes = await loop.run_in_executor(None, self._sync_itunes_fetch, title, artist)
            if art_bytes:
                self._art_cache[track_key] = art_bytes
                if self._last_track_id == track_key and self._manager:
                    session = self._manager.get_current_session()
                    if session:
                        await self._update_session_data(session)
        except Exception:
            pass

    @staticmethod
    def _sync_itunes_fetch(title: str, artist: str) -> Optional[bytes]:
        try:
            clean_title = re.sub(r'[\(\[].*?[\)\]]', '', title).strip()
            query = f"{artist} {clean_title}".strip()
            if not query:
                return None

            url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&entity=song&limit=1"
            req = urllib.request.Request(url, headers={"User-Agent": "WinIsland/2.0"})
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("resultCount", 0) > 0:
                    art_url = data["results"][0].get("artworkUrl100", "")
                    if art_url:
                        hd_url = art_url.replace("100x100bb.jpg", "300x300bb.jpg")
                        with urllib.request.urlopen(hd_url, timeout=3.0) as img_resp:
                            return img_resp.read()
        except Exception:
            pass
        return None
