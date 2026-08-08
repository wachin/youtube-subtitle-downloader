"""Workers that analyze videos and playlists off the GUI thread."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal

from ..services.settings_service import SettingsService
from ..services.ytdlp_service import YtDlpService, friendly_error
from .base_worker import BaseWorker


class VideoInfoWorker(BaseWorker):
    """Fetch video info and build its subtitle tracks in the background."""

    info_ready = pyqtSignal(object)  # VideoInfo
    playlist_detected = pyqtSignal(str, int)  # (playlist title, count)

    def __init__(self, url: str, settings: SettingsService, parent=None) -> None:
        super().__init__(parent)
        self._url = url
        self._settings = settings

    def run(self) -> None:
        try:
            if self.is_cancelled():
                return
            self._emit_log("Analyzing URL...")
            service = YtDlpService(self._settings)
            raw = service.get_raw_info(self._url, noplaylist=True)
            if self.is_cancelled():
                return
            info = service.to_video_info(raw, self._url)
            self._emit_log(f"Video found: {info.title}")
            self._emit_log(
                f"{len(info.manual_tracks)} manual subtitle(s), "
                f"{len(info.automatic_tracks)} automatic subtitle(s)."
            )
            if info.playlist_title and (info.playlist_count or 0) > 1:
                self.playlist_detected.emit(info.playlist_title, info.playlist_count)
            if self.is_cancelled():
                return
            self.info_ready.emit(info)
        except Exception as exc:  # noqa: BLE001 - normalized for the UI
            self.failed.emit(friendly_error(exc, self._url))


class PlaylistWorker(BaseWorker):
    """Extract the (flat) entries of a playlist in the background."""

    playlist_ready = pyqtSignal(object)  # PlaylistInfo

    def __init__(self, url: str, settings: SettingsService, parent=None) -> None:
        super().__init__(parent)
        self._url = url
        self._settings = settings

    def run(self) -> None:
        try:
            if self.is_cancelled():
                return
            self._emit_log("Fetching playlist...")
            service = YtDlpService(self._settings)
            playlist = service.get_playlist(self._url)
            if self.is_cancelled():
                return
            self._emit_log(
                f"Playlist found: {playlist.title} ({playlist.count} video(s))."
            )
            self.playlist_ready.emit(playlist)
        except Exception as exc:  # noqa: BLE001 - normalized for the UI
            self.failed.emit(friendly_error(exc, self._url))
