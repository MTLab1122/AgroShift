"""SQLAlchemy ORM Models for Module 01: Farm Management & Location Intelligence.

Strictly mirrors contracts in:
- shared/schemas/farm.schema.json
- shared/schemas/crop.schema.json

Implements:
- Farm model with coordinates, boundary GeoJSON, and agricultural parameters.
- CropHistory model with cascading one-to-many relationship (`farm.crop_history`).
- Explicit indexes on `district`, `soil_type`, `year`, `season`, and foreign keys.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from backend.app.database import Base


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Farm(Base):
    __tablename__ = "farms"

    # Primary Identifier (matches farm_id from shared schemas)
    farm_id = Column(String(64), primary_key=True, index=True, nullable=False)
    name = Column(String(128), nullable=False, index=True)
    owner_name = Column(String(128), nullable=False)
    contact_phone = Column(String(32), nullable=False)
    preferred_language = Column(String(8), nullable=False, default="en")

    # Geolocation / Centroid Coordinates
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    elevation_meters = Column(Float, nullable=True)
    village_or_town = Column(String(128), nullable=True)
    district = Column(String(64), nullable=False, index=True)
    province_or_region = Column(String(64), nullable=False)
    country = Column(String(64), nullable=False, default="Pakistan")

    # Spatial Boundary (GeoJSON serialized format)
    boundary_geojson = Column(Text, nullable=True)

    # Agricultural Attributes
    total_area_hectares = Column(Float, nullable=False)
    soil_type = Column(String(32), nullable=False, default="alluvial_clay", index=True)
    irrigation_source = Column(String(32), nullable=False, default="canal")
    water_availability = Column(String(32), nullable=True, default="adequate")
    salinity_level = Column(String(32), nullable=True)  # Approved optional parameter

    # Standing Crops (JSON array of strings)
    current_crops_json = Column(Text, nullable=False, default="[]")

    # Audit Timestamps
    created_at = Column(String(64), nullable=False, default=utc_now_iso)
    updated_at = Column(String(64), nullable=False, default=utc_now_iso)

    # One-to-many relationship with CropHistory (cascades on delete)
    crop_history = relationship(
        "CropHistory",
        back_populates="farm",
        cascade="all, delete-orphan",
        order_by="desc(CropHistory.year)",
    )

    __table_args__ = (
        Index("idx_farm_coords", "latitude", "longitude"),
        Index("idx_farm_district_prov", "district", "province_or_region"),
    )

    @property
    def current_crops(self) -> list[str]:
        try:
            return json.loads(self.current_crops_json) if self.current_crops_json else []
        except Exception:
            return []

    @current_crops.setter
    def current_crops(self, val: list[str]) -> None:
        self.current_crops_json = json.dumps(val or [])

    @property
    def boundary(self) -> dict | None:
        try:
            return json.loads(self.boundary_geojson) if self.boundary_geojson else None
        except Exception:
            return None

    @boundary.setter
    def boundary(self, val: dict | None) -> None:
        self.boundary_geojson = json.dumps(val) if val else None


class CropHistory(Base):
    __tablename__ = "crop_history"

    record_id = Column(String(64), primary_key=True, index=True, nullable=False)
    farm_id = Column(
        String(64),
        ForeignKey("farms.farm_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    crop_name = Column(String(64), nullable=False, index=True)
    variety = Column(String(64), nullable=True)
    season = Column(String(32), nullable=False, index=True)  # Kharif, Rabi, Zaid, Spring, Autumn, Perennial
    year = Column(Integer, nullable=False, index=True)

    sowing_date = Column(String(32), nullable=True)
    harvest_date = Column(String(32), nullable=True)
    area_planted_hectares = Column(Float, nullable=True)
    yield_amount_kg = Column(Float, nullable=True)
    status = Column(String(32), nullable=False, default="growing")  # planned, sown, growing, harvested, failed
    notes = Column(Text, nullable=True)

    created_at = Column(String(64), nullable=False, default=utc_now_iso)

    # Relationship back to Farm
    farm = relationship("Farm", back_populates="crop_history")

    __table_args__ = (
        Index("idx_crop_farm_season_year", "farm_id", "season", "year"),
    )
