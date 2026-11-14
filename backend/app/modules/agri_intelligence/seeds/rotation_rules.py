from sqlalchemy.orm import Session


def seed_rotation_rules(_session: Session) -> int:
    # No locally applicable rotation rule is seeded without supporting evidence.
    return 0
