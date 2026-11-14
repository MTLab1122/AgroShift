"""Canonical Farm Profile and Crop History Schemas (Module 01).

Defines the Pydantic v2 data models corresponding to shared/schemas/farm.schema.json.
"""

from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class CropHistoryEntry(BaseModel):
    """Historical cropping record for a farm parcel."""

    model_config = ConfigDict(extra="forbid")

    entry_id: str = Field(..., min_length=1, description="Unique identifier for history record")
    crop_name: str = Field(..., min_length=1, description="Crop cultivated")
    season: str = Field(..., min_length=1, description="Cropping season (e.g. Kharif, Rabi)")
    year: int = Field(..., ge=1900, description="Cropping year")
    yield_value: Optional[float] = Field(default=None, description="Observed crop yield")
    yield_unit: Optional[str] = Field(default=None, description="Yield unit (e.g. kg/acre, maunds/acre)")
    notes: Optional[str] = Field(default=None, description="Field notes, pest issues, or weather impacts")


class FarmProfile(BaseModel):
    """Canonical farm profile definition."""

    model_config = ConfigDict(extra="forbid")

    farm_id: str = Field(..., min_length=1, description="Unique farm identifier (e.g. farm-peshawar-001)")
    farm_name: str = Field(..., min_length=1, description="Descriptive farmer or village name")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees")
    area_value: float = Field(..., gt=0.0, description="Cultivated land area")
    area_unit: Literal["acres", "hectares", "kanals", "jeribs"] = Field(
        ..., description="Standard land measurement unit"
    )
    soil_type: Literal["clay", "sandy", "loamy", "silty", "clay_loam", "other", "unknown"] = Field(
        ..., description="Dominant topsoil classification"
    )
    irrigation_type: Literal[
        "canal", "tube_well", "rain_fed", "drip", "sprinkler", "other", "unknown"
    ] = Field(..., description="Primary irrigation water delivery method")
    water_availability: Literal["low", "medium", "high", "unknown"] = Field(
        ..., description="Reported seasonal water availability"
    )
    current_crop: str = Field(..., min_length=1, description="Currently standing or planned crop")
    season: Literal[
        "Kharif", "Rabi", "Zaid", "Spring", "Summer", "Winter", "Annual", "other", "unknown"
    ] = Field(..., description="Target agricultural season")
    crop_history: List[CropHistoryEntry] = Field(
        default_factory=list, description="Historical crop sequence"
    )
    is_demo_data: bool = Field(
        default=False,
        description="True when this farm profile is a synthetic integration fixture.",
    )
