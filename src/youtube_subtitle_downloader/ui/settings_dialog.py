"""Settings dialog (General, YouTube, Output, Privacy)."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..services.settings_service import SettingsService
from ..utils.filenames import PRESET_TEMPLATES

FORMATS = [("SRT", "srt"), ("VTT", "vtt"), ("TTML", "ttml"), ("JSON3", "json3"), ("Original", "original")]
TXT_MODES = [("Continuous text", "continuous"), ("Paragraphs", "paragraphs"), ("One line per subtitle", "lines")]
BROWSERS = ["", "Firefox", "Chromium", "Chrome", "Brave", "Edge"]
LANGUAGES = [("English", "en"), ("Español (planned)", "es")]
PREFERRED = ["", "en", "es", "fr", "de", "it", "pt", "pt-BR", "pt-PT", "ja", "zh", "zh-Hans", "zh-Hant", "ru"]


class SettingsDialog(QDialog):
    """Application settings dialog backed by SettingsService."""

    def __init__(self, settings: SettingsService, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("Settings")
        self.resize(520, 380)

        tabs = QTabWidget(self)
        tabs.addTab(self._general_tab(), "General")
        tabs.addTab(self._youtube_tab(), "YouTube")
        tabs.addTab(self._output_tab(), "Output")
        tabs.addTab(self._privacy_tab(), "Privacy")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs, 1)
        layout.addWidget(buttons)

        self._load_values()

    # -- tabs -------------------------------------------------------------
    def _general_tab(self) -> QWidget:
        widget = QWidget(self)
        form = QFormLayout(widget)

        self._language_combo = QComboBox(widget)
        for name, code in LANGUAGES:
            self._language_combo.addItem(name, code)

        self._preferred_combo = QComboBox(widget)
        self._preferred_combo.addItem("Default (none)", "")
        for code in PREFERRED[1:]:
            self._preferred_combo.addItem(code, code)

        self._auto_paste_check = QCheckBox(
            "Analyze automatically after pasting a URL", widget
        )
        form.addRow("Language:", self._language_combo)
        form.addRow("Preferred subtitle language:", self._preferred_combo)
        form.addRow("", self._auto_paste_check)
        return widget

    def _youtube_tab(self) -> QWidget:
        widget = QWidget(self)
        form = QFormLayout(widget)

        self._browser_combo = QComboBox(widget)
        for name in BROWSERS:
            self._browser_combo.addItem(name or "None", name)

        cookie_row = QHBoxLayout()
        self._cookies_file_edit = QLineEdit(widget)
        self._cookies_file_edit.setReadOnly(True)
        browse_button = QPushButton("Browse…", widget)
        browse_button.clicked.connect(self._browse_cookies)
        cookie_row.addWidget(self._cookies_file_edit, 1)
        cookie_row.addWidget(browse_button)

        form.addRow("Cookies from browser:", self._browser_combo)
        form.addRow("Cookies file:", cookie_row)
        note = QLabel(
            "Cookies are only used through yt-dlp; their content is never read "
            "or stored by this application."
        )
        note.setWordWrap(True)
        form.addRow("", note)
        return widget

    def _output_tab(self) -> QWidget:
        widget = QWidget(self)
        form = QFormLayout(widget)

        self._format_combo = QComboBox(widget)
        for name, code in FORMATS:
            self._format_combo.addItem(name, code)

        self._txt_check = QCheckBox("Also create a clean TXT file", widget)

        self._txt_mode_combo = QComboBox(widget)
        for name, code in TXT_MODES:
            self._txt_mode_combo.addItem(name, code)

        self._template_combo = QComboBox(widget)
        self._template_combo.setEditable(True)
        for name, template in PRESET_TEMPLATES.items():
            self._template_combo.addItem(f"{name}  →  {template}", template)
        self._template_combo.addItem("Custom", None)

        form.addRow("Default format:", self._format_combo)
        form.addRow("", self._txt_check)
        form.addRow("TXT mode:", self._txt_mode_combo)
        form.addRow("File name template:", self._template_combo)
        return widget

    def _privacy_tab(self) -> QWidget:
        widget = QWidget(self)
        form = QFormLayout(widget)
        self._history_check = QCheckBox(
            "Save a history of processed videos (dates, titles and URLs)", widget
        )
        form.addRow("", self._history_check)
        note = QLabel(
            "History is stored locally in the user data folder and can be "
            "cleared at any time from the File → History dialog."
        )
        note.setWordWrap(True)
        form.addRow("", note)
        return widget

    # -- load / save ------------------------------------------------------
    def _load_values(self) -> None:
        settings = self._settings
        self._set_combo_data(self._language_combo, settings.language())
        self._set_combo_data(self._preferred_combo, settings.preferred_language())
        self._auto_paste_check.setChecked(settings.auto_analyze_after_paste())
        self._set_combo_data(self._browser_combo, settings.cookies_browser())
        self._cookies_file_edit.setText(settings.cookies_file())
        self._set_combo_data(self._format_combo, settings.subtitle_format())
        self._txt_check.setChecked(settings.txt_enabled())
        self._set_combo_data(self._txt_mode_combo, settings.txt_mode())
        template = settings.filename_template()
        index = self._template_combo.findData(template)
        if index >= 0:
            self._template_combo.setCurrentIndex(index)
        else:
            self._template_combo.setCurrentIndex(
                self._template_combo.count() - 1
            )  # Custom
            self._template_combo.setEditText(template)

    def accept(self) -> None:  # noqa: D102 - overridden to persist
        settings = self._settings
        settings.set_language(self._language_combo.currentData())
        settings.set_preferred_language(self._preferred_combo.currentData())
        settings.set_auto_analyze_after_paste(self._auto_paste_check.isChecked())
        settings.set_cookies_browser(self._browser_combo.currentData())
        settings.set_cookies_file(self._cookies_file_edit.text().strip())
        settings.set_subtitle_format(self._format_combo.currentData())
        settings.set_txt_enabled(self._txt_check.isChecked())
        settings.set_txt_mode(self._txt_mode_combo.currentData())
        settings.set_filename_template(
            self._template_combo.currentText().strip()
            or self._template_combo.itemData(self._template_combo.currentIndex())
            or "%(title)s [%(id)s].%(language)s.%(ext)s"
        )
        settings.set_history_enabled(self._history_check.isChecked())
        settings.sync()
        super().accept()

    # -- helpers ----------------------------------------------------------
    def _set_combo_data(self, combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _browse_cookies(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select cookies file", "", "Cookies (*.txt);;All files (*)"
        )
        if path:
            self._cookies_file_edit.setText(path)
