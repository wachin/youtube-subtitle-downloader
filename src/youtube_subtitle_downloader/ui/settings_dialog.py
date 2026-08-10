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

from ..i18n import AVAILABLE_LANGUAGES
from ..services.settings_service import SettingsService
from ..utils.filenames import PRESET_TEMPLATES

FORMATS = [("SRT", "srt"), ("VTT", "vtt"), ("TTML", "ttml"), ("JSON3", "json3"), ("Original", "original")]
BROWSERS = ["", "Firefox", "Chromium", "Chrome", "Brave", "Edge"]
#: UI languages offered in the settings dialog. Single source of truth is
#: ``AVAILABLE_LANGUAGES`` in the i18n module (name, code) pairs.
LANGUAGES = list(AVAILABLE_LANGUAGES.items())
PREFERRED = ["", "en", "es", "fr", "de", "it", "pt", "pt-BR", "pt-PT", "ja", "zh", "zh-Hans", "zh-Hant", "ru"]


class SettingsDialog(QDialog):
    """Application settings dialog backed by SettingsService."""

    def __init__(self, settings: SettingsService, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle(self.tr("Settings"))
        self.resize(520, 380)

        tabs = QTabWidget(self)
        tabs.addTab(self._general_tab(), self.tr("General"))
        tabs.addTab(self._youtube_tab(), self.tr("YouTube"))
        tabs.addTab(self._output_tab(), self.tr("Output"))
        tabs.addTab(self._privacy_tab(), self.tr("Privacy"))

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
            self.tr("Analyze automatically after pasting a URL"), widget
        )
        self._notify_check = QCheckBox(
            self.tr(
                "Show a desktop notification when a download finishes and "
                "the window is not active"
            ),
            widget,
        )
        form.addRow(self.tr("Language:"), self._language_combo)
        form.addRow(self.tr("Preferred subtitle language:"), self._preferred_combo)
        form.addRow("", self._auto_paste_check)
        form.addRow("", self._notify_check)
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
        browse_button = QPushButton(self.tr("Browse…"), widget)
        browse_button.clicked.connect(self._browse_cookies)
        cookie_row.addWidget(self._cookies_file_edit, 1)
        cookie_row.addWidget(browse_button)

        form.addRow(self.tr("Cookies from browser:"), self._browser_combo)
        form.addRow(self.tr("Cookies file:"), cookie_row)
        note = QLabel(
            self.tr(
                "Cookies are only used through yt-dlp; their content is never read "
                "or stored by this application."
            )
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

        self._txt_check = QCheckBox(self.tr("Also create a clean TXT file"), widget)

        self._txt_mode_combo = QComboBox(widget)
        self._txt_mode_combo.addItem(self.tr("Continuous text"), "continuous")
        self._txt_mode_combo.addItem(self.tr("Paragraphs"), "paragraphs")
        self._txt_mode_combo.addItem(self.tr("One line per subtitle"), "lines")

        self._template_combo = QComboBox(widget)
        self._template_combo.setEditable(True)
        presets = PRESET_TEMPLATES
        self._template_combo.addItem(
            f"{self.tr('Title - Language')}  →  {presets['Title - Language']}",
            presets["Title - Language"],
        )
        self._template_combo.addItem(
            f"{self.tr('Title [ID] - Language')}  →  {presets['Title [ID] - Language']}",
            presets["Title [ID] - Language"],
        )
        self._template_combo.addItem(
            f"{self.tr('ID - Language')}  →  {presets['ID - Language']}",
            presets["ID - Language"],
        )
        self._template_combo.addItem(self.tr("Custom"), None)

        form.addRow(self.tr("Default format:"), self._format_combo)
        form.addRow("", self._txt_check)
        form.addRow(self.tr("TXT mode:"), self._txt_mode_combo)
        form.addRow(self.tr("File name template:"), self._template_combo)
        return widget

    def _privacy_tab(self) -> QWidget:
        widget = QWidget(self)
        form = QFormLayout(widget)
        self._history_check = QCheckBox(
            self.tr("Save a history of processed videos (dates, titles and URLs)"),
            widget,
        )
        form.addRow("", self._history_check)
        note = QLabel(
            self.tr(
                "History is stored locally in the user data folder and can be "
                "cleared at any time from the File → History dialog."
            )
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
        self._notify_check.setChecked(settings.notify_on_finish())
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
        settings.set_notify_on_finish(self._notify_check.isChecked())
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
            self,
            self.tr("Select cookies file"),
            "",
            self.tr("Cookies (*.txt);;All files (*)"),
        )
        if path:
            self._cookies_file_edit.setText(path)
