"""Worker that fetches subtitle content for the preview dialog."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal

from ..models.subtitle import SubtitleTrack
from ..services.subtitle_service import (
    SUPPORTED_EXTENSIONS,
    cues_to_txt,
    detect_format,
    parse_subtitles,
)
from ..services.settings_service import SettingsService
from ..services.ytdlp_service import YtDlpService, decode_subtitle_bytes, friendly_error
from .base_worker import BaseWorker


class PreviewWorker(BaseWorker):
    """Load subtitle text in the background and emit it as plain text."""

    content_ready = pyqtSignal(str)

    def __init__(
        self,
        track: SubtitleTrack,
        settings: SettingsService,
        source_ext: str | None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._track = track
        self._settings = settings
        self._source_ext = source_ext or (track.formats[0] if track.formats else None)

    def run(self) -> None:
        try:
            if self.is_cancelled():
                return
            service = YtDlpService(self._settings)
            data = service.fetch_subtitle_content(self._track)
            text = decode_subtitle_bytes(data)
            source_ext = detect_format(text) or self._source_ext
            if source_ext in SUPPORTED_EXTENSIONS:
                cues = parse_subtitles(text, source_ext)
                text = cues_to_txt(cues, mode="lines")
            if self.is_cancelled():
                return
            self.content_ready.emit(text)
        except Exception as exc:  # noqa: BLE001 - normalized for the UI
            self.failed.emit(friendly_error(exc))
