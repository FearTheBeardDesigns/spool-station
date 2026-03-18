"""Settings panel — API port, slicer paths, database management."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.prusalink.config import PrinterConfig, load_config, save_config


def _detect_prusaslicer_dir() -> str:
    """Auto-detect PrusaSlicer config directory."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", ""))
        p = base / "PrusaSlicer" / "filament"
    elif sys.platform == "darwin":
        p = Path.home() / "Library" / "Application Support" / "PrusaSlicer" / "filament"
    else:
        p = Path.home() / ".config" / "PrusaSlicer" / "filament"
    return str(p) if p.exists() else ""


def _detect_orcaslicer_dir() -> str:
    """Auto-detect OrcaSlicer config directory."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", ""))
        p = base / "OrcaSlicer" / "user"
    elif sys.platform == "darwin":
        p = Path.home() / "Library" / "Application Support" / "OrcaSlicer" / "user"
    else:
        p = Path.home() / ".config" / "OrcaSlicer" / "user"
    return str(p) if p.exists() else ""


class SettingsPanel(QWidget):
    """Application settings."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # API Settings
        api_group = QGroupBox("API SERVER")
        api_layout = QVBoxLayout(api_group)

        port_row = QHBoxLayout()
        port_row.addWidget(QLabel("PORT:"))
        self._port_spin = QSpinBox()
        self._port_spin.setRange(1024, 65535)
        self._port_spin.setValue(7912)
        self._port_spin.setToolTip("Port for the REST API server (default: 7912)")
        port_row.addWidget(self._port_spin)

        self._api_status = QLabel("\u25cf RUNNING")
        self._api_status.setStyleSheet(
            "color: #39FF14; font-weight: bold; background: transparent;"
        )
        self._api_status.setToolTip("API server status")
        port_row.addWidget(self._api_status)
        port_row.addStretch()
        api_layout.addLayout(port_row)

        url_label = QLabel("http://localhost:7912/api/v1/")
        url_label.setStyleSheet(
            "color: #00FFFF; font-size: 13px; background: transparent;"
        )
        url_label.setToolTip("Base URL for the REST API")
        api_layout.addWidget(url_label)

        layout.addWidget(api_group)

        # Slicer Paths
        slicer_group = QGroupBox("SLICER PATHS")
        slicer_layout = QVBoxLayout(slicer_group)

        prusa_row = QHBoxLayout()
        prusa_row.addWidget(QLabel("PRUSASLICER:"))
        self._prusa_path = QLineEdit(_detect_prusaslicer_dir())
        self._prusa_path.setToolTip("PrusaSlicer filament profile directory")
        prusa_row.addWidget(self._prusa_path)
        prusa_browse = QPushButton("BROWSE")
        prusa_browse.setToolTip("Browse for PrusaSlicer directory")
        prusa_browse.clicked.connect(lambda: self._browse(self._prusa_path))
        prusa_row.addWidget(prusa_browse)
        slicer_layout.addLayout(prusa_row)

        orca_row = QHBoxLayout()
        orca_row.addWidget(QLabel("ORCASLICER:"))
        self._orca_path = QLineEdit(_detect_orcaslicer_dir())
        self._orca_path.setToolTip("OrcaSlicer user profile directory")
        orca_row.addWidget(self._orca_path)
        orca_browse = QPushButton("BROWSE")
        orca_browse.setToolTip("Browse for OrcaSlicer directory")
        orca_browse.clicked.connect(lambda: self._browse(self._orca_path))
        orca_row.addWidget(orca_browse)
        slicer_layout.addLayout(orca_row)

        layout.addWidget(slicer_group)

        # Logo Station Integration
        logo_group = QGroupBox("LOGO STATION INTEGRATION")
        logo_layout = QVBoxLayout(logo_group)

        self._logo_enabled = QCheckBox("ENABLE COLOR API")
        self._logo_enabled.setChecked(True)
        self._logo_enabled.setToolTip(
            "Expose filament color inventory at /api/v1/colors for Logo Station"
        )
        logo_layout.addWidget(self._logo_enabled)

        info = QLabel(
            "Logo Station can query available colors at:\n"
            "http://localhost:7912/api/v1/colors"
        )
        info.setStyleSheet(
            "color: #8888AA; font-size: 13px; background: transparent;"
        )
        logo_layout.addWidget(info)

        layout.addWidget(logo_group)

        # Database
        db_group = QGroupBox("DATABASE")
        db_layout = QVBoxLayout(db_group)

        from app.db.engine import DB_PATH

        db_path_label = QLabel(f"PATH: {DB_PATH}")
        db_path_label.setStyleSheet(
            "color: #8888AA; font-size: 12px; background: transparent;"
        )
        db_path_label.setWordWrap(True)
        db_layout.addWidget(db_path_label)

        db_btn_row = QHBoxLayout()
        export_btn = QPushButton("EXPORT DB")
        export_btn.setToolTip("Export database as a backup file")
        export_btn.clicked.connect(self._export_db)
        db_btn_row.addWidget(export_btn)

        import_btn = QPushButton("IMPORT DB")
        import_btn.setToolTip("Import a database backup")
        import_btn.clicked.connect(self._import_db)
        db_btn_row.addWidget(import_btn)

        db_btn_row.addStretch()
        db_layout.addLayout(db_btn_row)

        layout.addWidget(db_group)

        # Printer Tracking (ESP32 + PrusaLink)
        printer_group = QGroupBox("PRINTER TRACKING")
        printer_layout = QVBoxLayout(printer_group)

        # Load saved config
        self._printer_config = load_config()

        # PrusaLink Host
        pl_row = QHBoxLayout()
        pl_row.addWidget(QLabel("PRUSALINK HOST:"))
        self._pl_host = QLineEdit(self._printer_config.prusalink_host)
        self._pl_host.setPlaceholderText("192.168.1.100")
        self._pl_host.setToolTip("PrusaLink printer IP address or hostname")
        pl_row.addWidget(self._pl_host)

        pl_test = QPushButton("TEST")
        pl_test.setToolTip("Test PrusaLink connection")
        pl_test.clicked.connect(self._test_prusalink)
        pl_row.addWidget(pl_test)
        printer_layout.addLayout(pl_row)

        # PrusaLink API Key
        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("API KEY:"))
        self._pl_key = QLineEdit(self._printer_config.prusalink_api_key)
        self._pl_key.setPlaceholderText("Your PrusaLink API key")
        self._pl_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._pl_key.setToolTip("PrusaLink API key (found in printer settings)")
        key_row.addWidget(self._pl_key)
        printer_layout.addLayout(key_row)

        # ESP32 Host
        esp_row = QHBoxLayout()
        esp_row.addWidget(QLabel("ESP32 HOST:"))
        self._esp_host = QLineEdit(self._printer_config.esp32_host)
        self._esp_host.setPlaceholderText("192.168.1.101")
        self._esp_host.setToolTip("ESP32 NFC logger IP address")
        esp_row.addWidget(self._esp_host)

        esp_test = QPushButton("TEST")
        esp_test.setToolTip("Test ESP32 connection")
        esp_test.clicked.connect(self._test_esp32)
        esp_row.addWidget(esp_test)
        printer_layout.addLayout(esp_row)

        # ESP32 status
        self._esp_status = QLabel("")
        self._esp_status.setStyleSheet(
            "color: #8888AA; font-size: 12px; background: transparent;"
        )
        printer_layout.addWidget(self._esp_status)

        # Auto-sync checkbox
        self._auto_sync = QCheckBox("AUTO-SYNC ON STARTUP")
        self._auto_sync.setChecked(self._printer_config.auto_sync)
        self._auto_sync.setToolTip(
            "Automatically sync completed prints from ESP32 when Spool Station starts"
        )
        printer_layout.addWidget(self._auto_sync)

        # Sync now + Save
        sync_row = QHBoxLayout()
        sync_btn = QPushButton("SYNC NOW")
        sync_btn.setObjectName("primaryButton")
        sync_btn.setToolTip("Manually sync completed prints from ESP32")
        sync_btn.clicked.connect(self._sync_now)
        sync_row.addWidget(sync_btn)

        save_printer_btn = QPushButton("SAVE")
        save_printer_btn.setToolTip("Save printer tracking configuration")
        save_printer_btn.clicked.connect(self._save_printer_config)
        sync_row.addWidget(save_printer_btn)

        sync_row.addStretch()
        printer_layout.addLayout(sync_row)

        layout.addWidget(printer_group)
        layout.addStretch()

    def _browse(self, line_edit: QLineEdit) -> None:
        path = QFileDialog.getExistingDirectory(self, "SELECT DIRECTORY")
        if path:
            line_edit.setText(path)

    def _export_db(self) -> None:
        import shutil

        from app.db.engine import DB_PATH

        dest, _ = QFileDialog.getSaveFileName(
            self, "EXPORT DATABASE", "spool_station_backup.db", "SQLite (*.db)"
        )
        if dest:
            shutil.copy2(str(DB_PATH), dest)

    def _import_db(self) -> None:
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.information(
            self,
            "Import",
            "Database import requires restarting the application.\n"
            "Replace the database file manually and restart.",
        )

    def get_api_port(self) -> int:
        return self._port_spin.value()

    def get_prusa_path(self) -> str:
        return self._prusa_path.text().strip()

    def get_orca_path(self) -> str:
        return self._orca_path.text().strip()

    def _save_printer_config(self) -> None:
        """Save printer tracking settings to disk."""
        self._printer_config.prusalink_host = self._pl_host.text().strip()
        self._printer_config.prusalink_api_key = self._pl_key.text().strip()
        self._printer_config.esp32_host = self._esp_host.text().strip()
        self._printer_config.auto_sync = self._auto_sync.isChecked()
        save_config(self._printer_config)
        QMessageBox.information(self, "Saved", "Printer tracking settings saved.")

    def _test_prusalink(self) -> None:
        """Test PrusaLink connection."""
        from app.prusalink.sync import test_prusalink_connection

        host = self._pl_host.text().strip()
        key = self._pl_key.text().strip()
        if not host or not key:
            QMessageBox.warning(self, "Missing", "Enter PrusaLink host and API key.")
            return

        result = test_prusalink_connection(host, key)
        if result:
            name = result.get("name", "Unknown Printer")
            QMessageBox.information(
                self, "Connected", f"PrusaLink connected!\nPrinter: {name}"
            )
        else:
            QMessageBox.warning(
                self, "Failed", "Could not connect to PrusaLink.\nCheck host and API key."
            )

    def _test_esp32(self) -> None:
        """Test ESP32 connection."""
        from app.prusalink.sync import test_esp32_connection

        host = self._esp_host.text().strip()
        if not host:
            QMessageBox.warning(self, "Missing", "Enter ESP32 host address.")
            return

        result = test_esp32_connection(host)
        if result:
            spool = result.get("active_spool_id", "None")
            state = result.get("printer_state", "UNKNOWN")
            self._esp_status.setText(
                f"ESP32 connected — Active spool: {spool} | Printer: {state}"
            )
            self._esp_status.setStyleSheet(
                "color: #39FF14; font-size: 12px; background: transparent;"
            )
            QMessageBox.information(self, "Connected", "ESP32 connected!")
        else:
            self._esp_status.setText("ESP32 not reachable")
            self._esp_status.setStyleSheet(
                "color: #FF2D95; font-size: 12px; background: transparent;"
            )
            QMessageBox.warning(
                self, "Failed", "Could not connect to ESP32.\nCheck the IP address."
            )

    def _sync_now(self) -> None:
        """Run a manual sync from ESP32."""
        from app.prusalink.sync import sync_pending_prints

        host = self._pl_host.text().strip()
        key = self._pl_key.text().strip()
        esp = self._esp_host.text().strip()

        if not esp:
            QMessageBox.warning(self, "Missing", "Enter ESP32 host address.")
            return

        config = PrinterConfig(
            prusalink_host=host,
            prusalink_api_key=key,
            esp32_host=esp,
        )
        result = sync_pending_prints(config)
        QMessageBox.information(self, "Sync Result", result.summary)

    def get_printer_config(self) -> PrinterConfig:
        """Return current printer config (from saved file)."""
        return load_config()

    def set_api_status(self, running: bool) -> None:
        if running:
            self._api_status.setText("\u25cf RUNNING")
            self._api_status.setStyleSheet(
                "color: #39FF14; font-weight: bold; background: transparent;"
            )
        else:
            self._api_status.setText("\u25cf STOPPED")
            self._api_status.setStyleSheet(
                "color: #FF2D95; font-weight: bold; background: transparent;"
            )
