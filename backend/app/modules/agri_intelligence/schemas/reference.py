from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from ..models.enums import (
    ApplicabilityMode,
    EvidenceOriginType,
    GeographicScopeType,
)
from ._base import ReadSchema, Schema, UpdateSchema


_GEOGRAPHIC_FIELDS = (
    "country_id",
    "province_state_id",
    "district_id",
    "locality_id",
    "agroecological_zone_id",
    "farm_id",
)


def _validate_geographic_scope(values: dict, *, allow_farm: bool) -> None:
    scope_type = values.get("scope_type")
    if scope_type is None:
        return
    expected = {
        GeographicScopeType.GLOBAL: set(),
        GeographicScopeType.COUNTRY: {"country_id"},
        GeographicScopeType.PROVINCE_STATE: {"province_state_id"},
        GeographicScopeType.DISTRICT: {"district_id"},
        GeographicScopeType.LOCALITY: {"locality_id"},
        GeographicScopeType.AGROECOLOGICAL_ZONE: {"agroecological_zone_id"},
        GeographicScopeType.FARM: {"farm_id"},
    }[scope_type]
    if scope_type is GeographicScopeType.FARM and not allow_farm:
        raise ValueError("FARM scope is only valid for evidence")
    present = {
        name for name in _GEOGRAPHIC_FIELDS
        if values.get(name) is not None
    }
    if present != expected:
        raise ValueError(f"{scope_type.value} scope requires exactly {sorted(expected)}")
    if scope_type is GeographicScopeType.FARM and not values["farm_id"].strip():
        raise ValueError("farm_id must not be blank")


class GeographicScopeInput(Schema):
    scope_type: GeographicScopeType
    country_id: int | None = Field(default=None, gt=0)
    province_state_id: int | None = Field(default=None, gt=0)
    district_id: int | None = Field(default=None, gt=0)
    locality_id: int | None = Field(default=None, gt=0)
    agroecological_zone_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_scope(self):
        _validate_geographic_scope(self.model_dump(), allow_farm=False)
        return self


class EvidenceGeographicScopeInput(GeographicScopeInput):
    farm_id: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_scope(self):
        _validate_geographic_scope(self.model_dump(), allow_farm=True)
        return self


class SourceApplicabilityInput(Schema):
    applicability_mode: ApplicabilityMode
    crop_id: int | None = Field(default=None, gt=0)
    variety_id: int | None = Field(default=None, gt=0)
    family_name: str | None = Field(default=None, min_length=1, max_length=120)

    @model_validator(mode="after")
    def validate_selector(self):
        selectors = {
            ApplicabilityMode.CROP: ("crop_id",),
            ApplicabilityMode.VARIETY: ("variety_id",),
            ApplicabilityMode.FAMILY: ("family_name",),
        }
        expected = selectors.get(self.applicability_mode)
        if expected is None:
            raise ValueError("ALL_CROPS applicability is represented separately")
        present = {
            name for name in ("crop_id", "variety_id", "family_name")
            if getattr(self, name) is not None
        }
        if present != set(expected):
            raise ValueError(
                f"{self.applicability_mode.value} requires exactly {expected}"
            )
        return self


class SourceApplicabilityCreate(SourceApplicabilityInput):
    source_id: int = Field(gt=0)
    all_crops_flag: Literal[False] = False


class SourceApplicabilityUpdate(UpdateSchema):
    applicability_mode: ApplicabilityMode | None = None
    crop_id: int | None = Field(default=None, gt=0)
    variety_id: int | None = Field(default=None, gt=0)
    family_name: str | None = Field(default=None, min_length=1, max_length=120)


class SourceApplicabilityRead(ReadSchema):
    id: int
    source_id: int
    applicability_mode: ApplicabilityMode
    all_crops_flag: bool
    crop_id: int | None
    variety_id: int | None
    family_name: str | None


class SourceAllCropsApplicabilityCreate(Schema):
    source_id: int = Field(gt=0)


class SourceAllCropsApplicabilityRead(ReadSchema):
    source_id: int
    all_crops_flag: bool
    applicability_mode: ApplicabilityMode


class SourceGeographicApplicabilityCreate(GeographicScopeInput):
    source_id: int = Field(gt=0)


class SourceGeographicApplicabilityUpdate(UpdateSchema):
    scope_type: GeographicScopeType | None = None
    country_id: int | None = Field(default=None, gt=0)
    province_state_id: int | None = Field(default=None, gt=0)
    district_id: int | None = Field(default=None, gt=0)
    locality_id: int | None = Field(default=None, gt=0)
    agroecological_zone_id: int | None = Field(default=None, gt=0)


