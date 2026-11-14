from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import CropRequirement
from ..models.enums import EvidenceStatus, RequirementType
from ..schemas.validation import FarmContext, FeasibilityStatus, ValidationCheck
from .validation_rules import SUPPORTED_EVIDENCE_STATUSES, missing_check


def validate_soil(
    session: Session,
    crop_id: int,
    variety_id: int | None,
    farm: FarmContext | None,
) -> ValidationCheck:
    requirements = list(
        session.scalars(
            select(CropRequirement).where(
                CropRequirement.crop_id == crop_id,
                CropRequirement.requirement_type == RequirementType.SOIL,
                (CropRequirement.variety_id.is_(None))
                | (CropRequirement.variety_id == variety_id),
            )
        )
    )
    supported = [
        row for row in requirements
        if row.evidence_status in SUPPORTED_EVIDENCE_STATUSES
        and row.primary_evidence_id is not None
        and (row.soil_ph_min is not None or row.soil_ph_max is not None)
    ]
    if farm is None or farm.soil_ph is None:
        return missing_check(
            "SOIL",
            "Soil suitability cannot be evaluated without a measured soil pH and evidenced crop pH bounds.",
            ["farm_context.soil_ph", "evidenced soil pH limits"],
            inputs={"soil_type": farm.soil_type if farm else None},
            limitations=[
                "Soil-type names alone are not used to infer suitability.",
                "Texture, drainage, organic matter, and salinity have no compatible evidenced thresholds in the current crop-requirement model.",
            ],
        )
    if not supported:
        return missing_check(
            "SOIL",
            "No evidenced soil pH bounds are available for this crop.",
            ["VERIFIED or PROVISIONAL soil requirement with primary evidence"],
            inputs={"soil_ph": str(farm.soil_ph)},
            limitations=["An unverified or name-only soil requirement is not treated as a suitability rule."],
        )

    checks = []
    evidence_ids = []
    for requirement in supported:
        evidence_ids.append(requirement.primary_evidence_id)
        outside = (
            requirement.soil_ph_min is not None
            and farm.soil_ph < requirement.soil_ph_min
        ) or (
            requirement.soil_ph_max is not None
            and farm.soil_ph > requirement.soil_ph_max
        )
        checks.append(
            FeasibilityStatus.INFEASIBLE
            if outside
            else (
                FeasibilityStatus.CONDITIONALLY_FEASIBLE
                if requirement.evidence_status is EvidenceStatus.PROVISIONAL
                else FeasibilityStatus.FEASIBLE
            )
        )
    status = (
        FeasibilityStatus.INFEASIBLE
        if FeasibilityStatus.INFEASIBLE in checks
        else (
            FeasibilityStatus.CONDITIONALLY_FEASIBLE
            if FeasibilityStatus.CONDITIONALLY_FEASIBLE in checks
            else FeasibilityStatus.FEASIBLE
        )
    )
    return ValidationCheck(
        check_code="SOIL",
        status=status,
        detail=(
            "Measured soil pH was compared only with evidenced crop pH bounds."
            if status is not FeasibilityStatus.INFEASIBLE
            else "Measured soil pH falls outside at least one evidenced crop pH bound."
        ),
        inputs={
            "soil_ph": str(farm.soil_ph),
            "soil_type": farm.soil_type,
            "soil_texture": farm.soil_texture,
            "drainage": farm.drainage,
            "organic_matter": str(farm.organic_matter) if farm.organic_matter is not None else None,
            "salinity": str(farm.salinity) if farm.salinity is not None else None,
            "requirements": [
                {
                    "minimum": str(row.soil_ph_min) if row.soil_ph_min is not None else None,
                    "maximum": str(row.soil_ph_max) if row.soil_ph_max is not None else None,
                    "status": row.evidence_status.value,
                }
                for row in supported
            ],
        },
        rules_applied=["Compare measured pH to each evidenced inclusive pH bound."],
        evidence_record_ids=sorted(set(evidence_ids)),
        missing_information=[],
        limitations=[
            "Soil-type names alone are not used to infer suitability.",
            "Texture, drainage, organic matter, and salinity are recorded but not evaluated without compatible evidence and thresholds.",
        ],
    )
