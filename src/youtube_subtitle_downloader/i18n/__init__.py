"""Internationalization support.

English is the primary language of the application (roadmap section 36):
the whole program is written in English and translations (Spanish first)
are added afterwards with Qt Linguist (``.ts`` / ``.qm`` files).
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QLibraryInfo, QTranslator

#: Language code -> display name (native).
AVAILABLE_LANGUAGES: dict[str, str] = {
    "en": "English",
    "es": "Español",
}


def translations_dir() -> Path:
    """Directory where packaged ``.qm`` files live."""
    return Path(__file__).resolve().parent.parent / "resources" / "translations"


def install_translator(app, language: str = "en") -> None:
    """Install Qt base + application translators for ``language``.

    ``en`` is the default language: nothing is loaded in that case.
    """
    if not language or language == "en":
        return

    qt_base = QTranslator(app)
    qt_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if qt_base.load(f"qtbase_{language}", qt_path):
        app.installTranslator(qt_base)

    app_translator = QTranslator(app)
    qm_file = translations_dir() / f"youtube_subtitle_downloader_{language}.qm"
    if qm_file.is_file() and app_translator.load(str(qm_file)):
        app.installTranslator(app_translator)
