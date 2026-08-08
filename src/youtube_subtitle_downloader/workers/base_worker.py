"""Base worker running off the GUI thread with cooperative cancellation."""

from __future__ import annotations

import threading

from PyQt6.QtCore import QThread, pyqtSignal


class BaseWorker(QThread):
    """A ``QThread`` subclass that can be stopped cleanly.

    Subclasses implement :meth:`run` and should check :meth:`is_cancelled`
    regularly. ``cancel()`` never kills the thread abruptly (no
    ``terminate()``), it just requests a cooperative stop (roadmap section 17).
    """

    log = pyqtSignal(str)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        """Request a clean stop of this worker."""
        self._cancel_event.set()
        self.cancelled.emit()

    def is_cancelled(self) -> bool:
        """True when cancellation has been requested."""
        return self._cancel_event.is_set()

    def _emit_log(self, message: str) -> None:
        self.log.emit(message)
