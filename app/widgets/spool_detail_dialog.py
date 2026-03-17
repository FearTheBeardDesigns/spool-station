"""Dialog for adding/editing a spool."""

from __future__ import annotations

from datetime import date

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from app.db.models import Filament, Spool, Vendor
from app.widgets.color_swatch_widget import ColorSwatchWidget


class SpoolDetailDialog(QDialog):
    """Modal dialog for creating or editing a spool."""

    def __init__(
        self,
        vendors: list[Vendor],
        filaments: list[Filament],
        spool: Spool | None = None,
        preselect_filament_id: int | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._spool = spool
        self._vendors = vendors
        self._all_filaments = filaments
        self.setWindowTitle("EDIT SPOOL" if spool else "ADD SPOOL")
        self.setMinimumWidth(460)
        self._build_ui()
        if preselect_filament_id is not None:
            self._select_filament(preselect_filament_id)
        if spool:
            self._populate(spool)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setSpacing(8)

        # Vendor filter
        self._vendor_combo = QComboBox()
        self._vendor_combo.addItem("-- All Vendors --", None)
        for v in self._vendors:
            self._vendor_combo.addItem(v.name, v.id)
        self._vendor_combo.currentIndexChanged.connect(self._on_vendor_changed)
        self._vendor_combo.setToolTip("Filter filaments by vendor")
        form.addRow("VENDOR:", self._vendor_combo)

        # Filament (signal connected later, after all widgets exist)
        self._filament_combo = QComboBox()
        self._filament_combo.setToolTip("Select filament product for this spool")
        form.addRow("FILAMENT:", self._filament_combo)

        # Color preview
        self._color_preview = ColorSwatchWidget("#FFFFFF", size=24, show_label=True)
        form.addRow("COLOR:", self._color_preview)

        # Initial weight
        self._initial_weight = QDoubleSpinBox()
        self._initial_weight.setRange(0.0, 10000.0)
        self._initial_weight.setValue(1000.0)
        self._initial_weight.setSuffix(" g")
        self._initial_weight.setToolTip("Net filament weight when new")
        form.addRow("INITIAL WEIGHT:", self._initial_weight)

        # Used weight
        self._used_weight = QDoubleSpinBox()
        self._used_weight.setRange(0.0, 10000.0)
        self._used_weight.setSuffix(" g")
        self._used_weight.setToolTip("Total grams consumed so far")
        self._used_weight.valueChanged.connect(self._update_remaining)
        form.addRow("USED WEIGHT:", self._used_weight)

        # Remaining (computed, read-only label)
        self._remaining_label = QLabel("1000.0 g (100%)")
        self._remaining_label.setStyleSheet(
            "color: #39FF14; font-weight: bold; background: transparent;"
        )
        self._remaining_label.setToolTip("Computed remaining filament")
        form.addRow("REMAINING:", self._remaining_label)
        self._initial_weight.valueChanged.connect(self._update_remaining)

        # Location
        self._location_edit = QLineEdit()
        self._location_edit.setPlaceholderText("e.g. Shelf A, Dry Box 1")
        self._location_edit.setToolTip("Physical storage location")
        form.addRow("LOCATION:", self._location_edit)

        # Lot number
        self._lot_edit = QLineEdit()
        self._lot_edit.setPlaceholderText("Manufacturer batch/lot number")
        self._lot_edit.setToolTip("Manufacturing lot or batch number")
        form.addRow("LOT #:", self._lot_edit)

        # Purchase date
        self._purchase_date = QDateEdit()
        self._purchase_date.setCalendarPopup(True)
        self._purchase_date.setDate(QDate.currentDate())
        self._purchase_date.setToolTip("When this spool was purchased")
        form.addRow("PURCHASED:", self._purchase_date)

        # Notes
        self._notes_edit = QTextEdit()
        self._notes_edit.setMaximumHeight(60)
        self._notes_edit.setPlaceholderText("Optional notes...")
        self._notes_edit.setToolTip("Free-text notes about this spool")
        form.addRow("NOTES:", self._notes_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Connect filament signal and populate now that all widgets exist
        self._filament_combo.currentIndexChanged.connect(self._on_filament_changed)
        self._refresh_filaments()

    def _refresh_filaments(self) -> None:
        self._filament_combo.clear()
        vendor_id = self._vendor_combo.currentData()
        for f in self._all_filaments:
            if vendor_id is not None and f.vendor_id != vendor_id:
                continue
            vendor_name = f.vendor.name if f.vendor else "?"
            label = f"{vendor_name} — {f.name} ({f.material})"
            self._filament_combo.addItem(label, f.id)
        self._on_filament_changed()

    def _on_vendor_changed(self) -> None:
        self._refresh_filaments()

    def _on_filament_changed(self) -> None:
        fil_id = self._filament_combo.currentData()
        if fil_id is None:
            return
        for f in self._all_filaments:
            if f.id == fil_id:
                self._color_preview.set_color(f.color_hex or "#FFFFFF")
                self._initial_weight.setValue(f.net_weight_g)
                break

    def _select_filament(self, filament_id: int) -> None:
        for i in range(self._filament_combo.count()):
            if self._filament_combo.itemData(i) == filament_id:
                self._filament_combo.setCurrentIndex(i)
                break

    def _populate(self, s: Spool) -> None:
        # Select vendor
        if s.filament:
            for i in range(self._vendor_combo.count()):
                if self._vendor_combo.itemData(i) == s.filament.vendor_id:
                    self._vendor_combo.setCurrentIndex(i)
                    break
        self._select_filament(s.filament_id)
        self._initial_weight.setValue(s.initial_weight_g)
        self._used_weight.setValue(s.used_weight_g)
        self._location_edit.setText(s.location or "")
        self._lot_edit.setText(s.lot_nr or "")
        if s.purchase_date:
            self._purchase_date.setDate(
                QDate(s.purchase_date.year, s.purchase_date.month, s.purchase_date.day)
            )
        self._notes_edit.setPlainText(s.notes or "")

    def _update_remaining(self) -> None:
        initial = self._initial_weight.value()
        used = self._used_weight.value()
        remaining = max(0.0, initial - used)
        pct = (remaining / initial * 100) if initial > 0 else 0
        color = "#39FF14" if pct > 50 else "#FF6B00" if pct > 25 else "#FF2D95"
        self._remaining_label.setText(f"{remaining:.1f} g ({pct:.0f}%)")
        self._remaining_label.setStyleSheet(
            f"color: {color}; font-weight: bold; background: transparent;"
        )

    def get_data(self) -> dict:
        """Return form data as a dict suitable for creating/updating a Spool."""
        qdate = self._purchase_date.date()
        return {
            "filament_id": self._filament_combo.currentData(),
            "initial_weight_g": self._initial_weight.value(),
            "used_weight_g": self._used_weight.value(),
            "location": self._location_edit.text().strip() or None,
            "lot_nr": self._lot_edit.text().strip() or None,
            "purchase_date": date(qdate.year(), qdate.month(), qdate.day()),
            "notes": self._notes_edit.toPlainText().strip() or None,
        }
