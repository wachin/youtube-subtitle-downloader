"""Tests for desktop notifications and theme icons (roadmap sections 52/34)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QIcon  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from youtube_subtitle_downloader.services.settings_service import SettingsService  # noqa: E402
from youtube_subtitle_downloader.utils.icons import (  # noqa: E402
    APP_ICON_NAME,
    app_icon,
    icon_path,
    theme_icon,
)
from youtube_subtitle_downloader.utils.notifications import (  # noqa: E402
    send_notification,
)

_APP: QApplication | None = None


def _app() -> QApplication:
    """Create (once) and keep the QApplication alive for the whole session."""
    global _APP
    if _APP is None:
        _APP = QApplication.instance() or QApplication([])
        _APP.setApplicationName("youtube-subtitle-downloader-tests")
        _APP.setOrganizationName("youtube-subtitle-downloader-tests")
    return _APP


# -- notifications ---------------------------------------------------------
def test_send_notification_uses_notify_send_when_available(monkeypatch) -> None:
    _app()
    monkeypatch.setattr(
        "youtube_subtitle_downloader.utils.notifications._notify_send",
        lambda title, message: True,
    )
    assert send_notification("Download finished", "2 subtitles downloaded.") is True


def test_send_notification_silent_when_nothing_is_available(monkeypatch) -> None:
    _app()
    import youtube_subtitle_downloader.utils.notifications as notifications

    monkeypatch.setattr(
        notifications, "_notify_send", lambda title, message: False
    )
    monkeypatch.setattr(
        notifications.QSystemTrayIcon,
        "isSystemTrayAvailable",
        staticmethod(lambda: False),
    )
    # No notify-send and no system tray: nothing can be emitted.
    assert send_notification("Download finished", "2 subtitles downloaded.") is False


def test_send_notification_tray_fallback(monkeypatch) -> None:
    _app()

    sent: list[tuple[str, str]] = []

    class FakeTray:
        def showMessage(self, title, message, _icon, _timeout) -> None:  # noqa: N802
            sent.append((title, message))

    import youtube_subtitle_downloader.utils.notifications as notifications

    monkeypatch.setattr(
        notifications, "_notify_send", lambda title, message: False
    )
    monkeypatch.setattr(
        notifications.QSystemTrayIcon,
        "isSystemTrayAvailable",
        staticmethod(lambda: True),
    )
    monkeypatch.setattr(notifications, "_tray_icon", lambda app: FakeTray())

    assert send_notification("Title", "Message") is True
    assert sent == [("Title", "Message")]


# -- settings --------------------------------------------------------------
def test_notify_on_finish_setting_roundtrip() -> None:
    _app()
    settings = SettingsService()
    settings.set_notify_on_finish(False)
    assert settings.notify_on_finish() is False
    settings.set_notify_on_finish(True)
    assert settings.notify_on_finish() is True


# -- theme icons -----------------------------------------------------------
def test_theme_icon_returns_qicon() -> None:
    _app()
    assert isinstance(theme_icon("edit-paste"), QIcon)
    assert APP_ICON_NAME  # the app icon name is defined and non-empty


# -- bundled logo ----------------------------------------------------------
def test_bundled_icon_path_exists() -> None:
    path = icon_path()
    assert path.is_file()
    assert path.suffix == ".svg"
    assert path.name == f"{APP_ICON_NAME}.svg"


def test_app_icon_returns_qicon() -> None:
    _app()
    assert isinstance(app_icon(), QIcon)


def test_bundled_icon_svg_is_valid_xml() -> None:
    import xml.etree.ElementTree as ET

    ET.parse(icon_path())  # raises if the SVG is not well-formed XML


def test_app_icon_uses_bundled_logo(monkeypatch) -> None:
    """app_icon() prefers the bundled SVG over the theme fallback.

    Note: this relies on the Qt SVG image-format plugin being available in
    the test environment (it is: ``PyQt6.QtSvg`` ships with PyQt6). If the
    bundled SVG ever failed to load, ``app_icon()`` would legitimately fall
    back to the theme and this assertion would need to change.
    """
    _app()
    loaded: list[str] = []
    monkeypatch.setattr(
        "youtube_subtitle_downloader.utils.icons.QIcon.fromTheme",
        lambda name: loaded.append(name) or QIcon(),
    )
    app_icon()
    assert loaded == []  # the bundled icon was used; the theme was never asked
