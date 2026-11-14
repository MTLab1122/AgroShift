from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import Field, field_validator, model_validator

from ..models.enums import EvidenceStatus, RequirementType
from ._base import ReadSchema, Schema, UpdateSchema


def _validate_calendar_fields(values: dict[str, Any], *, partial: bool = False) -> None:
    for start_name, end_name, cross_name, leap_name in (
        ("planting_start", "planting_end", "plant_crosses_year", "plant_leap_year_allowed"),
        ("harvest_start", "harvest_end", "harvest_crosses_year", "harvest_leap_year_allowed"),
    ):
        start = values.get(start_name)
        end = values.get(end_name)
        if not partial or {start_name, end_name} <= values.keys():
            if (start is None) != (end is None):
                raise ValueError(f"{start_name} and {end_name} must be provided together")
        if start is None or end is None:
            continue

        leap_allowed = values.get(leap_name, False)
        for field_name, month_day in ((start_name, start), (end_name, end)):
            if month_day == "02-29" and not leap_allowed:
                raise ValueError(f"{field_name} requires its leap-year flag")
            try:
                year = 2000 if leap_allowed else 2001
                datetime.strptime(f"{year}-{month_day}", "%Y-%m-%d")
            except ValueError as exc:
                raise ValueError(f"{field_name} must be a valid MM-DD value") from exc

        if cross_name in values or not partial:
            crosses_year = values.get(cross_name, False)
            if crosses_year != (start > end):
                raise ValueError(f"{cross_name} does not match the associated date range")


def _validate_requirement_fields(values: dict[str, Any], *, partial: bool = False) -> None:
    requirement_type = values.get("requirement_type")
    if requirement_type is None:
        return

    if isinstance(requirement_type, RequirementType):
        requirement_type = requirement_type.value

    groups = {
        RequirementType.SOIL.value: {"soil_type", "soil_ph_min", "soil_ph_max"},
        RequirementType.WATER.value: {
            "water_requirement", "water_requirement_unit", "water_requirement_basis",
        },
        RequirementType.TEMPERATURE.value: {"temperature_min", "temperature_max"},
        RequirementType.SALINITY.value: {"salinity_tolerance"},
        RequirementType.NUTRIENT.value: {
            "nutrient_n_value", "nutrient_n_unit", "nutrient_n_basis",
            "nutrient_p_value", "nutrient_p_unit", "nutrient_p_basis",
        },
        RequirementType.OTHER.value: {"other_description", "other_measurement_basis"},
    }
    all_fields = set().union(*groups.values())
    allowed = groups[requirement_type]
    supplied_fields = set(values) & all_fields
    if not partial:
        irrelevant = (all_fields - allowed) & {
            name for name, value in values.items() if value is not None
        }
        if irrelevant:
            raise ValueError(
                f"Fields {sorted(irrelevant)} do not apply to {requirement_type!r}"
            )

    if requirement_type == RequirementType.OTHER.value:
        description = values.get("other_description")
        if (not partial or "other_description" in values) and not description:
            raise ValueError("other_description is required for OTHER requirements")

    complete_groups = {
        RequirementType.WATER.value: ((
            "water_requirement", "water_requirement_unit", "water_requirement_basis",
        ),),
        RequirementType.TEMPERATURE.value: (("temperature_min", "temperature_max"),),
        RequirementType.NUTRIENT.value: (
            ("nutrient_n_value", "nutrient_n_unit", "nutrient_n_basis"),
            ("nutrient_p_value", "nutrient_p_unit", "nutrient_p_basis"),
        ),
    }
    for names in complete_groups.get(requirement_type, ()):
        if partial and not set(names) <= supplied_fields:
            continue
        present = [values.get(name) is not None for name in names]
        if any(present) and not all(present):
            raise ValueError(f"Fields {names} must be provided together")

    for lower_name, upper_name in (
        ("soil_ph_min", "soil_ph_max"),
        ("temperature_min", "temperature_max"),
    ):
        if lower_name in values and upper_name in values:
            lower = values.get(lower_name)
            upper = values.get(upper_name)
            if lower is not None and upper is not None and lower > upper:
                raise ValueError(f"{lower_name} must not exceed {upper_name}")


