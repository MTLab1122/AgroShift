from sqlalchemy.orm import Session


def seed_agroecological_zones(_session: Session) -> int:
    # No zone classification is seeded without reliable geographic evidence.
    return 0
