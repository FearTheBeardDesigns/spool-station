"""Fear The Beard Designs — 80s Retro Neon theme for PyQt6."""

from __future__ import annotations


class Colors:
    """Named color constants for use in Python code."""

    # Neon accents
    PINK = "#FF2D95"
    CYAN = "#00FFFF"
    PURPLE = "#B026FF"
    GREEN = "#39FF14"
    ORANGE = "#FF6B00"
    YELLOW = "#FFE500"
    BLUE = "#00A2FF"

    # Backgrounds (darkest to lightest)
    BG_DARKEST = "#0A0A0F"
    BG_DARK = "#12121A"
    BG_MEDIUM = "#1A1A2E"
    BG_PANEL = "#16162A"
    BG_INPUT = "#0E0E1A"
    BG_HOVER = "#222240"

    # Text
    TEXT_PRIMARY = "#E0E0F0"
    TEXT_SECONDARY = "#8888AA"
    TEXT_MUTED = "#555577"

    # Borders
    BORDER_SUBTLE = "#2A2A44"
    BORDER_GLOW = "#00FFFF"


THEME_QSS = """
/* ================================================================
   Fear The Beard Designs — 80s Retro Neon Theme (Spool Station)
   ================================================================ */

/* --- Root / Universal --- */
* {
    background-color: #12121A;
    color: #E0E0F0;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 17px;
    font-weight: bold;
}

QMainWindow {
    background-color: #12121A;
}

/* --- Toolbar --- */
QToolBar {
    background-color: #0A0A0F;
    border-bottom: 2px solid #00FFFF;
    spacing: 6px;
    padding: 4px;
}
QToolBar QToolButton {
    background-color: #1A1A2E;
    color: #E0E0F0;
    border: 1px solid #2A2A44;
    border-radius: 4px;
    padding: 4px 12px;
    font-family: "Consolas", monospace;
    font-weight: bold;
}
QToolBar QToolButton:hover {
    border-color: #00FFFF;
    color: #00FFFF;
}
QToolBar QToolButton:pressed {
    border-color: #FF2D95;
    color: #FF2D95;
}

/* --- Tabs --- */
QTabWidget::pane {
    background-color: #12121A;
    border: 1px solid #2A2A44;
    border-top: none;
}
QTabBar::tab {
    background-color: #16162A;
    color: #8888AA;
    border: 1px solid #2A2A44;
    border-bottom: 2px solid transparent;
    padding: 8px 16px;
    font-family: "Consolas", monospace;
    font-size: 17px;
    font-weight: bold;
}
QTabBar::tab:selected {
    background-color: #1A1A2E;
    color: #00FFFF;
    border-bottom: 2px solid #00FFFF;
}
QTabBar::tab:hover:!selected {
    color: #FF2D95;
    border-color: #FF2D95;
}

/* --- Buttons --- */
QPushButton {
    background-color: #1A1A2E;
    color: #E0E0F0;
    border: 1px solid #2A2A44;
    border-radius: 4px;
    padding: 6px 16px;
    font-family: "Consolas", monospace;
    font-weight: bold;
}
QPushButton:hover {
    border-color: #00FFFF;
    color: #00FFFF;
}
QPushButton:pressed {
    border-color: #FF2D95;
    color: #FF2D95;
}
QPushButton:disabled {
    background-color: #0A0A0F;
    color: #555577;
}

/* --- Primary Button (pink-to-purple gradient) --- */
QPushButton#primaryButton {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #FF2D95, stop:1 #B026FF);
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 32px;
    font-size: 18px;
}
QPushButton#primaryButton:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #00FFFF, stop:1 #00A2FF);
}

/* --- Secondary Button (cyan-to-blue gradient) --- */
QPushButton#secondaryButton {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #00FFFF, stop:1 #00A2FF);
    color: #0A0A0F;
    border: none;
    border-radius: 6px;
    padding: 10px 32px;
    font-size: 17px;
}
QPushButton#secondaryButton:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #39FF14, stop:1 #00FFFF);
}

/* --- Transfer Button (orange-to-yellow gradient) --- */
QPushButton#transferButton {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #FF6B00, stop:1 #FFE500);
    color: #0A0A0F;
    border: none;
    border-radius: 6px;
    padding: 10px 32px;
    font-size: 17px;
    font-weight: bold;
}
QPushButton#transferButton:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #FFE500, stop:1 #FF6B00);
}

/* --- Text Inputs --- */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0E0E1A;
    color: #39FF14;
    border: 1px solid #2A2A44;
    border-radius: 4px;
    padding: 4px 8px;
    font-family: "Consolas", monospace;
    selection-background-color: #B026FF;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #00FFFF;
}

/* --- Spin Boxes --- */
QSpinBox, QDoubleSpinBox {
    background-color: #0E0E1A;
    color: #39FF14;
    border: 1px solid #2A2A44;
    border-radius: 4px;
    padding: 4px 8px;
    font-family: "Consolas", monospace;
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #00FFFF;
}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {
    background-color: #1A1A2E;
    border: 1px solid #2A2A44;
    width: 20px;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #222240;
}

/* --- Combo Boxes --- */
QComboBox {
    background-color: #0E0E1A;
    color: #39FF14;
    border: 1px solid #2A2A44;
    border-radius: 4px;
    padding: 4px 8px;
    font-family: "Consolas", monospace;
}
QComboBox:focus {
    border-color: #00FFFF;
}
QComboBox::drop-down {
    background-color: #1A1A2E;
    border: 1px solid #2A2A44;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #0E0E1A;
    color: #39FF14;
    border: 1px solid #2A2A44;
    selection-background-color: #B026FF;
}

/* --- Date Edit --- */
QDateEdit {
    background-color: #0E0E1A;
    color: #39FF14;
    border: 1px solid #2A2A44;
    border-radius: 4px;
    padding: 4px 8px;
    font-family: "Consolas", monospace;
}
QDateEdit:focus {
    border-color: #00FFFF;
}

/* --- Radio Buttons --- */
QRadioButton {
    spacing: 8px;
    color: #E0E0F0;
    background: transparent;
}
QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #2A2A44;
    border-radius: 10px;
    background-color: #0E0E1A;
}
QRadioButton::indicator:checked {
    background-color: #00FFFF;
    border-color: #00FFFF;
}
QRadioButton::indicator:hover {
    border-color: #FF2D95;
}

/* --- Check Boxes --- */
QCheckBox {
    spacing: 8px;
    color: #E0E0F0;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #2A2A44;
    border-radius: 3px;
    background-color: #0E0E1A;
}
QCheckBox::indicator:checked {
    background-color: #00FFFF;
    border-color: #00FFFF;
}
QCheckBox::indicator:hover {
    border-color: #FF2D95;
}

/* --- Group Boxes --- */
QGroupBox {
    background-color: #16162A;
    border: 1px solid #2A2A44;
    border-radius: 8px;
    margin-top: 16px;
    padding-top: 24px;
    font-family: "Consolas", monospace;
}
QGroupBox::title {
    color: #B026FF;
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    font-weight: bold;
    letter-spacing: 1px;
}

/* --- Scroll Bars --- */
QScrollBar:vertical {
    background: #0A0A0F;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #2A2A44;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #B026FF;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #0A0A0F;
    height: 10px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #2A2A44;
    border-radius: 5px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: #B026FF;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* --- Table Widget --- */
QTableWidget, QTableView {
    background-color: #0E0E1A;
    color: #E0E0F0;
    border: 1px solid #2A2A44;
    gridline-color: #2A2A44;
    font-family: "Consolas", monospace;
    selection-background-color: #B026FF;
    selection-color: white;
}
QHeaderView::section {
    background-color: #16162A;
    color: #B026FF;
    border: 1px solid #2A2A44;
    padding: 6px;
    font-family: "Consolas", monospace;
    font-weight: bold;
}
QHeaderView::section:hover {
    color: #00FFFF;
}

/* --- List Widget --- */
QListWidget {
    background-color: #0E0E1A;
    color: #E0E0F0;
    border: 1px solid #2A2A44;
    font-family: "Consolas", monospace;
}
QListWidget::item:selected {
    background-color: #B026FF;
    color: white;
}
QListWidget::item:hover {
    background-color: #222240;
}

/* --- Progress Bar --- */
QProgressBar {
    background-color: #0A0A0F;
    border: 1px solid #2A2A44;
    border-radius: 4px;
    text-align: center;
    color: #00FFFF;
    font-weight: bold;
}
QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #FF2D95, stop:0.5 #B026FF, stop:1 #00FFFF);
    border-radius: 3px;
}

/* --- Splitter --- */
QSplitter::handle {
    background-color: #2A2A44;
}
QSplitter::handle:hover {
    background-color: #00FFFF;
}

/* --- Status Bar --- */
QStatusBar {
    background-color: #0A0A0F;
    color: #8888AA;
    border-top: 1px solid #2A2A44;
    font-family: "Consolas", monospace;
    font-size: 17px;
}

/* --- Header Bar --- */
QWidget#headerBar {
    background-color: #0A0A0F;
    border-bottom: 2px solid #00FFFF;
}

/* --- Tooltips --- */
QToolTip {
    background-color: #16162A;
    color: #E0E0F0;
    border: 1px solid #B026FF;
    padding: 4px 8px;
    font-family: "Consolas", monospace;
    font-size: 14px;
}
"""
