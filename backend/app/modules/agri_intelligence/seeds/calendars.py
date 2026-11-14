from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Crop, CropCalendar
from ..models.enums import EvidenceStatus


UNKNOWN_CALENDAR_NOTE = (
    "UNKNOWN: no crop-specific planting or harvest window has been verified "
    "for this seed. No geographic applicability is asserted."
)


def seed_unknown_calendars(session: Session) -> int:
    created = 0
    crops = session.scalars(select(Crop).where(Crop.active.is_(True))).all()
    for crop in crops:
        existing = session.scalar(
            select(CropCalendar.id).where(
                CropCalendar.crop_id == crop.id,
                CropCalendar.variety_id.is_(None),
                CropCalendar.country_id.is_(None),
                CropCalendar.province_state_id.is_(None),
                CropCalendar.district_id.is_(None),
                CropCalendar.agroecological_zone_id.is_(None),
                CropCalendar.planting_start.is_(None),
                CropCalendar.harvest_start.is_(None),
                CropCalendar.notes == UNKNOWN_CALENDAR_NOTE,
            )
        )
        if existing is None:
            session.add(
                CropCalendar(
                    crop_id=crop.id,
                    evidence_status=EvidenceStatus.UNKNOWN,
                    notes=UNKNOWN_CALENDAR_NOTE,
                )
            )
            created += 1
    session.flush()
    return created
