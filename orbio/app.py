"""Orbio application setup."""

import sys

from PyQt6.QtWebEngineWidgets import QWebEngineView  # noqa: F401 — must precede QApplication
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from orbio.browser_window import OrbioBrowserWindow


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Orbio")
    app.setApplicationVersion("0.2.0")
    app.setOrganizationName("Orbio")

    icon_path = str(__file__).replace("app.py", "assets/orbio_logo.png")
    app.setWindowIcon(QIcon(icon_path))

    window = OrbioBrowserWindow()
    window.show()

    return app.exec()
