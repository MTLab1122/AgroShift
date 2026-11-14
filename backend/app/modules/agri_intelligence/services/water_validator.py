from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CropRequirement
from ..models.enums import EvidenceStatus, RequirementType
from ..schemas.validation import FarmContext, FeasibilityStatus, ValidationCheck
from .validation_rules import SUPPORTED_EVIDENCE_STATUSES, missing_check


def validate_water(
    session: Session,
    crop_id: int,
    variety_id: int | None,
    farm: FarmContext | None,
) -> ValidationCheck:
    requirements = list(
        session.scalars(
            select(CropRequirement).where(
                CropRequirement.crop_id == crop_id,
                CropRequirement.requirement_type == RequirementType.WATER,
                (CropRequirement.variety_id.is_(None))
                | (CropRequirement.variety_id == variety_id),
            )
        )
    )
    supported = [
        row for row in requirements
        if row.evidence_status in SUPPORTED_EVIDENCE_STATUSES
        and row.primary_evidence_id is not None
        and row.water_requirement is not None
        and row.water_requirement_unit is not None
        and row.water_requirement_basis is not None
    ]
    if farm is None or farm.water_available is None:
        return missing_check(
            "WATER",
            "Available water cannot be compared with crop demand.",
            ["farm_context.water_available", "water unit and measurement basis"],
            limitations=["Rainfall is not converted into irrigation supply."],
        )
    if not supported:
        return missing_check(
            "WATER",
            "No evidenced crop water requirement with a unit and basis is available.",
            ["VERIFIED or PROVISIONAL water requirement with primary evidence"],
            inputs={
                "water_available": str(farm.water_available),
                "water_unit": farm.water_unit,
                "water_basis": farm.water_basis,
            },
        )

    statuses = []
    evidence_ids = []
    for requirement in supported:
        evidence_ids.append(requirement.primary_evidence_id)
        if (
            farm.water_unit != requirement.water_requirement_unit
            or farm.water_basis != requirement.water_requirement_basis
        ):
            statuses.append(FeasibilityStatus.INSUFFICIENT_DATA)
        elif farm.water_available < requirement.water_requirement:
            statuses.append(FeasibilityStatus.INFEASIBLE)
        elif requirement.evidence_status is EvidenceStatus.PROVISIONAL:
            statuses.append(FeasibilityStatus.CONDITIONALLY_FEASIBLE)
        else:
            statuses.append(FeasibilityStatus.FEASIBLE)
    status = (
        FeasibilityStatus.INFEASIBLE
        if FeasibilityStatus.INFEASIBLE in statuses
        else (
            FeasibilityStatus.INSUFFICIENT_DATA
            if FeasibilityStatus.INSUFFICIENT_DATA in statuses
            else (
                FeasibilityStatus.CONDITIONALLY_FEASIBLE
                if FeasibilityStatus.CONDITIONALLY_FEASIBLE in statuses
                else FeasibilityStatus.FEASIBLE
            )
        )
    )
    return ValidationCheck(
        check_code="WATER",
        status=status,
        detail=(
            "Available water was compared only when units and measurement bases matched."
        ),
        inputs={
            "available": str(farm.water_available),
            "unit": farm.water_unit,
            "basis": farm.water_basis,
            "requirements": [
                {
                    "value": str(row.water_requirement),
                    "unit": row.water_requirement_unit,
                    "basis": row.water_requirement_basis,
                    "status": row.evidence_status.value,
                }
                for row in supported
            ],
        },
        rules_applied=["No unit or measurement-basis conversion is performed."],
        evidence_record_ids=sorted(set(evidence_ids)),
        missing_information=(
            ["A crop requirement could not be compared because its unit or basis differs."]
            if status is FeasibilityStatus.INSUFFICIENT_DATA
            else []
        ),
        limitations=["Irrigation availability does not imply rainfall or other water sources."],
    )
