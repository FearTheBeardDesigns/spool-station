"""Embedded FastAPI server that runs in a background QThread."""

from __future__ import annotations

import threading
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.api.schemas import (
    ColorEntry,
    ColorMatchEntry,
    ColorMatchResponse,
    FilamentCreate,
    FilamentResponse,
    FilamentUpdate,
    HealthResponse,
    PaletteAssignment,
    PaletteMatchResponse,
    SpoolCreate,
    SpoolMeasure,
    SpoolResponse,
    SpoolUpdate,
    SpoolUse,
    VendorCreate,
    VendorResponse,
    VendorUpdate,
)
from app.db.engine import get_session
from app.db.models import Filament, Spool, UsageLog, Vendor
from app.utils.color_distance import color_distance

VERSION = "1.0.0"

app = FastAPI(title="Spool Station API", version=VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ────────────────────────────────────────────────────────────────


@app.get("/api/v1/health", response_model=HealthResponse)
def health():
    session = get_session()
    try:
        count = session.query(Spool).filter(Spool.archived == False).count()  # noqa: E712
    finally:
        session.close()
    return HealthResponse(status="ok", version=VERSION, spools=count)


# ── Vendors ───────────────────────────────────────────────────────────────


@app.get("/api/v1/vendors", response_model=list[VendorResponse])
def list_vendors():
    session = get_session()
    try:
        return session.query(Vendor).order_by(Vendor.name).all()
    finally:
        session.close()


@app.get("/api/v1/vendors/{vendor_id}", response_model=VendorResponse)
def get_vendor(vendor_id: int):
    session = get_session()
    try:
        v = session.get(Vendor, vendor_id)
        if not v:
            raise HTTPException(404, "Vendor not found")
        return v
    finally:
        session.close()


@app.post("/api/v1/vendors", response_model=VendorResponse, status_code=201)
def create_vendor(data: VendorCreate):
    session = get_session()
    try:
        v = Vendor(**data.model_dump())
        session.add(v)
        session.commit()
        session.refresh(v)
        return v
    finally:
        session.close()


@app.patch("/api/v1/vendors/{vendor_id}", response_model=VendorResponse)
def update_vendor(vendor_id: int, data: VendorUpdate):
    session = get_session()
    try:
        v = session.get(Vendor, vendor_id)
        if not v:
            raise HTTPException(404, "Vendor not found")
        for k, val in data.model_dump(exclude_unset=True).items():
            setattr(v, k, val)
        v.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(v)
        return v
    finally:
        session.close()


@app.delete("/api/v1/vendors/{vendor_id}", status_code=204)
def delete_vendor(vendor_id: int):
    session = get_session()
    try:
        v = session.get(Vendor, vendor_id)
        if not v:
            raise HTTPException(404, "Vendor not found")
        session.delete(v)
        session.commit()
    finally:
        session.close()


# ── Filaments ─────────────────────────────────────────────────────────────


@app.get("/api/v1/filaments", response_model=list[FilamentResponse])
def list_filaments(
    vendor_id: int | None = None,
    material: str | None = None,
):
    session = get_session()
    try:
        q = session.query(Filament)
        if vendor_id:
            q = q.filter(Filament.vendor_id == vendor_id)
        if material:
            q = q.filter(Filament.material == material)
        return q.order_by(Filament.name).all()
    finally:
        session.close()


@app.get("/api/v1/filaments/{filament_id}", response_model=FilamentResponse)
def get_filament(filament_id: int):
    session = get_session()
    try:
        f = session.get(Filament, filament_id)
        if not f:
            raise HTTPException(404, "Filament not found")
        return f
    finally:
        session.close()


@app.post("/api/v1/filaments", response_model=FilamentResponse, status_code=201)
def create_filament(data: FilamentCreate):
    session = get_session()
    try:
        f = Filament(**data.model_dump())
        session.add(f)
        session.commit()
        session.refresh(f)
        return f
    finally:
        session.close()


@app.patch("/api/v1/filaments/{filament_id}", response_model=FilamentResponse)
def update_filament(filament_id: int, data: FilamentUpdate):
    session = get_session()
    try:
        f = session.get(Filament, filament_id)
        if not f:
            raise HTTPException(404, "Filament not found")
        for k, val in data.model_dump(exclude_unset=True).items():
            setattr(f, k, val)
        f.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(f)
        return f
    finally:
        session.close()


@app.delete("/api/v1/filaments/{filament_id}", status_code=204)
def delete_filament(filament_id: int):
    session = get_session()
    try:
        f = session.get(Filament, filament_id)
        if not f:
            raise HTTPException(404, "Filament not found")
        if f.spools:
            raise HTTPException(403, "Cannot delete filament with existing spools")
        session.delete(f)
        session.commit()
    finally:
        session.close()


# ── Spools ────────────────────────────────────────────────────────────────


@app.get("/api/v1/spools", response_model=list[SpoolResponse])
def list_spools(
    filament_id: int | None = None,
    material: str | None = None,
    location: str | None = None,
    allow_archived: bool = False,
):
    session = get_session()
    try:
        q = session.query(Spool).join(Filament)
        if filament_id:
            q = q.filter(Spool.filament_id == filament_id)
        if material:
            q = q.filter(Filament.material == material)
        if location:
            q = q.filter(Spool.location == location)
        if not allow_archived:
            q = q.filter(Spool.archived == False)  # noqa: E712
        return q.all()
    finally:
        session.close()


@app.get("/api/v1/spools/{spool_id}", response_model=SpoolResponse)
def get_spool(spool_id: int):
    session = get_session()
    try:
        s = session.get(Spool, spool_id)
        if not s:
            raise HTTPException(404, "Spool not found")
        return s
    finally:
        session.close()


@app.post("/api/v1/spools", response_model=SpoolResponse, status_code=201)
def create_spool(data: SpoolCreate):
    session = get_session()
    try:
        s = Spool(**data.model_dump())
        session.add(s)
        session.commit()
        session.refresh(s)
        return s
    finally:
        session.close()


@app.patch("/api/v1/spools/{spool_id}", response_model=SpoolResponse)
def update_spool(spool_id: int, data: SpoolUpdate):
    session = get_session()
    try:
        s = session.get(Spool, spool_id)
        if not s:
            raise HTTPException(404, "Spool not found")
        for k, val in data.model_dump(exclude_unset=True).items():
            setattr(s, k, val)
        s.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(s)
        return s
    finally:
        session.close()


@app.delete("/api/v1/spools/{spool_id}", status_code=204)
def delete_spool(spool_id: int):
    session = get_session()
    try:
        s = session.get(Spool, spool_id)
        if not s:
            raise HTTPException(404, "Spool not found")
        session.delete(s)
        session.commit()
    finally:
        session.close()


@app.put("/api/v1/spools/{spool_id}/use", response_model=SpoolResponse)
def use_spool(spool_id: int, data: SpoolUse):
    session = get_session()
    try:
        s = session.get(Spool, spool_id)
        if not s:
            raise HTTPException(404, "Spool not found")
        s.used_weight_g += data.used_weight_g
        s.last_used = datetime.utcnow()
        if s.first_used is None:
            s.first_used = datetime.utcnow()

        log = UsageLog(
            spool_id=spool_id,
            used_weight_g=data.used_weight_g,
            source=data.source,
            project_name=data.project_name,
        )
        session.add(log)
        session.commit()
        session.refresh(s)
        return s
    finally:
        session.close()


@app.put("/api/v1/spools/{spool_id}/measure", response_model=SpoolResponse)
def measure_spool(spool_id: int, data: SpoolMeasure):
    session = get_session()
    try:
        s = session.get(Spool, spool_id)
        if not s:
            raise HTTPException(404, "Spool not found")

        s.measured_weight_g = data.measured_weight_g
        # Calculate used weight from measurement
        spool_tare = s.filament.spool_weight_g or 0
        if s.filament.vendor and s.filament.vendor.empty_spool_weight_g:
            spool_tare = spool_tare or s.filament.vendor.empty_spool_weight_g
        net_remaining = max(0.0, data.measured_weight_g - spool_tare)
        s.used_weight_g = max(0.0, s.initial_weight_g - net_remaining)
        s.updated_at = datetime.utcnow()

        session.commit()
        session.refresh(s)
        return s
    finally:
        session.close()


# ── Colors (Logo Station Integration) ────────────────────────────────────


@app.get("/api/v1/colors", response_model=list[ColorEntry])
def list_colors():
    """Return all active spool colors with remaining amounts."""
    session = get_session()
    try:
        spools = (
            session.query(Spool)
            .join(Filament)
            .join(Vendor)
            .filter(Spool.archived == False)  # noqa: E712
            .all()
        )
        result = []
        for s in spools:
            result.append(
                ColorEntry(
                    color_hex=s.filament.color_hex or "#FFFFFF",
                    color_name=s.filament.color_name,
                    material=s.filament.material,
                    vendor=s.filament.vendor.name if s.filament.vendor else "?",
                    filament_name=s.filament.name,
                    spool_id=s.id,
                    remaining_g=s.remaining_weight_g,
                    remaining_percent=s.remaining_percent,
                    remaining_m=s.remaining_length_m,
                )
            )
        return result
    finally:
        session.close()


@app.get("/api/v1/colors/match", response_model=ColorMatchResponse)
def match_color(
    hex: str = Query(..., description="Target hex color to match"),
    material: str | None = Query(None, description="Filter by material"),
    min_remaining_g: float = Query(0, description="Minimum remaining grams"),
):
    """Find closest spools to a target color. User picks from suggestions."""
    session = get_session()
    try:
        q = (
            session.query(Spool)
            .join(Filament)
            .join(Vendor)
            .filter(Spool.archived == False)  # noqa: E712
        )
        if material:
            q = q.filter(Filament.material == material)

        spools = q.all()
        matches = []
        target = hex if hex.startswith("#") else f"#{hex}"

        for s in spools:
            if s.remaining_weight_g < min_remaining_g:
                continue
            spool_color = s.filament.color_hex or "#FFFFFF"
            if not spool_color.startswith("#"):
                spool_color = f"#{spool_color}"
            dist = color_distance(target, spool_color)
            matches.append(
                ColorMatchEntry(
                    spool_id=s.id,
                    color_hex=spool_color,
                    distance=round(dist, 2),
                    color_name=s.filament.color_name,
                    material=s.filament.material,
                    vendor=s.filament.vendor.name if s.filament.vendor else "?",
                    filament_name=s.filament.name,
                    remaining_g=s.remaining_weight_g,
                )
            )

        matches.sort(key=lambda m: m.distance)
        return ColorMatchResponse(target_hex=target, matches=matches)
    finally:
        session.close()


@app.get("/api/v1/colors/match-palette", response_model=PaletteMatchResponse)
def match_palette(
    hexes: str = Query(..., description="Comma-separated hex colors"),
    material: str | None = Query(None, description="Filter by material"),
    min_remaining_g: float = Query(0, description="Minimum remaining grams"),
):
    """Match a full palette. Returns suggestions per color — user picks each."""
    hex_list = [h.strip() for h in hexes.split(",") if h.strip()]
    assignments = []
    for h in hex_list:
        result = match_color(hex=h, material=material, min_remaining_g=min_remaining_g)
        assignments.append(
            PaletteAssignment(
                requested_hex=result.target_hex,
                suggestions=result.matches,
            )
        )
    return PaletteMatchResponse(assignments=assignments)


# ── Server Runner ─────────────────────────────────────────────────────────

_server_thread: threading.Thread | None = None


def start_api_server(port: int = 7912) -> None:
    """Start the FastAPI server in a background daemon thread."""
    global _server_thread

    def _run():
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

    _server_thread = threading.Thread(target=_run, daemon=True)
    _server_thread.start()
