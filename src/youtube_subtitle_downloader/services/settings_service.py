"""Persistent application settings (QSettings) and optional history."""

from __future__ import annotations

import json
from typing import Any

from PyQt6.QtCore import QSettings

from ..utils.filenames import DEFAULT_TEMPLATE
from ..utils.paths import default_download_dir, ensure_dirs, history_file

HISTORY_LIMIT = 100


class SettingsService:
    """Thin wrapper around ``QSettings`` plus the JSON history store."""

    def __init__(self) -> None:
        self._settings = QSettings()
        self._settings.setFallbacksEnabled(False)
        ensure_dirs()

    # -- generic -----------------------------------------------------------
    def value(self, key: str, default: Any = None, type=None) -> Any:
        if type is None:
            return self._settings.value(key, default)
        return self._settings.value(key, default, type)

    def set_value(self, key: str, value: Any) -> None:
        self._settings.setValue(key, value)

    def sync(self) -> None:
        self._settings.sync()

    # -- general -----------------------------------------------------------
    def language(self) -> str:
        return str(self.value("general/language", "en"))

    def set_language(self, language: str) -> None:
        self.set_value("general/language", language)

    def preferred_language(self) -> str:
        return str(self.value("general/preferred_language", ""))

    def set_preferred_language(self, code: str) -> None:
        self.set_value("general/preferred_language", code)

    def auto_analyze_after_paste(self) -> bool:
        return bool(self.value("general/auto_analyze_after_paste", False, type=bool))

    def set_auto_analyze_after_paste(self, enabled: bool) -> None:
        self.set_value("general/auto_analyze_after_paste", enabled)

    def notify_on_finish(self) -> bool:
        return bool(self.value("general/notify_on_finish", True, type=bool))

    def set_notify_on_finish(self, enabled: bool) -> None:
        self.set_value("general/notify_on_finish", enabled)

    # -- YouTube / cookies -------------------------------------------------
    def cookies_browser(self) -> str:
        return str(self.value("youtube/cookies_browser", ""))

    def set_cookies_browser(self, browser: str) -> None:
        self.set_value("youtube/cookies_browser", browser)

    def cookies_file(self) -> str:
        return str(self.value("youtube/cookies_file", ""))

    def set_cookies_file(self, path: str) -> None:
        self.set_value("youtube/cookies_file", path)

    # -- output ------------------------------------------------------------
    def output_dir(self) -> str:
        return str(self.value("output/dir", str(default_download_dir())))

    def set_output_dir(self, path: str) -> None:
        self.set_value("output/dir", path)

    def subtitle_format(self) -> str:
        return str(self.value("output/format", "srt"))

    def set_subtitle_format(self, fmt: str) -> None:
        self.set_value("output/format", fmt)

    def txt_enabled(self) -> bool:
        return bool(self.value("output/txt_enabled", True, type=bool))

    def set_txt_enabled(self, enabled: bool) -> None:
        self.set_value("output/txt_enabled", enabled)

    def txt_mode(self) -> str:
        return str(self.value("output/txt_mode", "continuous"))

    def set_txt_mode(self, mode: str) -> None:
        self.set_value("output/txt_mode", mode)

    def filename_template(self) -> str:
        return str(self.value("output/template", DEFAULT_TEMPLATE))

    def set_filename_template(self, template: str) -> None:
        self.set_value("output/template", template)

    # -- privacy -----------------------------------------------------------
    def history_enabled(self) -> bool:
        return bool(self.value("privacy/history_enabled", True, type=bool))

    def set_history_enabled(self, enabled: bool) -> None:
        self.set_value("privacy/history_enabled", enabled)

    # -- window ------------------------------------------------------------
    def window_geometry(self) -> Any:
        return self.value("window/geometry")

    def window_state(self) -> Any:
        return self.value("window/state")

    def set_window_geometry(self, value: Any) -> None:
        self.set_value("window/geometry", value)

    def set_window_state(self, value: Any) -> None:
        self.set_value("window/state", value)

    # -- history -----------------------------------------------------------
    def _history_items(self) -> list[dict]:
        path = history_file()
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def _save_history_items(self, items: list[dict]) -> None:
        history_file().write_text(
            json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def history(self) -> list[dict]:
        return self._history_items()

    def add_history(self, entry: dict) -> None:
        """Prepend an entry and cap the history size."""
        items = self._history_items()
        items.insert(0, entry)
        self._save_history_items(items[:HISTORY_LIMIT])

    def remove_history(self, index: int) -> None:
        items = self._history_items()
        if 0 <= index < len(items):
            items.pop(index)
            self._save_history_items(items)

    def clear_history(self) -> None:
        self._save_history_items([])
