"""Optional desktop notifications (roadmap section 52).

A notification is emitted when a download finishes while the main window is
not active. No heavy third-party dependency is added: ``notify-send`` (part of
libnotify, present in most desktop Linux installs) is preferred, and the Qt
system tray bubble is used as a fallback when ``notify-send`` is unavailable.
"""

from __future__ import annotations

import shutil
import subprocess

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from .. import __app_name__
from .icons import APP_ICON_NAME, app_icon

_TRAY_ATTR = "_youtube_subtitle_tray_icon"


def _notify_send(title: str, message: str) -> bool:
    """Emit the notification with ``notify-send``; False if unavailable."""
    executable = shutil.which("notify-send")
    if not executable:
        return False
    try:
        # Argument list + shell=False: never build a shell command from input.
        subprocess.Popen(
            [
                executable,
                "--app-name",
                __app_name__,
                "--icon",
                APP_ICON_NAME,
                title,
                message,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return False
    return True


def _tray_icon(app) -> QSystemTrayIcon:
    """Create (once) the hidden tray icon used as the Qt fallback."""
    tray = getattr(app, _TRAY_ATTR, None)
    if tray is None:
        tray = QSystemTrayIcon(app_icon(), app)
        setattr(app, _TRAY_ATTR, tray)
    return tray


def send_notification(title: str, message: str) -> bool:
    """Show a desktop notification; return True when one was emitted."""
    if _notify_send(title, message):
        return True
    # Fallback: Qt tray bubble. Note that on most Linux platforms the bubble
    # only displays when the tray icon is visible; it is a best-effort path
    # (``notify-send`` is the primary mechanism).
    app = QApplication.instance()
    if app is not None and QSystemTrayIcon.isSystemTrayAvailable():
        _tray_icon(app).showMessage(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Information,
            5000,
        )
        return True
    return False
