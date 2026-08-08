"""Offscreen smoke tests for the GUI layer (no display required)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from youtube_subtitle_downloader.models.subtitle import SubtitleKind, SubtitleTrack  # noqa: E402
from youtube_subtitle_downloader.services.settings_service import SettingsService  # noqa: E402
from youtube_subtitle_downloader.ui.main_window import MainWindow  # noqa: E402
from youtube_subtitle_downloader.ui.subtitle_table_model import SubtitleTableModel  # noqa: E402


_APP: QApplication | None = None


def _app() -> QApplication:
    """Create (once) and keep the QApplication alive for the whole session."""
    global _APP
    if _APP is None:
        _APP = QApplication.instance() or QApplication([])
        _APP.setApplicationName("youtube-subtitle-downloader-tests")
        _APP.setOrganizationName("youtube-subtitle-downloader-tests")
    return _APP


def test_main_window_constructs():
    _app()
    window = MainWindow(SettingsService())
    assert "YouTube Subtitle Downloader" in window.windowTitle()
    window.close()


def test_table_model_checking_and_filtering():
    _app()
    model = SubtitleTableModel()
    tracks = [
        SubtitleTrack("es", SubtitleKind.AUTOMATIC, "Spanish", ["vtt", "srt"]),
        SubtitleTrack("en", SubtitleKind.MANUAL, "English", ["vtt"]),
        SubtitleTrack("es-orig", SubtitleKind.AUTOMATIC, "Spanish (Original)", ["vtt"]),
    ]
    model.set_tracks(tracks)
    assert model.rowCount() == 3

    model.check_all(True)
    assert model.checked_count() == 3
    assert len(model.checked_tracks()) == 3

    model.check_all(False)
    model.check_kind(SubtitleKind.MANUAL)
    assert len(model.checked_tracks()) == 1
    assert model.checked_tracks()[0].language_code == "en"

    # Filtering by native/English name and codes
    model.check_all(False)
    model.set_filter(kind=None, text="Español")
    assert model.rowCount() == 2  # es + es-orig match "Spanish"
    model.set_filter(kind=None, text="es-orig")
    assert model.rowCount() == 1


def test_model_preferred_language_selection():
    _app()
    model = SubtitleTableModel()
    model.set_tracks(
        [
            SubtitleTrack("es", SubtitleKind.AUTOMATIC, "Spanish", ["vtt"]),
            SubtitleTrack("en", SubtitleKind.AUTOMATIC, "English", ["vtt"]),
        ]
    )
    model.auto_select_preferred("es")
    assert len(model.checked_tracks()) == 1
    assert model.checked_tracks()[0].language_code == "es"