class SourceGeographicApplicabilityRead(ReadSchema):
    id: int
    source_id: int
    scope_type: GeographicScopeType
    country_id: int | None
    province_state_id: int | None
    district_id: int | None
    locality_id: int | None
    agroecological_zone_id: int | None


class AgroecologicalZoneGeographyCreate(Schema):
    agroecological_zone_id: int = Field(gt=0)
    country_id: int | None = Field(default=None, gt=0)
    province_state_id: int | None = Field(default=None, gt=0)
    district_id: int | None = Field(default=None, gt=0)
    locality_id: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def exactly_one_area(self):
        if sum(
            value is not None
            for value in (
                self.country_id,
                self.province_state_id,
                self.district_id,
                self.locality_id,
            )
        ) != 1:
            raise ValueError("Exactly one administrative area is required")
        return self


class AgroecologicalZoneGeographyUpdate(UpdateSchema):
    agroecological_zone_id: int | None = Field(default=None, gt=0)
    country_id: int | None = Field(default=None, gt=0)
    province_state_id: int | None = Field(default=None, gt=0)
    district_id: int | None = Field(default=None, gt=0)
    locality_id: int | None = Field(default=None, gt=0)


class AgroecologicalZoneGeographyRead(ReadSchema):
    id: int
    agroecological_zone_id: int
    country_id: int | None
    province_state_id: int | None
    district_id: int | None
    locality_id: int | None


class CropRotationRuleGeographicScopeCreate(GeographicScopeInput):
    crop_rotation_rule_id: int = Field(gt=0)


class CropRotationRuleGeographicScopeUpdate(UpdateSchema):
    scope_type: GeographicScopeType | None = None
    country_id: int | None = Field(default=None, gt=0)
    province_state_id: int | None = Field(default=None, gt=0)
    district_id: int | None = Field(default=None, gt=0)
    locality_id: int | None = Field(default=None, gt=0)
    agroecological_zone_id: int | None = Field(default=None, gt=0)
    crop_rotation_rule_id: int | None = Field(default=None, gt=0)


class CropRotationRuleGeographicScopeRead(ReadSchema):
    id: int
    crop_rotation_rule_id: int
    scope_type: GeographicScopeType
    country_id: int | None
    province_state_id: int | None
    district_id: int | None
    locality_id: int | None
    agroecological_zone_id: int | None


class EvidenceGeographicScopeCreate(EvidenceGeographicScopeInput):
    evidence_id: int = Field(gt=0)


class EvidenceGeographicScopeUpdate(UpdateSchema):
    scope_type: GeographicScopeType | None = None
    country_id: int | None = Field(default=None, gt=0)
    province_state_id: int | None = Field(default=None, gt=0)
    district_id: int | None = Field(default=None, gt=0)
    locality_id: int | None = Field(default=None, gt=0)
    agroecological_zone_id: int | None = Field(default=None, gt=0)
    farm_id: str | None = Field(default=None, max_length=120)


class EvidenceGeographicScopeRead(ReadSchema):
    id: int
    evidence_id: int
    scope_type: GeographicScopeType
    country_id: int | None
    province_state_id: int | None
    district_id: int | None
    locality_id: int | None
    agroecological_zone_id: int | None
    farm_id: str | None


