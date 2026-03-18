"""Profiles panel — slicer profile generation UI."""

from __future__ import annotations

import json
import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from sqlalchemy.orm import joinedload

from app.db.engine import get_session
from app.db.models import Filament, Spool, Vendor
from app.slicer.prusaslicer import generate_prusaslicer_profile
from app.slicer.prusaslicer import generate_spool_profile as prusa_spool_profile
from app.slicer.orcaslicer import generate_orcaslicer_profile
from app.slicer.orcaslicer import generate_spool_profile as orca_spool_profile


class ProfilesPanel(QWidget):
    """Slicer profile generation UI."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Target slicer
        slicer_group = QGroupBox("TARGET SLICER")
        slicer_layout = QHBoxLayout(slicer_group)
        self._prusa_radio = QRadioButton("PRUSASLICER")
        self._prusa_radio.setChecked(True)
        self._prusa_radio.setToolTip("Generate PrusaSlicer .ini filament profiles")
        slicer_layout.addWidget(self._prusa_radio)
        self._orca_radio = QRadioButton("ORCASLICER")
        self._orca_radio.setToolTip("Generate OrcaSlicer .json filament profiles")
        slicer_layout.addWidget(self._orca_radio)
        slicer_layout.addStretch()
        layout.addWidget(slicer_group)

        # Filament selection
        select_group = QGroupBox("SELECT FILAMENTS")
        select_layout = QVBoxLayout(select_group)

        btn_row = QHBoxLayout()
        select_all = QPushButton("SELECT ALL")
        select_all.setToolTip("Select all filaments")
        select_all.clicked.connect(self._select_all)
        btn_row.addWidget(select_all)
        deselect_all = QPushButton("DESELECT ALL")
        deselect_all.setToolTip("Deselect all filaments")
        deselect_all.clicked.connect(self._deselect_all)
        btn_row.addWidget(deselect_all)
        btn_row.addStretch()
        select_layout.addLayout(btn_row)

        self._filament_list = QListWidget()
        self._filament_list.setToolTip("Check filaments to generate profiles for")
        select_layout.addWidget(self._filament_list)

        layout.addWidget(select_group)

        # Output directory
        out_group = QGroupBox("OUTPUT DIRECTORY")
        out_layout = QHBoxLayout(out_group)
        self._output_dir = QLabel("(auto-detect)")
        self._output_dir.setStyleSheet(
            "color: #8888AA; font-size: 13px; background: transparent;"
        )
        self._output_dir.setWordWrap(True)
        out_layout.addWidget(self._output_dir)
        browse_btn = QPushButton("BROWSE")
        browse_btn.setToolTip("Choose custom output directory")
        browse_btn.clicked.connect(self._browse_output)
        out_layout.addWidget(browse_btn)
        layout.addWidget(out_group)

        # Spool profiles toggle
        spool_group = QGroupBox("SPOOL PROFILES")
        spool_layout = QVBoxLayout(spool_group)
        self._spool_profiles = QCheckBox("GENERATE PER-SPOOL PROFILES")
        self._spool_profiles.setToolTip(
            "Generate profiles for each physical spool in inventory.\n"
            "Profile names include remaining weight and correct spool color\n"
            "for accurate 3D preview in the slicer."
        )
        spool_layout.addWidget(self._spool_profiles)
        spool_info = QLabel(
            "Per-spool profiles show remaining weight and correct color\n"
            "in PrusaSlicer/OrcaSlicer 3D preview."
        )
        spool_info.setStyleSheet(
            "color: #8888AA; font-size: 12px; background: transparent;"
        )
        spool_layout.addWidget(spool_info)
        layout.addWidget(spool_group)

        # Generate button
        gen_btn = QPushButton("GENERATE PROFILES")
        gen_btn.setObjectName("primaryButton")
        gen_btn.setToolTip("Generate slicer filament profiles for selected filaments")
        gen_btn.clicked.connect(self._generate)
        layout.addWidget(gen_btn)

        # Log area
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(150)
        self._log.setToolTip("Generation log")
        layout.addWidget(self._log)

    def refresh(self) -> None:
        """Reload filaments into the selection list."""
        self._filament_list.clear()
        session = get_session()
        try:
            filaments = (
                session.query(Filament)
                .join(Vendor)
                .order_by(Vendor.name, Filament.name)
                .all()
            )
            for f in filaments:
                vendor_name = f.vendor.name if f.vendor else "?"
                item = QListWidgetItem(f"{vendor_name} — {f.name} ({f.material})")
                item.setCheckState(Qt.CheckState.Checked)
                item.setData(Qt.ItemDataRole.UserRole, f.id)
                self._filament_list.addItem(item)
        finally:
            session.close()

    def _select_all(self) -> None:
        for i in range(self._filament_list.count()):
            self._filament_list.item(i).setCheckState(Qt.CheckState.Checked)

    def _deselect_all(self) -> None:
        for i in range(self._filament_list.count()):
            self._filament_list.item(i).setCheckState(Qt.CheckState.Unchecked)

    def _browse_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "SELECT OUTPUT DIRECTORY")
        if path:
            self._output_dir.setText(path)

    def _get_output_dir(self) -> str | None:
        text = self._output_dir.text()
        if text and text != "(auto-detect)":
            return text
        # Auto-detect from parent settings panel
        main_win = self.window()
        if hasattr(main_win, "_settings_panel"):
            if self._prusa_radio.isChecked():
                p = main_win._settings_panel.get_prusa_path()
            else:
                p = main_win._settings_panel.get_orca_path()
            if p:
                return p
        return None

    def _generate(self) -> None:
        """Generate profiles for selected filaments."""
        output_dir = self._get_output_dir()
        if not output_dir:
            QMessageBox.warning(
                self,
                "No Output Directory",
                "Set a slicer path in Settings or choose an output directory.",
            )
            return

        os.makedirs(output_dir, exist_ok=True)
        is_prusa = self._prusa_radio.isChecked()

        selected_ids = []
        for i in range(self._filament_list.count()):
            item = self._filament_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_ids.append(item.data(Qt.ItemDataRole.UserRole))

        if not selected_ids:
            QMessageBox.information(self, "Nothing Selected", "Select at least one filament.")
            return

        self._log.clear()
        session = get_session()
        try:
            count = 0
            for fid in selected_ids:
                filament = session.get(Filament, fid)
                if not filament:
                    continue

                vendor_name = filament.vendor.name if filament.vendor else "Unknown"

                if is_prusa:
                    content = generate_prusaslicer_profile(filament, vendor_name)
                    filename = f"{vendor_name} {filament.name}.ini"
                    filepath = Path(output_dir) / filename
                    filepath.write_text(content, encoding="utf-8")
                else:
                    content = generate_orcaslicer_profile(filament, vendor_name)
                    filename = f"{vendor_name} {filament.name}.json"
                    filepath = Path(output_dir) / filename
                    filepath.write_text(
                        json.dumps(content, indent=2), encoding="utf-8"
                    )

                self._log.append(f"  \u2713 {filename}")
                count += 1

            # Generate spool profiles if toggle is on
            spool_count = 0
            if self._spool_profiles.isChecked():
                spools = (
                    session.query(Spool)
                    .options(
                        joinedload(Spool.filament).joinedload(Filament.vendor)
                    )
                    .filter(Spool.archived == False)  # noqa: E712
                    .all()
                )
                for sp in spools:
                    fil = sp.filament
                    vname = fil.vendor.name if fil.vendor else "Unknown"
                    color_name = fil.color_name or fil.name

                    if is_prusa:
                        content = prusa_spool_profile(sp, fil, vname)
                        filename = f"[Spool] {vname} {fil.material} {color_name}.ini"
                        filepath = Path(output_dir) / filename
                        filepath.write_text(content, encoding="utf-8")
                    else:
                        content = orca_spool_profile(sp, fil, vname)
                        filename = f"[Spool] {vname} {fil.material} {color_name}.json"
                        filepath = Path(output_dir) / filename
                        filepath.write_text(
                            json.dumps(content, indent=2), encoding="utf-8"
                        )

                    self._log.append(f"  \u2713 {filename}")
                    spool_count += 1

            slicer_name = "PrusaSlicer" if is_prusa else "OrcaSlicer"
            total = count + spool_count
            parts = [f"Generated {count} filament profiles"]
            if spool_count:
                parts.append(f"{spool_count} spool profiles")
            self._log.append(f"\n{' + '.join(parts)} for {slicer_name} to:")
            self._log.append(f"  {output_dir}")
        except Exception as e:
            self._log.append(f"\n  \u2717 Error: {e}")
        finally:
            session.close()
