"""Tests for the Spanish translation catalog (roadmap section 36)."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QCoreApplication, QLocale  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

import youtube_subtitle_downloader.i18n as i18n_mod  # noqa: E402
from youtube_subtitle_downloader.i18n import (  # noqa: E402
    install_translator,
    system_language,
    translations_dir,
)
from youtube_subtitle_downloader.services.settings_service import (  # noqa: E402
    SettingsService,
)

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


# -- system language detection -------------------------------------------


def test_system_language_spanish(monkeypatch) -> None:
    monkeypatch.setattr(
        i18n_mod.QLocale,
        "system",
        staticmethod(
            lambda: QLocale(QLocale.Language.Spanish, QLocale.Country.Ecuador)
        ),
    )
    assert system_language() == "es"


def test_system_language_english(monkeypatch) -> None:
    monkeypatch.setattr(
        i18n_mod.QLocale,
        "system",
        staticmethod(
            lambda: QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)
        ),
    )
    assert system_language() == "en"


def test_system_language_unsupported_falls_back_to_english(monkeypatch) -> None:
    monkeypatch.setattr(
        i18n_mod.QLocale,
        "system",
        staticmethod(
            lambda: QLocale(QLocale.Language.French, QLocale.Country.France)
        ),
    )
    assert system_language() == "en"


def test_settings_language_follows_system_when_unset(monkeypatch) -> None:
    _app()
    settings = SettingsService()
    settings._settings.remove("general/language")
    monkeypatch.setattr(
        i18n_mod.QLocale,
        "system",
        staticmethod(
            lambda: QLocale(QLocale.Language.Spanish, QLocale.Country.Spain)
        ),
    )
    try:
        assert settings.language() == "es"
    finally:
        settings._settings.remove("general/language")


def test_settings_stored_language_wins_over_system(monkeypatch) -> None:
    _app()
    settings = SettingsService()
    settings._settings.setValue("general/language", "en")
    monkeypatch.setattr(
        i18n_mod.QLocale,
        "system",
        staticmethod(
            lambda: QLocale(QLocale.Language.Spanish, QLocale.Country.Spain)
        ),
    )
    try:
        assert settings.language() == "en"
    finally:
        settings._settings.remove("general/language")
