"""Logging setup using the standard ``logging`` module.

Logs are stored under the per-user data directory with rotation and a size
limit. Sensitive data (cookies, URLs may be fine, but never cookie content)
must not be logged by the rest of the application.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from .paths import logs_dir

_LOGGER: logging.Logger | None = None

_MAX_BYTES = 512_000
_BACKUP_COUNT = 3


def setup_logging() -> logging.Logger:
    """Configure (once) and return the application logger."""
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    logger = logging.getLogger("youtube_subtitle_downloader")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    logs_dir().mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        logs_dir() / "app.log",
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(stream_handler)

    _LOGGER = logger
    return logger


def get_logger() -> logging.Logger:
    """Return the application logger, configuring it if needed."""
    return _LOGGER if _LOGGER is not None else setup_logging()
