from ..models.enums import EvidenceStatus
from ..schemas.validation import FeasibilityStatus, ValidationCheck


SUPPORTED_EVIDENCE_STATUSES = {
    EvidenceStatus.VERIFIED,
    EvidenceStatus.PROVISIONAL,
}

ROTATION_STATUS_MAP = {
    "COMPATIBLE": FeasibilityStatus.FEASIBLE,
    "SUITABLE": FeasibilityStatus.FEASIBLE,
    "CONDITIONALLY_COMPATIBLE": FeasibilityStatus.CONDITIONALLY_FEASIBLE,
    "CONDITIONAL": FeasibilityStatus.CONDITIONALLY_FEASIBLE,
    "INCOMPATIBLE": FeasibilityStatus.INFEASIBLE,
    "UNSUITABLE": FeasibilityStatus.INFEASIBLE,
    "NOT_RECOMMENDED": FeasibilityStatus.INFEASIBLE,
    "PROHIBITED": FeasibilityStatus.INFEASIBLE,
}


def combine_statuses(statuses: list[FeasibilityStatus]) -> FeasibilityStatus:
    if not statuses:
        return FeasibilityStatus.INSUFFICIENT_DATA
    if FeasibilityStatus.INFEASIBLE in statuses:
        return FeasibilityStatus.INFEASIBLE
    if FeasibilityStatus.INSUFFICIENT_DATA in statuses:
        return FeasibilityStatus.INSUFFICIENT_DATA
    if FeasibilityStatus.CONDITIONALLY_FEASIBLE in statuses:
        return FeasibilityStatus.CONDITIONALLY_FEASIBLE
    return FeasibilityStatus.FEASIBLE


def missing_check(
    code: str,
    detail: str,
    missing: list[str],
    *,
    inputs: dict | None = None,
    limitations: list[str] | None = None,
) -> ValidationCheck:
    return ValidationCheck(
        check_code=code,
        status=FeasibilityStatus.INSUFFICIENT_DATA,
        detail=detail,
        inputs=inputs or {},
        missing_information=missing,
        limitations=limitations or [],
    )


def evidence_status_result(status: EvidenceStatus) -> FeasibilityStatus:
    if status is EvidenceStatus.VERIFIED:
        return FeasibilityStatus.FEASIBLE
    if status is EvidenceStatus.PROVISIONAL:
        return FeasibilityStatus.CONDITIONALLY_FEASIBLE
    return FeasibilityStatus.INSUFFICIENT_DATA
