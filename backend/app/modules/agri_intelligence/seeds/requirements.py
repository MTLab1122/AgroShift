from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Crop, CropRequirement
from ..models.enums import EvidenceStatus, RequirementType


UNKNOWN_REQUIREMENT_NOTE = (
    "No verified crop-specific value is seeded; this row records a data gap only."
)
UNKNOWN_REQUIREMENT_TYPES = (
    RequirementType.SOIL,
    RequirementType.WATER,
    RequirementType.TEMPERATURE,
    RequirementType.SALINITY,
    RequirementType.NUTRIENT,
)


def seed_unknown_requirements(session: Session) -> int:
    created = 0
    crops = session.scalars(select(Crop).where(Crop.active.is_(True))).all()
    for crop in crops:
        for requirement_type in UNKNOWN_REQUIREMENT_TYPES:
            existing_id = session.scalar(
                select(CropRequirement.id).where(
                    CropRequirement.crop_id == crop.id,
                    CropRequirement.variety_id.is_(None),
                    CropRequirement.requirement_type == requirement_type,
                    CropRequirement.evidence_status == EvidenceStatus.UNKNOWN,
                    CropRequirement.limitations == UNKNOWN_REQUIREMENT_NOTE,
                )
            )
            if existing_id is None:
                session.add(
                    CropRequirement(
                        crop_id=crop.id,
                        requirement_type=requirement_type,
                        evidence_status=EvidenceStatus.UNKNOWN,
                        limitations=UNKNOWN_REQUIREMENT_NOTE,
                    )
                )
                created += 1
    session.flush()
    return created