class AgriculturalSourceCreate(Schema):
    all_crops_flag: bool = False
    organization: str | None = Field(default=None, max_length=240)
    title: str | None = Field(default=None, max_length=500)
    publication_url: str | None = None
    document_reference: str | None = Field(default=None, max_length=500)
    publication_date: date | None = None
    access_date: date | None = None
    source_type: str | None = Field(default=None, max_length=80)
    geographic_applicability: str | None = None
    crop_applicability: str | None = None
    evidence_class: str | None = Field(default=None, max_length=120)
    review_status: str | None = Field(default=None, max_length=80)
    limitations: str | None = None
    notes: str | None = None
    applicabilities: list[SourceApplicabilityInput] = Field(default_factory=list)
    geographic_applicabilities: list[GeographicScopeInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_applicability(self):
        if self.all_crops_flag and self.applicabilities:
            raise ValueError("ALL_CROPS cannot coexist with narrower applicability")
        return self


class AgriculturalSourceUpdate(UpdateSchema):
    all_crops_flag: bool | None = None
    organization: str | None = Field(default=None, max_length=240)
    title: str | None = Field(default=None, max_length=500)
    publication_url: str | None = None
    document_reference: str | None = Field(default=None, max_length=500)
    publication_date: date | None = None
    access_date: date | None = None
    source_type: str | None = Field(default=None, max_length=80)
    geographic_applicability: str | None = None
    crop_applicability: str | None = None
    evidence_class: str | None = Field(default=None, max_length=120)
    review_status: str | None = Field(default=None, max_length=80)
    limitations: str | None = None
    notes: str | None = None
    applicabilities: list[SourceApplicabilityInput] | None = None
    geographic_applicabilities: list[GeographicScopeInput] | None = None

    @model_validator(mode="after")
    def validate_applicability(self):
        if self.all_crops_flag is True and self.applicabilities:
            raise ValueError("ALL_CROPS cannot coexist with narrower applicability")
        return self


class AgriculturalSourceRead(ReadSchema):
    id: int
    all_crops_flag: bool
    organization: str | None
    title: str | None
    publication_url: str | None
    document_reference: str | None
    publication_date: date | None
    access_date: date | None
    source_type: str | None
    geographic_applicability: str | None
    crop_applicability: str | None
    evidence_class: str | None
    review_status: str | None
    limitations: str | None
    notes: str | None


class EvidenceRecordCreate(Schema):
    source_id: int | None = Field(default=None, gt=0)
    source_type: EvidenceOriginType
    source_locator: str | None = Field(default=None, max_length=500)
    statement: str | None = None
    limitations: str | None = None
    geographic_scopes: list[EvidenceGeographicScopeInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_published_source(self):
        if self.source_type is EvidenceOriginType.PUBLISHED_SOURCE and self.source_id is None:
            raise ValueError("PUBLISHED_SOURCE evidence requires source_id")
        return self


class EvidenceRecordUpdate(UpdateSchema):
    source_id: int | None = Field(default=None, gt=0)
    source_type: EvidenceOriginType | None = None
    source_locator: str | None = Field(default=None, max_length=500)
    statement: str | None = None
    limitations: str | None = None
    geographic_scopes: list[EvidenceGeographicScopeInput] | None = None


class EvidenceRecordRead(ReadSchema):
    id: int
    source_id: int | None
    source_type: EvidenceOriginType
    source_locator: str | None
    statement: str | None
    limitations: str | None
    geographic_scope_ids: list[int] = Field(default_factory=list)


class CountryCreate(Schema):
    name: str = Field(min_length=1, max_length=160)
    iso2_code: str | None = Field(default=None, min_length=2, max_length=2)
    iso3_code: str | None = Field(default=None, min_length=3, max_length=3)


class CountryUpdate(UpdateSchema):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    iso2_code: str | None = Field(default=None, min_length=2, max_length=2)
    iso3_code: str | None = Field(default=None, min_length=3, max_length=3)


class CountryRead(ReadSchema):
    id: int
    name: str
    iso2_code: str | None
    iso3_code: str | None


class ProvinceStateCreate(Schema):
    country_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=160)
    code: str | None = Field(default=None, max_length=40)


class ProvinceStateUpdate(UpdateSchema):
    country_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    code: str | None = Field(default=None, max_length=40)


class ProvinceStateRead(ReadSchema):
    id: int
    country_id: int
    name: str
    code: str | None


class DistrictCreate(Schema):
    province_state_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=160)
    code: str | None = Field(default=None, max_length=40)


class DistrictUpdate(UpdateSchema):
    province_state_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    code: str | None = Field(default=None, max_length=40)


class DistrictRead(ReadSchema):
    id: int
    province_state_id: int
    name: str
    code: str | None


class LocalityCreate(Schema):
    district_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=160)
    code: str | None = Field(default=None, max_length=40)


class LocalityUpdate(UpdateSchema):
    district_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    code: str | None = Field(default=None, max_length=40)


class LocalityRead(ReadSchema):
    id: int
    district_id: int
    name: str
    code: str | None


class AgroecologicalZoneCreate(Schema):
    name: str = Field(min_length=1, max_length=160)
    code: str | None = Field(default=None, max_length=60)
    description: str | None = None


class AgroecologicalZoneUpdate(UpdateSchema):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    code: str | None = Field(default=None, max_length=60)
    description: str | None = None


class AgroecologicalZoneRead(ReadSchema):
    id: int
    name: str
    code: str | None
    description: str | None
