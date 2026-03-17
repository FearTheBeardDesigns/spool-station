"""Pydantic request/response models for the REST API."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


# ── Vendor ────────────────────────────────────────────────────────────────

class VendorCreate(BaseModel):
    name: str
    website: str | None = None
    empty_spool_weight_g: float | None = None
    notes: str | None = None


class VendorUpdate(BaseModel):
    name: str | None = None
    website: str | None = None
    empty_spool_weight_g: float | None = None
    notes: str | None = None


class VendorResponse(BaseModel):
    id: int
    name: str
    website: str | None
    empty_spool_weight_g: float | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Filament ──────────────────────────────────────────────────────────────

class FilamentCreate(BaseModel):
    vendor_id: int
    name: str
    material: str
    color_hex: str = "#FFFFFF"
    color_name: str | None = None
    diameter_mm: float = 1.75
    density_g_cm3: float = 1.24
    net_weight_g: float = 1000.0
    spool_weight_g: float | None = None
    nozzle_temp_min: int | None = None
    nozzle_temp_max: int | None = None
    nozzle_temp_default: int | None = None
    bed_temp_min: int | None = None
    bed_temp_max: int | None = None
    bed_temp_default: int | None = None
    price: float | None = None
    price_unit: str | None = None


class FilamentUpdate(BaseModel):
    vendor_id: int | None = None
    name: str | None = None
    material: str | None = None
    color_hex: str | None = None
    color_name: str | None = None
    diameter_mm: float | None = None
    density_g_cm3: float | None = None
    net_weight_g: float | None = None
    spool_weight_g: float | None = None
    nozzle_temp_min: int | None = None
    nozzle_temp_max: int | None = None
    nozzle_temp_default: int | None = None
    bed_temp_min: int | None = None
    bed_temp_max: int | None = None
    bed_temp_default: int | None = None
    price: float | None = None
    price_unit: str | None = None


class FilamentResponse(BaseModel):
    id: int
    vendor_id: int
    name: str
    material: str
    color_hex: str
    color_name: str | None
    diameter_mm: float
    density_g_cm3: float
    net_weight_g: float
    spool_weight_g: float | None
    nozzle_temp_min: int | None
    nozzle_temp_max: int | None
    nozzle_temp_default: int | None
    bed_temp_min: int | None
    bed_temp_max: int | None
    bed_temp_default: int | None
    price: float | None
    price_unit: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Spool ─────────────────────────────────────────────────────────────────

class SpoolCreate(BaseModel):
    filament_id: int
    initial_weight_g: float = 1000.0
    used_weight_g: float = 0.0
    location: str | None = None
    lot_nr: str | None = None
    purchase_date: date | None = None
    notes: str | None = None


class SpoolUpdate(BaseModel):
    filament_id: int | None = None
    initial_weight_g: float | None = None
    used_weight_g: float | None = None
    location: str | None = None
    lot_nr: str | None = None
    purchase_date: date | None = None
    archived: bool | None = None
    notes: str | None = None


class SpoolUse(BaseModel):
    used_weight_g: float
    source: str | None = None
    project_name: str | None = None


class SpoolMeasure(BaseModel):
    measured_weight_g: float


class SpoolResponse(BaseModel):
    id: int
    filament_id: int
    initial_weight_g: float
    used_weight_g: float
    remaining_weight_g: float
    remaining_percent: float
    remaining_length_m: float | None
    location: str | None
    lot_nr: str | None
    purchase_date: date | None
    first_used: datetime | None
    last_used: datetime | None
    archived: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Colors (Logo Station Integration) ────────────────────────────────────

class ColorEntry(BaseModel):
    color_hex: str
    color_name: str | None
    material: str
    vendor: str
    filament_name: str
    spool_id: int
    remaining_g: float
    remaining_percent: float
    remaining_m: float | None


class ColorMatchEntry(BaseModel):
    spool_id: int
    color_hex: str
    distance: float
    color_name: str | None
    material: str
    vendor: str
    filament_name: str
    remaining_g: float


class ColorMatchResponse(BaseModel):
    target_hex: str
    matches: list[ColorMatchEntry]


class PaletteAssignment(BaseModel):
    requested_hex: str
    suggestions: list[ColorMatchEntry]


class PaletteMatchResponse(BaseModel):
    assignments: list[PaletteAssignment]


# ── Health ────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    spools: int
