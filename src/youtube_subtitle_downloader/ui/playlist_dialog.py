"""Playlist selection dialog."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from ..models.video import PlaylistEntry, PlaylistInfo


class PlaylistDialog(QDialog):
    """List playlist entries with checkboxes so the user can pick videos."""

    def __init__(self, playlist: PlaylistInfo, parent=None) -> None:
        super().__init__(parent)
        self._playlist = playlist
        self._items: list[tuple[QListWidgetItem, PlaylistEntry]] = []
        self.setWindowTitle("Playlist")
        self.resize(680, 480)

        layout = QVBoxLayout(self)
        title = QLabel(
            f"<b>{playlist.title}</b> ({playlist.count} video(s)) — "
            "select the videos to process"
        )
        title.setWordWrap(True)
        layout.addWidget(title)

        self._list = QListWidget(self)
        for entry in playlist.entries:
            duration = (
                f"{entry.duration // 60}:{entry.duration % 60:02d}"
                if entry.duration
                else "?"
            )
            channel = entry.channel or "unknown channel"
            item = QListWidgetItem(f"{entry.title}  —  {channel}  ({duration})")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setToolTip(entry.url)
            self._list.addItem(item)
            self._items.append((item, entry))
        layout.addWidget(self._list, 1)

        select_row = QHBoxLayout()
        all_button = QPushButton("Select all", self)
        all_button.clicked.connect(lambda: self._set_all(Qt.CheckState.Checked))
        none_button = QPushButton("Select none", self)
        none_button.clicked.connect(lambda: self._set_all(Qt.CheckState.Unchecked))
        select_row.addWidget(all_button)
        select_row.addWidget(none_button)
        select_row.addStretch(1)
        layout.addLayout(select_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _set_all(self, state: Qt.CheckState) -> None:
        for item, _entry in self._items:
            item.setCheckState(state)

    def selected_entries(self) -> list[PlaylistEntry]:
        return [
            entry
            for item, entry in self._items
            if item.checkState() == Qt.CheckState.Checked
        ]
