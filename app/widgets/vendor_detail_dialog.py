"""Dialog for adding/editing a vendor."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from app.db.models import Vendor


class VendorDetailDialog(QDialog):
    """Modal dialog for creating or editing a vendor."""

    def __init__(self, vendor: Vendor | None = None, parent=None) -> None:
        super().__init__(parent)
        self._vendor = vendor
        self.setWindowTitle("EDIT VENDOR" if vendor else "ADD VENDOR")
        self.setMinimumWidth(420)
        self._build_ui()
        if vendor:
            self._populate(vendor)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setSpacing(10)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. Hatchbox, Prusament, eSUN")
        self._name_edit.setToolTip("Manufacturer name")
        form.addRow("NAME:", self._name_edit)

        self._website_edit = QLineEdit()
        self._website_edit.setPlaceholderText("https://...")
        self._website_edit.setToolTip("Vendor website URL")
        form.addRow("WEBSITE:", self._website_edit)

        self._spool_weight = QDoubleSpinBox()
        self._spool_weight.setRange(0.0, 500.0)
        self._spool_weight.setSuffix(" g")
        self._spool_weight.setDecimals(1)
        self._spool_weight.setToolTip("Default empty spool weight for this vendor")
        form.addRow("EMPTY SPOOL WEIGHT:", self._spool_weight)

        self._notes_edit = QTextEdit()
        self._notes_edit.setMaximumHeight(80)
        self._notes_edit.setPlaceholderText("Optional notes...")
        self._notes_edit.setToolTip("Free-text notes about this vendor")
        form.addRow("NOTES:", self._notes_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate(self, v: Vendor) -> None:
        self._name_edit.setText(v.name or "")
        self._website_edit.setText(v.website or "")
        if v.empty_spool_weight_g:
            self._spool_weight.setValue(v.empty_spool_weight_g)
        self._notes_edit.setPlainText(v.notes or "")

    def get_data(self) -> dict:
        """Return form data as a dict suitable for creating/updating a Vendor."""
        data = {
            "name": self._name_edit.text().strip(),
            "website": self._website_edit.text().strip() or None,
            "empty_spool_weight_g": self._spool_weight.value() or None,
            "notes": self._notes_edit.toPlainText().strip() or None,
        }
        return data
