from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CropCalendar
from ..models.enums import EvidenceStatus
from ..schemas.validation import FarmContext, FeasibilityStatus, ValidationCheck
from .validation_rules import SUPPORTED_EVIDENCE_STATUSES, missing_check


_CALENDAR_SCOPE_FIELDS = (
    "country_id",
    "province_state_id",
    "district_id",
    "agroecological_zone_id",
)


def scope_matches(calendar: CropCalendar, farm: FarmContext) -> tuple[bool, list[str]]:
    has_scope = False
    missing: list[str] = []
    for field in _CALENDAR_SCOPE_FIELDS:
        expected = getattr(calendar, field)
        if expected is None:
            continue
        has_scope = True
        actual = getattr(farm, field)
        if actual is None:
            missing.append(f"farm_context.{field}")
        elif actual != expected:
            return False, []
    return has_scope and not missing, missing


def _within_window(value: date, start: str, end: str, crosses_year: bool) -> bool:
    current = (value.month, value.day)
    first = tuple(int(part) for part in start.split("-"))
    last = tuple(int(part) for part in end.split("-"))
    if crosses_year:
        return current >= first or current <= last
    return first <= current <= last


def validate_calendar(
    session: Session,
    crop_id: int,
    variety_id: int | None,
    farm: FarmContext | None,
    upcoming_season: str | None,
) -> ValidationCheck:
    rows = list(
        session.scalars(
            select(CropCalendar).where(
                CropCalendar.crop_id == crop_id,
                (CropCalendar.variety_id.is_(None))
                | (CropCalendar.variety_id == variety_id),
            )
        )
    )
    if farm is None:
        return missing_check(
            "CALENDAR",
            "Calendar applicability cannot be established without farm geography and planned dates.",
            ["farm_context geography", "farm_context planting_date", "farm_context harvest_date"],
        )

    candidates = []
    scope_missing = set()
    for row in rows:
        matches, missing = scope_matches(row, farm)
        scope_missing.update(missing)
        if matches and upcoming_season and row.season:
            if row.season.casefold() == upcoming_season.casefold():
                candidates.append(row)

    if not candidates:
        missing = []
        if scope_missing:
            missing.extend(sorted(scope_missing))
        if upcoming_season is None:
            missing.append("upcoming_season")
        if farm.planting_date is None or farm.harvest_date is None:
            missing.extend(
                field for field, value in (
                    ("farm_context.planting_date", farm.planting_date),
                    ("farm_context.harvest_date", farm.harvest_date),
                ) if value is None
            )
        missing.append("evidenced calendar matching farm scope and upcoming season")
        return missing_check(
            "CALENDAR",
            "No calendar record with known geographic applicability matches this farm and season.",
            sorted(set(missing)),
            inputs={
                "farm_scope": {
                    field: getattr(farm, field) for field in _CALENDAR_SCOPE_FIELDS
                },
                "upcoming_season": upcoming_season,
            },
            limitations=[
                "A calendar with no geographic scope is not treated as global.",
            ],
        )

    if farm.planting_date is None or farm.harvest_date is None:
        return missing_check(
            "CALENDAR",
            "A matching calendar exists, but planned planting and harvest dates are required for window comparison.",
            [
                field for field, value in (
                    ("farm_context.planting_date", farm.planting_date),
                    ("farm_context.harvest_date", farm.harvest_date),
                ) if value is None
            ],
            inputs={"calendar_ids": [row.id for row in candidates]},
        )

    results = []
    evidence_ids = []
    for row in candidates:
        if (
            row.evidence_status not in SUPPORTED_EVIDENCE_STATUSES
            or row.primary_evidence_id is None
        ):
            results.append(FeasibilityStatus.INSUFFICIENT_DATA)
            continue
        evidence_ids.append(row.primary_evidence_id)
        if (
            row.planting_start is None
            or row.planting_end is None
            or row.harvest_start is None
            or row.harvest_end is None
        ):
            results.append(FeasibilityStatus.INSUFFICIENT_DATA)
            continue
        in_window = _within_window(
            farm.planting_date, row.planting_start, row.planting_end, row.plant_crosses_year
        ) and _within_window(
            farm.harvest_date, row.harvest_start, row.harvest_end, row.harvest_crosses_year
        )
        if not in_window:
            results.append(FeasibilityStatus.INFEASIBLE)
        elif row.evidence_status is EvidenceStatus.PROVISIONAL:
            results.append(FeasibilityStatus.CONDITIONALLY_FEASIBLE)
        else:
            results.append(FeasibilityStatus.FEASIBLE)

    if FeasibilityStatus.INFEASIBLE in results and FeasibilityStatus.FEASIBLE in results:
        status = FeasibilityStatus.INSUFFICIENT_DATA
        detail = "Matching evidenced calendars disagree on the planned date windows."
    elif FeasibilityStatus.INFEASIBLE in results:
        status = FeasibilityStatus.INFEASIBLE
        detail = "Planned planting or harvest dates fall outside an evidenced calendar window."
    elif FeasibilityStatus.INSUFFICIENT_DATA in results:
        status = FeasibilityStatus.INSUFFICIENT_DATA
        detail = "At least one matching calendar lacks usable evidence or date windows."
    elif FeasibilityStatus.CONDITIONALLY_FEASIBLE in results:
        status = FeasibilityStatus.CONDITIONALLY_FEASIBLE
        detail = "The planned dates match provisional calendar evidence."
    else:
        status = FeasibilityStatus.FEASIBLE
        detail = "Planned dates match verified calendar windows."
    return ValidationCheck(
        check_code="CALENDAR",
        status=status,
        detail=detail,
        inputs={
            "planting_date": farm.planting_date.isoformat(),
            "harvest_date": farm.harvest_date.isoformat(),
            "upcoming_season": upcoming_season,
            "calendar_ids": [row.id for row in candidates],
        },
        rules_applied=[
            "Match season and at least one explicit administrative or agroecological scope.",
            "Compare recurring MM-DD windows with their persisted cross-year flags.",
        ],
        evidence_record_ids=sorted(set(evidence_ids)),
        missing_information=(
            ["Complete verified date-window fields on all applicable calendars."]
            if status is FeasibilityStatus.INSUFFICIENT_DATA
            else []
        ),
        limitations=["A calendar without an explicit geographic scope is not treated as global."],
    )
