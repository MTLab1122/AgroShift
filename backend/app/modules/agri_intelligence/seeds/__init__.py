from dataclasses import dataclass

from sqlalchemy.orm import Session

from .calendars import seed_unknown_calendars
from .crops import seed_crops, seed_varieties
from .geography import seed_peshawar_valley_geography
from .requirements import seed_unknown_requirements
from .rotation_rules import seed_rotation_rules
from .sources import seed_sources
from .zones import seed_agroecological_zones


@dataclass(frozen=True)
class SeedResult:
    sources: int
    crops: int
    varieties: int
    calendars: int
    requirements: int
    rotation_rules: int
    geography: int
    agroecological_zones: int


def seed_all(session: Session) -> SeedResult:
    result = SeedResult(
        sources=seed_sources(session),
        crops=seed_crops(session),
        varieties=seed_varieties(session),
        calendars=seed_unknown_calendars(session),
        requirements=seed_unknown_requirements(session),
        rotation_rules=seed_rotation_rules(session),
        geography=seed_peshawar_valley_geography(session),
        agroecological_zones=seed_agroecological_zones(session),
    )
    session.flush()
    return result


__all__ = ["SeedResult", "seed_all"]
