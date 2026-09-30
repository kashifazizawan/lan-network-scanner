"""Dark/light theme QSS for a professional IT look."""
from __future__ import annotations

DARK_QSS = """
* { font-family: 'Segoe UI', 'Inter', sans-serif; }
QMainWindow, QDialog { background-color: #1e2127; color: #e8eaed; }
QWidget { color: #e8eaed; font-size: 13px; }
QToolBar { background-color: #23262e; border: none; padding: 6px 8px; spacing: 6px; }
QToolButton { background: #2b2f38; border: 1px solid #3a3f4b; border-radius: 4px; padding: 5px 12px; color: #e8eaed; }
QToolButton:hover { background: #343945; }
QToolButton:disabled { color: #666; background: #23262e; }
QPushButton { background: #2b6cb0; color: white; border: none; border-radius: 4px; padding: 6px 16px; font-weight: 600; }
QPushButton:hover { background: #3182ce; }
QPushButton:disabled { background: #3a3f4b; color: #7a7f8a; }
QPushButton[accent="danger"] { background: #c53030; }
QPushButton[accent="danger"]:hover { background: #e53e3e; }
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
    background: #2b2f38; border: 1px solid #3a3f4b; border-radius: 4px; padding: 5px 8px; color: #e8eaed;
}
QComboBox:disabled, QLineEdit:disabled { color: #7a7f8a; }
QComboBox::drop-down { border: none; }
QTableWidget {
    background: #23262e; alternate-background-color: #282c35; gridline-color: #333842;
    border: 1px solid #3a3f4b; border-radius: 4px; selection-background-color: #2b6cb0;
}
QHeaderView::section {
    background: #2b2f38; color: #c3c8d0; padding: 6px; border: none; border-right: 1px solid #3a3f4b; font-weight: 600;
}
QTableWidget::item { padding: 4px 6px; }
QTabWidget::pane { border: 1px solid #3a3f4b; border-radius: 4px; }
QTabBar::tab { background: #23262e; padding: 8px 18px; color: #9aa0ab; border: 1px solid #3a3f4b; border-bottom: none; }
QTabBar::tab:selected { background: #2b6cb0; color: white; }
QStatusBar { background: #23262e; color: #9aa0ab; border-top: 1px solid #3a3f4b; }
QProgressBar { background: #2b2f38; border: 1px solid #3a3f4b; border-radius: 3px; text-align: center; color: #e8eaed; }
QProgressBar::chunk { background: #2b6cb0; border-radius: 3px; }
QMenu { background: #2b2f38; border: 1px solid #3a3f4b; }
QMenu::item:selected { background: #2b6cb0; color: white; }
QToolTip { background: #2b2f38; color: #e8eaed; border: 1px solid #3a3f4b; padding: 4px; }
QGroupBox { border: 1px solid #3a3f4b; border-radius: 5px; margin-top: 10px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
QSplitter::handle { background: #3a3f4b; }
QTreeWidget { background: #23262e; border: 1px solid #3a3f4b; }
QLabel#infoTitle { color: #9aa0ab; font-size: 11px; }
QLabel#infoValue { color: #e8eaed; font-size: 14px; font-weight: 600; }
QLabel#statusDot { font-size: 13px; }
"""

LIGHT_QSS = """
* { font-family: 'Segoe UI', 'Inter', sans-serif; }
QMainWindow, QDialog { background-color: #f5f6f8; color: #1a202c; }
QWidget { color: #1a202c; font-size: 13px; }
QToolBar { background-color: #ffffff; border-bottom: 1px solid #dde2e9; padding: 6px 8px; spacing: 6px; }
QToolButton { background: #eef1f5; border: 1px solid #d3dae4; border-radius: 4px; padding: 5px 12px; }
QToolButton:hover { background: #e2e8f0; }
QPushButton { background: #2b6cb0; color: white; border: none; border-radius: 4px; padding: 6px 16px; font-weight: 600; }
QPushButton:hover { background: #3182ce; }
QPushButton:disabled { background: #cbd5e0; color: #718096; }
QPushButton[accent="danger"] { background: #c53030; }
QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {
    background: #ffffff; border: 1px solid #cbd5e0; border-radius: 4px; padding: 5px 8px;
}
QTableWidget {
    background: #ffffff; alternate-background-color: #f7fafc; gridline-color: #e2e8f0;
    border: 1px solid #d3dae4; selection-background-color: #bee3f8; selection-color: #1a202c;
}
QHeaderView::section { background: #eef1f5; color: #4a5568; padding: 6px; border: none; border-right: 1px solid #d3dae4; font-weight: 600; }
QTabBar::tab { background: #eef1f5; padding: 8px 18px; color: #718096; border: 1px solid #d3dae4; border-bottom: none; }
QTabBar::tab:selected { background: #2b6cb0; color: white; }
QStatusBar { background: #ffffff; color: #718096; border-top: 1px solid #dde2e9; }
QProgressBar { background: #eef1f5; border: 1px solid #d3dae4; border-radius: 3px; text-align: center; }
QProgressBar::chunk { background: #2b6cb0; border-radius: 3px; }
QMenu { background: #ffffff; border: 1px solid #d3dae4; }
QMenu::item:selected { background: #2b6cb0; color: white; }
QToolTip { background: #ffffff; color: #1a202c; border: 1px solid #cbd5e0; padding: 4px; }
QGroupBox { border: 1px solid #d3dae4; border-radius: 5px; margin-top: 10px; font-weight: 600; background: white; }
QTreeWidget { background: #ffffff; border: 1px solid #d3dae4; }
QLabel#infoTitle { color: #718096; font-size: 11px; }
QLabel#infoValue { color: #1a202c; font-size: 14px; font-weight: 600; }
"""

ONLINE_COLOR = "#22a06b"
OFFLINE_COLOR = "#c53030"
UNKNOWN_COLOR = "#9aa0ab"


def apply_theme(app, theme: str = "dark") -> str:
    from PySide6.QtWidgets import QApplication  # noqa: F401

    qss = DARK_QSS if theme == "dark" else LIGHT_QSS
    app.setStyleSheet(qss)
    return theme
