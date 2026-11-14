from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import Field, model_validator

from backend.app.modules.nasa_data.schemas import ClimateSummary

from ._base import Schema


class FeasibilityStatus(str, Enum):
    FEASIBLE = "FEASIBLE"
    CONDITIONALLY_FEASIBLE = "CONDITIONALLY_FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class FarmContext(Schema):
    farm_id: str | None = Field(default=None, min_length=1, max_length=128)
    country_id: int | None = Field(default=None, gt=0)
    province_state_id: int | None = Field(default=None, gt=0)
    district_id: int | None = Field(default=None, gt=0)
    locality_id: int | None = Field(default=None, gt=0)
    agroecological_zone_id: int | None = Field(default=None, gt=0)
    area: Decimal | None = Field(default=None, gt=0)
    area_unit: str | None = Field(default=None, min_length=1, max_length=80)
    soil_type: str | None = Field(default=None, max_length=160)
    soil_ph: Decimal | None = Field(default=None, ge=0, le=14)
    soil_texture: str | None = Field(default=None, max_length=160)
    drainage: str | None = Field(default=None, max_length=160)
    organic_matter: Decimal | None = Field(default=None, ge=0)
    salinity: Decimal | None = Field(default=None, ge=0)
    salinity_unit: str | None = Field(default=None, max_length=80)
    irrigation_available: bool | None = None
    water_available: Decimal | None = Field(default=None, ge=0)
    water_unit: str | None = Field(default=None, max_length=80)
    water_basis: str | None = Field(default=None, max_length=160)
    season_duration_days: int | None = Field(default=None, gt=0)
    planting_date: date | None = None
    harvest_date: date | None = None

    @model_validator(mode="after")
    def validate_measurement_units(self):
        if self.water_available is not None and (
            self.water_unit is None or self.water_basis is None
        ):
            raise ValueError("water_unit and water_basis are required with water_available")
        if self.salinity is not None and self.salinity_unit is None:
            raise ValueError("salinity_unit is required with salinity")
        if self.area is not None and self.area_unit is None:
            raise ValueError("area_unit is required with area")
        if (
            self.planting_date is not None
            and self.harvest_date is not None
            and self.harvest_date < self.planting_date
        ):
            raise ValueError("harvest_date must not precede planting_date")
        return self


class CropSelector(Schema):
    crop_id: int | None = Field(default=None, gt=0)
    crop_identifier: str | None = Field(default=None, min_length=1, max_length=160)
    variety_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def require_crop_reference(self):
        if (self.crop_id is None) == (self.crop_identifier is None):
            raise ValueError("Provide exactly one of crop_id or crop_identifier")
        return self


class CropHistoryItem(CropSelector):
    source_record_id: str | None = Field(default=None, max_length=160)
    evidence_record_ids: list[int] = Field(default_factory=list)
    planted_on: date | None = None
    harvested_on: date | None = None
    season: str | None = Field(default=None, max_length=120)


class CropValidationRequest(CropSelector):
    farm_context: FarmContext | None = None
    upcoming_season: str | None = Field(default=None, max_length=120)
    climate: ClimateSummary | None = None
    prior_history: list[CropHistoryItem] = Field(default_factory=list)


class FarmValidationRequest(Schema):
    farm_id: str = Field(min_length=1, max_length=128)
    farm_context: FarmContext | None = None
    candidate_crops: list[CropSelector] = Field(default_factory=list)
    crop_history: list[CropHistoryItem] = Field(default_factory=list)
    upcoming_season: str | None = Field(default=None, max_length=120)
    climate: ClimateSummary | None = None

    @model_validator(mode="after")
    def match_context_farm(self):
        if (
            self.farm_context is not None
            and self.farm_context.farm_id is not None
            and self.farm_context.farm_id != self.farm_id
        ):
            raise ValueError("farm_context.farm_id must match farm_id")
        return self


class SequenceValidationRequest(Schema):
    sequence: list[CropSelector] = Field(min_length=1)
    prior_history: list[CropHistoryItem] = Field(default_factory=list)
    farm_context: FarmContext | None = None
    upcoming_season: str | None = Field(default=None, max_length=120)
    climate: ClimateSummary | None = None


class ValidationCheck(Schema):
    check_code: str
    status: FeasibilityStatus
    detail: str
    inputs: dict = Field(default_factory=dict)
    rules_applied: list[str] = Field(default_factory=list)
    evidence_record_ids: list[int] = Field(default_factory=list)
    source_ids: list[int] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class SourceReference(Schema):
    source_id: int
    organization: str | None = None
    title: str | None = None
    publication_url: str | None = None
    review_status: str | None = None


class CropValidationResult(Schema):
    status: FeasibilityStatus
    crop_id: int | None = None
    crop_slug: str | None = None
    farm_id: str | None = None
    checks: list[ValidationCheck] = Field(default_factory=list)
    inputs: dict = Field(default_factory=dict)
    evidence_record_ids: list[int] = Field(default_factory=list)
    source_references: list[SourceReference] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class FarmValidationResult(Schema):
    farm_id: str
    results: list[CropValidationResult] = Field(default_factory=list)
    status: FeasibilityStatus
    missing_information: list[str] = Field(default_factory=list)


class SequenceValidationResult(Schema):
    status: FeasibilityStatus
    crop_results: list[CropValidationResult] = Field(default_factory=list)
    transition_results: list[ValidationCheck] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
