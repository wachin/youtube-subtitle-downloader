"""System theme icons (roadmap section 34).

Prefer the desktop theme icons via ``QIcon.fromTheme()`` whenever they exist.
Widgets keep their text as a natural fallback: when the active theme lacks an
icon, ``theme_icon()`` returns a null ``QIcon`` and ``setIcon()`` is a no-op.
"""

from __future__ import annotations

from PyQt6.QtGui import QIcon

#: Freedesktop icon used for the application/tray icon (widely available).
APP_ICON_NAME = "applications-multimedia"


def theme_icon(name: str) -> QIcon:
    """Return the system theme icon ``name`` (may be a null icon)."""
    return QIcon.fromTheme(name)
