"""Dialog for adding/editing a filament."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from app.db.models import Filament, Vendor
from app.widgets.color_swatch_widget import ColorSwatchWidget
from app.widgets.screen_color_picker import ScreenColorPicker

MATERIALS = [
    "PLA", "PLA+", "PETG", "ABS", "ASA", "TPU", "Nylon", "PC",
    "PVA", "HIPS", "CF-PLA", "CF-PETG", "GF-PLA", "Wood-PLA",
    "Silk-PLA", "Marble-PLA", "PEEK", "PEI", "Other",
]

# Default tensile strength (MPa) per material type for FDM-printed parts
MATERIAL_TENSILE_DEFAULTS: dict[str, float] = {
    "PLA": 37.0,
    "PLA+": 46.0,
    "PETG": 50.0,
    "ABS": 40.0,
    "ABS+": 43.0,
    "ASA": 55.0,
    "TPU": 26.0,
    "Nylon": 70.0,
    "PC": 68.0,
    "PVA": 29.0,
    "HIPS": 25.0,
    "CF-PLA": 52.0,
    "CF-PETG": 63.0,
    "GF-PLA": 48.0,
    "Wood-PLA": 30.0,
    "Silk-PLA": 33.0,
    "Marble-PLA": 32.0,
    "PEEK": 100.0,
    "PEI": 85.0,
}


class FilamentDetailDialog(QDialog):
    """Modal dialog for creating or editing a filament."""

    def __init__(
        self,
        vendors: list[Vendor],
        filament: Filament | None = None,
        preselect_vendor_id: int | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._filament = filament
        self._vendors = vendors
        self.setWindowTitle("EDIT FILAMENT" if filament else "ADD FILAMENT")
        self.setMinimumWidth(480)
        self._build_ui()
        if preselect_vendor_id is not None:
            self._select_vendor(preselect_vendor_id)
        if filament:
            self._populate(filament)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setSpacing(8)

        # Vendor
        self._vendor_combo = QComboBox()
        for v in self._vendors:
            self._vendor_combo.addItem(v.name, v.id)
        self._vendor_combo.setToolTip("Select the manufacturer")
        form.addRow("VENDOR:", self._vendor_combo)

        # Name
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. PLA+ Red")
        self._name_edit.setToolTip("Filament product name")
        form.addRow("NAME:", self._name_edit)

        # Material
        self._material_combo = QComboBox()
        self._material_combo.addItems(MATERIALS)
        self._material_combo.setEditable(True)
        self._material_combo.setToolTip("Filament material type")
        self._material_combo.currentTextChanged.connect(self._on_material_changed)
        form.addRow("MATERIAL:", self._material_combo)

        # Color
        color_row = QHBoxLayout()
        self._color_hex_edit = QLineEdit("#FFFFFF")
        self._color_hex_edit.setMaximumWidth(100)
        self._color_hex_edit.setToolTip("Hex color code")
        self._color_hex_edit.textChanged.connect(self._on_color_text_changed)
        color_row.addWidget(self._color_hex_edit)

        self._color_swatch = ColorSwatchWidget("#FFFFFF", size=24, show_label=False)
        color_row.addWidget(self._color_swatch)

        pick_btn = QPushButton("PICK")
        pick_btn.setToolTip("Open color picker dialog")
        pick_btn.clicked.connect(self._pick_color)
        color_row.addWidget(pick_btn)

        eyedrop_btn = QPushButton("\u2388")
        eyedrop_btn.setFixedWidth(40)
        eyedrop_btn.setToolTip("Pick a color from anywhere on screen")
        eyedrop_btn.clicked.connect(self._pick_screen_color)
        color_row.addWidget(eyedrop_btn)
        color_row.addStretch()

        self._screen_picker = ScreenColorPicker()
        self._screen_picker.color_picked.connect(self._on_screen_color_picked)
        form.addRow("COLOR:", color_row)

        # Color name
        self._color_name_edit = QLineEdit()
        self._color_name_edit.setPlaceholderText("e.g. Fire Engine Red")
        self._color_name_edit.setToolTip("Human-readable color name")
        form.addRow("COLOR NAME:", self._color_name_edit)

        # Diameter
        self._diameter = QComboBox()
        self._diameter.addItems(["1.75", "2.85"])
        self._diameter.setToolTip("Filament diameter in mm")
        form.addRow("DIAMETER (mm):", self._diameter)

        # Density
        self._density = QDoubleSpinBox()
        self._density.setRange(0.5, 3.0)
        self._density.setValue(1.24)
        self._density.setDecimals(2)
        self._density.setSuffix(" g/cm\u00b3")
        self._density.setToolTip("Material density (PLA ~1.24, PETG ~1.27, ABS ~1.04)")
        form.addRow("DENSITY:", self._density)

        # Net weight
        self._net_weight = QDoubleSpinBox()
        self._net_weight.setRange(0.0, 10000.0)
        self._net_weight.setValue(1000.0)
        self._net_weight.setSuffix(" g")
        self._net_weight.setToolTip("Rated net filament weight per spool")
        form.addRow("NET WEIGHT:", self._net_weight)

        # Spool weight
        self._spool_weight = QDoubleSpinBox()
        self._spool_weight.setRange(0.0, 500.0)
        self._spool_weight.setSuffix(" g")
        self._spool_weight.setToolTip("Empty spool weight (overrides vendor default)")
        form.addRow("SPOOL WEIGHT:", self._spool_weight)

        # Temperature section
        temp_label = QLabel("TEMPERATURES")
        temp_label.setStyleSheet("color: #B026FF; font-weight: bold; background: transparent;")
        form.addRow(temp_label)

        # Nozzle temps
        nozzle_row = QHBoxLayout()
        self._nozzle_min = QSpinBox()
        self._nozzle_min.setRange(0, 500)
        self._nozzle_min.setSuffix(" \u00b0C")
        self._nozzle_min.setToolTip("Minimum nozzle temperature")
        nozzle_row.addWidget(QLabel("Min:"))
        nozzle_row.addWidget(self._nozzle_min)
        self._nozzle_default = QSpinBox()
        self._nozzle_default.setRange(0, 500)
        self._nozzle_default.setValue(210)
        self._nozzle_default.setSuffix(" \u00b0C")
        self._nozzle_default.setToolTip("Default nozzle temperature")
        nozzle_row.addWidget(QLabel("Default:"))
        nozzle_row.addWidget(self._nozzle_default)
        self._nozzle_max = QSpinBox()
        self._nozzle_max.setRange(0, 500)
        self._nozzle_max.setSuffix(" \u00b0C")
        self._nozzle_max.setToolTip("Maximum nozzle temperature")
        nozzle_row.addWidget(QLabel("Max:"))
        nozzle_row.addWidget(self._nozzle_max)
        form.addRow("NOZZLE:", nozzle_row)

        # Bed temps
        bed_row = QHBoxLayout()
        self._bed_min = QSpinBox()
        self._bed_min.setRange(0, 200)
        self._bed_min.setSuffix(" \u00b0C")
        self._bed_min.setToolTip("Minimum bed temperature")
        bed_row.addWidget(QLabel("Min:"))
        bed_row.addWidget(self._bed_min)
        self._bed_default = QSpinBox()
        self._bed_default.setRange(0, 200)
        self._bed_default.setValue(60)
        self._bed_default.setSuffix(" \u00b0C")
        self._bed_default.setToolTip("Default bed temperature")
        bed_row.addWidget(QLabel("Default:"))
        bed_row.addWidget(self._bed_default)
        self._bed_max = QSpinBox()
        self._bed_max.setRange(0, 200)
        self._bed_max.setSuffix(" \u00b0C")
        self._bed_max.setToolTip("Maximum bed temperature")
        bed_row.addWidget(QLabel("Max:"))
        bed_row.addWidget(self._bed_max)
        form.addRow("BED:", bed_row)

        # Printing speed / flow
        speed_label = QLabel("PRINTING LIMITS")
        speed_label.setStyleSheet("color: #B026FF; font-weight: bold; background: transparent;")
        form.addRow(speed_label)

        self._max_speed = QDoubleSpinBox()
        self._max_speed.setRange(0.0, 1000.0)
        self._max_speed.setSuffix(" mm/s")
        self._max_speed.setDecimals(0)
        self._max_speed.setToolTip("Maximum recommended printing speed")
        form.addRow("MAX SPEED:", self._max_speed)

        self._max_flow = QDoubleSpinBox()
        self._max_flow.setRange(0.0, 100.0)
        self._max_flow.setSuffix(" mm\u00b3/s")
        self._max_flow.setDecimals(1)
        self._max_flow.setToolTip("Maximum volumetric flow rate")
        form.addRow("MAX FLOW:", self._max_flow)

        # Tensile Strength
        self._tensile_strength = QDoubleSpinBox()
        self._tensile_strength.setRange(0.0, 500.0)
        self._tensile_strength.setSuffix(" MPa")
        self._tensile_strength.setDecimals(1)
        self._tensile_strength.setToolTip("Tensile strength of printed parts (MPa)")
        form.addRow("TENSILE STRENGTH:", self._tensile_strength)

        # Price
        price_row = QHBoxLayout()
        self._price = QDoubleSpinBox()
        self._price.setRange(0.0, 9999.0)
        self._price.setPrefix("$")
        self._price.setDecimals(2)
        self._price.setToolTip("Price per unit")
        price_row.addWidget(self._price)
        self._price_unit = QComboBox()
        self._price_unit.addItems(["per spool", "per kg"])
        self._price_unit.setToolTip("Price unit")
        price_row.addWidget(self._price_unit)
        form.addRow("PRICE:", price_row)

        # Properties section
        props_label = QLabel("PROPERTIES")
        props_label.setStyleSheet("color: #B026FF; font-weight: bold; background: transparent;")
        form.addRow(props_label)

        # Finish
        self._finish_combo = QComboBox()
        self._finish_combo.addItems(["", "matte", "glossy", "satin", "silk", "metallic"])
        self._finish_combo.setEditable(True)
        self._finish_combo.setToolTip("Surface finish type")
        form.addRow("FINISH:", self._finish_combo)

        # Pattern
        self._pattern_combo = QComboBox()
        self._pattern_combo.addItems(["", "sparkle", "marble", "wood", "galaxy", "rainbow"])
        self._pattern_combo.setEditable(True)
        self._pattern_combo.setToolTip("Visual pattern in the filament")
        form.addRow("PATTERN:", self._pattern_combo)

        # Checkboxes row
        check_row = QHBoxLayout()
        self._translucent_check = QCheckBox("Translucent")
        self._translucent_check.setToolTip("Filament is translucent/transparent")
        check_row.addWidget(self._translucent_check)
        self._glow_check = QCheckBox("Glow in Dark")
        self._glow_check.setToolTip("Filament glows in the dark")
        check_row.addWidget(self._glow_check)
        check_row.addStretch()
        form.addRow("FLAGS:", check_row)

        # Multi-color direction
        self._multi_color_combo = QComboBox()
        self._multi_color_combo.addItems(["", "coaxial", "longitudinal"])
        self._multi_color_combo.setToolTip("Multi-color transition direction")
        form.addRow("MULTI-COLOR:", self._multi_color_combo)

        # Spool type
        self._spool_type_combo = QComboBox()
        self._spool_type_combo.addItems(["", "plastic", "cardboard", "refill"])
        self._spool_type_combo.setEditable(True)
        self._spool_type_combo.setToolTip("Spool material type")
        form.addRow("SPOOL TYPE:", self._spool_type_combo)

        # External ID (read-only display)
        self._external_id_edit = QLineEdit()
        self._external_id_edit.setPlaceholderText("SpoolmanDB ID (auto-filled on import)")
        self._external_id_edit.setToolTip("External reference ID from SpoolmanDB")
        form.addRow("EXTERNAL ID:", self._external_id_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _select_vendor(self, vendor_id: int) -> None:
        for i in range(self._vendor_combo.count()):
            if self._vendor_combo.itemData(i) == vendor_id:
                self._vendor_combo.setCurrentIndex(i)
                break

    def _populate(self, f: Filament) -> None:
        self._select_vendor(f.vendor_id)
        self._name_edit.setText(f.name or "")
        idx = self._material_combo.findText(f.material)
        if idx >= 0:
            self._material_combo.setCurrentIndex(idx)
        else:
            self._material_combo.setEditText(f.material)
        self._color_hex_edit.setText(f.color_hex or "#FFFFFF")
        self._color_name_edit.setText(f.color_name or "")
        d_idx = 0 if f.diameter_mm == 1.75 else 1
        self._diameter.setCurrentIndex(d_idx)
        self._density.setValue(f.density_g_cm3)
        self._net_weight.setValue(f.net_weight_g)
        if f.spool_weight_g:
            self._spool_weight.setValue(f.spool_weight_g)
        if f.nozzle_temp_min:
            self._nozzle_min.setValue(f.nozzle_temp_min)
        if f.nozzle_temp_default:
            self._nozzle_default.setValue(f.nozzle_temp_default)
        if f.nozzle_temp_max:
            self._nozzle_max.setValue(f.nozzle_temp_max)
        if f.bed_temp_min:
            self._bed_min.setValue(f.bed_temp_min)
        if f.bed_temp_default:
            self._bed_default.setValue(f.bed_temp_default)
        if f.bed_temp_max:
            self._bed_max.setValue(f.bed_temp_max)
        if f.max_print_speed:
            self._max_speed.setValue(f.max_print_speed)
        if f.max_volumetric_flow:
            self._max_flow.setValue(f.max_volumetric_flow)
        if f.tensile_strength_mpa:
            self._tensile_strength.setValue(f.tensile_strength_mpa)
        if f.price:
            self._price.setValue(f.price)
        if f.price_unit == "per_kg":
            self._price_unit.setCurrentIndex(1)
        if f.finish:
            idx = self._finish_combo.findText(f.finish)
            if idx >= 0:
                self._finish_combo.setCurrentIndex(idx)
            else:
                self._finish_combo.setEditText(f.finish)
        if f.pattern:
            idx = self._pattern_combo.findText(f.pattern)
            if idx >= 0:
                self._pattern_combo.setCurrentIndex(idx)
            else:
                self._pattern_combo.setEditText(f.pattern)
        if f.translucent:
            self._translucent_check.setChecked(True)
        if f.glow:
            self._glow_check.setChecked(True)
        if f.multi_color_direction:
            idx = self._multi_color_combo.findText(f.multi_color_direction)
            if idx >= 0:
                self._multi_color_combo.setCurrentIndex(idx)
        if f.spool_type:
            idx = self._spool_type_combo.findText(f.spool_type)
            if idx >= 0:
                self._spool_type_combo.setCurrentIndex(idx)
            else:
                self._spool_type_combo.setEditText(f.spool_type)
        if f.external_id:
            self._external_id_edit.setText(f.external_id)

    def _on_material_changed(self, material: str) -> None:
        default = MATERIAL_TENSILE_DEFAULTS.get(material, 37.0)
        self._tensile_strength.setValue(default)

    def _on_color_text_changed(self, text: str) -> None:
        if QColor(text).isValid():
            self._color_swatch.set_color(text)

    def _pick_color(self) -> None:
        current = QColor(self._color_hex_edit.text())
        if not current.isValid():
            current = QColor("#FFFFFF")
        color = QColorDialog.getColor(current, self, "PICK FILAMENT COLOR")
        if color.isValid():
            self._color_hex_edit.setText(color.name().upper())

    def _pick_screen_color(self) -> None:
        self.hide()
        self._screen_picker.start()

    def _on_screen_color_picked(self, hex_color: str) -> None:
        self._color_hex_edit.setText(hex_color)
        self.show()

    def get_data(self) -> dict:
        """Return form data as a dict suitable for creating/updating a Filament."""
        return {
            "vendor_id": self._vendor_combo.currentData(),
            "name": self._name_edit.text().strip(),
            "material": self._material_combo.currentText().strip(),
            "color_hex": self._color_hex_edit.text().strip(),
            "color_name": self._color_name_edit.text().strip() or None,
            "diameter_mm": float(self._diameter.currentText()),
            "density_g_cm3": self._density.value(),
            "net_weight_g": self._net_weight.value(),
            "spool_weight_g": self._spool_weight.value() or None,
            "nozzle_temp_min": self._nozzle_min.value() or None,
            "nozzle_temp_default": self._nozzle_default.value() or None,
            "nozzle_temp_max": self._nozzle_max.value() or None,
            "bed_temp_min": self._bed_min.value() or None,
            "bed_temp_default": self._bed_default.value() or None,
            "bed_temp_max": self._bed_max.value() or None,
            "max_print_speed": self._max_speed.value() or None,
            "max_volumetric_flow": self._max_flow.value() or None,
            "tensile_strength_mpa": self._tensile_strength.value() or None,
            "price": self._price.value() or None,
            "price_unit": "per_kg" if self._price_unit.currentIndex() == 1 else "per_spool",
            "finish": self._finish_combo.currentText().strip() or None,
            "pattern": self._pattern_combo.currentText().strip() or None,
            "translucent": self._translucent_check.isChecked() or None,
            "glow": self._glow_check.isChecked() or None,
            "multi_color_direction": self._multi_color_combo.currentText().strip() or None,
            "spool_type": self._spool_type_combo.currentText().strip() or None,
            "external_id": self._external_id_edit.text().strip() or None,
        }
