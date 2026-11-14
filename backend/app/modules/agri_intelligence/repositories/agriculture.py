from typing import Any

from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models import (
    AgriculturalSource,
    AgroecologicalZone,
    AgroecologicalZoneGeography,
    Country,
    Crop,
    CropCalendar,
    CropRequirement,
    CropRotationRule,
    CropVariety,
    District,
    EvidenceGeographicScope,
    EvidenceRecord,
    Locality,
    ProvinceState,
    SourceAllCropsApplicability,
    SourceApplicability,
    SourceGeographicApplicability,
)
from ..models.associations import CropRotationRuleGeographicScope
from ..schemas.crops import (
    CropCalendarCreate,
    CropCalendarUpdate,
    CropCreate,
    CropRequirementCreate,
    CropRequirementUpdate,
    CropRotationRuleCreate,
    CropRotationRuleUpdate,
    CropUpdate,
    CropVarietyCreate,
    CropVarietyUpdate,
)
from ..schemas.reference import (
    AgriculturalSourceCreate,
    AgriculturalSourceUpdate,
    AgroecologicalZoneGeographyCreate,
    AgroecologicalZoneGeographyUpdate,
    AgroecologicalZoneCreate,
    AgroecologicalZoneUpdate,
    CountryCreate,
    CountryUpdate,
    DistrictCreate,
    DistrictUpdate,
    EvidenceRecordCreate,
    EvidenceRecordUpdate,
    EvidenceGeographicScopeCreate,
    EvidenceGeographicScopeUpdate,
    LocalityCreate,
    LocalityUpdate,
    ProvinceStateCreate,
    ProvinceStateUpdate,
    CropRotationRuleGeographicScopeCreate,
    CropRotationRuleGeographicScopeUpdate,
    SourceApplicabilityCreate,
    SourceApplicabilityUpdate,
    SourceGeographicApplicabilityCreate,
    SourceGeographicApplicabilityUpdate,
)
from .base import RecordNotFoundError, Repository


class CropRepository(Repository[Crop]):
    def __init__(self, session: Session):
        super().__init__(
            session, Crop, CropCreate, CropUpdate,
            relationships={"evidence_record_ids": ("evidence_records", EvidenceRecord)},
        )


class CropVarietyRepository(Repository[CropVariety]):
    def __init__(self, session: Session):
        super().__init__(
            session, CropVariety, CropVarietyCreate, CropVarietyUpdate,
            relationships={"evidence_record_ids": ("evidence_records", EvidenceRecord)},
        )


class CropCalendarRepository(Repository[CropCalendar]):
    def __init__(self, session: Session):
        super().__init__(
            session, CropCalendar, CropCalendarCreate, CropCalendarUpdate,
            relationships={"evidence_record_ids": ("evidence_records", EvidenceRecord)},
        )


class CropRequirementRepository(Repository[CropRequirement]):
    def __init__(self, session: Session):
        super().__init__(
            session, CropRequirement, CropRequirementCreate, CropRequirementUpdate,
            relationships={"evidence_record_ids": ("evidence_records", EvidenceRecord)},
        )


class CropRotationRuleRepository(Repository[CropRotationRule]):
    def __init__(self, session: Session):
        super().__init__(
            session, CropRotationRule, CropRotationRuleCreate, CropRotationRuleUpdate,
            relationships={
                "evidence_record_ids": ("evidence_records", EvidenceRecord),
                "geographic_scope_ids": (
                    "geographic_scopes", CropRotationRuleGeographicScope
                ),
            },
        )


class CountryRepository(Repository[Country]):
    def __init__(self, session: Session):
        super().__init__(session, Country, CountryCreate, CountryUpdate)


class ProvinceStateRepository(Repository[ProvinceState]):
    def __init__(self, session: Session):
        super().__init__(session, ProvinceState, ProvinceStateCreate, ProvinceStateUpdate)


class DistrictRepository(Repository[District]):
    def __init__(self, session: Session):
        super().__init__(session, District, DistrictCreate, DistrictUpdate)


class LocalityRepository(Repository[Locality]):
    def __init__(self, session: Session):
        super().__init__(session, Locality, LocalityCreate, LocalityUpdate)


class AgroecologicalZoneRepository(Repository[AgroecologicalZone]):
    def __init__(self, session: Session):
        super().__init__(
            session, AgroecologicalZone, AgroecologicalZoneCreate, AgroecologicalZoneUpdate
        )


class AgroecologicalZoneGeographyRepository(Repository[AgroecologicalZoneGeography]):
    def __init__(self, session: Session):
        super().__init__(
            session,
            AgroecologicalZoneGeography,
            AgroecologicalZoneGeographyCreate,
            AgroecologicalZoneGeographyUpdate,
        )


