"""QAbstractTableModel backing the subtitle language table."""

from __future__ import annotations

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, pyqtSignal

from ..models.subtitle import SubtitleKind, SubtitleTrack, searchable_names

COLUMNS = ("", "Language", "Code", "Type", "Formats")


def _is_checked(value) -> bool:
    """Return True when *value* represents a checked checkbox.

    The view delegate hands check states to ``setData`` as plain integers
    (``2`` for checked, ``0`` for unchecked). On PyQt6 6.9+ the
    ``Qt.CheckState`` enum no longer compares equal to integers, so compare
    through the enum constructor instead of ``value == Qt.CheckState.Checked``.
    """
    return Qt.CheckState(value) == Qt.CheckState.Checked


class SubtitleTableModel(QAbstractTableModel):
    """Table of subtitle tracks with a checkable first column."""

    checked_changed = pyqtSignal(int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._tracks: list[SubtitleTrack] = []
        self._checked: set[int] = set()
        self._kind_filter: SubtitleKind | None = None
        self._text_filter = ""

    # -- setup ------------------------------------------------------------
    def set_tracks(self, tracks: list[SubtitleTrack]) -> None:
        self.beginResetModel()
        self._tracks = list(tracks)
        self._checked = set()
        self.endResetModel()
        self.checked_changed.emit(len(self._checked))

    def set_filter(self, kind: SubtitleKind | None = None, text: str = "") -> None:
        self._kind_filter = kind
        self._text_filter = (text or "").strip().lower()
        self.layoutChanged.emit()

    def _visible_indices(self) -> list[int]:
        indices = []
        for index, track in enumerate(self._tracks):
            if self._kind_filter is not None and track.kind is not self._kind_filter:
                continue
            if self._text_filter:
                haystack = " ".join(
                    [
                        track.display_name,
                        track.language_name,
                        track.language_code,
                        track.base_code,
                        *searchable_names(track.language_code),
                    ]
                ).lower()
                if self._text_filter not in haystack:
                    continue
            indices.append(index)
        return indices

    # -- selection helpers ------------------------------------------------
    def track_at(self, row: int) -> SubtitleTrack | None:
        """Return the track currently displayed at *row* (honoring the filter)."""
        indices = self._visible_indices()
        if 0 <= row < len(indices):
            return self._tracks[indices[row]]
        return None

    def checked_tracks(self) -> list[SubtitleTrack]:
        visible = set(self._visible_indices())
        return [self._tracks[i] for i in sorted(self._checked) if i in visible]

    def checked_count(self) -> int:
        return len(self._checked)

    def check_all(self, checked: bool = True) -> None:
        self._checked = set(range(len(self._tracks))) if checked else set()
        self.layoutChanged.emit()
        self.checked_changed.emit(len(self._checked))

    def check_kind(self, kind: SubtitleKind, checked: bool = True) -> None:
        for index, track in enumerate(self._tracks):
            if track.kind is kind:
                if checked:
                    self._checked.add(index)
                else:
                    self._checked.discard(index)
        self.layoutChanged.emit()
        self.checked_changed.emit(len(self._checked))

    def auto_select_preferred(self, language_code: str) -> None:
        """Select tracks matching the user preferred language, if any."""
        target = language_code.strip().lower()
        if not target:
            return
        for index, track in enumerate(self._tracks):
            if track.base_code.lower() == target:
                self._checked.add(index)
        self.layoutChanged.emit()
        self.checked_changed.emit(len(self._checked))

    # -- Qt model API -----------------------------------------------------
    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._visible_indices())

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802
        return len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            return COLUMNS[section]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        original = self._visible_indices()[index.row()]
        track = self._tracks[original]
        column = index.column()

        if column == 0:
            if role == Qt.ItemDataRole.CheckStateRole:
                return (
                    Qt.CheckState.Checked
                    if original in self._checked
                    else Qt.CheckState.Unchecked
                )
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            if column == 1:
                return track.display_name
            if column == 2:
                return track.language_code
            if column == 3:
                return track.kind.display_name
            if column == 4:
                return ", ".join(track.formats)
            return None

        if role == Qt.ItemDataRole.ToolTipRole:
            return f"{track.display_name} ({track.language_code})"

        if role == Qt.ItemDataRole.TextAlignmentRole and column in (0, 3):
            return int(Qt.AlignmentFlag.AlignCenter)

        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() == 0:
            flags |= Qt.ItemFlag.ItemIsUserCheckable
        return flags

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if (
            index.isValid()
            and index.column() == 0
            and role == Qt.ItemDataRole.CheckStateRole
        ):
            original = self._visible_indices()[index.row()]
            if _is_checked(value):
                self._checked.add(original)
            else:
                self._checked.discard(original)
            self.dataChanged.emit(
                index, index, [Qt.ItemDataRole.CheckStateRole]
            )
            self.checked_changed.emit(len(self._checked))
            return True
        return False
