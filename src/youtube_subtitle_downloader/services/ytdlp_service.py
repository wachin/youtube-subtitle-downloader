"""Isolated backend for all yt-dlp interaction.

All calls to yt-dlp go through this module so the project can adapt to
changes in yt-dlp by editing mostly this file (roadmap section 24).
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import yt_dlp
from yt_dlp.utils import DownloadError

from ..models.subtitle import SubtitleKind, SubtitleTrack, language_name
from ..models.video import PlaylistEntry, PlaylistInfo, VideoInfo
from .settings_service import SettingsService

log = logging.getLogger(__name__)

#: Formats the application understands natively (in preference order).
SUPPORTED_EXT_PRIORITY = ["srt", "vtt", "ttml", "json3"]

#: Browsers supported for ``--cookies-from-browser``.
BROWSERS: dict[str, str] = {
    "firefox": "firefox",
    "chromium": "chromium",
    "chrome": "chrome",
    "brave": "brave",
    "edge": "edge",
}

_YOUTUBE_HINT = re.compile(r"youtube\.com|youtu\.be|youtube-nocookie\.com", re.IGNORECASE)

#: GitHub endpoint used to check for the latest stable yt-dlp release.
_GITHUB_LATEST_RELEASE_URL = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"


def version() -> str | None:
    """yt-dlp library version, or None when not importable."""
    try:
        return yt_dlp.version.__version__
    except Exception:
        return None


def latest_version(timeout: int = 10) -> str | None:
    """Latest stable yt-dlp release tag (e.g. ``2026.07.04``) or None.

    Returns ``None`` when the check cannot be performed (no network, GitHub
    unreachable, malformed response). This is a read-only query: it never
    installs or modifies anything (roadmap section 40).
    """
    request = urllib.request.Request(
        _GITHUB_LATEST_RELEASE_URL,
        headers={"User-Agent": "youtube-subtitle-downloader"},
    )
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
        try:
            payload = json.load(response)
        finally:
            response.close()
    except Exception:  # noqa: BLE001 - any failure means "cannot check"
        return None
    tag = str(payload.get("tag_name") or "").strip().lstrip("v")
    return tag or None


def _version_key(version: str) -> tuple[int, ...]:
    """Normalize a version like ``2026.07.04`` into a comparable tuple."""
    parts: list[int] = []
    for part in version.replace("-", ".").split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        if digits:
            parts.append(int(digits))
    return tuple(parts)


def check_update() -> tuple[bool, str | None]:
    """Return ``(update_available, latest_version)``.

    ``latest_version`` is ``None`` when the check could not be performed;
    ``update_available`` is only ever True when a genuinely newer stable
    release exists and the installed version is known.
    """
    latest = latest_version()
    if latest is None:
        return False, None
    installed = version()
    if not installed:
        return False, latest
    return _version_key(latest) > _version_key(installed), latest


def ffmpeg_version() -> str | None:
    """Detect the ffmpeg version without requiring it to be present."""
    path = shutil.which("ffmpeg")
    if not path:
        return None
    try:
        output = subprocess.run(
            [path, "-version"], capture_output=True, text=True, timeout=10
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    first = output.splitlines()[0] if output else ""
    parts = first.split()
    if len(parts) >= 3 and parts[1] == "version":
        return parts[2]
    return first or None


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def is_youtube_url(url: str) -> bool:
    """Permissive local check; yt-dlp remains the definitive validator."""
    return bool(_YOUTUBE_HINT.search(url or ""))


def friendly_error(exc: BaseException, url: str = "") -> str:
    """Translate low-level exceptions into user friendly messages."""
    message = str(exc) or type(exc).__name__
    lowered = message.lower()

    if isinstance(exc, DownloadError):
        if "is not a valid url" in lowered or "unsupported url" in lowered:
            return "The URL does not look like a valid URL."
        if "private video" in lowered:
            return "This video is private and cannot be accessed."
        if "removed" in lowered or "has been deleted" in lowered:
            return "This video has been removed or no longer exists."
        if "unavailable" in lowered:
            return "Video unavailable. It may be removed, region-restricted or embed-restricted."
        if "sign in" in lowered or "log in" in lowered or "login" in lowered:
            return "YouTube requires you to sign in to access this video. Try enabling cookies."
        if "age" in lowered:
            return "This video is age-restricted."
        if "not part of any channel" in lowered or "unavailable" in lowered:
            return "This video is unavailable."
        if "http error 403" in lowered or "http error 404" in lowered:
            return "YouTube rejected the request (HTTP error). The video may be restricted."
        if "timed out" in lowered:
            return "The request timed out. Check your internet connection and try again."
        return message

    if isinstance(
        exc, (urllib.error.URLError, TimeoutError, ConnectionError, OSError)
    ):
        return "Network error. Check your internet connection and try again."

    if isinstance(exc, Exception) and "timed out" in lowered:
        return "The request timed out. Check your internet connection and try again."

    return message


def _ordered_exts(exts: list[str]) -> list[str]:
    """Order extensions with the natively supported ones first."""
    def key(ext: str) -> tuple[int, str]:
        if ext in SUPPORTED_EXT_PRIORITY:
            return (SUPPORTED_EXT_PRIORITY.index(ext), ext)
        return (99, ext)

    return list(dict.fromkeys(sorted(exts, key=key)))


class YtDlpService:
    """High level, GUI-friendly wrapper around the yt-dlp Python API."""

    def __init__(self, settings: SettingsService) -> None:
        self._settings = settings

    @property
    def settings(self) -> SettingsService:
        return self._settings

    def is_available(self) -> bool:
        return version() is not None

    @property
    def installed_version(self) -> str | None:
        return version()

    def _cookies_options(self) -> dict:
        options: dict = {}
        browser = self._settings.cookies_browser()
        if browser and browser in BROWSERS:
            options["cookiesfrombrowser"] = (BROWSERS[browser],)
        cookie_file = self._settings.cookies_file()
        if cookie_file and Path(cookie_file).is_file():
            options["cookiefile"] = cookie_file
        return options

    def _base_options(self, *, noplaylist: bool = True, extract_flat: bool = False) -> dict:
        options: dict = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": noplaylist,
            "extract_flat": extract_flat,
            "retries": 2,
            "socket_timeout": 30,
        }
        options.update(self._cookies_options())
        return options

    # -- info --------------------------------------------------------------
    def get_raw_info(self, url: str, *, noplaylist: bool = True) -> dict:
        """Extract structured video/playlist info without downloading."""
        with yt_dlp.YoutubeDL(
            self._base_options(noplaylist=noplaylist)
        ) as ydl:
            info = ydl.extract_info(url, download=False)
        return info or {}

    def build_tracks(self, info: dict) -> list[SubtitleTrack]:
        """Build subtitle tracks from ``subtitles`` / ``automatic_captions``.

        Handles the common YouTube case where only automatic captions exist
        while the CLI says "has no subtitles" (roadmap section 58).
        """
        tracks: list[SubtitleTrack] = []
        for kind, key in (
            (SubtitleKind.MANUAL, "subtitles"),
            (SubtitleKind.AUTOMATIC, "automatic_captions"),
        ):
            subtitles = info.get(key) or {}
            for code, formats in subtitles.items():
                if not formats:
                    continue
                best = formats[0]
                exts = [f.get("ext") for f in formats if f.get("ext")]
                track = SubtitleTrack(
                    language_code=str(code),
                    kind=kind,
                    language_name=language_name(str(code), best.get("name")),
                    formats=_ordered_exts(exts),
                    url=best.get("url"),
                    is_original=str(code).lower().endswith("-orig"),
                )
                tracks.append(track)
        return tracks

    def to_video_info(self, info: dict, url: str) -> VideoInfo:
        """Convert a raw yt-dlp info dict into our VideoInfo model."""
        return VideoInfo(
            video_id=str(info.get("id") or ""),
            title=str(info.get("title") or "(untitled)"),
            url=url,
            channel=str(info.get("channel") or info.get("uploader") or ""),
            duration=info.get("duration"),
            upload_date=str(info.get("upload_date")) if info.get("upload_date") else None,
            thumbnail_url=info.get("thumbnail"),
            tracks=self.build_tracks(info),
            playlist_title=info.get("playlist"),
            playlist_count=info.get("playlist_count"),
        )

    # -- playlists ---------------------------------------------------------
    def get_playlist(self, url: str) -> PlaylistInfo:
        """Extract a flat playlist (entries without full metadata)."""
        with yt_dlp.YoutubeDL(
            self._base_options(noplaylist=False, extract_flat=True)
        ) as ydl:
            info = ydl.extract_info(url, download=False)
        info = info or {}
        entries = [
            PlaylistEntry(
                video_id=str(entry.get("id") or ""),
                title=str(entry.get("title") or "(untitled)"),
                url=str(entry.get("url") or entry.get("webpage_url") or ""),
                channel=str(entry.get("channel") or entry.get("uploader") or ""),
                duration=entry.get("duration"),
            )
            for entry in (info.get("entries") or [])
            if entry
        ]
        return PlaylistInfo(
            playlist_id=str(info.get("id") or ""),
            title=str(info.get("title") or "Playlist"),
            entries=entries,
        )

    # -- subtitle content --------------------------------------------------
    def fetch_subtitle_content(self, track: SubtitleTrack) -> bytes:
        """Download the raw subtitle data for a track using yt-dlp's opener."""
        if not track.url:
            raise DownloadError("The subtitle track has no data URL.")
        with yt_dlp.YoutubeDL(self._base_options()) as ydl:
            return ydl.urlopen(track.url).read()


def decode_subtitle_bytes(data: bytes) -> str:
    """Decode raw subtitle bytes, tolerating BOM and fallback encodings."""
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")