class CropCreate(Schema):
    slug: str = Field(min_length=1, max_length=160, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    common_name: str | None = Field(default=None, max_length=160)
    scientific_name: str | None = Field(default=None, max_length=200)
    crop_family: str | None = Field(default=None, max_length=120)
    crop_category: str | None = Field(default=None, max_length=120)
    is_legume: bool | None = None
    description: str | None = None
    active: bool = True
    evidence_status: EvidenceStatus = EvidenceStatus.UNKNOWN
    metadata_json: dict[str, Any] | None = None
    primary_evidence_id: int | None = Field(default=None, gt=0)
    evidence_record_ids: list[int] = Field(default_factory=list)

    @field_validator("evidence_record_ids")
    @classmethod
    def unique_evidence_ids(cls, values: list[int]) -> list[int]:
        if len(values) != len(set(values)):
            raise ValueError("evidence_record_ids must not contain duplicates")
        return values

    @model_validator(mode="after")
    def require_primary_evidence(self):
        if self.evidence_status in {EvidenceStatus.VERIFIED, EvidenceStatus.PROVISIONAL}:
            if self.primary_evidence_id is None:
                raise ValueError("VERIFIED and PROVISIONAL crops require primary evidence")
        return self


class CropUpdate(UpdateSchema):
    slug: str | None = Field(default=None, min_length=1, max_length=160, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    common_name: str | None = Field(default=None, max_length=160)
    scientific_name: str | None = Field(default=None, max_length=200)
    crop_family: str | None = Field(default=None, max_length=120)
    crop_category: str | None = Field(default=None, max_length=120)
    is_legume: bool | None = None
    description: str | None = None
    active: bool | None = None
    evidence_status: EvidenceStatus | None = None
    metadata_json: dict[str, Any] | None = None
    primary_evidence_id: int | None = Field(default=None, gt=0)
    evidence_record_ids: list[int] | None = None


class CropRead(ReadSchema):
    id: int
    slug: str
    common_name: str | None
    scientific_name: str | None
    crop_family: str | None
    crop_category: str | None
    is_legume: bool | None
    description: str | None
    active: bool
    evidence_status: EvidenceStatus
    metadata_json: dict[str, Any] | None
    primary_evidence_id: int | None
    evidence_record_ids: list[int] = Field(default_factory=list)
    variety_ids: list[int] = Field(default_factory=list)
    calendar_ids: list[int] = Field(default_factory=list)
    requirement_ids: list[int] = Field(default_factory=list)


class CropVarietyCreate(Schema):
    crop_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=200)
    maturity_class: str | None = Field(default=None, max_length=120)
    regional_adaptation: str | None = Field(default=None, max_length=500)
    duration_days: int | None = Field(default=None, ge=0)
    evidence_status: EvidenceStatus = EvidenceStatus.UNKNOWN
    source_id: int | None = Field(default=None, gt=0)
    metadata_json: dict[str, Any] | None = None
    primary_evidence_id: int | None = Field(default=None, gt=0)
    evidence_record_ids: list[int] = Field(default_factory=list)

    @field_validator("evidence_record_ids")
    @classmethod
    def unique_evidence_ids(cls, values: list[int]) -> list[int]:
        if len(values) != len(set(values)):
            raise ValueError("evidence_record_ids must not contain duplicates")
        return values

    @model_validator(mode="after")
    def require_primary_evidence(self):
        if self.evidence_status in {EvidenceStatus.VERIFIED, EvidenceStatus.PROVISIONAL}:
            if self.primary_evidence_id is None:
                raise ValueError("VERIFIED and PROVISIONAL varieties require primary evidence")
        return self


class CropVarietyUpdate(UpdateSchema):
    crop_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    maturity_class: str | None = Field(default=None, max_length=120)
    regional_adaptation: str | None = Field(default=None, max_length=500)
    duration_days: int | None = Field(default=None, ge=0)
    evidence_status: EvidenceStatus | None = None
    source_id: int | None = Field(default=None, gt=0)
    metadata_json: dict[str, Any] | None = None
    primary_evidence_id: int | None = Field(default=None, gt=0)
    evidence_record_ids: list[int] | None = None


class CropVarietyRead(ReadSchema):
    id: int
    crop_id: int
    name: str
    maturity_class: str | None
    regional_adaptation: str | None
    duration_days: int | None
    evidence_status: EvidenceStatus
    source_id: int | None
    metadata_json: dict[str, Any] | None
    primary_evidence_id: int | None
    evidence_record_ids: list[int] = Field(default_factory=list)
    calendar_ids: list[int] = Field(default_factory=list)
    requirement_ids: list[int] = Field(default_factory=list)


class CropCalendarCreate(Schema):
    crop_id: int = Field(gt=0)
    variety_id: int | None = Field(default=None, gt=0)
    country_id: int | None = Field(default=None, gt=0)
    province_state_id: int | None = Field(default=None, gt=0)
    district_id: int | None = Field(default=None, gt=0)
    agroecological_zone_id: int | None = Field(default=None, gt=0)
    region_label: str | None = Field(default=None, max_length=240)
    season: str | None = Field(default=None, max_length=120)
    planting_start: str | None = Field(default=None, min_length=5, max_length=5)
    planting_end: str | None = Field(default=None, min_length=5, max_length=5)
    harvest_start: str | None = Field(default=None, min_length=5, max_length=5)
    harvest_end: str | None = Field(default=None, min_length=5, max_length=5)
    plant_crosses_year: bool = False
    harvest_crosses_year: bool = False
    plant_leap_year_allowed: bool = False
    harvest_leap_year_allowed: bool = False
    growing_duration_days: int | None = Field(default=None, ge=0)
    calendar_source_id: int | None = Field(default=None, gt=0)
    confidence_level: Decimal | None = Field(default=None, ge=0, le=1)
    evidence_status: EvidenceStatus = EvidenceStatus.UNKNOWN
    notes: str | None = None
    primary_evidence_id: int | None = Field(default=None, gt=0)
    evidence_record_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_calendar(self):
        _validate_calendar_fields(self.model_dump())
        if self.evidence_status in {EvidenceStatus.VERIFIED, EvidenceStatus.PROVISIONAL}:
            if self.primary_evidence_id is None:
                raise ValueError("VERIFIED and PROVISIONAL calendars require primary evidence")
        return self


class CropCalendarUpdate(UpdateSchema):
    crop_id: int | None = Field(default=None, gt=0)
    variety_id: int | None = Field(default=None, gt=0)
    country_id: int | None = Field(default=None, gt=0)
    province_state_id: int | None = Field(default=None, gt=0)
    district_id: int | None = Field(default=None, gt=0)
    agroecological_zone_id: int | None = Field(default=None, gt=0)
    region_label: str | None = Field(default=None, max_length=240)
    season: str | None = Field(default=None, max_length=120)
    planting_start: str | None = Field(default=None, min_length=5, max_length=5)
    planting_end: str | None = Field(default=None, min_length=5, max_length=5)
    harvest_start: str | None = Field(default=None, min_length=5, max_length=5)
    harvest_end: str | None = Field(default=None, min_length=5, max_length=5)
    plant_crosses_year: bool | None = None
    harvest_crosses_year: bool | None = None
    plant_leap_year_allowed: bool | None = None
    harvest_leap_year_allowed: bool | None = None
    growing_duration_days: int | None = Field(default=None, ge=0)
    calendar_source_id: int | None = Field(default=None, gt=0)
    confidence_level: Decimal | None = Field(default=None, ge=0, le=1)
    evidence_status: EvidenceStatus | None = None
    notes: str | None = None
    primary_evidence_id: int | None = Field(default=None, gt=0)
    evidence_record_ids: list[int] | None = None

    @model_validator(mode="after")
    def validate_calendar(self):
        values = self.model_dump(exclude_unset=True)
        _validate_calendar_fields(values, partial=True)
        return self


class CropCalendarRead(ReadSchema):
    id: int
    crop_id: int
    variety_id: int | None
    country_id: int | None
    province_state_id: int | None
    district_id: int | None
    agroecological_zone_id: int | None
    region_label: str | None
    season: str | None
    planting_start: str | None
    planting_end: str | None
    harvest_start: str | None
    harvest_end: str | None
    plant_crosses_year: bool
    harvest_crosses_year: bool
    plant_leap_year_allowed: bool
    harvest_leap_year_allowed: bool
    growing_duration_days: int | None
    calendar_source_id: int | None
    confidence_level: Decimal | None
    evidence_status: EvidenceStatus
    notes: str | None
    primary_evidence_id: int | None
    evidence_record_ids: list[int] = Field(default_factory=list)


class CropRequirementCreate(Schema):
    crop_id: int = Field(gt=0)
    variety_id: int | None = Field(default=None, gt=0)
    requirement_type: RequirementType
    soil_type: str | None = Field(default=None, max_length=160)
    soil_ph_min: Decimal | None = Field(default=None, ge=0, le=14)
    soil_ph_max: Decimal | None = Field(default=None, ge=0, le=14)
    water_requirement: Decimal | None = Field(default=None, ge=0)
    water_requirement_unit: str | None = Field(default=None, max_length=80)
    water_requirement_basis: str | None = Field(default=None, max_length=160)
    temperature_min: Decimal | None = None
    temperature_max: Decimal | None = None
    salinity_tolerance: str | None = Field(default=None, max_length=240)
    additional_conditions: str | None = None
    source_id: int | None = Field(default=None, gt=0)
    evidence_status: EvidenceStatus = EvidenceStatus.UNKNOWN
    limitations: str | None = None
    nutrient_n_value: Decimal | None = Field(default=None, ge=0)
    nutrient_n_unit: str | None = Field(default=None, max_length=80)
    nutrient_n_basis: str | None = Field(default=None, max_length=160)
    nutrient_p_value: Decimal | None = Field(default=None, ge=0)
    nutrient_p_unit: str | None = Field(default=None, max_length=80)
    nutrient_p_basis: str | None = Field(default=None, max_length=160)
    other_description: str | None = None
    other_measurement_basis: str | None = Field(default=None, max_length=160)
    primary_evidence_id: int | None = Field(default=None, gt=0)
    evidence_record_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_measurements(self):
        _validate_requirement_fields(self.model_dump())
        if self.evidence_status in {EvidenceStatus.VERIFIED, EvidenceStatus.PROVISIONAL}:
            if self.primary_evidence_id is None:
                raise ValueError("VERIFIED and PROVISIONAL requirements require primary evidence")
        return self


class CropRequirementUpdate(UpdateSchema):
    crop_id: int | None = Field(default=None, gt=0)
    variety_id: int | None = Field(default=None, gt=0)
    requirement_type: RequirementType | None = None
    soil_type: str | None = Field(default=None, max_length=160)
    soil_ph_min: Decimal | None = Field(default=None, ge=0, le=14)
    soil_ph_max: Decimal | None = Field(default=None, ge=0, le=14)
    water_requirement: Decimal | None = Field(default=None, ge=0)
    water_requirement_unit: str | None = Field(default=None, max_length=80)
    water_requirement_basis: str | None = Field(default=None, max_length=160)
    temperature_min: Decimal | None = None
    temperature_max: Decimal | None = None
    salinity_tolerance: str | None = Field(default=None, max_length=240)
    additional_conditions: str | None = None
    source_id: int | None = Field(default=None, gt=0)
    evidence_status: EvidenceStatus | None = None
    limitations: str | None = None
    nutrient_n_value: Decimal | None = Field(default=None, ge=0)
    nutrient_n_unit: str | None = Field(default=None, max_length=80)
    nutrient_n_basis: str | None = Field(default=None, max_length=160)
    nutrient_p_value: Decimal | None = Field(default=None, ge=0)
    nutrient_p_unit: str | None = Field(default=None, max_length=80)
    nutrient_p_basis: str | None = Field(default=None, max_length=160)
    other_description: str | None = None
    other_measurement_basis: str | None = Field(default=None, max_length=160)
    primary_evidence_id: int | None = Field(default=None, gt=0)
    evidence_record_ids: list[int] | None = None

    @model_validator(mode="after")
    def validate_measurements(self):
        _validate_requirement_fields(self.model_dump(exclude_unset=True), partial=True)
        return self


class CropRequirementRead(ReadSchema):
    id: int
    crop_id: int
    variety_id: int | None
    requirement_type: RequirementType
    soil_type: str | None
    soil_ph_min: Decimal | None
    soil_ph_max: Decimal | None
    water_requirement: Decimal | None
    water_requirement_unit: str | None
    water_requirement_basis: str | None
    temperature_min: Decimal | None
    temperature_max: Decimal | None
    salinity_tolerance: str | None
    additional_conditions: str | None
    source_id: int | None
    evidence_status: EvidenceStatus
    limitations: str | None
    nutrient_n_value: Decimal | None
    nutrient_n_unit: str | None
    nutrient_n_basis: str | None
    nutrient_p_value: Decimal | None
    nutrient_p_unit: str | None
    nutrient_p_basis: str | None
    other_description: str | None
    other_measurement_basis: str | None
    primary_evidence_id: int | None
    evidence_record_ids: list[int] = Field(default_factory=list)


class CropRotationRuleCreate(Schema):
    previous_crop_id: int | None = Field(default=None, gt=0)
    next_crop_id: int | None = Field(default=None, gt=0)
    previous_variety_id: int | None = Field(default=None, gt=0)
    next_variety_id: int | None = Field(default=None, gt=0)
    source_family: str | None = Field(default=None, max_length=120)
    target_family: str | None = Field(default=None, max_length=120)
    rule_type: str | None = Field(default=None, max_length=120)
    compatibility_status: str | None = Field(default=None, max_length=120)
    severity: str | None = Field(default=None, max_length=120)
    explanation: str | None = None
    geographic_scope: str | None = None
    evidence_source_id: int | None = Field(default=None, gt=0)
    confidence_level: Decimal = Field(ge=0, le=1)
    evidence_status: EvidenceStatus = EvidenceStatus.UNKNOWN
    primary_evidence_id: int | None = Field(default=None, gt=0)
    evidence_record_ids: list[int] = Field(default_factory=list)
    geographic_scope_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_selectors(self):
        sources = (
            self.previous_crop_id,
            self.previous_variety_id,
            bool(self.source_family and self.source_family.strip()),
        )
        targets = (
            self.next_crop_id,
            self.next_variety_id,
            bool(self.target_family and self.target_family.strip()),
        )
        if sum(value is not None and value is not False for value in sources) != 1:
            raise ValueError("Exactly one previous-crop selector is required")
        if sum(value is not None and value is not False for value in targets) != 1:
            raise ValueError("Exactly one next-crop selector is required")
        if self.evidence_status in {EvidenceStatus.VERIFIED, EvidenceStatus.PROVISIONAL}:
            if self.primary_evidence_id is None:
                raise ValueError("VERIFIED and PROVISIONAL rotation rules require primary evidence")
        return self


class CropRotationRuleUpdate(UpdateSchema):
    previous_crop_id: int | None = Field(default=None, gt=0)
    next_crop_id: int | None = Field(default=None, gt=0)
    previous_variety_id: int | None = Field(default=None, gt=0)
    next_variety_id: int | None = Field(default=None, gt=0)
    source_family: str | None = Field(default=None, max_length=120)
    target_family: str | None = Field(default=None, max_length=120)
    rule_type: str | None = Field(default=None, max_length=120)
    compatibility_status: str | None = Field(default=None, max_length=120)
    severity: str | None = Field(default=None, max_length=120)
    explanation: str | None = None
    geographic_scope: str | None = None
    evidence_source_id: int | None = Field(default=None, gt=0)
    confidence_level: Decimal | None = Field(default=None, ge=0, le=1)
    evidence_status: EvidenceStatus | None = None
    primary_evidence_id: int | None = Field(default=None, gt=0)
    evidence_record_ids: list[int] | None = None
    geographic_scope_ids: list[int] | None = None

    @model_validator(mode="after")
    def validate_selectors(self):
        values = self.model_dump(exclude_unset=True)
        for selectors in (
            ("previous_crop_id", "previous_variety_id", "source_family"),
            ("next_crop_id", "next_variety_id", "target_family"),
        ):
            selected = [
                values[name]
                for name in selectors
                if name in values and values[name] is not None and values[name] != ""
            ]
            if len(selected) > 1:
                raise ValueError(f"Selectors {selectors} are mutually exclusive")
        return self


class CropRotationRuleRead(ReadSchema):
    id: int
    previous_crop_id: int | None
    next_crop_id: int | None
    previous_variety_id: int | None
    next_variety_id: int | None
    source_family: str | None
    target_family: str | None
    rule_type: str | None
    compatibility_status: str | None
    severity: str | None
    explanation: str | None
    geographic_scope: str | None
    evidence_source_id: int | None
    confidence_level: Decimal
    evidence_status: EvidenceStatus
    primary_evidence_id: int | None
    evidence_record_ids: list[int] = Field(default_factory=list)
    geographic_scope_ids: list[int] = Field(default_factory=list)
