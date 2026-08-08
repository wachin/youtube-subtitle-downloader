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
from ..models.subtitle import SubtitleKind
from ..models.video import PlaylistEntry, VideoInfo
from ..services.settings_service import SettingsService
from ..services.ytdlp_service import YtDlpService, is_youtube_url
from ..utils.filenames import DEFAULT_TEMPLATE, PRESET_TEMPLATES
from ..utils.logging import get_logger
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
TXT_MODES = [
    ("Continuous text", "continuous"),
    ("Paragraphs", "paragraphs"),
    ("One line per subtitle", "lines"),
]


class MainWindow(QMainWindow):
    """Main window implementing the roadmap flow."""

    def __init__(self, settings: SettingsService, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self._video: VideoInfo | None = None
        self._worker = None
        self._pending_playlist_entries: list[PlaylistEntry] = []
        self._thumbnail_reply: QNetworkReply | None = None

        self.setWindowTitle(__app_name__)
        self.resize(860, 640)

        self._network = QNetworkAccessManager(self)
        self._network.finished.connect(self._on_thumbnail_loaded)

        self._build_ui()
        self._build_menus()
        self._build_shortcuts()
        self.setAcceptDrops(True)
        self._restore_window_state()
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
        url_row.addWidget(QLabel("URL:"))
        self._url_edit = QLineEdit(central)
        self._url_edit.setPlaceholderText(
            "https://www.youtube.com/watch?v=… or any supported YouTube URL"
        )
        self._url_edit.setClearButtonEnabled(True)
        self._url_edit.returnPressed.connect(self._analyze)
        url_row.addWidget(self._url_edit, 1)
        self._paste_btn = QPushButton("Paste URL", central)
        self._paste_btn.setToolTip("Paste a YouTube URL from the clipboard")
        self._paste_btn.clicked.connect(self._paste_url)
        url_row.addWidget(self._paste_btn)
        self._analyze_btn = QPushButton("Analyze", central)
        self._analyze_btn.setDefault(True)
        self._analyze_btn.setToolTip("Fetch the video info and its subtitles (Ctrl+L focuses the URL)")
        self._analyze_btn.clicked.connect(self._analyze)
        url_row.addWidget(self._analyze_btn)
        root.addLayout(url_row)

        # Video info
        info_row = QHBoxLayout()
        self._thumb_label = QLabel(central)
        self._thumb_label.setFixedSize(160, 90)
        self._thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb_label.setText("No image")
        self._thumb_label.setStyleSheet("background: rgba(0,0,0,0.06); border-radius: 4px;")
        info_row.addWidget(self._thumb_label)
        info_col = QVBoxLayout()
        self._title_label = QLabel("No video analyzed yet.", central)
        self._title_label.setWordWrap(True)
        self._title_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._channel_label = QLabel("", central)
        self._channel_label.setStyleSheet("font-weight: bold;")
        self._meta_label = QLabel("", central)
        self._meta_label.setStyleSheet("color: gray;")
        info_col.addWidget(self._title_label)
        info_col.addWidget(self._channel_label)
        info_col.addWidget(self._meta_label)
        info_col.addStretch(1)
        info_row.addLayout(info_col, 1)
        root.addLayout(info_row)

        # Search / filter
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Search language:"))
        self._search_edit = QLineEdit(central)
        self._search_edit.setPlaceholderText("Spanish, Español, es, es-orig …")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.textChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self._search_edit, 1)
        self._select_all_btn = QPushButton("Select all", central)
        self._select_all_btn.clicked.connect(lambda: self._model.check_all(True))
        self._select_none_btn = QPushButton("Select none", central)
        self._select_none_btn.clicked.connect(lambda: self._model.check_all(False))
        self._select_manual_btn = QPushButton("Manual only", central)
        self._select_manual_btn.clicked.connect(
            lambda: self._model.check_kind(SubtitleKind.MANUAL, True)
        )
        self._select_auto_btn = QPushButton("Automatic only", central)
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
        self._tabs.addTab(QWidget(central), "All")
        self._tabs.addTab(QWidget(central), "Subtitles")
        self._tabs.addTab(QWidget(central), "Automatic")
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
        options = QGroupBox("Options", central)
        opt_layout = QVBoxLayout(options)
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Format:"))
        self._format_combo = QComboBox(options)
        for name, code in FORMATS:
            self._format_combo.addItem(name, code)
        row1.addWidget(self._format_combo)
        self._txt_check = QCheckBox("Also create clean TXT file", options)
        row1.addWidget(self._txt_check)
        row1.addWidget(QLabel("TXT mode:"))
        self._txt_mode_combo = QComboBox(options)
        for name, code in TXT_MODES:
            self._txt_mode_combo.addItem(name, code)
        row1.addWidget(self._txt_mode_combo)
        row1.addStretch(1)
        opt_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Save to:"))
        self._dir_edit = QLineEdit(options)
        row2.addWidget(self._dir_edit, 1)
        browse_btn = QPushButton("Browse…", options)
        browse_btn.clicked.connect(self._browse_output_dir)
        row2.addWidget(browse_btn)
        row2.addWidget(QLabel("File name:"))
        self._template_combo = QComboBox(options)
        self._template_combo.setEditable(True)
        for name, template in PRESET_TEMPLATES.items():
            self._template_combo.addItem(f"{name}  →  {template}", template)
        self._template_combo.addItem("Custom", None)
        row2.addWidget(self._template_combo, 1)
        opt_layout.addLayout(row2)
        root.addWidget(options)

        # Progress + action buttons
        action_row = QHBoxLayout()
        self._preview_btn = QPushButton("Preview", central)
        self._preview_btn.setToolTip("Preview the selected subtitle (double-click a row)")
        self._preview_btn.clicked.connect(self._open_preview)
        action_row.addWidget(self._preview_btn)
        action_row.addStretch(1)
        self._cancel_btn = QPushButton("Cancel", central)
        self._cancel_btn.clicked.connect(self._cancel_current)
        self._cancel_btn.setEnabled(False)
        action_row.addWidget(self._cancel_btn)
        self._download_btn = QPushButton("Download selected", central)
        self._download_btn.clicked.connect(self._download)
        action_row.addWidget(self._download_btn)
        root.addLayout(action_row)

        self._progress = QProgressBar(central)
        self._progress.setVisible(False)
        root.addWidget(self._progress)

        # Log panel
        log_header = QHBoxLayout()
        self._log_toggle = QToolButton(central)
        self._log_toggle.setText("Details / Log")
        self._log_toggle.setCheckable(True)
        self._log_toggle.setChecked(False)
        self._log_toggle.toggled.connect(self._toggle_log)
        self._copy_log_btn = QPushButton("Copy log", central)
        self._copy_log_btn.clicked.connect(self._copy_log)
        self._clear_log_btn = QPushButton("Clear log", central)
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
        self.statusBar().showMessage("Ready.")

    def _build_menus(self) -> None:
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        new_action = QAction("&New URL", self)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self._new_url)
        file_menu.addAction(new_action)
        open_folder = QAction("Open &downloads folder", self)
        open_folder.triggered.connect(self._open_output_folder)
        file_menu.addAction(open_folder)
        history_action = QAction("&History…", self)
        history_action.triggered.connect(self._show_history)
        file_menu.addAction(history_action)
        file_menu.addSeparator()
        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        tools_menu = menu_bar.addMenu("&Tools")
        settings_action = QAction("&Settings…", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._show_settings)
        tools_menu.addAction(settings_action)
        check_action = QAction("&Check yt-dlp", self)
        check_action.triggered.connect(self._show_system_info)
        tools_menu.addAction(check_action)

        help_menu = menu_bar.addMenu("&Help")
        help_action = QAction("&Help", self)
        help_action.setShortcut(QKeySequence("F1"))
        help_action.triggered.connect(self._show_help)
        help_menu.addAction(help_action)
        system_action = QAction("&System info", self)
        system_action.triggered.connect(self._show_system_info)
        help_menu.addAction(system_action)
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

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
            self.statusBar().showMessage(f"Ready — yt-dlp {version or 'unknown'}")
        else:
            self._append_log("yt-dlp is not installed.")
            QMessageBox.warning(
                self,
                "yt-dlp not found",
                "yt-dlp was not found.\n\n"
                "This application uses yt-dlp to communicate with YouTube.\n"
                "On Debian/Ubuntu you can install it with your package manager "
                "or by following the official yt-dlp documentation.",
            )

    # ------------------------------------------------------------------
    # Video analysis
    # ------------------------------------------------------------------
    def _analyze(self) -> None:
        url = self._url_edit.text().strip()
        if not url:
            self.statusBar().showMessage("Enter a YouTube URL first.")
            return
        if self._worker is not None and self._worker.isRunning():
            return

        self._video = None
        self._pending_playlist_entries = []
        self._model.set_tracks([])
        self._thumb_label.setText("No image")
        self._title_label.setText("Analyzing…")
        self._channel_label.setText("")
        self._meta_label.setText("")

        worker = VideoInfoWorker(url, self._settings, self)
        self._start_worker(worker)
        worker.info_ready.connect(self._on_info_ready)
        worker.playlist_detected.connect(self._on_playlist_detected)
        self._set_busy(True, "Analyzing video…")
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
            f"{len(info.manual_tracks)} manual / {len(info.automatic_tracks)} "
            "automatic subtitle track(s)."
        )

    def _on_playlist_detected(self, title: str, count: int) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("Playlist detected")
        box.setText(
            f"This URL belongs to the playlist “{title}” with {count} video(s)."
        )
        only_button = box.addButton(
            "Analyze only this video", QMessageBox.ButtonRole.AcceptRole
        )
        all_button = box.addButton(
            "Analyze entire playlist", QMessageBox.ButtonRole.ActionRole
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
            self.statusBar().showMessage("No videos selected from the playlist.")
            return
        self._pending_playlist_entries = entries
        self._append_log(
            f"Playlist: {len(entries)} video(s) selected; "
            "analyzing the first one for subtitle selection."
        )
        first = entries[0]
        worker = VideoInfoWorker(first.url, self._settings, self)
        self._start_worker(worker)
        worker.info_ready.connect(self._on_info_ready)
        worker.playlist_detected.connect(self._on_playlist_detected)
        self._set_busy(True, f"Analyzing video 1/{len(entries)}…")
        worker.start()

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------
    def _download(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        if self._video is None:
            self.statusBar().showMessage("Analyze a video first.")
            return
        tracks = self._model.checked_tracks()
        if not tracks:
            self.statusBar().showMessage("Select at least one subtitle to download.")
            return

        outdir_text = self._dir_edit.text().strip() or str(default_download_dir())
        outdir = Path(outdir_text).expanduser()
        try:
            outdir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.warning(self, "Error", f"Cannot create the destination folder:\n{exc}")
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
        self._set_busy(True, "Downloading…")
        self._append_log(
            f"Downloading {len(tracks)} track(s) for {len(urls)} video(s) into "
            f"{outdir}…"
        )
        worker.start()

    def _on_progress(self, done: int, total: int) -> None:
        self._progress.setRange(0, max(total, 1))
        self._progress.setValue(done)
        self.statusBar().showMessage(f"Progress: {done}/{total}")

    def _on_track_finished(self, result) -> None:
        if result.ok:
            self._append_log(f"Completed: {result.language_name} → {result.path}")
        elif result.skipped:
            self._append_log(f"Skipped: {result.language_name} — {result.error}")
        else:
            self._append_log(f"Failed: {result.language_name} — {result.error}")
        self._update_state()

    def _on_batch_finished(self, results) -> None:
        self._set_busy(False, "Download finished.")
        self._progress.setVisible(False)
        self._update_state()

        ok = [r for r in results if r.ok]
        if ok:
            self._save_history(results)
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
            self._append_log("Cancellation requested…")
            self.statusBar().showMessage("Cancelling…")

    # ------------------------------------------------------------------
    # Video info display
    # ------------------------------------------------------------------
    def _set_video_info(self, info: VideoInfo) -> None:
        self._title_label.setText(info.title)
        self._channel_label.setText(info.channel)
        meta_parts = []
        if info.formatted_duration:
            meta_parts.append(info.formatted_duration)
        if info.formatted_upload_date:
            meta_parts.append(f"Published {info.formatted_upload_date}")
        if info.video_id:
            meta_parts.append(f"ID: {info.video_id}")
        self._meta_label.setText(" · ".join(meta_parts))
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
            self._thumb_label.setText("No image")
        reply.deleteLater()
        self._thumbnail_reply = None

    # ------------------------------------------------------------------
    # Misc actions
    # ------------------------------------------------------------------
    def _paste_url(self) -> None:
        text = QApplication.clipboard().text().strip()
        if is_youtube_url(text):
            self._url_edit.setText(text)
            self._append_log("Pasted a YouTube URL from the clipboard.")
            if self._settings.auto_analyze_after_paste():
                self._analyze()
        else:
            self.statusBar().showMessage("The clipboard does not contain a YouTube URL.")

    def _new_url(self) -> None:
        self._video = None
        self._pending_playlist_entries = []
        self._url_edit.clear()
        self._model.set_tracks([])
        self._thumb_label.setText("No image")
        self._title_label.setText("No video analyzed yet.")
        self._channel_label.setText("")
        self._meta_label.setText("")
        self.statusBar().showMessage("Ready.")
        self._url_edit.setFocus()

    def _browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Select destination folder", self._dir_edit.text() or str(Path.home())
        )
        if path:
            self._dir_edit.setText(path)

    def _open_output_folder(self) -> None:
        folder = self._dir_edit.text().strip() or str(default_download_dir())
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def _show_settings(self) -> None:
        dialog = SettingsDialog(self._settings, self)
        if dialog.exec() == SettingsDialog.DialogCode.Accepted:
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
            "Help",
            "1. Paste a YouTube URL (or drag & drop it onto the window).\n"
            "2. Press Analyze to fetch the video and its subtitles.\n"
            "3. Check the languages you want (tabs filter manual/automatic).\n"
            "4. Choose format, TXT option, destination folder and file name.\n"
            "5. Press Download selected.\n\n"
            "Shortcuts: Ctrl+L URL · Ctrl+F search · Ctrl+D download · "
            "Ctrl+, settings · Ctrl+Q quit.",
        )

    def _open_preview(self) -> None:
        if self._video is None:
            return
        tracks = self._model.checked_tracks()
        if len(tracks) != 1:
            self.statusBar().showMessage("Select exactly one subtitle to preview.")
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
            self.statusBar().showMessage("Select at least one subtitle to download.")

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
        self._set_busy(False, "Error")
        self._progress.setVisible(False)
        self._update_state()
        self._append_log(f"Error: {message}")
        QMessageBox.warning(self, "Error", message)

    def _on_worker_cancelled(self) -> None:
        self._set_busy(False, "Cancelled.")
        self._progress.setVisible(False)
        self._update_state()
        self._append_log("Operation cancelled.")

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
            self._append_log("Dropped a URL onto the window.")

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
