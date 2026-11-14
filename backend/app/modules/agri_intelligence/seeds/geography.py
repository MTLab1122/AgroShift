from sqlalchemy.orm import Session

from ..models import Country, ProvinceState
from ._helpers import get_or_create


def seed_peshawar_valley_geography(session: Session) -> int:
    created = 0
    pakistan, was_created = get_or_create(
        session,
        Country,
        lookup={"name": "Pakistan"},
        values={"name": "Pakistan"},
    )
    created += int(was_created)
    _province, was_created = get_or_create(
        session,
        ProvinceState,
        lookup={"country_id": pakistan.id, "name": "Khyber Pakhtunkhwa"},
        values={"country_id": pakistan.id, "name": "Khyber Pakhtunkhwa"},
    )
    created += int(was_created)
    return created
