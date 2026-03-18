"""Printer Edit Dialog — add or edit a printer configuration."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.prusalink.config import PrinterConfig


class PrinterEditDialog(QDialog):
    """Dialog for adding or editing a printer configuration."""

    def __init__(self, config: PrinterConfig | None = None, parent=None):
        super().__init__(parent)
        self._config = config or PrinterConfig()
        self._is_new = config is None
        self.setWindowTitle("ADD PRINTER" if self._is_new else "EDIT PRINTER")
        self.setMinimumWidth(450)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()

        # Printer name
        self._name_edit = QLineEdit(self._config.name)
        self._name_edit.setPlaceholderText("e.g. Prusa MK4, Ender 3")
        self._name_edit.setToolTip("Friendly name for this printer")
        form.addRow("NAME:", self._name_edit)

        # PrusaLink Host
        pl_row = QHBoxLayout()
        self._pl_host = QLineEdit(self._config.prusalink_host)
        self._pl_host.setPlaceholderText("192.168.1.100")
        self._pl_host.setToolTip("PrusaLink printer IP address or hostname")
        pl_row.addWidget(self._pl_host)
        pl_test = QPushButton("TEST")
        pl_test.setToolTip("Test PrusaLink connection")
        pl_test.clicked.connect(self._test_prusalink)
        pl_row.addWidget(pl_test)
        form.addRow("PRUSALINK HOST:", pl_row)

        # API Key
        self._pl_key = QLineEdit(self._config.prusalink_api_key)
        self._pl_key.setPlaceholderText("Your PrusaLink API key")
        self._pl_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._pl_key.setToolTip("PrusaLink API key (found in printer settings)")
        form.addRow("API KEY:", self._pl_key)

        # ESP32 Host
        esp_row = QHBoxLayout()
        self._esp_host = QLineEdit(self._config.esp32_host)
        self._esp_host.setPlaceholderText("192.168.1.101")
        self._esp_host.setToolTip("ESP32 NFC logger IP address for this printer")
        esp_row.addWidget(self._esp_host)
        esp_test = QPushButton("TEST")
        esp_test.setToolTip("Test ESP32 connection")
        esp_test.clicked.connect(self._test_esp32)
        esp_row.addWidget(esp_test)
        form.addRow("ESP32 HOST:", esp_row)

        layout.addLayout(form)

        # Status label for test results
        self._status = QLabel("")
        self._status.setStyleSheet(
            "color: #8888AA; font-size: 12px; background: transparent;"
        )
        layout.addWidget(self._status)

        # Auto-sync
        self._auto_sync = QCheckBox("AUTO-SYNC ON STARTUP")
        self._auto_sync.setChecked(self._config.auto_sync)
        self._auto_sync.setToolTip(
            "Automatically sync completed prints from this printer on startup"
        )
        layout.addWidget(self._auto_sync)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing Name", "Enter a printer name.")
            return
        self.accept()

    def get_config(self) -> PrinterConfig:
        """Return the edited PrinterConfig."""
        self._config.name = self._name_edit.text().strip()
        self._config.prusalink_host = self._pl_host.text().strip()
        self._config.prusalink_api_key = self._pl_key.text().strip()
        self._config.esp32_host = self._esp_host.text().strip()
        self._config.auto_sync = self._auto_sync.isChecked()
        return self._config

    def _test_prusalink(self) -> None:
        from app.prusalink.sync import test_prusalink_connection

        host = self._pl_host.text().strip()
        key = self._pl_key.text().strip()
        if not host or not key:
            QMessageBox.warning(self, "Missing", "Enter PrusaLink host and API key.")
            return

        result = test_prusalink_connection(host, key)
        if result:
            name = result.get("name", "Unknown Printer")
            self._status.setText(f"✓ PrusaLink connected — {name}")
            self._status.setStyleSheet(
                "color: #39FF14; font-size: 12px; background: transparent;"
            )
        else:
            self._status.setText("✗ Could not connect to PrusaLink")
            self._status.setStyleSheet(
                "color: #FF2D95; font-size: 12px; background: transparent;"
            )

    def _test_esp32(self) -> None:
        from app.prusalink.sync import test_esp32_connection

        host = self._esp_host.text().strip()
        if not host:
            QMessageBox.warning(self, "Missing", "Enter ESP32 host address.")
            return

        result = test_esp32_connection(host)
        if result:
            spool = result.get("active_spool_id", "None")
            state = result.get("printer_state", "UNKNOWN")
            printer_name = result.get("printer_name", "")
            label = f"✓ ESP32 connected — Spool: {spool} | State: {state}"
            if printer_name:
                label += f" | {printer_name}"
            self._status.setText(label)
            self._status.setStyleSheet(
                "color: #39FF14; font-size: 12px; background: transparent;"
            )
        else:
            self._status.setText("✗ Could not connect to ESP32")
            self._status.setStyleSheet(
                "color: #FF2D95; font-size: 12px; background: transparent;"
            )
