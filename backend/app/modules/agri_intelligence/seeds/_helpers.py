from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session


def get_or_create(
    session: Session,
    model: type,
    *,
    lookup: dict[str, Any],
    values: dict[str, Any],
):
    statement = select(model).filter_by(**lookup)
    record = session.scalar(statement)
    if record is not None:
        return record, False
    record = model(**values)
    session.add(record)
    session.flush()
    return record, True
