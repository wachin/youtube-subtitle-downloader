"""Filesystem paths for user data, cache, logs and downloads.

Never hard-code home directories: XDG conventions are respected and the
user's home directory is always discovered through ``Path.home()``.
"""

from __future__ import annotations

import os
from pathlib import Path

APP_DIR_NAME = "youtube-subtitle-downloader"


def _env_or(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value) if value else default


def data_dir() -> Path:
    """Per-user data directory (history, logs, ...)."""
    return _env_or(
        "XDG_DATA_HOME", Path.home() / ".local" / "share"
    ) / APP_DIR_NAME


def cache_dir() -> Path:
    """Per-user cache directory."""
    return _env_or("XDG_CACHE_HOME", Path.home() / ".cache") / APP_DIR_NAME


def config_dir() -> Path:
    """Per-user config directory (QSettings also lives under XDG config)."""
    return _env_or("XDG_CONFIG_HOME", Path.home() / ".config") / APP_DIR_NAME


def logs_dir() -> Path:
    """Directory where rotating application logs are stored."""
    return data_dir() / "logs"


def history_file() -> Path:
    """JSON file that stores the optional video history."""
    return data_dir() / "history.json"


def default_download_dir() -> Path:
    """Sensible default output directory (``~/Videos/Subtitles``)."""
    videos = Path.home() / "Videos"
    if videos.is_dir():
        return videos / "Subtitles"
    return Path.home() / "Subtitles"


def ensure_dirs() -> None:
    """Create all directories the application needs."""
    for directory in (data_dir(), cache_dir(), logs_dir()):
        directory.mkdir(parents=True, exist_ok=True)
