"""Data models for subtitle tracks and cues."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SubtitleKind(Enum):
    """Whether a subtitle track was provided by the creator or auto-generated."""

    MANUAL = "manual"
    AUTOMATIC = "automatic"

    @property
    def display_name(self) -> str:
        """Human readable name of the track kind."""
        return "Manual" if self is SubtitleKind.MANUAL else "Automatic"


#: Common language codes mapping to (English name, native name). yt-dlp usually
#: provides a "name"; these are only a fallback to make the table friendlier
#: and to let the search accept both English and native names.
_COMMON_LANGUAGES: dict[str, tuple[str, str]] = {
    "en": ("English", "English"),
    "es": ("Spanish", "Español"),
    "fr": ("French", "Français"),
    "de": ("German", "Deutsch"),
    "it": ("Italian", "Italiano"),
    "pt": ("Portuguese", "Português"),
    "pt-BR": ("Portuguese (Brazil)", "Português (Brasil)"),
    "pt-PT": ("Portuguese (Portugal)", "Português (Portugal)"),
    "ja": ("Japanese", "日本語"),
    "ko": ("Korean", "한국어"),
    "zh": ("Chinese", "中文"),
    "zh-Hans": ("Chinese (Simplified)", "简体中文"),
    "zh-Hant": ("Chinese (Traditional)", "繁體中文"),
    "ru": ("Russian", "Русский"),
    "ar": ("Arabic", "العربية"),
    "hi": ("Hindi", "हिन्दी"),
    "nl": ("Dutch", "Nederlands"),
    "pl": ("Polish", "Polski"),
    "tr": ("Turkish", "Türkçe"),
    "sv": ("Swedish", "Svenska"),
    "uk": ("Ukrainian", "Українська"),
    "vi": ("Vietnamese", "Tiếng Việt"),
}


def language_name(code: str, fallback: str | None = None) -> str:
    """Return a human readable name for a language code.

    The explicit ``fallback`` (usually yt-dlp's ``name`` field) wins when
    present; otherwise the most specific common mapping is used, then the
    base code, then the code itself.
    """
    if fallback and fallback.strip():
        return fallback.strip()
    for key, (english, _native) in _COMMON_LANGUAGES.items():
        if key.lower() == code.lower():
            return english
    base = code.split("-")[0].lower()
    for key, (english, _native) in _COMMON_LANGUAGES.items():
        if key.lower() == base:
            return english
    return code


def language_native_name(code: str) -> str:
    """Return the native name of a language code, if known."""
    for key, (_english, native) in _COMMON_LANGUAGES.items():
        if key.lower() == code.lower():
            return native
    base = code.split("-")[0].lower()
    for key, (_english, native) in _COMMON_LANGUAGES.items():
        if key.lower() == base:
            return native
    return code


def searchable_names(code: str) -> list[str]:
    """Names that should match the language search box."""
    names = [code, code.split("-")[0]]
    for key, (english, native) in _COMMON_LANGUAGES.items():
        if key.lower() == code.lower() or key.lower() == code.split("-")[0].lower():
            names.extend([english, native])
    return list(dict.fromkeys(names))


@dataclass
class SubtitleTrack:
    """A single subtitle track (one language, one type)."""

    language_code: str
    kind: SubtitleKind
    language_name: str = ""
    formats: list[str] = field(default_factory=list)
    url: str | None = None
    is_original: bool = False

    def __post_init__(self) -> None:
        if self.language_code.lower().endswith("-orig"):
            self.is_original = True
        if not self.language_name:
            self.language_name = language_name(self.base_code)

    @property
    def base_code(self) -> str:
        """Language code without the ``-orig`` suffix, e.g. ``es-orig`` -> ``es``."""
        code = self.language_code
        if code.lower().endswith("-orig"):
            code = code[: -len("-orig")]
        return code

    @property
    def display_name(self) -> str:
        """Name shown in the table, e.g. ``Spanish (Original)``."""
        name = self.language_name or self.language_code
        if self.is_original:
            return f"{name} (Original)"
        return name

    def matches(self, other: "SubtitleTrack") -> bool:
        """True when both tracks refer to the same language and kind."""
        return (
            self.base_code.lower() == other.base_code.lower()
            and self.kind is other.kind
        )


@dataclass
class SubtitleCue:
    """One subtitle entry with timing and text lines (tags stripped)."""

    start: float  # seconds
    end: float  # seconds
    lines: list[str]

    @property
    def text(self) -> str:
        """The cue text joined into a single line."""
        return " ".join(line.strip() for line in self.lines if line.strip())
