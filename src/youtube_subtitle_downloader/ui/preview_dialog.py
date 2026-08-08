"""Read-only subtitle preview dialog with search, copy and save."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication, QTextCursor
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QFileDialog,
    QMessageBox,
)

from ..i18n import kind_display_name, translate_args
from ..models.subtitle import SubtitleTrack
from ..models.video import VideoInfo
from ..services.settings_service import SettingsService
from ..utils.filenames import sanitize_filename
from ..workers.preview_worker import PreviewWorker


class PreviewDialog(QDialog):
    """Preview a downloaded subtitle as clean text."""

    def __init__(
        self,
        track: SubtitleTrack,
        video: VideoInfo,
        settings: SettingsService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._track = track
        self._video = video
        self._settings = settings
        self._worker: PreviewWorker | None = None
        self._text = ""
        self.setWindowTitle(self.tr("Subtitle preview"))
        self.resize(680, 520)
        self._build_ui()
        self._start_loading()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        info = QLabel(
            f"<b>{sanitize_filename(self._video.title)}</b><br>"
            f"{self._track.display_name} · {self._track.language_code} · "
            f"{kind_display_name(self._track.kind.value)}"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self._editor = QPlainTextEdit(self)
        self._editor.setReadOnly(True)
        self._editor.setPlaceholderText(self.tr("Loading…"))
        layout.addWidget(self._editor, 1)

        find_row = QHBoxLayout()
        find_row.addWidget(QLabel(self.tr("Find:")))
        self._find_edit = QLineEdit(self)
        self._find_edit.setClearButtonEnabled(True)
        self._find_edit.returnPressed.connect(self._find_next)
        find_row.addWidget(self._find_edit, 1)
        prev_button = QPushButton(self.tr("Previous"), self)
        prev_button.clicked.connect(self._find_previous)
        next_button = QPushButton(self.tr("Next"), self)
        next_button.clicked.connect(self._find_next)
        find_row.addWidget(prev_button)
        find_row.addWidget(next_button)
        layout.addLayout(find_row)

        buttons = QHBoxLayout()
        copy_button = QPushButton(self.tr("Copy"), self)
        copy_button.clicked.connect(self._copy_text)
        copy_clean_button = QPushButton(self.tr("Copy clean text"), self)
        copy_clean_button.clicked.connect(self._copy_text)
        select_all_button = QPushButton(self.tr("Select all"), self)
        select_all_button.clicked.connect(self._select_all)
        save_button = QPushButton(self.tr("Save as…"), self)
        save_button.clicked.connect(self._save_as)
        close_button = QPushButton(self.tr("Close"), self)
        close_button.clicked.connect(self.accept)
        buttons.addWidget(copy_button)
        buttons.addWidget(copy_clean_button)
        buttons.addWidget(select_all_button)
        buttons.addStretch(1)
        buttons.addWidget(save_button)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

    def _start_loading(self) -> None:
        source_ext = self._track.formats[0] if self._track.formats else None
        worker = PreviewWorker(self._track, self._settings, source_ext, self)
        worker.content_ready.connect(self._on_content)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(worker.deleteLater)
        self._worker = worker
        worker.start()

    def _on_content(self, text: str) -> None:
        self._text = text
        self._editor.setPlainText(text)

    def _on_failed(self, message: str) -> None:
        self._editor.setPlainText(
            translate_args(self.tr("Could not load the subtitle:\n%1"), message)
        )

    # -- actions ----------------------------------------------------------
    def _copy_text(self) -> None:
        selected = self._editor.textCursor().selectedText()
        QGuiApplication.clipboard().setText(selected or self._text)

    def _select_all(self) -> None:
        self._editor.selectAll()

    def _find_next(self) -> None:
        text = self._find_edit.text()
        if text and not self._editor.find(text):
            cursor = self._editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self._editor.setTextCursor(cursor)
            self._editor.find(text)

    def _find_previous(self) -> None:
        text = self._find_edit.text()
        if text:
            self._editor.find(text, Qt.FindFlag.FindBackward)

    def _save_as(self) -> None:
        suggested = (
            sanitize_filename(self._video.title)
            + f" [{self._track.base_code}].txt"
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save subtitle as…"),
            str(Path(self._settings.output_dir()) / suggested),
            self.tr("Text files (*.txt);;All files (*)"),
        )
        if not path:
            return
        try:
            Path(path).write_text(self._editor.toPlainText(), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(
                self,
                self.tr("Error"),
                translate_args(self.tr("Cannot write the file:\n%1"), str(exc)),
            )
