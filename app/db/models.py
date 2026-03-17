"""SQLAlchemy ORM models for Spool Station."""

from __future__ import annotations

import math
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    website: Mapped[str | None] = mapped_column(String(256), nullable=True)
    empty_spool_weight_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    filaments: Mapped[list[Filament]] = relationship(
        "Filament", back_populates="vendor", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Vendor id={self.id} name={self.name!r}>"


class Filament(Base):
    __tablename__ = "filaments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vendor_id: Mapped[int] = mapped_column(Integer, ForeignKey("vendors.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    material: Mapped[str] = mapped_column(String(64), nullable=False)
    color_hex: Mapped[str] = mapped_column(String(9), nullable=False, default="#FFFFFF")
    color_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    diameter_mm: Mapped[float] = mapped_column(Float, nullable=False, default=1.75)
    density_g_cm3: Mapped[float] = mapped_column(Float, nullable=False, default=1.24)
    net_weight_g: Mapped[float] = mapped_column(Float, nullable=False, default=1000.0)
    spool_weight_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    nozzle_temp_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nozzle_temp_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nozzle_temp_default: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bed_temp_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bed_temp_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bed_temp_default: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tensile_strength_mpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_print_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_volumetric_flow: Mapped[float | None] = mapped_column(Float, nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    finish: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pattern: Mapped[str | None] = mapped_column(String(32), nullable=True)
    translucent: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    glow: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    multi_color_direction: Mapped[str | None] = mapped_column(String(32), nullable=True)
    color_hexes: Mapped[str | None] = mapped_column(String(128), nullable=True)
    spool_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    settings_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    vendor: Mapped[Vendor] = relationship("Vendor", back_populates="filaments")
    spools: Mapped[list[Spool]] = relationship(
        "Spool", back_populates="filament", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Filament id={self.id} name={self.name!r} material={self.material!r}>"


class Spool(Base):
    __tablename__ = "spools"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filament_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("filaments.id"), nullable=False
    )
    initial_weight_g: Mapped[float] = mapped_column(Float, nullable=False, default=1000.0)
    used_weight_g: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    measured_weight_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    location: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lot_nr: Mapped[str | None] = mapped_column(String(64), nullable=True)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    first_used: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_used: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    filament: Mapped[Filament] = relationship("Filament", back_populates="spools")
    usage_logs: Mapped[list[UsageLog]] = relationship(
        "UsageLog", back_populates="spool", cascade="all, delete-orphan"
    )

    @property
    def remaining_weight_g(self) -> float:
        return max(0.0, self.initial_weight_g - self.used_weight_g)

    @property
    def remaining_percent(self) -> float:
        if self.initial_weight_g <= 0:
            return 0.0
        return (self.remaining_weight_g / self.initial_weight_g) * 100.0

    @property
    def remaining_length_m(self) -> float | None:
        """Estimated remaining length from weight, density, and diameter."""
        fil = self.filament
        if not fil or fil.density_g_cm3 <= 0 or fil.diameter_mm <= 0:
            return None
        r_cm = fil.diameter_mm / 20.0
        area_cm2 = math.pi * r_cm**2
        vol_cm3 = self.remaining_weight_g / fil.density_g_cm3
        length_cm = vol_cm3 / area_cm2
        return length_cm / 100.0

    def __repr__(self) -> str:
        return (
            f"<Spool id={self.id} filament_id={self.filament_id} "
            f"remaining={self.remaining_weight_g:.0f}g>"
        )


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    spool_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("spools.id"), nullable=False
    )
    used_weight_g: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    project_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    spool: Mapped[Spool] = relationship("Spool", back_populates="usage_logs")

    def __repr__(self) -> str:
        return f"<UsageLog spool={self.spool_id} used={self.used_weight_g:.1f}g>"
