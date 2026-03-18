"""OrcaSlicer .json filament profile generator."""

from __future__ import annotations

import re

from app.db.models import Filament, Spool


def _slugify(text: str) -> str:
    """Convert text to a safe slug for filament_id."""
    return re.sub(r"[^a-zA-Z0-9]", "_", text)[:8]


def generate_orcaslicer_profile(filament: Filament, vendor_name: str) -> dict:
    """Generate an OrcaSlicer filament profile as a Python dict (JSON-serializable)."""
    nozzle = filament.nozzle_temp_default or 210
    bed = filament.bed_temp_default or 60
    density = filament.density_g_cm3 or 1.24
    diameter = filament.diameter_mm or 1.75
    color = filament.color_hex or "#FFFFFF"

    if not color.startswith("#"):
        color = f"#{color}"

    price_per_kg = 0.0
    if filament.price:
        if filament.price_unit == "per_kg":
            price_per_kg = filament.price
        elif filament.net_weight_g and filament.net_weight_g > 0:
            price_per_kg = filament.price / (filament.net_weight_g / 1000.0)

    profile_name = f"{vendor_name} {filament.name}"
    filament_id = _slugify(f"{vendor_name}_{filament.name}")

    # Map material to OrcaSlicer inherits base
    material_map = {
        "PLA": "Generic PLA",
        "PLA+": "Generic PLA",
        "PETG": "Generic PETG",
        "ABS": "Generic ABS",
        "ASA": "Generic ASA",
        "TPU": "Generic TPU",
        "Nylon": "Generic PA",
        "PC": "Generic PC",
        "PVA": "Generic PVA",
    }
    inherits = material_map.get(filament.material, f"Generic {filament.material}")

    profile = {
        "type": "filament",
        "name": profile_name,
        "inherits": inherits,
        "from": "User",
        "instantiation": "true",
        "filament_id": [filament_id],
        "filament_type": [filament.material],
        "filament_colour": [color],
        "filament_diameter": [str(diameter)],
        "filament_density": [str(density)],
        "filament_cost": [str(f"{price_per_kg:.2f}")],
        "filament_vendor": [vendor_name],
        "nozzle_temperature": [str(nozzle)],
        "nozzle_temperature_initial_layer": [str(nozzle + 5)],
        "hot_plate_temp": [str(bed)],
        "hot_plate_temp_initial_layer": [str(bed + 5)],
    }

    if filament.max_volumetric_flow:
        profile["filament_max_volumetric_speed"] = [str(filament.max_volumetric_flow)]

    return profile


def generate_spool_profile(spool: Spool, filament: Filament, vendor_name: str) -> dict:
    """Generate a per-spool OrcaSlicer profile with correct color and remaining weight.

    Profile name format: '{Vendor} {Material} {Color} — {remaining}g'
    """
    nozzle = filament.nozzle_temp_default or 210
    bed = filament.bed_temp_default or 60
    density = filament.density_g_cm3 or 1.24
    diameter = filament.diameter_mm or 1.75
    color = filament.color_hex or "#FFFFFF"

    if not color.startswith("#"):
        color = f"#{color}"

    remaining = spool.remaining_weight_g
    color_name = filament.color_name or filament.name

    price_per_kg = 0.0
    if filament.price:
        if filament.price_unit == "per_kg":
            price_per_kg = filament.price
        elif filament.net_weight_g and filament.net_weight_g > 0:
            price_per_kg = filament.price / (filament.net_weight_g / 1000.0)

    profile_name = f"{vendor_name} {filament.material} {color_name} — {remaining:.0f}g"
    filament_id = _slugify(f"spool_{spool.id}_{filament.material}")

    material_map = {
        "PLA": "Generic PLA",
        "PLA+": "Generic PLA",
        "PETG": "Generic PETG",
        "ABS": "Generic ABS",
        "ASA": "Generic ASA",
        "TPU": "Generic TPU",
        "Nylon": "Generic PA",
        "PC": "Generic PC",
        "PVA": "Generic PVA",
    }
    inherits = material_map.get(filament.material, f"Generic {filament.material}")

    profile = {
        "type": "filament",
        "name": profile_name,
        "inherits": inherits,
        "from": "User",
        "instantiation": "true",
        "filament_id": [filament_id],
        "filament_type": [filament.material],
        "filament_colour": [color],
        "filament_diameter": [str(diameter)],
        "filament_density": [str(density)],
        "filament_cost": [str(f"{price_per_kg:.2f}")],
        "filament_vendor": [vendor_name],
        "nozzle_temperature": [str(nozzle)],
        "nozzle_temperature_initial_layer": [str(nozzle + 5)],
        "hot_plate_temp": [str(bed)],
        "hot_plate_temp_initial_layer": [str(bed + 5)],
    }

    if filament.max_volumetric_flow:
        profile["filament_max_volumetric_speed"] = [str(filament.max_volumetric_flow)]

    return profile
