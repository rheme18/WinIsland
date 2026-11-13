"""
WinIsland - Weather Background Service
Fetches lightweight local weather updates (temperature & condition) via wttr.in JSON API.
Provides monochrome icon mappings for the Dynamic Island expanded header.
"""

import json
import urllib.request
from typing import Optional
from PyQt6.QtCore import QThread, pyqtSignal


class WeatherWorker(QThread):
    """
    Background worker thread that fetches local weather once on startup
    and refreshes every 25 minutes. Emits (temperature_str, condition_str, icon_type).
    """
    weather_updated = pyqtSignal(str, str, str)  # e.g. ("9°C", "Parçalı Bulutlu", "weather_partly_cloudy")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._last_temp: str = "--°"
        self._last_desc: str = ""
        self._last_icon: str = "weather_sun"

    def run(self) -> None:
        while self._running:
            self._fetch_weather()
            # Sleep in small slices so thread can terminate promptly on quit (25 minutes)
            for _ in range(25 * 60):
                if not self._running:
                    return
                self.msleep(1000)

    def _fetch_weather(self) -> None:
        try:
            req = urllib.request.Request(
                "https://wttr.in/?format=j1",
                headers={"User-Agent": "WinIsland/2.0 (Windows NT 10.0; DynamicIsland)"}
            )
            with urllib.request.urlopen(req, timeout=4) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    curr = data.get("current_condition", [{}])[0]
                    temp_c = curr.get("temp_C", "")
                    weather_desc = curr.get("weatherDesc", [{}])[0].get("value", "")

                    if temp_c:
                        temp_str = f"{temp_c}°C"
                        icon_type = self._map_icon(weather_desc)
                        self._last_temp = temp_str
                        self._last_desc = weather_desc
                        self._last_icon = icon_type
                        self.weather_updated.emit(temp_str, weather_desc, icon_type)
        except Exception:
            # Fallback gracefully without breaking or logging errors
            pass

    @staticmethod
    def _map_icon(desc: str) -> str:
        d = desc.lower()
        if any(w in d for w in ("snow", "blizzard", "sleet", "ice", "frost")):
            return "weather_snow"
        if any(w in d for w in ("rain", "shower", "drizzle", "storm", "thunder")):
            return "weather_rain"
        if any(w in d for w in ("partly", "scattered", "broken")):
            return "weather_partly_cloudy"
        if any(w in d for w in ("cloud", "overcast", "fog", "mist", "haze")):
            return "weather_cloud"
        return "weather_sun"

    def stop(self) -> None:
        self._running = False
        self.wait(1500)
