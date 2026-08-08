"""Data models for video information, playlists and download results."""

from __future__ import annotations

from dataclasses import dataclass, field

from .subtitle import SubtitleKind, SubtitleTrack


@dataclass
class VideoInfo:
    """Metadata of a single video plus its available subtitle tracks."""

    video_id: str
    title: str
    url: str
    channel: str = ""
    duration: int | None = None  # seconds
    upload_date: str | None = None  # YYYYMMDD
    thumbnail_url: str | None = None
    tracks: list[SubtitleTrack] = field(default_factory=list)
    playlist_title: str | None = None
    playlist_count: int | None = None

    @property
    def manual_tracks(self) -> list[SubtitleTrack]:
        return [t for t in self.tracks if t.kind is SubtitleKind.MANUAL]

    @property
    def automatic_tracks(self) -> list[SubtitleTrack]:
        return [t for t in self.tracks if t.kind is SubtitleKind.AUTOMATIC]

    def find_track(self, language_code: str, kind: SubtitleKind) -> SubtitleTrack | None:
        """Find a track by language code and kind.

        An exact code match (e.g. ``es``) is preferred over an original
        variant (``es-orig``).
        """
        target = language_code.lower()
        for track in self.tracks:
            if track.kind is kind and track.language_code.lower() == target:
                return track
        for track in self.tracks:
            if track.kind is kind and track.base_code.lower() == target:
                return track
        return None

    @property
    def formatted_duration(self) -> str:
        """Duration as ``HH:MM:SS`` (or ``MM:SS``)."""
        if not self.duration:
            return ""
        seconds = int(self.duration)
        hours, rem = divmod(seconds, 3600)
        minutes, secs = divmod(rem, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    @property
    def formatted_upload_date(self) -> str:
        """Upload date as ``YYYY-MM-DD`` when available."""
        if not self.upload_date or len(self.upload_date) != 8:
            return ""
        return f"{self.upload_date[0:4]}-{self.upload_date[4:6]}-{self.upload_date[6:8]}"


@dataclass
class PlaylistEntry:
    """A lightweight playlist entry (no subtitle data fetched yet)."""

    video_id: str
    title: str
    url: str
    channel: str = ""
    duration: int | None = None


@dataclass
class PlaylistInfo:
    """A playlist with its (flat) entries."""

    playlist_id: str
    title: str
    entries: list[PlaylistEntry] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.entries)


@dataclass
class DownloadResult:
    """Outcome of downloading a single subtitle track."""

    ok: bool
    video_title: str = ""
    language_code: str = ""
    language_name: str = ""
    path: str = ""
    error: str = ""
    skipped: bool = False

    @property
    def status_text(self) -> str:
        """Short status shown in logs / completion dialog."""
        if self.skipped:
            return "Skipped"
        if self.ok:
            return "Completed"
        return "Failed"
