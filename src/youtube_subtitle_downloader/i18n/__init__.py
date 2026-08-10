"""Internationalization support.

English is the primary language of the application (roadmap section 36):
the whole program is written in English and translations (Spanish first)
are added with Qt Linguist (``.ts`` / ``.qm`` files).
"""

from __future__ import annotations

import re
from pathlib import Path

from PyQt6.QtCore import QCoreApplication, QLibraryInfo, QLocale, QTranslator

#: Language code -> display name (native).
AVAILABLE_LANGUAGES: dict[str, str] = {
    "en": "English",
    "es": "Español",
    "de": "Deutsch",
    "fr": "Français",
    "ja": "日本語",
    "ko": "한국어",
    "pt_BR": "Português (Brasil)",
    "ru": "Русский",
    "zh_CN": "简体中文",
    "zh_TW": "繁體中文",
}

#: Attribute used to remember the installed translators so they can be
#: replaced when the user switches the language at runtime.
_TRANSLATOR_ATTR = "_youtube_subtitle_translators"


def translations_dir() -> Path:
    """Directory where packaged ``.qm`` files live."""
    return Path(__file__).resolve().parent.parent / "resources" / "translations"


def system_language() -> str:
    """Best supported language for the current system locale.

    The system UI language preferences are honoured (on Linux these come
    from ``LANGUAGE``/``LANG``). The first supported language is used and
    ``en`` is returned when none of the supported languages matches, so the
    application always opens in a language it can actually display.
    """
    locale = QLocale.system()
    for tag in locale.uiLanguages():
        code = tag.replace("-", "_")
        # Prefer the full code (e.g. ``pt_BR``, ``zh_CN``) and fall back to
        # the bare language part (e.g. ``es`` from ``es_EC``).
        if code in AVAILABLE_LANGUAGES:
            return code
        base = code.split("_")[0].lower()
        if base in AVAILABLE_LANGUAGES:
            return base
    return "en"


def translate_args(text: str, *values) -> str:
    """Replace Qt ``%1``/``%2``… placeholders with ``values``.

    PyQt6's ``tr()`` returns a plain ``str`` (QString.arg() does not exist), so
    the classic ``tr("...%1").arg(x)`` idiom does not work. This helper keeps
    the ``%N`` placeholders that Qt Linguist understands in the source/ts
    files and substitutes them in Python with a single pass (values that
    themselves contain ``%N`` are not re-processed).
    """

    def _replace(match: "re.Match[str]") -> str:
        index = int(match.group(1)) - 1
        if 0 <= index < len(values):
            return str(values[index])
        return match.group(0)

    return re.sub(r"%(\d+)", _replace, text)


def kind_display_name(kind: str) -> str:
    """Translated display name of a subtitle kind (``manual``/``automatic``)."""
    if kind == "manual":
        return QCoreApplication.translate("SubtitleKind", "Manual")
    return QCoreApplication.translate("SubtitleKind", "Automatic")


def install_translator(app, language: str = "en") -> None:
    """Install Qt base + application translators for ``language``.

    ``en`` is the default language: nothing is loaded in that case.
    Calling this again with another language replaces any previously
    installed translators, so it can be used to switch the language at
    runtime without restarting the application.
    """
    # Remove any previously installed translators (language switch).
    for translator in getattr(app, _TRANSLATOR_ATTR, []):
        app.removeTranslator(translator)
        translator.deleteLater()
    setattr(app, _TRANSLATOR_ATTR, [])

    if not language or language == "en":
        return

    translators: list[QTranslator] = []

    qt_base = QTranslator(app)
    qt_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if qt_base.load(f"qtbase_{language}", qt_path):
        app.installTranslator(qt_base)
        translators.append(qt_base)

    app_translator = QTranslator(app)
    qm_file = translations_dir() / f"youtube_subtitle_downloader_{language}.qm"
    if qm_file.is_file() and app_translator.load(str(qm_file)):
        app.installTranslator(app_translator)
        translators.append(app_translator)

    setattr(app, _TRANSLATOR_ATTR, translators)
