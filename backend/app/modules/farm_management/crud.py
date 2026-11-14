"""CRUD and Business Logic Operations for Farms and Crop History (Module 01)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.app.modules.farm_management.models import Farm, CropHistory
from backend.app.modules.farm_management.schemas import (
    FarmCreate,
    FarmUpdate,
    CropHistoryCreate,
    CropHistoryUpdate,
    calculate_polygon_area_ha,
)


def get_farms(db: Session, skip: int = 0, limit: int = 100) -> List[Farm]:
    return db.query(Farm).offset(skip).limit(limit).all()


def get_farm_by_id(db: Session, farm_id: str) -> Optional[Farm]:
    return db.query(Farm).filter(Farm.farm_id == farm_id).first()


def create_farm(db: Session, farm_in: FarmCreate) -> Farm:
    farm_id = farm_in.farm_id or f"farm-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()

    # If boundary polygon supplied but area was 0 or omitted, calculate geodesic estimate
    total_area = farm_in.total_area_hectares
    if farm_in.boundary and farm_in.boundary.type == "Polygon" and total_area <= 0:
        total_area = calculate_polygon_area_ha(farm_in.boundary.coordinates)

    db_farm = Farm(
        farm_id=farm_id,
        name=farm_in.name,
        owner_name=farm_in.owner_name,
        contact_phone=farm_in.contact_phone,
        preferred_language=farm_in.preferred_language,
        latitude=farm_in.location.latitude,
        longitude=farm_in.location.longitude,
        elevation_meters=farm_in.location.elevation_meters,
        village_or_town=farm_in.location.village_or_town,
        district=farm_in.location.district,
        province_or_region=farm_in.location.province_or_region,
        country=farm_in.location.country,
        boundary_geojson=json.dumps(farm_in.boundary.model_dump()) if farm_in.boundary else None,
        total_area_hectares=total_area,
        soil_type=farm_in.soil_type,
        irrigation_source=farm_in.irrigation_source,
        water_availability=farm_in.water_availability,
        salinity_level=farm_in.salinity_level,
        current_crops_json=json.dumps(farm_in.current_crops or []),
        created_at=now,
        updated_at=now,
    )

    db.add(db_farm)
    db.commit()
    db.refresh(db_farm)
    return db_farm


def update_farm(db: Session, farm_id: str, farm_in: FarmUpdate) -> Optional[Farm]:
    db_farm = get_farm_by_id(db, farm_id)
    if not db_farm:
        return None

    update_data = farm_in.model_dump(exclude_unset=True)

    if "location" in update_data and update_data["location"]:
        loc = update_data["location"]
        db_farm.latitude = loc["latitude"]
        db_farm.longitude = loc["longitude"]
        db_farm.elevation_meters = loc.get("elevation_meters")
        db_farm.village_or_town = loc.get("village_or_town")
        db_farm.district = loc["district"]
        db_farm.province_or_region = loc["province_or_region"]
        db_farm.country = loc.get("country", "Pakistan")

    if "boundary" in update_data:
        db_farm.boundary_geojson = json.dumps(update_data["boundary"]) if update_data["boundary"] else None

    if "current_crops" in update_data:
        db_farm.current_crops_json = json.dumps(update_data["current_crops"] or [])

    scalar_fields = [
        "name",
        "owner_name",
        "contact_phone",
        "preferred_language",
        "total_area_hectares",
        "soil_type",
        "irrigation_source",
        "water_availability",
        "salinity_level",
    ]
    for field in scalar_fields:
        if field in update_data:
            setattr(db_farm, field, update_data[field])

    db_farm.updated_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    db.refresh(db_farm)
    return db_farm


def delete_farm(db: Session, farm_id: str) -> bool:
    db_farm = get_farm_by_id(db, farm_id)
    if not db_farm:
        return False
    db.delete(db_farm)
    db.commit()
    return True


# ==============================================================================
# Crop History Operations
# ==============================================================================

def get_crops_by_farm(db: Session, farm_id: str) -> List[CropHistory]:
    return (
        db.query(CropHistory)
        .filter(CropHistory.farm_id == farm_id)
        .order_by(CropHistory.year.desc())
        .all()
    )


def create_crop_record(db: Session, farm_id: str, crop_in: CropHistoryCreate) -> Optional[CropHistory]:
    farm = get_farm_by_id(db, farm_id)
    if not farm:
        return None

    record_id = crop_in.record_id or f"crop-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()

    db_crop = CropHistory(
        record_id=record_id,
        farm_id=farm_id,
        crop_name=crop_in.crop_name,
        variety=crop_in.variety,
        season=crop_in.season,
        year=crop_in.year,
        sowing_date=crop_in.sowing_date,
        harvest_date=crop_in.harvest_date,
        area_planted_hectares=crop_in.area_planted_hectares,
        yield_amount_kg=crop_in.yield_amount_kg,
        status=crop_in.status,
        notes=crop_in.notes,
        created_at=now,
    )
    db.add(db_crop)
    db.commit()
    db.refresh(db_crop)
    return db_crop


def update_crop_record(
    db: Session, farm_id: str, record_id: str, crop_in: CropHistoryUpdate
) -> Optional[CropHistory]:
    db_crop = (
        db.query(CropHistory)
        .filter(CropHistory.farm_id == farm_id, CropHistory.record_id == record_id)
        .first()
    )
    if not db_crop:
        return None

    update_data = crop_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(db_crop, field, val)

    db.commit()
    db.refresh(db_crop)
    return db_crop


def delete_crop_record(db: Session, farm_id: str, record_id: str) -> bool:
    db_crop = (
        db.query(CropHistory)
        .filter(CropHistory.farm_id == farm_id, CropHistory.record_id == record_id)
        .first()
    )
    if not db_crop:
        return False
    db.delete(db_crop)
    db.commit()
    return True
