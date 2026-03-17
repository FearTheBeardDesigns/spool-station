"""Spool Station — Filament spool inventory manager.

Fear The Beard Designs Creative Studio
"""

from __future__ import annotations

import sys

from PyQt6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.theme import THEME_QSS


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Spool Station")
    app.setStyleSheet(THEME_QSS)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
