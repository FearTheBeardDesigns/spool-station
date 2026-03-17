"""SpoolmanDB integration — fetch and parse community filament database."""

from __future__ import annotations

import json
import urllib.request
from collections import defaultdict

SPOOLMANDB_URL = "https://donkie.github.io/SpoolmanDB/filaments.json"


def fetch_spoolmandb() -> list[dict]:
    """Fetch the full SpoolmanDB filaments.json and return parsed entries."""
    req = urllib.request.Request(SPOOLMANDB_URL, headers={"User-Agent": "SpoolStation/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def group_by_manufacturer(entries: list[dict]) -> dict[str, list[dict]]:
    """Group SpoolmanDB entries by manufacturer name."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        mfr = entry.get("manufacturer", "Unknown")
        groups[mfr].append(entry)
    return dict(groups)


def map_to_filament_data(entry: dict) -> dict:
    """Convert a SpoolmanDB entry to a dict compatible with Filament model."""
    # Build color name from name + finish/glow/translucent info
    name = entry.get("name", "Unknown")
    color_name_parts = [name]
    if entry.get("finish"):
        color_name_parts.append(entry["finish"])
    if entry.get("glow"):
        color_name_parts.append("Glow")
    if entry.get("translucent"):
        color_name_parts.append("Translucent")
    color_name = " ".join(color_name_parts) if len(color_name_parts) > 1 else ""

    # Ensure color_hex has # prefix
    hex_raw = entry.get("color_hex") or "FFFFFF"
    color_hex = f"#{hex_raw}" if not hex_raw.startswith("#") else hex_raw

    # Multi-color hex list (stored as comma-separated)
    color_hexes = None
    if entry.get("color_hexes"):
        color_hexes = ",".join(
            f"#{h}" if not h.startswith("#") else h for h in entry["color_hexes"]
        )

    # Temperature ranges → min/max
    nozzle_min = nozzle_max = bed_min = bed_max = None
    ext_range = entry.get("extruder_temp_range")
    if ext_range and len(ext_range) == 2:
        nozzle_min, nozzle_max = ext_range
    bed_range = entry.get("bed_temp_range")
    if bed_range and len(bed_range) == 2:
        bed_min, bed_max = bed_range

    return {
        "name": name,
        "material": entry.get("material", "PLA"),
        "color_hex": color_hex,
        "color_name": color_name or None,
        "diameter_mm": entry.get("diameter", 1.75),
        "density_g_cm3": entry.get("density", 1.24),
        "net_weight_g": entry.get("weight", 1000.0),
        "spool_weight_g": entry.get("spool_weight"),
        "nozzle_temp_min": nozzle_min,
        "nozzle_temp_max": nozzle_max,
        "nozzle_temp_default": entry.get("extruder_temp"),
        "bed_temp_min": bed_min,
        "bed_temp_max": bed_max,
        "bed_temp_default": entry.get("bed_temp"),
        "finish": entry.get("finish"),
        "pattern": entry.get("pattern"),
        "translucent": entry.get("translucent"),
        "glow": entry.get("glow"),
        "multi_color_direction": entry.get("multi_color_direction"),
        "color_hexes": color_hexes,
        "spool_type": entry.get("spool_type"),
        "external_id": entry.get("id"),
    }
