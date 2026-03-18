"""Main window for Spool Station."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.db.engine import init_db
from app.widgets.inventory_panel import InventoryPanel
from app.widgets.profiles_panel import ProfilesPanel
from app.widgets.settings_panel import SettingsPanel
from app.widgets.vendors_panel import VendorsPanel


class MainWindow(QMainWindow):
    """Spool Station main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SPOOL STATION — Fear The Beard Designs")
        self.setMinimumSize(1100, 700)

        # Initialize database
        init_db()

        # Build UI
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header bar
        main_layout.addWidget(self._build_header())

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setMinimumWidth(380)

        self._inventory_panel = InventoryPanel()
        self._vendors_panel = VendorsPanel()
        self._profiles_panel = ProfilesPanel()
        self._settings_panel = SettingsPanel()

        self._tabs.addTab(self._inventory_panel, "\u26A1 Inventory")
        self._tabs.addTab(self._vendors_panel, "\u26A1 Vendors")
        self._tabs.addTab(self._profiles_panel, "\u26A1 Profiles")
        self._tabs.addTab(self._settings_panel, "\u26A1 Settings")
        self._tabs.tabBar().setExpanding(False)
        self._tabs.setUsesScrollButtons(True)

        # Refresh relevant panels when switching tabs
        self._tabs.currentChanged.connect(self._on_tab_changed)

        main_layout.addWidget(self._tabs)

        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        # Start API server
        self._start_api()

        # Auto-sync from ESP32 on startup (delayed to let UI finish loading)
        QTimer.singleShot(2000, self._auto_sync)

        # Periodic background sync every 5 minutes
        self._sync_timer = QTimer(self)
        self._sync_timer.timeout.connect(self._background_sync)
        self._sync_timer.start(5 * 60 * 1000)

    def _build_header(self) -> QWidget:
        """Build the branded header bar."""
        header = QWidget()
        header.setObjectName("headerBar")
        header.setFixedHeight(56)

        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(12, 0, 12, 0)
        h_layout.setSpacing(12)

        # Logo
        logo_path = Path(__file__).parent.parent / "resources" / "logo.png"
        if logo_path.exists():
            logo_label = QLabel()
            pix = QPixmap(str(logo_path))
            if not pix.isNull():
                pix = pix.scaled(
                    40, 40,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                logo_label.setPixmap(pix)
                logo_label.setFixedSize(40, 40)
                h_layout.addWidget(logo_label)

        # Title
        title = QLabel("SPOOL STATION")
        title.setStyleSheet(
            "color: #00FFFF; font-size: 24px; font-weight: bold; "
            "font-family: 'Consolas', monospace; background: transparent;"
        )
        h_layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("F E A R  T H E  B E A R D  D E S I G N S")
        subtitle.setStyleSheet(
            "color: #FF2D95; font-size: 14px; font-weight: bold; "
            "font-family: 'Consolas', monospace; background: transparent;"
        )
        h_layout.addWidget(subtitle)

        h_layout.addStretch()

        # Decorative dots
        dots = QLabel(
            '<span style="color:#FF2D95;">\u25cf</span> '
            '<span style="color:#B026FF;">\u25cf</span> '
            '<span style="color:#00FFFF;">\u25cf</span>'
        )
        dots.setStyleSheet("font-size: 14px; background: transparent;")
        h_layout.addWidget(dots)

        return header

    def _on_tab_changed(self, index: int) -> None:
        """Refresh panel data when switching tabs."""
        widget = self._tabs.widget(index)
        if hasattr(widget, "refresh"):
            widget.refresh()

    def _start_api(self) -> None:
        """Start the embedded FastAPI server."""
        try:
            from app.api.server import start_api_server

            port = self._settings_panel.get_api_port()
            start_api_server(port)
            self._settings_panel.set_api_status(True)
            self._status_bar.showMessage(
                f"API running on http://localhost:{port}/api/v1/  |  Ready"
            )
        except Exception as e:
            self._settings_panel.set_api_status(False)
            self._status_bar.showMessage(f"API failed to start: {e}")

    def _auto_sync(self) -> None:
        """Auto-sync completed prints from ESP32 on startup if enabled."""
        try:
            from app.prusalink.config import load_config
            from app.prusalink.sync import sync_pending_prints

            config = load_config()
            if not config.auto_sync or not config.esp32_host:
                return

            result = sync_pending_prints(config)
            if result.prints_synced > 0:
                self._status_bar.showMessage(
                    f"Auto-sync: {result.summary}", 10000
                )
                # Refresh inventory if visible
                self._inventory_panel.refresh()
            elif result.errors:
                self._status_bar.showMessage(
                    f"Auto-sync: {result.summary}", 10000
                )
        except Exception:
            pass  # Silent fail on startup — don't block the app

    def _background_sync(self) -> None:
        """Periodic background sync (every 5 minutes)."""
        try:
            from app.prusalink.config import load_config
            from app.prusalink.sync import sync_pending_prints

            config = load_config()
            if not config.auto_sync or not config.esp32_host:
                return

            result = sync_pending_prints(config)
            if result.prints_synced > 0:
                self._status_bar.showMessage(
                    f"Background sync: {result.summary}", 10000
                )
                self._inventory_panel.refresh()
        except Exception:
            pass
