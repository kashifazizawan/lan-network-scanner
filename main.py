#!/usr/bin/env python3
"""LAN Network Scanner — entry point.

Usage:
    python main.py            normal launch
    python main.py --sample   launch and load sample data (no scanning)
"""
from __future__ import annotations

import sys


def main() -> int:
    from app.logger import setup_logging, install_excepthook
    log_path = setup_logging()

    from PySide6.QtWidgets import QApplication, QMessageBox
    from PySide6.QtCore import Qt

    # High-DPI support on Windows
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("LAN Network Scanner")
    app.setOrganizationName("LanScanner")

    from app.config import load_settings
    from app.ui.theme import apply_theme
    from app.ui.main_window import MainWindow

    settings = load_settings()
    apply_theme(app, settings.theme)

    win = MainWindow(settings)

    def show_error(text: str):
        QMessageBox.critical(None, "Unexpected error", text)

    install_excepthook(show_error)

    win.show()
    if "--sample" in sys.argv:
        win._load_sample_data()

    import logging
    logging.getLogger("lanscanner").info("Application started (log: %s)", log_path)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
