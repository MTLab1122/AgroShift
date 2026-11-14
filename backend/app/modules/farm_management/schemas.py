"""Pydantic v2 Schemas for Module 01: Farm Management & Location Intelligence.

Strictly aligned with shared/schemas/farm.schema.json and shared/schemas/crop.schema.json.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


SupportedLanguage = Literal["en", "ur", "ps"]

SoilType = Literal[
    "alluvial_clay",
    "sandy_loam",
    "clay_loam",
    "silt_loam",
    "sandy",
    "peat",
    "other",
]

IrrigationSource = Literal[
    "canal",
    "tube_well",
    "drip",
    "sprinkler",
    "rainfed",
    "river_lift",
    "other",
]

CropSeason = Literal[
    "Kharif",
    "Rabi",
    "Zaid",
    "Spring",
    "Autumn",
    "Perennial",
    "Other",
]

CropStatus = Literal["planned", "sown", "growing", "harvested", "failed"]


class FarmLocation(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees")
    elevation_meters: Optional[float] = Field(None, description="Elevation above sea level in meters")
    village_or_town: Optional[str] = Field(None, max_length=128)
    district: str = Field(..., min_length=2, max_length=64)
    province_or_region: str = Field(..., min_length=2, max_length=64)
    country: str = Field(default="Pakistan", max_length=64)


class FarmBoundary(BaseModel):
    type: Literal["Polygon", "MultiPolygon"]
    coordinates: List[Any] = Field(..., description="GeoJSON coordinate array")

    @field_validator("coordinates")
    @classmethod
    def validate_polygon_coordinates(cls, v: List[Any]) -> List[Any]:
        if not v or not isinstance(v, list):
            raise ValueError("Coordinates must be a non-empty list of coordinate rings.")
        return v


def calculate_polygon_area_ha(coordinates: List[List[List[float]]]) -> float:
    """Calculate geodesic approximate polygon area in hectares from GeoJSON coordinates [[ [lon, lat], ... ]]."""
    if not coordinates or not coordinates[0] or len(coordinates[0]) < 3:
        return 0.0

    ring = coordinates[0]
    radius = 6378137.0  # Earth radius in meters
    area = 0.0

    for i in range(len(ring)):
        j = (i + 1) % len(ring)
        lon1, lat1 = ring[i][0], ring[i][1]
        lon2, lat2 = ring[j][0], ring[j][1]

        r_lat1 = math.radians(lat1)
        r_lat2 = math.radians(lat2)
        r_lon1 = math.radians(lon1)
        r_lon2 = math.radians(lon2)

        area += (r_lon2 - r_lon1) * (2 + math.sin(r_lat1) + math.sin(r_lat2))

    area_m2 = abs((area * radius * radius) / 2.0)
    return round(area_m2 / 10000.0, 2)


# ==============================================================================
# Farm Profile Schemas
# ==============================================================================

class FarmCreate(BaseModel):
    farm_id: Optional[str] = Field(None, description="Optional custom identifier (e.g. farm-peshawar-001)")
    name: str = Field(..., min_length=2, max_length=100)
    owner_name: str = Field(..., min_length=2, max_length=100)
    contact_phone: str = Field(..., min_length=5, max_length=25)
    preferred_language: SupportedLanguage = Field(default="en")
    location: FarmLocation
    boundary: Optional[FarmBoundary] = None
    total_area_hectares: float = Field(..., gt=0.0)
    soil_type: SoilType = Field(default="alluvial_clay")
    irrigation_source: IrrigationSource = Field(default="canal")
    water_availability: Optional[str] = Field("adequate")
    salinity_level: Optional[str] = None
    current_crops: List[str] = Field(default_factory=list)


class FarmUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    owner_name: Optional[str] = Field(None, min_length=2, max_length=100)
    contact_phone: Optional[str] = Field(None, min_length=5, max_length=25)
    preferred_language: Optional[SupportedLanguage] = None
    location: Optional[FarmLocation] = None
    boundary: Optional[FarmBoundary] = None
    total_area_hectares: Optional[float] = Field(None, gt=0.0)
    soil_type: Optional[SoilType] = None
    irrigation_source: Optional[IrrigationSource] = None
    water_availability: Optional[str] = None
    salinity_level: Optional[str] = None
    current_crops: Optional[List[str]] = None


class FarmResponse(BaseModel):
    farm_id: str
    name: str
    owner_name: str
    contact_phone: str
    preferred_language: SupportedLanguage
    location: FarmLocation
    boundary: Optional[FarmBoundary] = None
    total_area_hectares: float
    soil_type: SoilType
    irrigation_source: IrrigationSource
    water_availability: Optional[str] = None
    salinity_level: Optional[str] = None
    current_crops: List[str]
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


# ==============================================================================
# Crop History Schemas
# ==============================================================================

class CropHistoryCreate(BaseModel):
    record_id: Optional[str] = None
    crop_name: str = Field(..., min_length=2, max_length=64)
    variety: Optional[str] = None
    season: CropSeason
    year: int = Field(..., ge=1980, le=2100)
    sowing_date: Optional[str] = None
    harvest_date: Optional[str] = None
    area_planted_hectares: Optional[float] = Field(None, gt=0.0)
    yield_amount_kg: Optional[float] = Field(None, ge=0.0)
    status: CropStatus = Field(default="growing")
    notes: Optional[str] = None


class CropHistoryUpdate(BaseModel):
    crop_name: Optional[str] = None
    variety: Optional[str] = None
    season: Optional[CropSeason] = None
    year: Optional[int] = Field(None, ge=1980, le=2100)
    sowing_date: Optional[str] = None
    harvest_date: Optional[str] = None
    area_planted_hectares: Optional[float] = None
    yield_amount_kg: Optional[float] = None
    status: Optional[CropStatus] = None
    notes: Optional[str] = None


class CropHistoryResponse(BaseModel):
    record_id: str
    farm_id: str
    crop_name: str
    variety: Optional[str] = None
    season: CropSeason
    year: int
    sowing_date: Optional[str] = None
    harvest_date: Optional[str] = None
    area_planted_hectares: Optional[float] = None
    yield_amount_kg: Optional[float] = None
    status: CropStatus
    notes: Optional[str] = None
    created_at: str

    model_config = {"from_attributes": True}


# ==============================================================================
# Conversational Assistant Schemas
# ==============================================================================

class AssistantChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    language: SupportedLanguage = Field(default="en")
    current_extracted: Optional[Dict[str, Any]] = None


class AssistantChatResponse(BaseModel):
    session_id: str
    reply_message: str
    language: SupportedLanguage
    extracted_farm: Dict[str, Any]
    missing_fields: List[str]
    is_ready_for_confirmation: bool
