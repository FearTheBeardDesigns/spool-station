"""Settings panel — API port, slicer paths, database management, printer tracking."""

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
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.prusalink.config import (
    PrinterConfig,
    load_all_configs,
    load_config,
    save_all_configs,
)


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
        self._printer_configs: list[PrinterConfig] = []
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

        # Printer Tracking (multi-printer)
        printer_group = QGroupBox("PRINTER TRACKING")
        printer_layout = QVBoxLayout(printer_group)

        # Printer table
        self._printer_table = QTableWidget()
        self._printer_table.setColumnCount(4)
        self._printer_table.setHorizontalHeaderLabels([
            "NAME", "PRUSALINK HOST", "ESP32 HOST", "AUTO-SYNC",
        ])
        self._printer_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._printer_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._printer_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._printer_table.setMaximumHeight(160)
        self._printer_table.setToolTip("Configured printers with ESP32 NFC readers")
        self._printer_table.doubleClicked.connect(self._edit_printer)
        printer_layout.addWidget(self._printer_table)

        # Printer buttons
        printer_btn_row = QHBoxLayout()

        add_btn = QPushButton("ADD PRINTER")
        add_btn.setObjectName("primaryButton")
        add_btn.setToolTip("Add a new printer with ESP32 NFC reader")
        add_btn.clicked.connect(self._add_printer)
        printer_btn_row.addWidget(add_btn)

        edit_btn = QPushButton("EDIT")
        edit_btn.setToolTip("Edit selected printer configuration")
        edit_btn.clicked.connect(self._edit_printer)
        printer_btn_row.addWidget(edit_btn)

        remove_btn = QPushButton("REMOVE")
        remove_btn.setToolTip("Remove selected printer")
        remove_btn.clicked.connect(self._remove_printer)
        printer_btn_row.addWidget(remove_btn)

        sync_all_btn = QPushButton("SYNC ALL")
        sync_all_btn.setToolTip("Sync completed prints from all configured printers")
        sync_all_btn.clicked.connect(self._sync_all)
        printer_btn_row.addWidget(sync_all_btn)

        printer_btn_row.addStretch()
        printer_layout.addLayout(printer_btn_row)

        layout.addWidget(printer_group)
        layout.addStretch()

        # Load printer configs into table
        self._load_printer_table()

    def _load_printer_table(self) -> None:
        """Load all printer configs and populate the table."""
        self._printer_configs = load_all_configs()
        self._printer_table.setRowCount(len(self._printer_configs))
        for i, cfg in enumerate(self._printer_configs):
            name_item = QTableWidgetItem(cfg.name or f"Printer {i + 1}")
            name_item.setData(Qt.ItemDataRole.UserRole, cfg.id)
            self._printer_table.setItem(i, 0, name_item)
            self._printer_table.setItem(i, 1, QTableWidgetItem(cfg.prusalink_host))
            self._printer_table.setItem(i, 2, QTableWidgetItem(cfg.esp32_host))
            sync_text = "Yes" if cfg.auto_sync else "No"
            self._printer_table.setItem(i, 3, QTableWidgetItem(sync_text))

    def _get_selected_printer_index(self) -> int | None:
        row = self._printer_table.currentRow()
        return row if row >= 0 else None

    def _add_printer(self) -> None:
        from app.widgets.printer_edit_dialog import PrinterEditDialog

        dlg = PrinterEditDialog(parent=self)
        if dlg.exec() == PrinterEditDialog.DialogCode.Accepted:
            config = dlg.get_config()
            self._printer_configs.append(config)
            save_all_configs(self._printer_configs)
            self._load_printer_table()

    def _edit_printer(self) -> None:
        idx = self._get_selected_printer_index()
        if idx is None:
            return

        from app.widgets.printer_edit_dialog import PrinterEditDialog

        config = self._printer_configs[idx]
        dlg = PrinterEditDialog(config=config, parent=self)
        if dlg.exec() == PrinterEditDialog.DialogCode.Accepted:
            self._printer_configs[idx] = dlg.get_config()
            save_all_configs(self._printer_configs)
            self._load_printer_table()

    def _remove_printer(self) -> None:
        idx = self._get_selected_printer_index()
        if idx is None:
            return

        name = self._printer_configs[idx].name or f"Printer {idx + 1}"
        reply = QMessageBox.question(
            self,
            "Remove Printer",
            f"Remove printer '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._printer_configs.pop(idx)
            save_all_configs(self._printer_configs)
            self._load_printer_table()

    def _sync_all(self) -> None:
        """Sync all configured printers."""
        from app.prusalink.sync import sync_all_printers

        configs = [c for c in self._printer_configs if c.esp32_host]
        if not configs:
            QMessageBox.information(
                self, "No Printers", "Add a printer with an ESP32 host first."
            )
            return

        result = sync_all_printers(configs)
        QMessageBox.information(self, "Sync Result", result.summary)

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

    def get_printer_config(self) -> PrinterConfig:
        """Return first printer config (backward compat)."""
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