class SourceApplicabilityRepository(Repository[SourceApplicability]):
    def __init__(self, session: Session):
        super().__init__(
            session,
            SourceApplicability,
            SourceApplicabilityCreate,
            SourceApplicabilityUpdate,
        )


class SourceGeographicApplicabilityRepository(Repository[SourceGeographicApplicability]):
    def __init__(self, session: Session):
        super().__init__(
            session,
            SourceGeographicApplicability,
            SourceGeographicApplicabilityCreate,
            SourceGeographicApplicabilityUpdate,
        )


class EvidenceGeographicScopeRepository(Repository[EvidenceGeographicScope]):
    def __init__(self, session: Session):
        super().__init__(
            session,
            EvidenceGeographicScope,
            EvidenceGeographicScopeCreate,
            EvidenceGeographicScopeUpdate,
        )


class CropRotationRuleGeographicScopeRepository(
    Repository[CropRotationRuleGeographicScope]
):
    def __init__(self, session: Session):
        super().__init__(
            session,
            CropRotationRuleGeographicScope,
            CropRotationRuleGeographicScopeCreate,
            CropRotationRuleGeographicScopeUpdate,
        )


class AgriculturalSourceRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, data: AgriculturalSourceCreate | dict[str, Any]) -> AgriculturalSource:
        values = Repository._dump(AgriculturalSourceCreate, data)
        narrow = values.pop("applicabilities", [])
        geographic = values.pop("geographic_applicabilities", [])
        source = AgriculturalSource(**values)
        self.session.add(source)
        self.session.flush()
        self._replace_applicabilities(source, narrow, geographic)
        if source.all_crops_flag:
            self.session.add(SourceAllCropsApplicability(source=source))
        self.session.flush()
        return source

    def get(self, source_id: int) -> AgriculturalSource:
        return self._get(source_id)

    def list(
        self, *, filters: dict[str, Any] | None = None, offset: int = 0, limit: int = 100
    ) -> list[AgriculturalSource]:
        return self._list(AgriculturalSource, filters, offset, limit)

    def update(
        self, source_id: int, data: AgriculturalSourceUpdate | dict[str, Any]
    ) -> AgriculturalSource:
        source = self.get(source_id)
        changes = Repository._dump(AgriculturalSourceUpdate, data)
        narrow = changes.pop("applicabilities", None)
        geographic = changes.pop("geographic_applicabilities", None)
        previous_all_crops = source.all_crops_flag
        merged_narrow = narrow if narrow is not None else [
            self._applicability_values(item) for item in source.applicabilities
        ]
        merged_geographic = geographic if geographic is not None else [
            self._scope_values(item) for item in source.geographic_applicabilities
        ]
        merged = {
            attribute.key: getattr(source, attribute.key)
            for attribute in AgriculturalSource.__mapper__.column_attrs
            if attribute.key != "id"
        }
        merged.update(changes)
        merged["applicabilities"] = merged_narrow
        merged["geographic_applicabilities"] = merged_geographic
        AgriculturalSourceCreate.model_validate(merged)
        replace_associations = narrow is not None or geographic is not None or (
            "all_crops_flag" in changes
            and changes["all_crops_flag"] != previous_all_crops
        )
        if replace_associations:
            self.session.execute(
                delete(SourceApplicability).where(SourceApplicability.source_id == source_id)
            )
            self.session.execute(
                delete(SourceGeographicApplicability).where(
                    SourceGeographicApplicability.source_id == source_id
                )
            )
            marker = self.session.get(SourceAllCropsApplicability, source_id)
            if marker is not None:
                self.session.delete(marker)
            self.session.flush()
            self.session.expire(
                source,
                ["applicabilities", "geographic_applicabilities", "all_crops_applicability"],
            )
        for name, value in changes.items():
            setattr(source, name, value)
        if replace_associations:
            self.session.flush()
            self._replace_applicabilities(source, merged_narrow, merged_geographic)
            if source.all_crops_flag:
                self.session.add(SourceAllCropsApplicability(source=source))
        self.session.flush()
        return source

    def delete(self, source_id: int) -> None:
        self.session.delete(self.get(source_id))
        self.session.flush()

    def _replace_applicabilities(
        self, source: AgriculturalSource, narrow: list, geographic: list
    ) -> None:
        for item in narrow:
            values = item.model_dump() if isinstance(item, BaseModel) else dict(item)
            self.session.add(
                SourceApplicability(
                    source=source,
                    all_crops_flag=False,
                    **values,
                )
            )
        for item in geographic:
            values = item.model_dump() if isinstance(item, BaseModel) else dict(item)
            self.session.add(
                SourceGeographicApplicability(
                    source=source,
                    scope_type=values.pop("scope_type"),
                    **values,
                )
            )

    @staticmethod
    def _applicability_values(item: SourceApplicability) -> dict[str, Any]:
        return {
            "applicability_mode": item.applicability_mode,
            "crop_id": item.crop_id,
            "variety_id": item.variety_id,
            "family_name": item.family_name,
        }

    @staticmethod
    def _scope_values(item: SourceGeographicApplicability) -> dict[str, Any]:
        return {
            "scope_type": item.scope_type,
            "country_id": item.country_id,
            "province_state_id": item.province_state_id,
            "district_id": item.district_id,
            "locality_id": item.locality_id,
            "agroecological_zone_id": item.agroecological_zone_id,
        }

    def _get(self, source_id: int) -> AgriculturalSource:
        source = self.session.get(AgriculturalSource, source_id)
        if source is None:
            raise RecordNotFoundError(AgriculturalSource, source_id)
        return source

    def _list(self, model, filters, offset, limit):
        if offset < 0 or limit < 1:
            raise ValueError("offset must be non-negative and limit must be positive")
        statement = select(model)
        for name, value in (filters or {}).items():
            if name not in model.__table__.columns:
                raise ValueError(f"{name!r} is not a filterable {model.__name__} field")
            statement = statement.where(getattr(model, name) == value)
        return list(self.session.scalars(statement.order_by(model.id).offset(offset).limit(limit)))


class EvidenceRecordRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, data: EvidenceRecordCreate | dict[str, Any]) -> EvidenceRecord:
        values = Repository._dump(EvidenceRecordCreate, data)
        scopes = values.pop("geographic_scopes", [])
        evidence = EvidenceRecord(**values)
        self.session.add(evidence)
        self.session.flush()
        for scope in scopes:
            scope_values = scope.model_dump() if isinstance(scope, BaseModel) else dict(scope)
            self.session.add(EvidenceGeographicScope(evidence=evidence, **scope_values))
        self.session.flush()
        return evidence

    def get(self, evidence_id: int) -> EvidenceRecord:
        evidence = self.session.get(EvidenceRecord, evidence_id)
        if evidence is None:
            raise RecordNotFoundError(EvidenceRecord, evidence_id)
        return evidence

    def list(
        self, *, filters: dict[str, Any] | None = None, offset: int = 0, limit: int = 100
    ) -> list[EvidenceRecord]:
        return self._list(filters, offset, limit)

    def update(
        self, evidence_id: int, data: EvidenceRecordUpdate | dict[str, Any]
    ) -> EvidenceRecord:
        evidence = self.get(evidence_id)
        changes = Repository._dump(EvidenceRecordUpdate, data)
        scopes = changes.pop("geographic_scopes", None)
        merged = {
            attribute.key: getattr(evidence, attribute.key)
            for attribute in EvidenceRecord.__mapper__.column_attrs
            if attribute.key != "id"
        }
        merged.update(changes)
        if scopes is not None:
            merged["geographic_scopes"] = scopes
        elif evidence.geographic_scopes:
            merged["geographic_scopes"] = [
                {
                    "scope_type": item.scope_type,
                    "country_id": item.country_id,
                    "province_state_id": item.province_state_id,
                    "district_id": item.district_id,
                    "locality_id": item.locality_id,
                    "agroecological_zone_id": item.agroecological_zone_id,
                    "farm_id": item.farm_id,
                }
                for item in evidence.geographic_scopes
            ]
        EvidenceRecordCreate.model_validate(merged)
        for name, value in changes.items():
            setattr(evidence, name, value)
        if scopes is not None:
            evidence.geographic_scopes.clear()
            evidence.geographic_scopes.extend(
                EvidenceGeographicScope(
                    evidence=evidence,
                    **(scope.model_dump() if isinstance(scope, BaseModel) else dict(scope)),
                )
                for scope in scopes
            )
        self.session.flush()
        return evidence

    def delete(self, evidence_id: int) -> None:
        self.session.delete(self.get(evidence_id))
        self.session.flush()

    def _list(self, filters, offset, limit):
        if offset < 0 or limit < 1:
            raise ValueError("offset must be non-negative and limit must be positive")
        statement = select(EvidenceRecord)
        for name, value in (filters or {}).items():
            if name not in EvidenceRecord.__table__.columns:
                raise ValueError(f"{name!r} is not a filterable EvidenceRecord field")
            statement = statement.where(getattr(EvidenceRecord, name) == value)
        return list(
            self.session.scalars(
                statement.order_by(EvidenceRecord.id).offset(offset).limit(limit)
            )
        )
