"""Vendors panel — two-pane: vendor list (left), filaments for selected vendor (right)."""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.db.engine import get_session
from app.db.models import Filament, Vendor
from app.db.seed_data import SEED_VENDORS
from app.db.spoolmandb import fetch_spoolmandb, group_by_manufacturer, map_to_filament_data
from app.widgets.color_swatch_widget import ColorSwatchWidget
from app.widgets.filament_detail_dialog import FilamentDetailDialog
from app.widgets.vendor_detail_dialog import VendorDetailDialog


class VendorsPanel(QWidget):
    """Two-pane vendor/filament management."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Vendor list
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel("MANUFACTURERS")
        lbl.setStyleSheet(
            "color: #B026FF; font-weight: bold; font-size: 14px; background: transparent;"
        )
        left_layout.addWidget(lbl)

        self._vendor_list = QListWidget()
        self._vendor_list.currentRowChanged.connect(self._on_vendor_selected)
        self._vendor_list.setToolTip("Select a vendor to see their filaments")
        left_layout.addWidget(self._vendor_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("ADD")
        add_btn.setObjectName("secondaryButton")
        add_btn.setToolTip("Add a new vendor")
        add_btn.clicked.connect(self._add_vendor)
        btn_row.addWidget(add_btn)

        import_btn = QPushButton("IMPORT PRESET")
        import_btn.setObjectName("primaryButton")
        import_btn.setToolTip("Import a manufacturer with pre-loaded filament catalog")
        import_btn.clicked.connect(self._import_preset)
        btn_row.addWidget(import_btn)

        self._update_btn = QPushButton("UPDATE CATALOG")
        self._update_btn.setToolTip("Merge new filaments from latest preset into selected vendor")
        self._update_btn.clicked.connect(self._update_catalog)
        self._update_btn.setEnabled(False)
        btn_row.addWidget(self._update_btn)

        spoolmandb_btn = QPushButton("SPOOLMANDB")
        spoolmandb_btn.setToolTip("Import filaments from community SpoolmanDB database")
        spoolmandb_btn.clicked.connect(self._import_spoolmandb)
        btn_row.addWidget(spoolmandb_btn)

        edit_btn = QPushButton("EDIT")
        edit_btn.setToolTip("Edit selected vendor")
        edit_btn.clicked.connect(self._edit_vendor)
        btn_row.addWidget(edit_btn)

        del_btn = QPushButton("DELETE")
        del_btn.setToolTip("Delete selected vendor")
        del_btn.clicked.connect(self._delete_vendor)
        btn_row.addWidget(del_btn)
        left_layout.addLayout(btn_row)

        splitter.addWidget(left)

        # Right: Filament table
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Header row with label + material filter
        header_row = QHBoxLayout()
        self._filament_label = QLabel("FILAMENTS")
        self._filament_label.setStyleSheet(
            "color: #B026FF; font-weight: bold; font-size: 14px; background: transparent;"
        )
        header_row.addWidget(self._filament_label)
        header_row.addStretch()

        filter_lbl = QLabel("MATERIAL:")
        filter_lbl.setStyleSheet("color: #E0E0F0; background: transparent;")
        header_row.addWidget(filter_lbl)
        self._material_filter = QComboBox()
        self._material_filter.addItem("All")
        self._material_filter.setMinimumWidth(100)
        self._material_filter.setToolTip("Filter filaments by material type")
        self._material_filter.currentTextChanged.connect(self._on_material_filter_changed)
        header_row.addWidget(self._material_filter)

        self._fav_filter = QCheckBox("FAVORITES")
        self._fav_filter.setToolTip("Show only favorite filaments")
        self._fav_filter.stateChanged.connect(self._on_material_filter_changed)
        header_row.addWidget(self._fav_filter)
        right_layout.addLayout(header_row)

        self._filament_table = QTableWidget()
        self._filament_table.setColumnCount(9)
        self._filament_table.setHorizontalHeaderLabels(
            ["\u2605", "COLOR", "NAME", "MATERIAL", "TENSILE", "DIAMETER", "DENSITY", "TEMP", "PRICE"]
        )
        self._filament_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._filament_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._filament_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._filament_table.setToolTip("Filament products for the selected vendor")
        self._filament_table.cellClicked.connect(self._on_filament_cell_clicked)
        right_layout.addWidget(self._filament_table)

        fil_btn_row = QHBoxLayout()
        add_fil_btn = QPushButton("ADD FILAMENT")
        add_fil_btn.setObjectName("secondaryButton")
        add_fil_btn.setToolTip("Add a new filament for this vendor")
        add_fil_btn.clicked.connect(self._add_filament)
        fil_btn_row.addWidget(add_fil_btn)

        edit_fil_btn = QPushButton("EDIT")
        edit_fil_btn.setToolTip("Edit selected filament")
        edit_fil_btn.clicked.connect(self._edit_filament)
        fil_btn_row.addWidget(edit_fil_btn)

        copy_fil_btn = QPushButton("COPY")
        copy_fil_btn.setToolTip("Duplicate selected filament (new name, same specs)")
        copy_fil_btn.clicked.connect(self._copy_filament)
        fil_btn_row.addWidget(copy_fil_btn)

        del_fil_btn = QPushButton("DELETE")
        del_fil_btn.setToolTip("Delete selected filament")
        del_fil_btn.clicked.connect(self._delete_filament)
        fil_btn_row.addWidget(del_fil_btn)
        right_layout.addLayout(fil_btn_row)

        splitter.addWidget(right)
        splitter.setSizes([250, 550])

        layout.addWidget(splitter)

    def refresh(self) -> None:
        """Reload all vendors from database."""
        self._vendor_list.clear()
        session = get_session()
        try:
            vendors = session.query(Vendor).order_by(Vendor.name).all()
            for v in vendors:
                spool_count = sum(len(f.spools) for f in v.filaments)
                item = QListWidgetItem(f"{v.name}  ({len(v.filaments)} filaments, {spool_count} spools)")
                item.setData(Qt.ItemDataRole.UserRole, v.id)
                self._vendor_list.addItem(item)
        finally:
            session.close()

        if self._vendor_list.count() > 0:
            self._vendor_list.setCurrentRow(0)
        else:
            self._filament_table.setRowCount(0)

    def _on_vendor_selected(self, row: int) -> None:
        if row < 0:
            self._filament_table.setRowCount(0)
            self._update_btn.setEnabled(False)
            return

        vendor_id = self._vendor_list.item(row).data(Qt.ItemDataRole.UserRole)
        session = get_session()
        try:
            vendor = session.get(Vendor, vendor_id)
            if not vendor:
                return
            self._filament_label.setText(f"FILAMENTS — {vendor.name.upper()}")
            # Enable UPDATE CATALOG if vendor has a matching preset
            seed_names = {s["name"] for s in SEED_VENDORS}
            self._update_btn.setEnabled(vendor.name in seed_names)
            filaments = (
                session.query(Filament)
                .filter(Filament.vendor_id == vendor_id)
                .order_by(Filament.name)
                .all()
            )
            # Update material filter options
            materials = sorted({f.material for f in filaments})
            self._material_filter.blockSignals(True)
            prev = self._material_filter.currentText()
            self._material_filter.clear()
            self._material_filter.addItem("All")
            self._material_filter.addItems(materials)
            # Restore previous selection if still valid
            idx = self._material_filter.findText(prev)
            self._material_filter.setCurrentIndex(idx if idx >= 0 else 0)
            self._material_filter.blockSignals(False)

            # Apply material filter
            mat_filter = self._material_filter.currentText()
            if mat_filter != "All":
                filaments = [f for f in filaments if f.material == mat_filter]

            # Apply favorites filter
            if self._fav_filter.isChecked():
                filaments = [f for f in filaments if f.favorite]

            self._populate_filament_table(filaments)
        finally:
            session.close()

    def _on_material_filter_changed(self, *_args) -> None:
        """Re-filter the filament table when material or favorites filter changes."""
        row = self._vendor_list.currentRow()
        if row >= 0:
            self._on_vendor_selected(row)

    def _on_filament_cell_clicked(self, row: int, col: int) -> None:
        """Toggle favorite when star column is clicked."""
        if col != 0:
            return
        item = self._filament_table.item(row, 0)
        if item is None:
            return
        fil_id = item.data(Qt.ItemDataRole.UserRole + 1)
        if fil_id is None:
            return
        session = get_session()
        try:
            filament = session.get(Filament, fil_id)
            if filament:
                filament.favorite = not filament.favorite
                session.commit()
                item.setText("\u2605" if filament.favorite else "\u2606")
        finally:
            session.close()

    def _populate_filament_table(self, filaments: list) -> None:
        """Fill the filament table with the given list of Filament objects."""
        self._filament_table.setRowCount(len(filaments))
        for i, f in enumerate(filaments):
            # Favorite star
            star = QTableWidgetItem("\u2605" if f.favorite else "\u2606")
            star.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            star.setData(Qt.ItemDataRole.UserRole + 1, f.id)
            self._filament_table.setItem(i, 0, star)
            # Color swatch
            swatch = ColorSwatchWidget(f.color_hex or "#FFFFFF", size=20, show_label=True)
            self._filament_table.setCellWidget(i, 1, swatch)
            # Name
            self._filament_table.setItem(i, 2, QTableWidgetItem(f.name))
            # Material
            self._filament_table.setItem(i, 3, QTableWidgetItem(f.material))
            # Tensile strength
            ts = f"{f.tensile_strength_mpa:.0f} MPa" if f.tensile_strength_mpa else "\u2014"
            self._filament_table.setItem(i, 4, QTableWidgetItem(ts))
            # Diameter
            self._filament_table.setItem(i, 5, QTableWidgetItem(f"{f.diameter_mm} mm"))
            # Density
            self._filament_table.setItem(
                i, 6, QTableWidgetItem(f"{f.density_g_cm3:.2f} g/cm\u00b3")
            )
            # Temp
            temp_str = f"{f.nozzle_temp_default}\u00b0C" if f.nozzle_temp_default else "\u2014"
            self._filament_table.setItem(i, 7, QTableWidgetItem(temp_str))
            # Price
            price_str = f"${f.price:.2f}" if f.price else "\u2014"
            self._filament_table.setItem(i, 8, QTableWidgetItem(price_str))

            # Store filament id in name column
            self._filament_table.item(i, 2).setData(Qt.ItemDataRole.UserRole, f.id)

        # Set star column narrow
        self._filament_table.setColumnWidth(0, 30)

    def _get_selected_vendor_id(self) -> int | None:
        item = self._vendor_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _get_selected_filament_id(self) -> int | None:
        row = self._filament_table.currentRow()
        if row < 0:
            return None
        item = self._filament_table.item(row, 2)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _add_vendor(self) -> None:
        dlg = VendorDetailDialog(parent=self)
        if dlg.exec() == QMessageBox.DialogCode.Accepted:
            data = dlg.get_data()
            if not data["name"]:
                QMessageBox.warning(self, "Error", "Vendor name is required.")
                return
            session = get_session()
            try:
                vendor = Vendor(**data)
                session.add(vendor)
                session.commit()
            finally:
                session.close()
            self.refresh()

    def _import_preset(self) -> None:
        """Show a picker of pre-loaded manufacturers and import the selected one."""
        # Check which vendors are already imported
        session = get_session()
        try:
            existing = {v.name for v in session.query(Vendor.name).all()}
        finally:
            session.close()

        available = [s for s in SEED_VENDORS if s["name"] not in existing]
        if not available:
            QMessageBox.information(
                self, "All Imported", "All preset manufacturers have already been imported."
            )
            return

        # Build picker dialog
        dlg = QDialog(self)
        dlg.setWindowTitle("IMPORT PRESET MANUFACTURER")
        dlg.setMinimumWidth(360)
        dlg.setMinimumHeight(400)
        lay = QVBoxLayout(dlg)

        info = QLabel("Select manufacturers to import with their full filament catalogs:")
        info.setWordWrap(True)
        info.setStyleSheet("color: #E0E0F0; background: transparent;")
        lay.addWidget(info)

        preset_list = QListWidget()
        preset_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for seed in available:
            count = len(seed.get("filaments", []))
            item = QListWidgetItem(f"{seed['name']}  ({count} filaments)")
            item.setData(Qt.ItemDataRole.UserRole, seed["name"])
            preset_list.addItem(item)
        lay.addWidget(preset_list)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        lay.addWidget(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        selected_names = [
            preset_list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(preset_list.count())
            if preset_list.item(i).isSelected()
        ]
        if not selected_names:
            return

        session = get_session()
        try:
            total_filaments = 0
            for seed in SEED_VENDORS:
                if seed["name"] not in selected_names:
                    continue
                vendor = Vendor(
                    name=seed["name"],
                    website=seed.get("website", ""),
                    empty_spool_weight_g=seed.get("empty_spool_weight_g"),
                    notes=f"Imported from preset catalog",
                )
                session.add(vendor)
                session.flush()  # get vendor.id

                for fil_data in seed.get("filaments", []):
                    filament = Filament(
                        vendor_id=vendor.id,
                        name=fil_data["name"],
                        material=fil_data.get("material", "PLA"),
                        color_hex=fil_data.get("color_hex", "#FFFFFF"),
                        color_name=fil_data.get("color_name", ""),
                        diameter_mm=fil_data.get("diameter_mm", 1.75),
                        density_g_cm3=fil_data.get("density_g_cm3", 1.24),
                        net_weight_g=fil_data.get("net_weight_g", 1000.0),
                        spool_weight_g=seed.get("empty_spool_weight_g"),
                        nozzle_temp_min=fil_data.get("nozzle_temp_min"),
                        nozzle_temp_max=fil_data.get("nozzle_temp_max"),
                        nozzle_temp_default=fil_data.get("nozzle_temp_default"),
                        bed_temp_min=fil_data.get("bed_temp_min"),
                        bed_temp_max=fil_data.get("bed_temp_max"),
                        bed_temp_default=fil_data.get("bed_temp_default"),
                        max_print_speed=fil_data.get("max_print_speed"),
                        max_volumetric_flow=fil_data.get("max_volumetric_flow"),
                        tensile_strength_mpa=fil_data.get("tensile_strength_mpa"),
                        price=fil_data.get("price"),
                        price_unit=fil_data.get("price_unit"),
                    )
                    session.add(filament)
                    total_filaments += 1

            session.commit()
            QMessageBox.information(
                self,
                "Import Complete",
                f"Imported {len(selected_names)} manufacturer(s) with {total_filaments} filaments.",
            )
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Import Error", str(e))
        finally:
            session.close()

        self.refresh()

    def _update_catalog(self) -> None:
        """Merge new/updated filaments from seed data into the selected vendor."""
        vendor_id = self._get_selected_vendor_id()
        if vendor_id is None:
            return

        session = get_session()
        try:
            vendor = session.get(Vendor, vendor_id)
            if not vendor:
                return

            # Find matching seed entry
            seed = next((s for s in SEED_VENDORS if s["name"] == vendor.name), None)
            if not seed:
                QMessageBox.information(
                    self, "No Preset", "No preset catalog found for this vendor."
                )
                return

            # Build lookup of existing filaments by name
            existing = (
                session.query(Filament)
                .filter(Filament.vendor_id == vendor_id)
                .all()
            )
            lookup = {f.name: f for f in existing}

            added = 0
            updated = 0
            skipped = 0

            _SPEC_FIELDS = [
                "material", "color_hex", "color_name", "diameter_mm",
                "density_g_cm3", "net_weight_g", "nozzle_temp_min",
                "nozzle_temp_max", "nozzle_temp_default", "bed_temp_min",
                "bed_temp_max", "bed_temp_default", "max_print_speed",
                "max_volumetric_flow", "tensile_strength_mpa", "price",
                "price_unit",
            ]

            for fil_data in seed.get("filaments", []):
                name = fil_data["name"]
                existing_fil = lookup.get(name)

                if existing_fil is None:
                    # New filament — add it
                    filament = Filament(
                        vendor_id=vendor_id,
                        name=name,
                        material=fil_data.get("material", "PLA"),
                        color_hex=fil_data.get("color_hex", "#FFFFFF"),
                        color_name=fil_data.get("color_name", ""),
                        diameter_mm=fil_data.get("diameter_mm", 1.75),
                        density_g_cm3=fil_data.get("density_g_cm3", 1.24),
                        net_weight_g=fil_data.get("net_weight_g", 1000.0),
                        spool_weight_g=seed.get("empty_spool_weight_g"),
                        nozzle_temp_min=fil_data.get("nozzle_temp_min"),
                        nozzle_temp_max=fil_data.get("nozzle_temp_max"),
                        nozzle_temp_default=fil_data.get("nozzle_temp_default"),
                        bed_temp_min=fil_data.get("bed_temp_min"),
                        bed_temp_max=fil_data.get("bed_temp_max"),
                        bed_temp_default=fil_data.get("bed_temp_default"),
                        max_print_speed=fil_data.get("max_print_speed"),
                        max_volumetric_flow=fil_data.get("max_volumetric_flow"),
                        tensile_strength_mpa=fil_data.get("tensile_strength_mpa"),
                        price=fil_data.get("price"),
                        price_unit=fil_data.get("price_unit"),
                    )
                    session.add(filament)
                    added += 1
                elif existing_fil.spools:
                    # Has spools — don't touch
                    skipped += 1
                else:
                    # No spools — safe to update specs
                    for field in _SPEC_FIELDS:
                        if field in fil_data:
                            setattr(existing_fil, field, fil_data[field])
                    existing_fil.updated_at = datetime.utcnow()
                    updated += 1

            session.commit()

            parts = []
            if added:
                parts.append(f"Added {added} new filament(s)")
            if updated:
                parts.append(f"Updated {updated} filament(s)")
            if skipped:
                parts.append(f"Skipped {skipped} with active spools")
            if not parts:
                parts.append("Catalog is already up to date")

            QMessageBox.information(
                self, "Catalog Updated", "\n".join(parts)
            )
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Update Error", str(e))
        finally:
            session.close()

        self.refresh()

    def _import_spoolmandb(self) -> None:
        """Fetch SpoolmanDB and let user pick manufacturers to import/merge."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            entries = fetch_spoolmandb()
            by_mfr = group_by_manufacturer(entries)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(
                self, "Fetch Error",
                f"Could not fetch SpoolmanDB:\n{e}"
            )
            return
        QApplication.restoreOverrideCursor()

        # Build picker dialog
        dlg = QDialog(self)
        dlg.setWindowTitle("SPOOLMANDB — SELECT MANUFACTURERS")
        dlg.setMinimumWidth(420)
        dlg.setMinimumHeight(500)
        lay = QVBoxLayout(dlg)

        info = QLabel(
            f"Found {len(by_mfr)} manufacturers with {len(entries)} filaments.\n"
            "Select manufacturers to import or update:"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #E0E0F0; background: transparent;")
        lay.addWidget(info)

        picker = QListWidget()
        picker.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for name in sorted(by_mfr.keys()):
            count = len(by_mfr[name])
            item = QListWidgetItem(f"{name}  ({count} filaments)")
            item.setData(Qt.ItemDataRole.UserRole, name)
            picker.addItem(item)
        lay.addWidget(picker)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        lay.addWidget(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        selected = [
            picker.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(picker.count())
            if picker.item(i).isSelected()
        ]
        if not selected:
            return

        session = get_session()
        try:
            total_added = 0
            total_updated = 0
            total_skipped = 0
            vendors_created = 0

            for mfr_name in selected:
                # Find or create vendor
                vendor = (
                    session.query(Vendor)
                    .filter(Vendor.name == mfr_name)
                    .first()
                )
                if vendor is None:
                    vendor = Vendor(name=mfr_name)
                    session.add(vendor)
                    session.flush()
                    vendors_created += 1

                # Build lookup of existing filaments by name
                existing = {
                    f.name: f
                    for f in session.query(Filament)
                    .filter(Filament.vendor_id == vendor.id)
                    .all()
                }

                for entry in by_mfr[mfr_name]:
                    fil_data = map_to_filament_data(entry)
                    name = fil_data["name"]
                    existing_fil = existing.get(name)

                    if existing_fil is None:
                        filament = Filament(vendor_id=vendor.id, **fil_data)
                        session.add(filament)
                        total_added += 1
                    elif existing_fil.spools:
                        total_skipped += 1
                    else:
                        for k, v in fil_data.items():
                            if k != "name":
                                setattr(existing_fil, k, v)
                        existing_fil.updated_at = datetime.utcnow()
                        total_updated += 1

            session.commit()

            parts = []
            if vendors_created:
                parts.append(f"Created {vendors_created} new vendor(s)")
            if total_added:
                parts.append(f"Added {total_added} filament(s)")
            if total_updated:
                parts.append(f"Updated {total_updated} filament(s)")
            if total_skipped:
                parts.append(f"Skipped {total_skipped} with active spools")
            if not parts:
                parts.append("Everything is already up to date")

            QMessageBox.information(
                self, "SpoolmanDB Import Complete", "\n".join(parts)
            )
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Import Error", str(e))
        finally:
            session.close()

        self.refresh()

    def _edit_vendor(self) -> None:
        vendor_id = self._get_selected_vendor_id()
        if vendor_id is None:
            return
        session = get_session()
        try:
            vendor = session.get(Vendor, vendor_id)
            if not vendor:
                return
            dlg = VendorDetailDialog(vendor=vendor, parent=self)
            if dlg.exec() == QMessageBox.DialogCode.Accepted:
                data = dlg.get_data()
                if not data["name"]:
                    QMessageBox.warning(self, "Error", "Vendor name is required.")
                    return
                for k, v in data.items():
                    setattr(vendor, k, v)
                vendor.updated_at = datetime.utcnow()
                session.commit()
        finally:
            session.close()
        self.refresh()

    def _delete_vendor(self) -> None:
        vendor_id = self._get_selected_vendor_id()
        if vendor_id is None:
            return
        reply = QMessageBox.question(
            self,
            "DELETE VENDOR",
            "Delete this vendor and all its filaments/spools?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        session = get_session()
        try:
            vendor = session.get(Vendor, vendor_id)
            if vendor:
                session.delete(vendor)
                session.commit()
        finally:
            session.close()
        self.refresh()

    def _add_filament(self) -> None:
        vendor_id = self._get_selected_vendor_id()
        session = get_session()
        try:
            vendors = session.query(Vendor).order_by(Vendor.name).all()
            if not vendors:
                QMessageBox.information(self, "No Vendors", "Add a vendor first.")
                return
            dlg = FilamentDetailDialog(
                vendors=vendors,
                preselect_vendor_id=vendor_id,
                parent=self,
            )
            if dlg.exec() == QMessageBox.DialogCode.Accepted:
                data = dlg.get_data()
                if not data["name"]:
                    QMessageBox.warning(self, "Error", "Filament name is required.")
                    return
                filament = Filament(**data)
                session.add(filament)
                session.commit()
        finally:
            session.close()
        self.refresh()

    def _edit_filament(self) -> None:
        filament_id = self._get_selected_filament_id()
        if filament_id is None:
            return
        session = get_session()
        try:
            filament = session.get(Filament, filament_id)
            if not filament:
                return
            vendors = session.query(Vendor).order_by(Vendor.name).all()
            dlg = FilamentDetailDialog(
                vendors=vendors, filament=filament, parent=self
            )
            if dlg.exec() == QMessageBox.DialogCode.Accepted:
                data = dlg.get_data()
                for k, v in data.items():
                    setattr(filament, k, v)
                filament.updated_at = datetime.utcnow()
                session.commit()
        finally:
            session.close()
        self.refresh()

    def _copy_filament(self) -> None:
        """Duplicate the selected filament with a '(Copy)' suffix."""
        filament_id = self._get_selected_filament_id()
        if filament_id is None:
            return
        session = get_session()
        try:
            src = session.get(Filament, filament_id)
            if not src:
                return
            vendors = session.query(Vendor).order_by(Vendor.name).all()
            # Pre-create a copy with modified name
            copy = Filament(
                vendor_id=src.vendor_id,
                name=f"{src.name} (Copy)",
                material=src.material,
                color_hex=src.color_hex,
                color_name=src.color_name,
                diameter_mm=src.diameter_mm,
                density_g_cm3=src.density_g_cm3,
                net_weight_g=src.net_weight_g,
                spool_weight_g=src.spool_weight_g,
                nozzle_temp_min=src.nozzle_temp_min,
                nozzle_temp_max=src.nozzle_temp_max,
                nozzle_temp_default=src.nozzle_temp_default,
                bed_temp_min=src.bed_temp_min,
                bed_temp_max=src.bed_temp_max,
                bed_temp_default=src.bed_temp_default,
                tensile_strength_mpa=src.tensile_strength_mpa,
                max_print_speed=src.max_print_speed,
                max_volumetric_flow=src.max_volumetric_flow,
                price=src.price,
                price_unit=src.price_unit,
                settings_json=src.settings_json,
            )
            # Open edit dialog so user can change the name/color
            dlg = FilamentDetailDialog(
                vendors=vendors, filament=copy, parent=self
            )
            if dlg.exec() == QMessageBox.DialogCode.Accepted:
                data = dlg.get_data()
                new_filament = Filament(**data)
                session.add(new_filament)
                session.commit()
        finally:
            session.close()
        self.refresh()

    def _delete_filament(self) -> None:
        filament_id = self._get_selected_filament_id()
        if filament_id is None:
            return
        reply = QMessageBox.question(
            self,
            "DELETE FILAMENT",
            "Delete this filament and all its spools?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        session = get_session()
        try:
            filament = session.get(Filament, filament_id)
            if filament:
                session.delete(filament)
                session.commit()
        finally:
            session.close()
        self.refresh()
