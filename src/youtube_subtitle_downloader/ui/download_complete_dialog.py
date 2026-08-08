"""Completion dialog shown after a batch download."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ..i18n import translate_args
from ..models.video import DownloadResult


class DownloadCompleteDialog(QDialog):
    """Summarize a finished download batch (roadmap section 51)."""

    def __init__(
        self,
        results: list[DownloadResult],
        folder: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._folder = folder
        self.setWindowTitle(self.tr("Download completed"))

        ok = [r for r in results if r.ok]
        failed = [r for r in results if not r.ok and not r.skipped]
        skipped = [r for r in results if r.skipped]

        lines = [self.tr("<h3>Download completed.</h3>")]
        lines.append(
            translate_args(
                self.tr("<p><b>%1</b> subtitle(s) downloaded.</p>"), len(ok)
            )
        )
        if skipped:
            lines.append(
                translate_args(
                    self.tr("<p>%1 subtitle(s) were not available.</p>"),
                    len(skipped),
                )
            )
        if failed:
            lines.append(
                translate_args(
                    self.tr("<p>%1 subtitle(s) failed.</p>"), len(failed)
                )
            )
            detail = "<br>".join(
                f"• {r.language_name}: {r.error}" for r in failed[:5]
            )
            lines.append(f"<p><i>{detail}</i></p>")
        lines.append(
            translate_args(
                self.tr("<p>Folder: <code>%1</code></p>"), str(Path(folder))
            )
        )

        layout = QVBoxLayout(self)
        label = QLabel("".join(lines))
        label.setWordWrap(True)
        layout.addWidget(label)

        buttons = QHBoxLayout()
        view_button = QPushButton(self.tr("View files"), self)
        view_button.clicked.connect(self._open_folder)
        open_button = QPushButton(self.tr("Open folder"), self)
        open_button.clicked.connect(self._open_folder)
        close_button = QPushButton(self.tr("Close"), self)
        close_button.clicked.connect(self.accept)
        buttons.addWidget(view_button)
        buttons.addWidget(open_button)
        buttons.addStretch(1)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

    def _open_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(self._folder))
