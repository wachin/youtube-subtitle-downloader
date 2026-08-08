"""History dialog (File → History)."""

from __future__ import annotations

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices, QGuiApplication
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ..services.settings_service import SettingsService

COLUMNS = ("Date", "Title", "URL", "Languages", "Folder")


class HistoryDialog(QDialog):
    """Show, open, copy and delete entries from the video history."""

    def __init__(self, settings: SettingsService, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("History")
        self.resize(760, 420)

        layout = QVBoxLayout(self)
        self._table = QTableWidget(0, len(COLUMNS), self)
        self._table.setHorizontalHeaderLabels(COLUMNS)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.doubleClicked.connect(self._open_selected_url)
        layout.addWidget(self._table, 1)

        buttons = QHBoxLayout()
        open_url = QPushButton("Open URL", self)
        open_url.clicked.connect(self._open_selected_url)
        open_folder = QPushButton("Open folder", self)
        open_folder.clicked.connect(self._open_selected_folder)
        copy_url = QPushButton("Copy URL", self)
        copy_url.clicked.connect(self._copy_selected_url)
        buttons.addWidget(open_url)
        buttons.addWidget(open_folder)
        buttons.addWidget(copy_url)
        buttons.addStretch(1)
        delete_button = QPushButton("Delete entry", self)
        delete_button.clicked.connect(self._delete_selected)
        clear_button = QPushButton("Clear all", self)
        clear_button.clicked.connect(self._clear_all)
        close_button = QPushButton("Close", self)
        close_button.clicked.connect(self.accept)
        buttons.addWidget(delete_button)
        buttons.addWidget(clear_button)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        self._reload()

    def _reload(self) -> None:
        items = self._settings.history()
        self._table.setRowCount(len(items))
        for row, entry in enumerate(items):
            values = [
                entry.get("date", ""),
                entry.get("title", ""),
                entry.get("url", ""),
                ", ".join(entry.get("languages", [])),
                entry.get("folder", ""),
            ]
            for column, value in enumerate(values):
                self._table.setItem(row, column, QTableWidgetItem(str(value)))
        if not items:
            self._table.setRowCount(1)
            self._table.setItem(0, 1, QTableWidgetItem("No history yet."))

    def _selected_row(self) -> int:
        rows = self._table.selectionModel().selectedRows()
        return rows[0].row() if rows else -1

    def _entry_at(self, row: int) -> dict | None:
        items = self._settings.history()
        if 0 <= row < len(items):
            return items[row]
        return None

    def _open_selected_url(self, *_args) -> None:
        entry = self._entry_at(self._selected_row())
        if entry and entry.get("url"):
            QDesktopServices.openUrl(QUrl(entry["url"]))

    def _open_selected_folder(self) -> None:
        entry = self._entry_at(self._selected_row())
        folder = (entry or {}).get("folder", "")
        if folder:
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def _copy_selected_url(self) -> None:
        entry = self._entry_at(self._selected_row())
        if entry and entry.get("url"):
            QGuiApplication.clipboard().setText(entry["url"])

    def _delete_selected(self) -> None:
        row = self._selected_row()
        if row >= 0:
            self._settings.remove_history(row)
            self._reload()

    def _clear_all(self) -> None:
        if not self._settings.history():
            return
        answer = QMessageBox.question(
            self,
            "Clear history",
            "Delete the whole history? This cannot be undone.",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._settings.clear_history()
            self._reload()
