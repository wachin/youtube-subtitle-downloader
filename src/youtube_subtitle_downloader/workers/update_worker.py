"""Worker that checks for a newer yt-dlp release off the GUI thread."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal

from ..services.ytdlp_service import check_update
from .base_worker import BaseWorker


class UpdateCheckWorker(BaseWorker):
    """Query the latest stable yt-dlp release without blocking the UI.

    Emits ``check_done`` with ``(update_available, latest_version)`` — the
    latest version is ``None`` when the check could not be performed. The
    worker only queries the GitHub API; it never installs or modifies
    anything (roadmap section 40: no destructive automatic updates).
    """

    check_done = pyqtSignal(bool, object)  # (update_available, latest_version | None)

    def run(self) -> None:
        try:
            if self.is_cancelled():
                return
            available, latest = check_update()
            if self.is_cancelled():
                return
            self.check_done.emit(available, latest)
        except Exception as exc:  # noqa: BLE001 - normalized for the UI
            self.failed.emit(str(exc))
