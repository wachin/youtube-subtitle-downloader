"""Tests for the Spanish translation catalog (roadmap section 36)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QCoreApplication  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from youtube_subtitle_downloader.i18n import install_translator, translations_dir  # noqa: E402

_APP: QApplication | None = None


def _app() -> QApplication:
    global _APP
    if _APP is None:
        _APP = QApplication.instance() or QApplication([])
        _APP.setApplicationName("youtube-subtitle-downloader-tests")
        _APP.setOrganizationName("youtube-subtitle-downloader-tests")
    return _APP


def test_spanish_catalog_exists() -> None:
    assert (translations_dir() / "youtube_subtitle_downloader_es.qm").is_file()


def test_spanish_translation_applies() -> None:
    app = _app()
    install_translator(app, "es")
    try:
        assert QCoreApplication.translate("MainWindow", "Analyze") == "Analizar"
        assert (
            QCoreApplication.translate("MainWindow", "Download selected")
            == "Descargar seleccionados"
        )
        assert (
            QCoreApplication.translate("SettingsDialog", "Language:") == "Idioma:"
        )
        assert (
            QCoreApplication.translate("PreviewDialog", "Copy clean text")
            == "Copiar texto limpio"
        )
    finally:
        install_translator(app, "en")


def test_english_is_default() -> None:
    app = _app()
    install_translator(app, "en")
    assert QCoreApplication.translate("MainWindow", "Analyze") == "Analyze"


def test_unknown_language_falls_back_to_english() -> None:
    app = _app()
    install_translator(app, "fr")  # no catalog: stays in English
    assert QCoreApplication.translate("MainWindow", "Analyze") == "Analyze"
