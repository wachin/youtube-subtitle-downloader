"""Tests for the translation catalogs (roadmap section 36)."""

import os

import pytest  # noqa: E402

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


def test_every_available_language_has_a_catalog() -> None:
    for code in i18n_mod.AVAILABLE_LANGUAGES:
        if code == "en":
            continue  # English is the source language, no catalog needed.
        assert (
            translations_dir() / f"youtube_subtitle_downloader_{code}.qm"
        ).is_file(), f"missing catalog for {code}"


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
    install_translator(app, "xx")  # no catalog: stays in English
    assert QCoreApplication.translate("MainWindow", "Analyze") == "Analyze"


# -- every bundled translation spot-checked -------------------------------

#: language code -> expected translation of "Analyze", "Close" and the
#: About-dialog "License" row (added with the author info redesign).
LICENSE_SOURCE = "<p><b>License:</b> GPL-3.0-or-later</p>"
CATALOG_SPOT_CHECKS: dict[str, tuple[str, str, str]] = {
    "es": ("Analizar", "Cerrar", "<p><b>Licencia:</b> GPL-3.0-or-later</p>"),
    "de": ("Analysieren", "Schließen", "<p><b>Lizenz:</b> GPL-3.0-or-later</p>"),
    "fr": ("Analyser", "Fermer", "<p><b>Licence :</b> GPL-3.0-or-later</p>"),
    "ja": ("解析", "閉じる", "<p><b>ライセンス:</b> GPL-3.0-or-later</p>"),
    "ko": ("분석", "닫기", "<p><b>라이선스:</b> GPL-3.0-or-later</p>"),
    "pt_BR": ("Analisar", "Fechar", "<p><b>Licença:</b> GPL-3.0-or-later</p>"),
    "ru": ("Анализировать", "Закрыть", "<p><b>Лицензия:</b> GPL-3.0-or-later</p>"),
    "zh_CN": ("分析", "关闭", "<p><b>许可证：</b> GPL-3.0-or-later</p>"),
    "zh_TW": ("分析", "關閉", "<p><b>授權條款：</b> GPL-3.0-or-later</p>"),
}


@pytest.mark.parametrize("code", sorted(CATALOG_SPOT_CHECKS))
def test_catalog_translation_applies(code: str) -> None:
    analyze, close, license_row = CATALOG_SPOT_CHECKS[code]
    app = _app()
    install_translator(app, code)
    try:
        assert (
            QCoreApplication.translate("MainWindow", "Analyze") == analyze
        ), f"Analyze not translated in {code}"
        assert (
            QCoreApplication.translate("AboutDialog", "Close") == close
        ), f"Close not translated in {code}"
        assert (
            QCoreApplication.translate("AboutDialog", LICENSE_SOURCE) == license_row
        ), f"About License row not translated in {code}"
    finally:
        install_translator(app, "en")


# -- system language detection -------------------------------------------


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
            lambda: QLocale(QLocale.Language.Greek, QLocale.Country.Greece)
        ),
    )
    assert system_language() == "en"


def test_system_language_full_code_brazilian_portuguese(monkeypatch) -> None:
    monkeypatch.setattr(
        i18n_mod.QLocale,
        "system",
        staticmethod(
            lambda: QLocale(QLocale.Language.Portuguese, QLocale.Country.Brazil)
        ),
    )
    assert system_language() == "pt_BR"


def test_system_language_full_code_chinese_simplified(monkeypatch) -> None:
    monkeypatch.setattr(
        i18n_mod.QLocale,
        "system",
        staticmethod(
            lambda: QLocale(QLocale.Language.Chinese, QLocale.Country.China)
        ),
    )
    assert system_language() == "zh_CN"


def test_system_language_full_code_chinese_traditional(monkeypatch) -> None:
    monkeypatch.setattr(
        i18n_mod.QLocale,
        "system",
        staticmethod(
            lambda: QLocale(QLocale.Language.Chinese, QLocale.Country.Taiwan)
        ),
    )
    assert system_language() == "zh_TW"


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
