"""Application bootstrap."""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from . import __app_name__, __org_name__, __version__
from .utils.icons import APP_ICON_NAME, theme_icon
from .utils.logging import setup_logging


def main(argv: list[str] | None = None) -> int:
    """Run the desktop application."""
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(__org_name__)
    app.setWindowIcon(theme_icon(APP_ICON_NAME))

    setup_logging()

    # QSettings requires the names above; SettingsService may be created after.
    from .i18n import install_translator
    from .services.settings_service import SettingsService
    from .ui.main_window import MainWindow

    settings = SettingsService()
    install_translator(app, settings.language())

    window = MainWindow(settings)
    window.show()
    return app.exec()
