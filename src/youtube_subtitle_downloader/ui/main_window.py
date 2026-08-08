"""Main application window."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QAction, QDesktopServices, QKeySequence, QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTableView,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import __app_name__, __version__
from ..i18n import translate_args
from ..models.subtitle import SubtitleKind
from ..models.video import PlaylistEntry, VideoInfo
from ..services.settings_service import SettingsService
from ..services.ytdlp_service import YtDlpService, is_youtube_url
from ..utils.filenames import DEFAULT_TEMPLATE, PRESET_TEMPLATES
from ..utils.icons import APP_ICON_NAME, theme_icon
from ..utils.logging import get_logger
from ..utils.notifications import send_notification
from ..utils.paths import default_download_dir
from ..workers.download_worker import DownloadWorker
from ..workers.video_info_worker import PlaylistWorker, VideoInfoWorker
from .about_dialog import AboutDialog
from .download_complete_dialog import DownloadCompleteDialog
from .history_dialog import HistoryDialog
from .playlist_dialog import PlaylistDialog
from .preview_dialog import PreviewDialog
from .settings_dialog import SettingsDialog
from .subtitle_table_model import SubtitleTableModel

log = get_logger()

FORMATS = [("SRT", "srt"), ("VTT", "vtt"), ("TTML", "ttml"), ("JSON3", "json3"), ("Original", "original")]


class MainWindow(QMainWindow):
    """Main window implementing the roadmap flow."""

    def __init__(self, settings: SettingsService, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._video: VideoInfo | None = None
        self._worker = None
        self._pending_playlist_entries: list[PlaylistEntry] = []
        self._thumbnail_reply: QNetworkReply | None = None
        self._language = settings.language()

        self.setWindowTitle(__app_name__)
        self.setWindowIcon(theme_icon(APP_ICON_NAME))
        self.resize(860, 640)

        self._network = QNetworkAccessManager(self)
        self._network.finished.connect(self._on_thumbnail_loaded)

        self._build_ui()
        self._build_menus()
        self._build_shortcuts()
        self.setAcceptDrops(True)
        self._restore_window_state()
        self._apply_texts()
        self._apply_settings_to_ui()
        self._update_state()
        self._check_environment()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget(self)
        root = QVBoxLayout(central)

        # URL row
        url_row = QHBoxLayout()
        self._url_label = QLabel(central)
        url_row.addWidget(self._url_label)
        self._url_edit = QLineEdit(central)
        self._url_edit.setClearButtonEnabled(True)
        self._url_edit.returnPressed.connect(self._analyze)
        url_row.addWidget(self._url_edit, 1)
        self._paste_btn = QPushButton(central)
        self._paste_btn.setIcon(theme_icon("edit-paste"))
        self._paste_btn.clicked.connect(self._paste_url)
        url_row.addWidget(self._paste_btn)
        self._analyze_btn = QPushButton(central)
        self._analyze_btn.setIcon(theme_icon("system-search"))
        self._analyze_btn.setDefault(True)
        self._analyze_btn.clicked.connect(self._analyze)
        url_row.addWidget(self._analyze_btn)
        root.addLayout(url_row)

        # Video info
        info_row = QHBoxLayout()
        self._thumb_label = QLabel(central)
        self._thumb_label.setFixedSize(160, 90)
        self._thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb_label.setStyleSheet("background: rgba(0,0,0,0.06); border-radius: 4px;")
        info_row.addWidget(self._thumb_label)
        info_col = QVBoxLayout()
        self._title_label = QLabel(central)
        self._title_label.setWordWrap(True)
        self._title_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._channel_label = QLabel(central)
        self._channel_label.setStyleSheet("font-weight: bold;")
        self._meta_label = QLabel(central)
        self._meta_label.setStyleSheet("color: gray;")
        info_col.addWidget(self._title_label)
        info_col.addWidget(self._channel_label)
        info_col.addWidget(self._meta_label)
        info_col.addStretch(1)
        info_row.addLayout(info_col, 1)
        root.addLayout(info_row)

        # Search / filter
        filter_row = QHBoxLayout()
        self._search_label = QLabel(central)
        filter_row.addWidget(self._search_label)
        self._search_edit = QLineEdit(central)
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self._search_edit, 1)
        self._select_all_btn = QPushButton(central)
        self._select_all_btn.setIcon(theme_icon("edit-select-all"))
        self._select_all_btn.clicked.connect(lambda: self._model.check_all(True))
        self._select_none_btn = QPushButton(central)
        self._select_none_btn.setIcon(theme_icon("edit-select-none"))
        self._select_none_btn.clicked.connect(lambda: self._model.check_all(False))
        self._select_manual_btn = QPushButton(central)
        self._select_manual_btn.clicked.connect(
            lambda: self._model.check_kind(SubtitleKind.MANUAL, True)
        )
        self._select_auto_btn = QPushButton(central)
        self._select_auto_btn.clicked.connect(
            lambda: self._model.check_kind(SubtitleKind.AUTOMATIC, True)
        )
        for button in (
            self._select_all_btn,
            self._select_none_btn,
            self._select_manual_btn,
            self._select_auto_btn,
        ):
            filter_row.addWidget(button)
        root.addLayout(filter_row)

        # Tabs + table
        self._tabs = QTabWidget(central)
        self._tab_all = QWidget(central)
        self._tab_manual = QWidget(central)
        self._tab_auto = QWidget(central)
        self._tabs.addTab(self._tab_all, "")
        self._tabs.addTab(self._tab_manual, "")
        self._tabs.addTab(self._tab_auto, "")
        self._tabs.currentChanged.connect(self._on_tab_changed)
        root.addWidget(self._tabs)

        self._model = SubtitleTableModel(self)
        self._model.checked_changed.connect(self._on_checked_changed)
        self._table = QTableView(central)
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setColumnWidth(0, 34)
        self._table.setColumnWidth(2, 90)
        self._table.setColumnWidth(3, 110)
        self._table.setColumnWidth(4, 180)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.clicked.connect(self._on_table_clicked)
        self._table.doubleClicked.connect(self._on_table_double_clicked)
        root.addWidget(self._table, 1)

        # Options
        self._options_box = QGroupBox(central)
        opt_layout = QVBoxLayout(self._options_box)
        row1 = QHBoxLayout()
        self._format_label = QLabel(self._options_box)
        row1.addWidget(self._format_label)
        self._format_combo = QComboBox(self._options_box)
        for name, code in FORMATS:
            self._format_combo.addItem(name, code)
        row1.addWidget(self._format_combo)
        self._txt_check = QCheckBox(self._options_box)
        row1.addWidget(self._txt_check)
        self._txt_mode_label = QLabel(self._options_box)
        row1.addWidget(self._txt_mode_label)
        self._txt_mode_combo = QComboBox(self._options_box)
        # Translated items are (re)built in _apply_texts().
        row1.addWidget(self._txt_mode_combo)
        row1.addStretch(1)
        opt_layout.addLayout(row1)

        row2 = QHBoxLayout()
        self._dir_label = QLabel(self._options_box)
        row2.addWidget(self._dir_label)
        self._dir_edit = QLineEdit(self._options_box)
        row2.addWidget(self._dir_edit, 1)
        self._browse_btn = QPushButton(self._options_box)
        self._browse_btn.setIcon(theme_icon("folder-open"))
        self._browse_btn.clicked.connect(self._browse_output_dir)
        row2.addWidget(self._browse_btn)
        self._template_label = QLabel(self._options_box)
        row2.addWidget(self._template_label)
        self._template_combo = QComboBox(self._options_box)
        self._template_combo.setEditable(True)
        # Translated items are (re)built in _apply_texts().
        row2.addWidget(self._template_combo, 1)
        opt_layout.addLayout(row2)
        root.addWidget(self._options_box)

        # Progress + action buttons
        action_row = QHBoxLayout()
        self._preview_btn = QPushButton(central)
        self._preview_btn.setIcon(theme_icon("document-preview"))
        self._preview_btn.clicked.connect(self._open_preview)
        action_row.addWidget(self._preview_btn)
        action_row.addStretch(1)
        self._cancel_btn = QPushButton(central)
        self._cancel_btn.setIcon(theme_icon("process-stop"))
        self._cancel_btn.clicked.connect(self._cancel_current)
        self._cancel_btn.setEnabled(False)
        action_row.addWidget(self._cancel_btn)
        self._download_btn = QPushButton(central)
        self._download_btn.setIcon(theme_icon("go-down"))
        self._download_btn.clicked.connect(self._download)
        action_row.addWidget(self._download_btn)
        root.addLayout(action_row)

        self._progress = QProgressBar(central)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        # Log panel
        log_header = QHBoxLayout()
        self._log_toggle = QToolButton(central)
        self._log_toggle.setIcon(theme_icon("view-list-details"))
        self._log_toggle.setCheckable(True)
        self._log_toggle.setChecked(False)
        self._log_toggle.toggled.connect(self._toggle_log)
        self._copy_log_btn = QPushButton(central)
        self._copy_log_btn.setIcon(theme_icon("edit-copy"))
        self._copy_log_btn.clicked.connect(self._copy_log)
        self._clear_log_btn = QPushButton(central)
        self._clear_log_btn.setIcon(theme_icon("edit-clear-all"))
        self._clear_log_btn.clicked.connect(lambda: self._log_edit.clear())
        log_header.addWidget(self._log_toggle)
        log_header.addWidget(self._copy_log_btn)
        log_header.addWidget(self._clear_log_btn)
        log_header.addStretch(1)
        root.addLayout(log_header)

        self._log_edit = QPlainTextEdit(central)
        self._log_edit.setReadOnly(True)
        self._log_edit.setMaximumBlockCount(2000)
        self._log_edit.setVisible(False)
        root.addWidget(self._log_edit)

        self.setCentralWidget(central)

    def _apply_texts(self) -> None:
        """(Re)apply every static, user visible text (called on language change)."""
        self.setWindowTitle(self.tr(__app_name__))

        self._url_label.setText(self.tr("URL:"))
        self._url_edit.setPlaceholderText(
            self.tr("https://www.youtube.com/watch?v=… or any supported YouTube URL")
        )
        self._paste_btn.setText(self.tr("Paste URL"))
        self._paste_btn.setToolTip(self.tr("Paste a YouTube URL from the clipboard"))
        self._analyze_btn.setText(self.tr("Analyze"))
        self._analyze_btn.setToolTip(
            self.tr("Fetch the video info and its subtitles (Ctrl+L focuses the URL)")
        )

        if self._thumb_label.pixmap() is None:
            self._thumb_label.setText(self.tr("No image"))
        if self._video is None:
            self._title_label.setText(self.tr("No video analyzed yet."))
            self._channel_label.setText("")
            self._meta_label.setText("")
        else:
            self._update_meta_label()

        self._search_label.setText(self.tr("Search language:"))
        self._search_edit.setPlaceholderText(self.tr("Spanish, Español, es, es-orig …"))
        self._select_all_btn.setText(self.tr("Select all"))
        self._select_none_btn.setText(self.tr("Select none"))
        self._select_manual_btn.setText(self.tr("Manual only"))
        self._select_auto_btn.setText(self.tr("Automatic only"))

        self._tabs.setTabText(0, self.tr("All"))
        self._tabs.setTabText(1, self.tr("Subtitles"))
        self._tabs.setTabText(2, self.tr("Automatic"))

        self._options_box.setTitle(self.tr("Options"))
        self._format_label.setText(self.tr("Format:"))
        self._txt_check.setText(self.tr("Also create clean TXT file"))
        self._txt_mode_label.setText(self.tr("TXT mode:"))
        self._dir_label.setText(self.tr("Save to:"))
        self._browse_btn.setText(self.tr("Browse…"))
        self._template_label.setText(self.tr("File name:"))

        self._preview_btn.setText(self.tr("Preview"))
        self._preview_btn.setToolTip(
            self.tr("Preview the selected subtitle (double-click a row)")
        )
        self._cancel_btn.setText(self.tr("Cancel"))
        self._download_btn.setText(self.tr("Download selected"))

        self._log_toggle.setText(self.tr("Details / Log"))
        self._copy_log_btn.setText(self.tr("Copy log"))
        self._clear_log_btn.setText(self.tr("Clear log"))

        # Rebuild translatable combo items, keeping the current selection.
        current_mode = self._txt_mode_combo.currentData()
        self._txt_mode_combo.clear()
        self._txt_mode_combo.addItem(self.tr("Continuous text"), "continuous")
        self._txt_mode_combo.addItem(self.tr("Paragraphs"), "paragraphs")
        self._txt_mode_combo.addItem(self.tr("One line per subtitle"), "lines")
        self._set_combo_data(self._txt_mode_combo, current_mode)

        current_template = (
            self._template_combo.currentText().strip()
            or self._template_combo.currentData()
        )
        self._template_combo.clear()
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
        index = self._template_combo.findData(current_template)
        if index >= 0:
            self._template_combo.setCurrentIndex(index)
        elif current_template:
            self._template_combo.setCurrentIndex(self._template_combo.count() - 1)
            self._template_combo.setEditText(current_template)

    def _build_menus(self) -> None:
        menu_bar = self.menuBar()

        self._file_menu = menu_bar.addMenu("")
        self._new_url_action = QAction(self)
        self._new_url_action.setIcon(theme_icon("document-new"))
        self._new_url_action.setShortcut(QKeySequence("Ctrl+N"))
        self._new_url_action.triggered.connect(self._new_url)
        self._file_menu.addAction(self._new_url_action)
        self._open_folder_action = QAction(self)
        self._open_folder_action.setIcon(theme_icon("folder-open"))
        self._open_folder_action.triggered.connect(self._open_output_folder)
        self._file_menu.addAction(self._open_folder_action)
        self._history_action = QAction(self)
        self._history_action.setIcon(theme_icon("document-open-recent"))
        self._history_action.triggered.connect(self._show_history)
        self._file_menu.addAction(self._history_action)
        self._file_menu.addSeparator()
        self._quit_action = QAction(self)
        self._quit_action.setIcon(theme_icon("application-exit"))
        self._quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        self._quit_action.triggered.connect(self.close)
        self._file_menu.addAction(self._quit_action)

        self._tools_menu = menu_bar.addMenu("")
        self._settings_action = QAction(self)
        self._settings_action.setIcon(theme_icon("preferences-system"))
        self._settings_action.setShortcut(QKeySequence("Ctrl+,"))
        self._settings_action.triggered.connect(self._show_settings)
        self._tools_menu.addAction(self._settings_action)
        self._check_action = QAction(self)
        self._check_action.setIcon(theme_icon("system-run"))
        self._check_action.triggered.connect(self._show_system_info)
        self._tools_menu.addAction(self._check_action)

        self._help_menu = menu_bar.addMenu("")
        self._help_action = QAction(self)
        self._help_action.setIcon(theme_icon("help-contents"))
        self._help_action.setShortcut(QKeySequence("F1"))
        self._help_action.triggered.connect(self._show_help)
        self._help_menu.addAction(self._help_action)
        self._system_action = QAction(self)
        self._system_action.setIcon(theme_icon("computer"))
        self._system_action.triggered.connect(self._show_system_info)
        self._help_menu.addAction(self._system_action)
        self._about_action = QAction(self)
        self._about_action.setIcon(theme_icon("help-about"))
        self._about_action.triggered.connect(self._show_about)
        self._help_menu.addAction(self._about_action)

        self._apply_menu_texts()

    def _apply_menu_texts(self) -> None:
        self._file_menu.setTitle(self.tr("&File"))
        self._new_url_action.setText(self.tr("&New URL"))
        self._open_folder_action.setText(self.tr("Open &downloads folder"))
        self._history_action.setText(self.tr("&History…"))
        self._quit_action.setText(self.tr("&Quit"))

        self._tools_menu.setTitle(self.tr("&Tools"))
        self._settings_action.setText(self.tr("&Settings…"))
        self._check_action.setText(self.tr("&Check yt-dlp"))

        self._help_menu.setTitle(self.tr("&Help"))
        self._help_action.setText(self.tr("&Help"))
        self._system_action.setText(self.tr("&System info"))
        self._about_action.setText(self.tr("&About"))

    def _build_shortcuts(self) -> None:
        # Shortcuts that do not conflict with normal text editing.
        url_action = QAction(self)
        url_action.setShortcut(QKeySequence("Ctrl+L"))
        url_action.triggered.connect(lambda: self._url_edit.setFocus())
        self.addAction(url_action)

        search_action = QAction(self)
        search_action.setShortcut(QKeySequence("Ctrl+F"))
        search_action.triggered.connect(lambda: self._search_edit.setFocus())
        self.addAction(search_action)

        download_action = QAction(self)
        download_action.setShortcut(QKeySequence("Ctrl+D"))
        download_action.triggered.connect(self._download)
        self.addAction(download_action)

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    def _set_busy(self, busy: bool, message: str) -> None:
        self._analyze_btn.setEnabled(not busy)
        self._download_btn.setEnabled(not busy and self._model.checked_count() > 0)
        self._cancel_btn.setEnabled(busy)
        self._progress.setVisible(busy)
        if busy:
            self._progress.setRange(0, 0)
        self.statusBar().showMessage(message)
        QApplication.processEvents()

    def _update_state(self) -> None:
        checked = self._model.checked_count()
        self._download_btn.setEnabled(checked > 0 and not self._cancel_btn.isEnabled())
        self._preview_btn.setEnabled(checked == 1)

    def _apply_settings_to_ui(self) -> None:
        settings = self._settings
        self._dir_edit.setText(settings.output_dir())
        self._set_combo_data(self._format_combo, settings.subtitle_format())
        self._txt_check.setChecked(settings.txt_enabled())
        self._set_combo_data(self._txt_mode_combo, settings.txt_mode())
        template = settings.filename_template()
        index = self._template_combo.findData(template)
        if index >= 0:
            self._template_combo.setCurrentIndex(index)
        else:
            self._template_combo.setCurrentIndex(self._template_combo.count() - 1)
            self._template_combo.setEditText(template)

    def _check_environment(self) -> None:
        service = YtDlpService(self._settings)
        if service.is_available():
            version = service.installed_version
            self.statusBar().showMessage(
                translate_args(self.tr("Ready — yt-dlp %1"), version or self.tr("unknown"))
            )
        else:
            self._append_log(self.tr("yt-dlp is not installed."))
            QMessageBox.warning(
                self,
                self.tr("yt-dlp not found"),
                self.tr(
                    "yt-dlp was not found.\n\n"
                    "This application uses yt-dlp to communicate with YouTube.\n"
                    "On Debian/Ubuntu you can install it with your package manager "
                    "or by following the official yt-dlp documentation."
                ),
            )

    # ------------------------------------------------------------------
    # Video analysis
    # ------------------------------------------------------------------
    def _analyze(self) -> None:
        url = self._url_edit.text().strip()
        if not url:
            self.statusBar().showMessage(self.tr("Enter a YouTube URL first."))
            return
        if self._worker is not None and self._worker.isRunning():
            return

        self._video = None
        self._pending_playlist_entries = []
        self._model.set_tracks([])
        self._thumb_label.setText(self.tr("No image"))
        self._title_label.setText(self.tr("Analyzing…"))
        self._channel_label.setText("")
        self._meta_label.setText("")

        worker = VideoInfoWorker(url, self._settings, self)
        self._start_worker(worker)
        worker.info_ready.connect(self._on_info_ready)
        worker.playlist_detected.connect(self._on_playlist_detected)
        self._set_busy(True, self.tr("Analyzing video…"))
        worker.start()

    def _on_info_ready(self, info: VideoInfo) -> None:
        self._video = info
        self._set_video_info(info)
        self._model.set_tracks(info.tracks)
        preferred = self._settings.preferred_language()
        if preferred:
            self._model.auto_select_preferred(preferred)
        self._set_busy(False, f"{info.title}")
        self._update_state()
        self._append_log(
            translate_args(
                self.tr("%1 manual / %2 automatic subtitle track(s)."),
                len(info.manual_tracks),
                len(info.automatic_tracks),
            )
        )

    def _on_playlist_detected(self, title: str, count: int) -> None:
        box = QMessageBox(self)
        box.setWindowTitle(self.tr("Playlist detected"))
        box.setText(
            translate_args(
                self.tr("This URL belongs to the playlist “%1” with %2 video(s)."),
                title,
                count,
            )
        )
        only_button = box.addButton(
            self.tr("Analyze only this video"), QMessageBox.ButtonRole.AcceptRole
        )
        all_button = box.addButton(
            self.tr("Analyze entire playlist"), QMessageBox.ButtonRole.ActionRole
        )
        box.setDefaultButton(only_button)
        box.exec()
        if box.clickedButton() is all_button and self._video is not None:
            self._load_playlist(self._video.url)

    def _load_playlist(self, url: str) -> None:
        worker = PlaylistWorker(url, self._settings, self)
        self._start_worker(worker)
        worker.playlist_ready.connect(self._on_playlist_ready)
        worker.start()

    def _on_playlist_ready(self, playlist) -> None:
        dialog = PlaylistDialog(playlist, self)
        if dialog.exec() != PlaylistDialog.DialogCode.Accepted:
            return
        entries = dialog.selected_entries()
        if not entries:
            self.statusBar().showMessage(self.tr("No videos selected from the playlist."))
            return
        self._pending_playlist_entries = entries
        self._append_log(
            translate_args(
                self.tr(
                    "Playlist: %1 video(s) selected; analyzing the first one for subtitle selection."
                ),
                len(entries),
            )
        )
        first = entries[0]
        worker = VideoInfoWorker(first.url, self._settings, self)
        self._start_worker(worker)
        worker.info_ready.connect(self._on_info_ready)
        worker.playlist_detected.connect(self._on_playlist_detected)
        self._set_busy(
            True, translate_args(self.tr("Analyzing video %1/%2…"), 1, len(entries))
        )
        worker.start()

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------
    def _download(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        if self._video is None:
            self.statusBar().showMessage(self.tr("Analyze a video first."))
            return
        tracks = self._model.checked_tracks()
        if not tracks:
            self.statusBar().showMessage(
                self.tr("Select at least one subtitle to download.")
            )
            return

        outdir_text = self._dir_edit.text().strip() or str(default_download_dir())
        outdir = Path(outdir_text).expanduser()
        try:
            outdir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.warning(
                self,
                self.tr("Error"),
                translate_args(
                    self.tr("Cannot create the destination folder:\n%1"), str(exc)
                ),
            )
            return

        urls = (
            [entry.url for entry in self._pending_playlist_entries]
            if self._pending_playlist_entries
            else [self._video.url]
        )
        options = {
            "format": self._format_combo.currentData(),
            "txt_enabled": self._txt_check.isChecked(),
            "txt_mode": self._txt_mode_combo.currentData(),
            "template": self._template_combo.currentText().strip()
            or DEFAULT_TEMPLATE,
            "output_dir": str(outdir),
        }

        worker = DownloadWorker(urls, tracks, self._settings, options, self)
        self._start_worker(worker)
        worker.progress.connect(self._on_progress)
        worker.status.connect(lambda message: self.statusBar().showMessage(message))
        worker.track_finished.connect(self._on_track_finished)
        worker.batch_finished.connect(self._on_batch_finished)

        total = len(urls) * len(tracks)
        self._progress.setRange(0, total)
        self._progress.setValue(0)
        self._set_busy(True, self.tr("Downloading…"))
        self._append_log(
            translate_args(
                self.tr("Downloading %1 track(s) for %2 video(s) into %3…"),
                len(tracks),
                len(urls),
                str(outdir),
            )
        )
        worker.start()

    def _on_progress(self, done: int, total: int) -> None:
        self._progress.setRange(0, max(total, 1))
        self._progress.setValue(done)
        self.statusBar().showMessage(
            translate_args(self.tr("Progress: %1/%2"), done, total)
        )

    def _on_track_finished(self, result) -> None:
        if result.ok:
            self._append_log(
                translate_args(
                    self.tr("Completed: %1 → %2"), result.language_name, result.path
                )
            )
        elif result.skipped:
            self._append_log(
                translate_args(
                    self.tr("Skipped: %1 — %2"), result.language_name, result.error
                )
            )
        else:
            self._append_log(
                translate_args(
                    self.tr("Failed: %1 — %2"), result.language_name, result.error
                )
            )
        self._update_state()

    def _on_batch_finished(self, results) -> None:
        self._set_busy(False, self.tr("Download finished."))
        self._progress.setVisible(False)
        self._update_state()

        ok = [r for r in results if r.ok]
        if ok:
            self._save_history(results)
            # Notify before the modal dialog so absent users get the alert
            # immediately; attentive users (active window) get none.
            if self._settings.notify_on_finish() and not self.isActiveWindow():
                send_notification(
                    self.tr("Download finished"),
                    translate_args(
                        self.tr("Downloaded %1 subtitle(s)."), len(ok)
                    ),
                )
            DownloadCompleteDialog(results, self._dir_edit.text().strip(), self).exec()

    def _save_history(self, results) -> None:
        if not self._settings.history_enabled() or self._video is None:
            return
        ok = [r for r in results if r.ok]
        if not ok:
            return
        self._settings.add_history(
            {
                "date": datetime.now().isoformat(timespec="seconds"),
                "title": self._video.title,
                "url": self._video.url,
                "languages": sorted({r.language_code for r in ok}),
                "folder": self._dir_edit.text().strip(),
            }
        )

    def _cancel_current(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._append_log(self.tr("Cancellation requested…"))
            self.statusBar().showMessage(self.tr("Cancelling…"))

    # ------------------------------------------------------------------
    # Video info display
    # ------------------------------------------------------------------
    def _update_meta_label(self) -> None:
        """Rebuild the video metadata line (also used on language change)."""
        if self._video is None:
            return
        meta_parts = []
        if self._video.formatted_duration:
            meta_parts.append(self._video.formatted_duration)
        if self._video.formatted_upload_date:
            meta_parts.append(
                translate_args(
                    self.tr("Published %1"), self._video.formatted_upload_date
                )
            )
        if self._video.video_id:
            meta_parts.append(translate_args(self.tr("ID: %1"), self._video.video_id))
        self._meta_label.setText(" · ".join(meta_parts))

    def _set_video_info(self, info: VideoInfo) -> None:
        self._title_label.setText(info.title)
        self._channel_label.setText(info.channel)
        self._update_meta_label()
        if info.thumbnail_url:
            request = QNetworkRequest(QUrl(info.thumbnail_url))
            self._thumbnail_reply = self._network.get(request)

    def _on_thumbnail_loaded(self, reply: QNetworkReply) -> None:
        if reply.error() == QNetworkReply.NetworkError.NoError:
            pixmap = QPixmap()
            if pixmap.loadFromData(reply.readAll()):
                self._thumb_label.setPixmap(
                    pixmap.scaled(
                        self._thumb_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
        else:
            self._thumb_label.setText(self.tr("No image"))
        reply.deleteLater()
        self._thumbnail_reply = None

    # ------------------------------------------------------------------
    # Misc actions
    # ------------------------------------------------------------------
    def _paste_url(self) -> None:
        text = QApplication.clipboard().text().strip()
        if is_youtube_url(text):
            self._url_edit.setText(text)
            self._append_log(self.tr("Pasted a YouTube URL from the clipboard."))
            if self._settings.auto_analyze_after_paste():
                self._analyze()
        else:
            self.statusBar().showMessage(
                self.tr("The clipboard does not contain a YouTube URL.")
            )

    def _new_url(self) -> None:
        self._video = None
        self._pending_playlist_entries = []
        self._url_edit.clear()
        self._model.set_tracks([])
        self._thumb_label.setText(self.tr("No image"))
        self._title_label.setText(self.tr("No video analyzed yet."))
        self._channel_label.setText("")
        self._meta_label.setText("")
        self.statusBar().showMessage(self.tr("Ready."))
        self._url_edit.setFocus()

    def _browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            self.tr("Select destination folder"),
            self._dir_edit.text() or str(Path.home()),
        )
        if path:
            self._dir_edit.setText(path)

    def _open_output_folder(self) -> None:
        folder = self._dir_edit.text().strip() or str(default_download_dir())
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def _show_settings(self) -> None:
        dialog = SettingsDialog(self._settings, self)
        if dialog.exec() == SettingsDialog.DialogCode.Accepted:
            new_language = self._settings.language()
            if new_language != self._language:
                from ..i18n import install_translator

                install_translator(QApplication.instance(), new_language)
                self._language = new_language
                self._apply_texts()
                self._apply_menu_texts()
                self.statusBar().showMessage(self.tr("Ready."))
            self._apply_settings_to_ui()

    def _show_history(self) -> None:
        HistoryDialog(self._settings, self).exec()

    def _show_about(self) -> None:
        AboutDialog(self._settings, self).exec()

    def _show_system_info(self) -> None:
        AboutDialog(self._settings, self).exec()

    def _show_help(self) -> None:
        QMessageBox.information(
            self,
            self.tr("Help"),
            self.tr(
                "1. Paste a YouTube URL (or drag & drop it onto the window).\n"
                "2. Press Analyze to fetch the video and its subtitles.\n"
                "3. Check the languages you want (tabs filter manual/automatic).\n"
                "4. Choose format, TXT option, destination folder and file name.\n"
                "5. Press Download selected.\n\n"
                "Shortcuts: Ctrl+L URL · Ctrl+F search · Ctrl+D download · "
                "Ctrl+, settings · Ctrl+Q quit."
            ),
        )

    def _open_preview(self) -> None:
        if self._video is None:
            return
        tracks = self._model.checked_tracks()
        if len(tracks) != 1:
            self.statusBar().showMessage(
                self.tr("Select exactly one subtitle to preview.")
            )
            return
        PreviewDialog(tracks[0], self._video, self._settings, self).exec()

    def _on_table_clicked(self, index) -> None:
        """Toggle the row checkbox when the user clicks anywhere on the row.

        Column 0 is the checkbox itself and is already handled by the item
        view delegate, so only clicks on the other columns need handling.
        """
        if not index.isValid() or index.column() == 0:
            return
        check_index = self._model.index(index.row(), 0)
        state = self._model.data(check_index, Qt.ItemDataRole.CheckStateRole)
        new_state = (
            Qt.CheckState.Unchecked
            if state == Qt.CheckState.Checked
            else Qt.CheckState.Checked
        )
        self._model.setData(check_index, new_state, Qt.ItemDataRole.CheckStateRole)

    def _on_table_double_clicked(self, index) -> None:
        """Preview the double-clicked subtitle directly."""
        if self._video is None or not index.isValid():
            return
        track = self._model.track_at(index.row())
        if track is not None:
            PreviewDialog(track, self._video, self._settings, self).exec()

    # ------------------------------------------------------------------
    # Filters / tabs / log
    # ------------------------------------------------------------------
    def _on_filter_changed(self, text: str) -> None:
        self._model.set_filter(self._current_kind(), text)

    def _on_tab_changed(self, _index: int) -> None:
        self._model.set_filter(self._current_kind(), self._search_edit.text())

    def _current_kind(self):
        index = self._tabs.currentIndex()
        if index == 1:
            return SubtitleKind.MANUAL
        if index == 2:
            return SubtitleKind.AUTOMATIC
        return None

    def _on_checked_changed(self, count: int) -> None:
        self._download_btn.setEnabled(
            count > 0 and not self._cancel_btn.isEnabled()
        )
        self._preview_btn.setEnabled(count == 1)
        if not count:
            self.statusBar().showMessage(
                self.tr("Select at least one subtitle to download.")
            )

    def _append_log(self, message: str) -> None:
        self._log_edit.appendPlainText(message)
        log.info(message)

    def _toggle_log(self, visible: bool) -> None:
        self._log_edit.setVisible(visible)

    def _copy_log(self) -> None:
        QApplication.clipboard().setText(self._log_edit.toPlainText())

    # ------------------------------------------------------------------
    # Workers
    # ------------------------------------------------------------------
    def _start_worker(self, worker) -> None:
        self._worker = worker
        worker.log.connect(self._append_log)
        worker.failed.connect(self._on_worker_failed)
        worker.cancelled.connect(self._on_worker_cancelled)
        worker.finished.connect(lambda: self._on_worker_finished(worker))

    def _on_worker_failed(self, message: str) -> None:
        self._set_busy(False, self.tr("Error"))
        self._progress.setVisible(False)
        self._update_state()
        self._append_log(f"Error: {message}")
        QMessageBox.warning(self, self.tr("Error"), message)

    def _on_worker_cancelled(self) -> None:
        self._set_busy(False, self.tr("Cancelled."))
        self._progress.setVisible(False)
        self._update_state()
        self._append_log(self.tr("Operation cancelled."))

    def _on_worker_finished(self, worker) -> None:
        if self._worker is worker:
            self._worker = None

    # ------------------------------------------------------------------
    # Drag & drop, close
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasText() and is_youtube_url(event.mimeData().text()):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        text = event.mimeData().text().strip()
        if text:
            self._url_edit.setText(text)
            event.acceptProposedAction()
            self._append_log(self.tr("Dropped a URL onto the window."))

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(3000)
        settings = self._settings
        settings.set_window_geometry(self.saveGeometry())
        settings.set_window_state(self.saveState())
        settings.sync()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Window state
    # ------------------------------------------------------------------
    def _restore_window_state(self) -> None:
        geometry = self._settings.window_geometry()
        if geometry:
            self.restoreGeometry(geometry)
        state = self._settings.window_state()
        if state:
            self.restoreState(state)

    @staticmethod
    def _set_combo_data(combo, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)
