"""About and system information dialog."""

from __future__ import annotations

import platform
import sys

from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR, Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .. import __app_name__, __version__
from ..i18n import translate_args
from ..services.ytdlp_service import YtDlpService, ffmpeg_version, version
from ..utils.icons import app_icon


class AboutDialog(QDialog):
    """About tab plus a system information tab."""

    def __init__(self, settings=None, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle(self.tr("About"))
        self.resize(580, 420)

        tabs = QTabWidget(self)
        tabs.addTab(self._about_tab(), self.tr("About"))
        tabs.addTab(self._system_tab(), self.tr("System info"))
        close_button = QPushButton(self.tr("Close"), self)
        close_button.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs, 1)
        layout.addWidget(close_button)

    def _about_tab(self) -> QWidget:
        widget = QWidget(self)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)

        # Left column: the application logo, large and vertically centred.
        icon_column = QVBoxLayout()
        icon_label = QLabel(widget)
        icon_label.setPixmap(app_icon().pixmap(160, 160))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_column.addStretch(1)
        icon_column.addWidget(icon_label)
        icon_column.addStretch(1)
        layout.addLayout(icon_column, 0)

        # Right column: program information with clickable links.
        text = QLabel(widget)
        text.setText(
            f"<h2>{__app_name__}</h2>"
            f"<p>{translate_args(self.tr('Version %1'), __version__)}</p>"
            + self.tr(
                "<p>A desktop application (Python 3 + PyQt6) that downloads YouTube "
                "subtitles using the <b>yt-dlp</b> library.</p>"
            )
            + "<hr>"
            + "<p>© 2026 Washington Indacochea Delgado</p>"
            + self.tr(
                '<p><b>Email:</b> <a href="mailto:linuxfrontier@proton.me">'
                "linuxfrontier@proton.me</a></p>"
            )
            + self.tr("<p><b>License:</b> GPL-3.0-or-later</p>")
            + self.tr(
                '<p><b>Website:</b> <a href="https://github.com/wachin/'
                'youtube-subtitle-downloader">github.com/wachin/'
                "youtube-subtitle-downloader</a></p>"
            )
            + self.tr("<p><b>Technologies used:</b> Python 3, PyQt6, yt-dlp</p>")
        )
        text.setWordWrap(True)
        text.setOpenExternalLinks(True)
        text.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        layout.addWidget(text, 1)
        return widget

    def _system_tab(self) -> QWidget:
        widget = QWidget(self)
        form = QFormLayout(widget)
        not_found = self.tr("not found")
        info = [
            (self.tr("Python"), platform.python_version()),
            (self.tr("Qt"), QT_VERSION_STR),
            (self.tr("PyQt6"), PYQT_VERSION_STR),
            (self.tr("yt-dlp"), version() or not_found),
            (self.tr("FFmpeg"), ffmpeg_version() or not_found),
            (self.tr("Operating system"), platform.platform()),
            (self.tr("Architecture"), platform.machine()),
            (self.tr("Executable"), sys.executable),
        ]
        for name, value in info:
            label = QLabel(str(value))
            label.setTextInteractionFlags(
                label.textInteractionFlags() | Qt.TextInteractionFlag.TextSelectableByMouse
            )
            form.addRow(f"{name}:", label)
        return widget
