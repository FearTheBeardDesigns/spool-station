"""Inventory panel — main spool inventory table with filters."""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sqlalchemy.orm import joinedload

from app.db.engine import get_session
from app.db.models import Filament, Spool, UsageLog, Vendor
from app.widgets.color_swatch_widget import ColorSwatchWidget
from app.widgets.spool_detail_dialog import SpoolDetailDialog


class InventoryPanel(QWidget):
    """Main spool inventory table with filters and actions."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Filter row
        filter_row = QHBoxLayout()

        filter_row.addWidget(QLabel("MATERIAL:"))
        self._material_filter = QComboBox()
        self._material_filter.addItem("All")
        self._material_filter.setToolTip("Filter spools by material type")
        self._material_filter.currentIndexChanged.connect(self._apply_filters)
        filter_row.addWidget(self._material_filter)

        filter_row.addWidget(QLabel("LOCATION:"))
        self._location_filter = QComboBox()
        self._location_filter.addItem("All")
        self._location_filter.setToolTip("Filter spools by storage location")
        self._location_filter.currentIndexChanged.connect(self._apply_filters)
        filter_row.addWidget(self._location_filter)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search...")
        self._search_edit.setToolTip("Search by filament name, vendor, or color")
        self._search_edit.textChanged.connect(self._apply_filters)
        filter_row.addWidget(self._search_edit)

        self._show_archived = QCheckBox("SHOW ARCHIVED")
        self._show_archived.setToolTip("Include archived (empty/retired) spools")
        self._show_archived.stateChanged.connect(self._apply_filters)
        filter_row.addWidget(self._show_archived)

        layout.addLayout(filter_row)

        # Main table
        self._table = QTableWidget()
        self._table.setColumnCount(9)
        self._table.setHorizontalHeaderLabels([
            "COLOR", "FILAMENT", "VENDOR", "MATERIAL",
            "REMAINING", "%", "LENGTH", "LOCATION", "LAST USED",
        ])
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSortingEnabled(True)
        self._table.setToolTip("Your filament spool inventory")
        self._table.doubleClicked.connect(self._edit_spool)
        layout.addWidget(self._table)

        # Action buttons
        btn_row = QHBoxLayout()

        add_btn = QPushButton("ADD SPOOL")
        add_btn.setObjectName("primaryButton")
        add_btn.setToolTip("Add a new spool to inventory")
        add_btn.clicked.connect(self._add_spool)
        btn_row.addWidget(add_btn)

        edit_btn = QPushButton("EDIT")
        edit_btn.setToolTip("Edit selected spool")
        edit_btn.clicked.connect(self._edit_spool)
        btn_row.addWidget(edit_btn)

        use_btn = QPushButton("USE FILAMENT")
        use_btn.setObjectName("transferButton")
        use_btn.setToolTip("Log filament usage for the selected spool")
        use_btn.clicked.connect(self._use_filament)
        btn_row.addWidget(use_btn)

        archive_btn = QPushButton("ARCHIVE")
        archive_btn.setToolTip("Mark spool as archived (empty/retired)")
        archive_btn.clicked.connect(self._archive_spool)
        btn_row.addWidget(archive_btn)

        nfc_btn = QPushButton("WRITE NFC TAG")
        nfc_btn.setToolTip("Write the selected spool's ID to an NFC tag via ESP32")
        nfc_btn.clicked.connect(self._write_nfc_tag)
        btn_row.addWidget(nfc_btn)

        sync_btn = QPushButton("SYNC PRINTER")
        sync_btn.setObjectName("transferButton")
        sync_btn.setToolTip("Sync completed prints from ESP32 and deduct filament usage")
        sync_btn.clicked.connect(self._sync_printer)
        btn_row.addWidget(sync_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def refresh(self) -> None:
        """Reload all spools from database."""
        self._table.setSortingEnabled(False)

        # Collect filter options
        materials = set()
        locations = set()

        session = get_session()
        try:
            query = (
                session.query(Spool)
                .options(
                    joinedload(Spool.filament).joinedload(Filament.vendor)
                )
                .order_by(Spool.id)
            )

            spools = query.all()

            # Collect unique materials and locations for filter dropdowns
            for s in spools:
                materials.add(s.filament.material)
                if s.location:
                    locations.add(s.location)

            # Update filter dropdowns (preserve selection)
            current_mat = self._material_filter.currentText()
            current_loc = self._location_filter.currentText()
            self._material_filter.blockSignals(True)
            self._location_filter.blockSignals(True)
            self._material_filter.clear()
            self._material_filter.addItem("All")
            for m in sorted(materials):
                self._material_filter.addItem(m)
            self._location_filter.clear()
            self._location_filter.addItem("All")
            for loc in sorted(locations):
                self._location_filter.addItem(loc)
            # Restore selection
            idx = self._material_filter.findText(current_mat)
            if idx >= 0:
                self._material_filter.setCurrentIndex(idx)
            idx = self._location_filter.findText(current_loc)
            if idx >= 0:
                self._location_filter.setCurrentIndex(idx)
            self._material_filter.blockSignals(False)
            self._location_filter.blockSignals(False)

            # Populate table
            self._all_spools_data = []
            for s in spools:
                self._all_spools_data.append({
                    "id": s.id,
                    "color_hex": s.filament.color_hex or "#FFFFFF",
                    "filament_name": s.filament.name,
                    "vendor_name": s.filament.vendor.name if s.filament.vendor else "?",
                    "material": s.filament.material,
                    "remaining_g": s.remaining_weight_g,
                    "remaining_pct": s.remaining_percent,
                    "remaining_m": s.remaining_length_m,
                    "location": s.location or "",
                    "last_used": s.last_used,
                    "archived": s.archived,
                })
        finally:
            session.close()

        self._apply_filters()
        self._table.setSortingEnabled(True)

    def _apply_filters(self) -> None:
        """Filter and display spools based on current filter settings."""
        mat_filter = self._material_filter.currentText()
        loc_filter = self._location_filter.currentText()
        search = self._search_edit.text().strip().lower()
        show_archived = self._show_archived.isChecked()

        filtered = []
        for d in getattr(self, "_all_spools_data", []):
            if not show_archived and d["archived"]:
                continue
            if mat_filter != "All" and d["material"] != mat_filter:
                continue
            if loc_filter != "All" and d["location"] != loc_filter:
                continue
            if search:
                haystack = f"{d['filament_name']} {d['vendor_name']} {d['color_hex']} {d['material']} {d['location']}".lower()
                if search not in haystack:
                    continue
            filtered.append(d)

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(filtered))

        for i, d in enumerate(filtered):
            # Color swatch
            swatch = ColorSwatchWidget(d["color_hex"], size=20, show_label=True)
            self._table.setCellWidget(i, 0, swatch)

            # Filament name
            item = QTableWidgetItem(d["filament_name"])
            item.setData(Qt.ItemDataRole.UserRole, d["id"])
            self._table.setItem(i, 1, item)

            # Vendor
            self._table.setItem(i, 2, QTableWidgetItem(d["vendor_name"]))

            # Material
            self._table.setItem(i, 3, QTableWidgetItem(d["material"]))

            # Remaining weight
            self._table.setItem(
                i, 4, QTableWidgetItem(f"{d['remaining_g']:.0f} g")
            )

            # Remaining % (colored)
            pct = d["remaining_pct"]
            pct_item = QTableWidgetItem(f"{pct:.0f}%")
            if pct > 50:
                pct_item.setForeground(Qt.GlobalColor.green)
            elif pct > 25:
                pct_item.setForeground(Qt.GlobalColor.yellow)
            else:
                pct_item.setForeground(Qt.GlobalColor.red)
            self._table.setItem(i, 5, pct_item)

            # Length
            length_str = f"{d['remaining_m']:.1f} m" if d["remaining_m"] else "—"
            self._table.setItem(i, 6, QTableWidgetItem(length_str))

            # Location
            self._table.setItem(i, 7, QTableWidgetItem(d["location"]))

            # Last used
            last = d["last_used"]
            last_str = last.strftime("%Y-%m-%d") if last else "Never"
            self._table.setItem(i, 8, QTableWidgetItem(last_str))

        self._table.setSortingEnabled(True)

    def _get_selected_spool_id(self) -> int | None:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 1)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _add_spool(self) -> None:
        session = get_session()
        try:
            vendors = session.query(Vendor).order_by(Vendor.name).all()
            filaments = (
                session.query(Filament)
                .options(joinedload(Filament.vendor))
                .order_by(Filament.name)
                .all()
            )
            if not filaments:
                QMessageBox.information(
                    self, "No Filaments", "Add a vendor and filament first.\n\n"
                    "Go to the VENDORS tab, click IMPORT PRESET to load a "
                    "manufacturer catalog, then return here to add spools."
                )
                return
            dlg = SpoolDetailDialog(
                vendors=vendors, filaments=filaments, parent=self
            )
            if dlg.exec() == SpoolDetailDialog.DialogCode.Accepted:
                data = dlg.get_data()
                if data.get("filament_id") is None:
                    QMessageBox.warning(self, "Error", "No filament selected.")
                    return
                spool = Spool(**data)
                session.add(spool)
                session.commit()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error Adding Spool", str(e))
        finally:
            session.close()
        self.refresh()

    def _edit_spool(self) -> None:
        spool_id = self._get_selected_spool_id()
        if spool_id is None:
            return
        session = get_session()
        try:
            spool = session.get(Spool, spool_id)
            if not spool:
                return
            vendors = session.query(Vendor).order_by(Vendor.name).all()
            filaments = (
                session.query(Filament)
                .options(joinedload(Filament.vendor))
                .order_by(Filament.name)
                .all()
            )
            dlg = SpoolDetailDialog(
                vendors=vendors, filaments=filaments, spool=spool, parent=self
            )
            if dlg.exec() == SpoolDetailDialog.DialogCode.Accepted:
                data = dlg.get_data()
                for k, v in data.items():
                    setattr(spool, k, v)
                spool.updated_at = datetime.utcnow()
                session.commit()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error Editing Spool", str(e))
        finally:
            session.close()
        self.refresh()

    def _use_filament(self) -> None:
        """Quick-use dialog: log filament consumption."""
        spool_id = self._get_selected_spool_id()
        if spool_id is None:
            QMessageBox.information(self, "No Selection", "Select a spool first.")
            return

        from PyQt6.QtWidgets import QDialog, QDialogButtonBox

        dlg = QDialog(self)
        dlg.setWindowTitle("USE FILAMENT")
        dlg.setMinimumWidth(320)
        form_layout = QVBoxLayout(dlg)

        form = QFormLayout()
        weight_spin = QDoubleSpinBox()
        weight_spin.setRange(0.1, 5000.0)
        weight_spin.setValue(10.0)
        weight_spin.setSuffix(" g")
        weight_spin.setToolTip("Grams of filament used")
        form.addRow("AMOUNT USED:", weight_spin)

        source_combo = QComboBox()
        source_combo.addItems(["manual", "prusaslicer", "orcaslicer", "other"])
        source_combo.setToolTip("Source of usage (how was it tracked)")
        form.addRow("SOURCE:", source_combo)

        project_edit = QLineEdit()
        project_edit.setPlaceholderText("Optional project name")
        project_edit.setToolTip("What was printed")
        form.addRow("PROJECT:", project_edit)

        form_layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form_layout.addWidget(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        session = get_session()
        try:
            spool = session.get(Spool, spool_id)
            if not spool:
                return
            used = weight_spin.value()
            spool.used_weight_g += used
            spool.last_used = datetime.utcnow()
            if spool.first_used is None:
                spool.first_used = datetime.utcnow()

            log = UsageLog(
                spool_id=spool_id,
                used_weight_g=used,
                source=source_combo.currentText(),
                project_name=project_edit.text().strip() or None,
            )
            session.add(log)
            session.commit()
        finally:
            session.close()
        self.refresh()

    def _archive_spool(self) -> None:
        spool_id = self._get_selected_spool_id()
        if spool_id is None:
            return
        session = get_session()
        try:
            spool = session.get(Spool, spool_id)
            if not spool:
                return
            spool.archived = not spool.archived
            spool.updated_at = datetime.utcnow()
            session.commit()
        finally:
            session.close()
        self.refresh()

    def _write_nfc_tag(self) -> None:
        """Open NFC write dialog for the selected spool."""
        spool_id = self._get_selected_spool_id()
        if spool_id is None:
            QMessageBox.information(self, "No Selection", "Select a spool first.")
            return

        from app.prusalink.config import load_config
        from app.widgets.nfc_write_dialog import NfcWriteDialog

        config = load_config()
        if not config.esp32_host:
            QMessageBox.warning(
                self,
                "No ESP32 Configured",
                "Set the ESP32 host address in Settings → Printer Tracking first.",
            )
            return

        session = get_session()
        try:
            spool = (
                session.query(Spool)
                .options(joinedload(Spool.filament).joinedload(Filament.vendor))
                .filter(Spool.id == spool_id)
                .first()
            )
            if not spool:
                return

            dlg = NfcWriteDialog(
                spool_id=spool.id,
                spool_name=spool.filament.name,
                vendor_name=spool.filament.vendor.name if spool.filament.vendor else "?",
                color_hex=spool.filament.color_hex or "#FFFFFF",
                material=spool.filament.material,
                remaining_g=spool.remaining_weight_g,
                esp32_host=config.esp32_host,
                parent=self,
            )
            dlg.exec()
        finally:
            session.close()

    def _sync_printer(self) -> None:
        """Manually sync completed prints from ESP32."""
        from app.prusalink.config import PrinterConfig, load_config
        from app.prusalink.sync import sync_pending_prints

        config = load_config()
        if not config.esp32_host:
            QMessageBox.warning(
                self,
                "No ESP32 Configured",
                "Set the ESP32 host address in Settings → Printer Tracking first.",
            )
            return

        result = sync_pending_prints(config)
        QMessageBox.information(self, "Sync Result", result.summary)
        if result.prints_synced > 0:
            self.refresh()
