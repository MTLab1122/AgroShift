from sqlalchemy.orm import Session

from ..models import Crop, CropVariety
from ..models.enums import EvidenceStatus
from ._helpers import get_or_create


INITIAL_CROP_NAMES = (
    ("wheat", "Wheat"),
    ("maize", "Maize"),
    ("rice", "Rice"),
    ("sugarcane", "Sugarcane"),
    ("mustard", "Mustard"),
    ("chickpea", "Chickpea"),
    ("lentil", "Lentil"),
    ("mung-bean", "Mung bean"),
)


def seed_crops(session: Session) -> int:
    created = 0
    for slug, common_name in INITIAL_CROP_NAMES:
        _crop, was_created = get_or_create(
            session,
            Crop,
            lookup={"slug": slug},
            values={
                "slug": slug,
                "common_name": common_name,
                "evidence_status": EvidenceStatus.UNKNOWN,
            },
        )
        created += int(was_created)
    return created


def seed_varieties(_session: Session) -> int:
    # The available institutional source names no variety identifiers.
    return 0
