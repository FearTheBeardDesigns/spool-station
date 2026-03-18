"""NFC Write Dialog — write spool IDs to NFC tags via ESP32."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.widgets.color_swatch_widget import ColorSwatchWidget


class _NfcWriteWorker(QThread):
    """Background thread for NFC write operation."""

    finished = pyqtSignal(bool, str)  # success, message

    def __init__(self, esp32_host: str, spool_id: int, parent=None):
        super().__init__(parent)
        self.esp32_host = esp32_host
        self.spool_id = spool_id

    def run(self):
        import json
        import urllib.request

        url = f"http://{self.esp32_host}:8080/nfc/write"
        body = json.dumps({"spool_id": self.spool_id}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "SpoolStation/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("ok"):
                    self.finished.emit(True, "NFC tag written successfully!")
                else:
                    self.finished.emit(False, data.get("error", "Write failed"))
        except Exception as e:
            self.finished.emit(False, f"Connection error: {e}")


class _NfcReadWorker(QThread):
    """Background thread for NFC read operation."""

    finished = pyqtSignal(bool, str)  # success, message

    def __init__(self, esp32_host: str, parent=None):
        super().__init__(parent)
        self.esp32_host = esp32_host

    def run(self):
        import json
        import urllib.request

        url = f"http://{self.esp32_host}:8080/nfc/read"
        req = urllib.request.Request(
            url, headers={"User-Agent": "SpoolStation/1.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                spool_id = data.get("spool_id")
                if spool_id:
                    self.finished.emit(True, f"Tag contains spool ID: {spool_id}")
                else:
                    self.finished.emit(True, "No tag detected or tag is blank")
        except Exception as e:
            self.finished.emit(False, f"Connection error: {e}")


class NfcWriteDialog(QDialog):
    """Dialog for writing a spool ID to an NFC tag via ESP32."""

    def __init__(
        self,
        spool_id: int,
        spool_name: str,
        vendor_name: str,
        color_hex: str,
        material: str,
        remaining_g: float,
        esp32_host: str,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("WRITE NFC TAG")
        self.setMinimumWidth(400)
        self._spool_id = spool_id
        self._esp32_host = esp32_host
        self._worker = None
        self._build_ui(spool_name, vendor_name, color_hex, material, remaining_g)

    def _build_ui(
        self,
        spool_name: str,
        vendor_name: str,
        color_hex: str,
        material: str,
        remaining_g: float,
    ) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Spool info header
        info_label = QLabel("SPOOL TO WRITE")
        info_label.setStyleSheet(
            "color: #00FFFF; font-size: 14px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(info_label)

        # Color + details row
        detail_row = QHBoxLayout()
        swatch = ColorSwatchWidget(color_hex, size=40, show_label=True)
        detail_row.addWidget(swatch)

        details = QLabel(
            f"<b>{vendor_name}</b> — {spool_name}<br>"
            f"{material} | {remaining_g:.0f}g remaining<br>"
            f"Spool ID: {self._spool_id}"
        )
        details.setStyleSheet(
            "color: #DDDDDD; font-size: 13px; background: transparent;"
        )
        detail_row.addWidget(details)
        detail_row.addStretch()
        layout.addLayout(detail_row)

        # Instructions
        instructions = QLabel(
            "1. Place a blank NTAG213 tag on the NFC reader\n"
            "2. Click WRITE to program the tag with this spool's ID\n"
            "3. Stick the tag on the physical spool"
        )
        instructions.setStyleSheet(
            "color: #8888AA; font-size: 12px; background: transparent;"
        )
        layout.addWidget(instructions)

        # Status
        self._status_label = QLabel("Ready — place tag on reader")
        self._status_label.setStyleSheet(
            "color: #FFD700; font-size: 13px; font-weight: bold; "
            "background: transparent; padding: 8px;"
        )
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)

        # Buttons
        btn_row = QHBoxLayout()

        self._write_btn = QPushButton("WRITE TAG")
        self._write_btn.setObjectName("primaryButton")
        self._write_btn.setToolTip("Write spool ID to the NFC tag on the reader")
        self._write_btn.clicked.connect(self._write_tag)
        btn_row.addWidget(self._write_btn)

        read_btn = QPushButton("READ TAG")
        read_btn.setToolTip("Read the current NFC tag to verify")
        read_btn.clicked.connect(self._read_tag)
        btn_row.addWidget(read_btn)

        close_btn = QPushButton("CLOSE")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def _write_tag(self) -> None:
        """Write spool ID to NFC tag via ESP32."""
        self._write_btn.setEnabled(False)
        self._status_label.setText("Writing tag...")
        self._status_label.setStyleSheet(
            "color: #FFD700; font-size: 13px; font-weight: bold; "
            "background: transparent; padding: 8px;"
        )

        self._worker = _NfcWriteWorker(self._esp32_host, self._spool_id, self)
        self._worker.finished.connect(self._on_write_done)
        self._worker.start()

    def _on_write_done(self, success: bool, message: str) -> None:
        self._write_btn.setEnabled(True)
        if success:
            self._status_label.setText(f"✓ {message}")
            self._status_label.setStyleSheet(
                "color: #39FF14; font-size: 13px; font-weight: bold; "
                "background: transparent; padding: 8px;"
            )
        else:
            self._status_label.setText(f"✗ {message}")
            self._status_label.setStyleSheet(
                "color: #FF2D95; font-size: 13px; font-weight: bold; "
                "background: transparent; padding: 8px;"
            )

    def _read_tag(self) -> None:
        """Read current NFC tag via ESP32."""
        self._status_label.setText("Reading tag...")
        self._status_label.setStyleSheet(
            "color: #FFD700; font-size: 13px; font-weight: bold; "
            "background: transparent; padding: 8px;"
        )

        self._worker = _NfcReadWorker(self._esp32_host, self)
        self._worker.finished.connect(self._on_read_done)
        self._worker.start()

    def _on_read_done(self, success: bool, message: str) -> None:
        if success:
            self._status_label.setText(f"✓ {message}")
            self._status_label.setStyleSheet(
                "color: #00FFFF; font-size: 13px; font-weight: bold; "
                "background: transparent; padding: 8px;"
            )
        else:
            self._status_label.setText(f"✗ {message}")
            self._status_label.setStyleSheet(
                "color: #FF2D95; font-size: 13px; font-weight: bold; "
                "background: transparent; padding: 8px;"
            )
