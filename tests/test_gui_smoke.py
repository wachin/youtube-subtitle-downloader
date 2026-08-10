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


def test_setdata_accepts_int_check_states():
    """Regression: PyQt6 6.9 hands check states to setData as plain ints."""
    _app()
    model = SubtitleTableModel()
    model.set_tracks([SubtitleTrack("es", SubtitleKind.AUTOMATIC, "Spanish", ["vtt"])])
    index = model.index(0, 0)

    # The view delegate passes int 2 (== Qt.CheckState.Checked) and int 0.
    assert model.setData(index, 2, Qt.ItemDataRole.CheckStateRole)
    assert model.checked_count() == 1
    assert (
        model.data(index, Qt.ItemDataRole.CheckStateRole) == Qt.CheckState.Checked
    )

    assert model.setData(index, 0, Qt.ItemDataRole.CheckStateRole)
    assert model.checked_count() == 0

    # The enum form keeps working too.
    assert model.setData(index, Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
    assert model.checked_count() == 1


def test_clicking_a_row_checks_it():
    """Clicking anywhere on a row toggles its checkbox (and enables download)."""
    from PyQt6.QtTest import QTest

    _app()
    window = MainWindow(SettingsService())
    window._model.set_tracks(
        [SubtitleTrack("es", SubtitleKind.AUTOMATIC, "Spanish", ["vtt"])]
    )
    window.show()
    _app().processEvents()

    view = window._table
    index = window._model.index(0, 1)  # the "Spanish" text cell
    rect = view.visualRect(index)
    QTest.mouseClick(
        view.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        rect.center(),
    )
    _app().processEvents()

    assert window._model.checked_count() == 1
    assert window._download_btn.isEnabled()

    # Clicking the row again unchecks it.
    QTest.mouseClick(
        view.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        rect.center(),
    )
    _app().processEvents()
    assert window._model.checked_count() == 0
    window.close()


def test_about_dialog_shows_author_links_and_big_icon():
    """The About dialog shows the author info, clickable links and a big logo."""
    from PyQt6.QtWidgets import QLabel, QTabWidget

    from youtube_subtitle_downloader.ui.about_dialog import AboutDialog

    _app()
    dialog = AboutDialog(SettingsService())
    tabs = dialog.findChild(QTabWidget)
    assert tabs is not None
    assert tabs.count() == 2  # About + System info

    about_widget = tabs.widget(0)
    labels = about_widget.findChildren(QLabel)

    icon_labels = [
        lbl
        for lbl in labels
        if lbl.pixmap() is not None and not lbl.pixmap().isNull()
    ]
    text_labels = [lbl for lbl in labels if lbl not in icon_labels]

    # The application logo is shown large on the left.
    assert len(icon_labels) == 1
    pixmap = icon_labels[0].pixmap()
    assert pixmap.width() >= 160 and pixmap.height() >= 160

    # Author, licence, contact, website and technologies are present.
    content = "".join(lbl.text() for lbl in text_labels)
    assert "© 2026 Washington Indacochea Delgado" in content
    assert "mailto:linuxfrontier@proton.me" in content
    assert "GPL-3.0-or-later" in content
    assert "https://github.com/wachin/youtube-subtitle-downloader" in content
    assert "Python 3" in content and "yt-dlp" in content

    # Email and website are real clickable links (open external apps).
    link_label = next(lbl for lbl in text_labels if lbl.openExternalLinks())
    assert link_label.textInteractionFlags() & (
        Qt.TextInteractionFlag.TextBrowserInteraction
    )
    dialog.close()


def test_tools_menu_has_update_check_action():
    """The Tools menu offers the manual 'Check for yt-dlp update' action."""
    _app()
    window = MainWindow(SettingsService())
    texts = [action.text() for action in window._tools_menu.actions()]
    assert any("yt-dlp update" in text for text in texts)
    window.close()


def test_clicking_the_checkbox_indicator_checks_it():
    """Direct clicks on the checkbox indicator toggle the state once."""
    from PyQt6.QtCore import QPoint
    from PyQt6.QtWidgets import QStyle, QStyleOptionViewItem
    from PyQt6.QtTest import QTest

    _app()
    window = MainWindow(SettingsService())
    window._model.set_tracks(
        [SubtitleTrack("es", SubtitleKind.AUTOMATIC, "Spanish", ["vtt"])]
    )
    window.show()
    _app().processEvents()

    view = window._table
    model = window._model
    index = model.index(0, 0)
    opt = QStyleOptionViewItem()
    opt.initFrom(view)
    opt.rect = view.visualRect(index)
    opt.checkState = model.data(index, Qt.ItemDataRole.CheckStateRole)
    opt.state |= QStyle.StateFlag.State_Enabled
    opt.features |= QStyleOptionViewItem.ViewItemFeature.HasCheckIndicator
    indicator = view.style().subElementRect(
        QStyle.SubElement.SE_ItemViewItemCheckIndicator, opt, view
    )
    QTest.mouseClick(
        view.viewport(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        indicator.center(),
    )
    _app().processEvents()

    assert model.checked_count() == 1
    assert window._download_btn.isEnabled()
    window.close()
