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
        self.setWindowTitle("Download completed")

        ok = [r for r in results if r.ok]
        failed = [r for r in results if not r.ok and not r.skipped]
        skipped = [r for r in results if r.skipped]

        lines = [f"<h3>Download completed.</h3>"]
        lines.append(f"<p><b>{len(ok)}</b> subtitle(s) downloaded.</p>")
        if skipped:
            lines.append(f"<p>{len(skipped)} subtitle(s) were not available.</p>")
        if failed:
            lines.append(f"<p>{len(failed)} subtitle(s) failed.</p>")
            detail = "<br>".join(
                f"• {r.language_name}: {r.error}" for r in failed[:5]
            )
            lines.append(f"<p><i>{detail}</i></p>")
        lines.append(f'<p>Folder: <code>{Path(folder)}</code></p>')

        layout = QVBoxLayout(self)
        label = QLabel("".join(lines))
        label.setWordWrap(True)
        layout.addWidget(label)

        buttons = QHBoxLayout()
        view_button = QPushButton("View files", self)
        view_button.clicked.connect(self._open_folder)
        open_button = QPushButton("Open folder", self)
        open_button.clicked.connect(self._open_folder)
        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.accept)
        buttons.addWidget(view_button)
        buttons.addWidget(open_button)
        buttons.addStretch(1)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

    def _open_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(self._folder))
