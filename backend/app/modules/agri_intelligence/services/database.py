from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Crop, CropCalendar, CropVariety
from ..models.enums import EvidenceStatus
from ..repositories import (
    AgriculturalSourceRepository,
    CropCalendarRepository,
    CropRepository,
    CropVarietyRepository,
    EvidenceRecordRepository,
)


class CropDatabaseService:
    def __init__(self, session: Session):
        self.crops = CropRepository(session)
        self.varieties = CropVarietyRepository(session)

    def create_crop(self, data):
        return self.crops.create(data)

    def get_crop(self, crop_id: int) -> Crop:
        return self.crops.get(crop_id)

    def list_crops(
        self, *, active: bool | None = None, offset: int = 0, limit: int = 100
    ) -> list[Crop]:
        filters = {} if active is None else {"active": active}
        return self.crops.list(filters=filters, offset=offset, limit=limit)

    def update_crop(self, crop_id: int, data) -> Crop:
        return self.crops.update(crop_id, data)

    def delete_crop(self, crop_id: int) -> None:
        self.crops.delete(crop_id)

    def create_variety(self, data):
        return self.varieties.create(data)

    def get_variety(self, variety_id: int) -> CropVariety:
        return self.varieties.get(variety_id)

    def list_varieties(
        self, *, crop_id: int | None = None, offset: int = 0, limit: int = 100
    ) -> list[CropVariety]:
        filters = {} if crop_id is None else {"crop_id": crop_id}
        return self.varieties.list(filters=filters, offset=offset, limit=limit)

    def update_variety(self, variety_id: int, data) -> CropVariety:
        return self.varieties.update(variety_id, data)

    def delete_variety(self, variety_id: int) -> None:
        self.varieties.delete(variety_id)


class CropCalendarService:
    def __init__(self, session: Session):
        self.session = session
        self.calendars = CropCalendarRepository(session)

    def create(self, data):
        return self.calendars.create(data)

    def get(self, calendar_id: int) -> CropCalendar:
        return self.calendars.get(calendar_id)

    def list(
        self,
        *,
        crop_id: int | None = None,
        variety_id: int | None = None,
        country_id: int | None = None,
        province_state_id: int | None = None,
        district_id: int | None = None,
        agroecological_zone_id: int | None = None,
        evidence_status: EvidenceStatus | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[CropCalendar]:
        if offset < 0 or limit < 1:
            raise ValueError("offset must be non-negative and limit must be positive")
        filters = {
            key: value
            for key, value in {
                "crop_id": crop_id,
                "variety_id": variety_id,
                "country_id": country_id,
                "province_state_id": province_state_id,
                "district_id": district_id,
                "agroecological_zone_id": agroecological_zone_id,
                "evidence_status": evidence_status,
            }.items()
            if value is not None
        }
        statement = select(CropCalendar)
        for field, value in filters.items():
            statement = statement.where(getattr(CropCalendar, field) == value)
        return list(
            self.session.scalars(
                statement.order_by(CropCalendar.id).offset(offset).limit(limit)
            )
        )

    def update(self, calendar_id: int, data) -> CropCalendar:
        return self.calendars.update(calendar_id, data)

    def delete(self, calendar_id: int) -> None:
        self.calendars.delete(calendar_id)


class AgriculturalResearchService:
    def __init__(self, session: Session):
        self.sources = AgriculturalSourceRepository(session)
        self.evidence = EvidenceRecordRepository(session)

    def create_source(self, data):
        return self.sources.create(data)

    def get_source(self, source_id: int):
        return self.sources.get(source_id)

    def list_sources(
        self, *, filters: dict[str, Any] | None = None, offset: int = 0, limit: int = 100
    ):
        return self.sources.list(filters=filters, offset=offset, limit=limit)

    def update_source(self, source_id: int, data):
        return self.sources.update(source_id, data)

    def delete_source(self, source_id: int) -> None:
        self.sources.delete(source_id)

    def create_evidence(self, data):
        return self.evidence.create(data)

    def get_evidence(self, evidence_id: int):
        return self.evidence.get(evidence_id)

    def list_evidence(
        self, *, filters: dict[str, Any] | None = None, offset: int = 0, limit: int = 100
    ):
        return self.evidence.list(filters=filters, offset=offset, limit=limit)

    def update_evidence(self, evidence_id: int, data):
        return self.evidence.update(evidence_id, data)

    def delete_evidence(self, evidence_id: int) -> None:
        self.evidence.delete(evidence_id)
