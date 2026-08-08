"""Worker that downloads several subtitle tracks, possibly across videos."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import pyqtSignal

from ..services.downloader import download_one
from ..services.settings_service import SettingsService
from ..services.ytdlp_service import YtDlpService, friendly_error
from ..utils.logging import get_logger
from .base_worker import BaseWorker

log = get_logger()


class DownloadWorker(BaseWorker):
    """Download selected tracks for one or more videos in the background.

    ``tracks`` come from the first analyzed video; for additional videos
    (playlist mode) each track is matched by language code and kind, and
    missing tracks are reported as skipped.
    """

    progress = pyqtSignal(int, int)  # done, total
    status = pyqtSignal(str)
    track_finished = pyqtSignal(object)  # DownloadResult
    batch_finished = pyqtSignal(object)  # list[DownloadResult]

    def __init__(
        self,
        urls: list[str],
        tracks,
        settings: SettingsService,
        options: dict,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._urls = list(urls)
        self._tracks = list(tracks)
        self._settings = settings
        self._options = options

    def run(self) -> None:
        service = YtDlpService(self._settings)
        outdir = Path(self._options["output_dir"])
        try:
            outdir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self.failed.emit(f"Cannot create the destination folder: {exc}")
            return

        results = []
        total = len(self._urls) * len(self._tracks)
        done = 0
        self.progress.emit(0, total)

        for url in self._urls:
            if self.is_cancelled():
                break
            try:
                raw = service.get_raw_info(url, noplaylist=True)
            except Exception as exc:  # noqa: BLE001 - normalized for the UI
                log.exception("Failed to analyze %s", url)
                self._emit_log(f"Failed to analyze video: {friendly_error(exc, url)}")
                continue
            if self.is_cancelled():
                break
            info = service.to_video_info(raw, url)
            self.status.emit(f"Downloading: {info.title}")

            for requested in self._tracks:
                if self.is_cancelled():
                    break
                done += 1
                self.progress.emit(done, total)
                target = info.find_track(requested.language_code, requested.kind)
                if target is None:
                    result = download_one(
                        service,
                        requested,
                        video_title=info.title,
                        video_id=info.video_id,
                        fmt=self._options["format"],
                        template=self._options["template"],
                        outdir=str(outdir),
                        txt_enabled=self._options.get("txt_enabled", False),
                        txt_mode=self._options.get("txt_mode", "continuous"),
                    )
                    result.skipped = True
                    result.error = "Subtitle not available for this video."
                else:
                    result = download_one(
                        service,
                        target,
                        video_title=info.title,
                        video_id=info.video_id,
                        fmt=self._options["format"],
                        template=self._options["template"],
                        outdir=str(outdir),
                        txt_enabled=self._options.get("txt_enabled", False),
                        txt_mode=self._options.get("txt_mode", "continuous"),
                    )
                results.append(result)
                self.track_finished.emit(result)

        self.batch_finished.emit(results)
