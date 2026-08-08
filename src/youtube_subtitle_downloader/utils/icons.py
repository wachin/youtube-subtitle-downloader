"""Application icons (roadmap section 34) and the bundled program logo.

The application bundles its own logo as ``resources/icons/youtube-subtitle-
downloader.svg`` (Freedesktop-compatible name). ``app_icon()`` loads it and
falls back to the desktop theme icon when the SVG cannot be loaded. The
``theme_icon()`` helper is used for the various buttons and menu actions:
widgets keep their text as a natural fallback when the active theme lacks an
icon, in which case ``theme_icon()`` returns a null ``QIcon`` and ``setIcon()``
is a no-op.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtGui import QIcon

#: Freedesktop icon name of the application (matches the bundled SVG name).
APP_ICON_NAME = "youtube-subtitle-downloader"

def theme_icon(name: str) -> QIcon:
    """Return the system theme icon ``name`` (may be a null icon)."""
    return QIcon.fromTheme(name)


def icon_path() -> Path:
    """Absolute path of the bundled application logo (SVG)."""
    return (
        Path(__file__).resolve().parent.parent
        / "resources"
        / "icons"
        / f"{APP_ICON_NAME}.svg"
    )


def app_icon() -> QIcon:
    """Return the bundled application logo, falling back to the theme.

    The fallback uses ``APP_ICON_NAME`` again: when the SVG cannot be loaded
    (for example a missing Qt SVG plugin) the icon may also be installed in
    the desktop icon theme, e.g. at
    ``~/.local/share/icons/hicolor/scalable/apps/``.
    """
    icon = QIcon(str(icon_path()))
    if icon.isNull():
        icon = theme_icon(APP_ICON_NAME)
    return icon
