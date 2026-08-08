"""About and system information dialog."""

from __future__ import annotations

import platform
import sys

from PyQt6.QtCore import PYQT_VERSION_STR, QT_VERSION_STR, Qt
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .. import __app_name__, __version__
from ..i18n import translate_args
from ..services.ytdlp_service import YtDlpService, ffmpeg_version, version


class AboutDialog(QDialog):
    """About tab plus a system information tab."""

    def __init__(self, settings=None, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle(self.tr("About"))
        self.resize(460, 360)

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
        layout = QVBoxLayout(widget)
        label = QLabel(
            f"<h2>{__app_name__}</h2>"
            f"<p>{translate_args(self.tr('Version %1'), __version__)}</p>"
            + self.tr(
                "<p>A desktop application (Python 3 + PyQt6) that downloads YouTube "
                "subtitles using the <b>yt-dlp</b> library. English is the primary "
                "language; Spanish is the first translation.</p>"
            )
            + self.tr("<p>Licensed under the <b>GNU GPL v3 or later</b>.</p>")
        )
        label.setWordWrap(True)
        label.setOpenExternalLinks(True)
        layout.addWidget(label)
        layout.addStretch(1)
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
