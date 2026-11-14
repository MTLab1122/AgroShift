from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import (
    AgroecologicalZone,
    Country,
    Crop,
    CropRotationRule,
    CropVariety,
    District,
    Locality,
    ProvinceState,
)
from ..models.associations import CropRotationRuleGeographicScope
from ..models.enums import EvidenceStatus, GeographicScopeType
from ..schemas.validation import FarmContext, FeasibilityStatus, ValidationCheck
from .validation_rules import (
    ROTATION_STATUS_MAP,
    SUPPORTED_EVIDENCE_STATUSES,
    missing_check,
)


def _source_matches(
    rule: CropRotationRule,
    crop: Crop,
    variety: CropVariety | None,
) -> bool:
    if rule.previous_crop_id is not None:
        return rule.previous_crop_id == crop.id
    if rule.previous_variety_id is not None:
        return variety is not None and rule.previous_variety_id == variety.id
    return bool(rule.source_family and crop.crop_family == rule.source_family)


def _target_matches(
    rule: CropRotationRule,
    crop: Crop,
    variety: CropVariety | None,
) -> bool:
    if rule.next_crop_id is not None:
        return rule.next_crop_id == crop.id
    if rule.next_variety_id is not None:
        return variety is not None and rule.next_variety_id == variety.id
    return bool(rule.target_family and crop.crop_family == rule.target_family)


def _farm_administrative_path(
    session: Session,
    farm_context: FarmContext | None,
) -> dict[str, int] | None:
    if farm_context is None:
        return {}

    provided = {
        "country_id": farm_context.country_id,
        "province_state_id": farm_context.province_state_id,
        "district_id": farm_context.district_id,
        "locality_id": farm_context.locality_id,
    }
    if all(value is None for value in provided.values()):
        return {}

    if farm_context.locality_id is not None:
        locality = session.get(Locality, farm_context.locality_id)
        if locality is None:
            return None
        district = session.get(District, locality.district_id)
        if district is None:
            return None
        province = session.get(ProvinceState, district.province_state_id)
        if province is None:
            return None
        path = {
            "country_id": province.country_id,
            "province_state_id": province.id,
            "district_id": district.id,
            "locality_id": locality.id,
        }
    elif farm_context.district_id is not None:
        district = session.get(District, farm_context.district_id)
        if district is None:
            return None
        province = session.get(ProvinceState, district.province_state_id)
        if province is None:
            return None
        path = {
            "country_id": province.country_id,
            "province_state_id": province.id,
            "district_id": district.id,
        }
    elif farm_context.province_state_id is not None:
        province = session.get(ProvinceState, farm_context.province_state_id)
        if province is None:
            return None
        path = {
            "country_id": province.country_id,
            "province_state_id": province.id,
        }
    else:
        country = session.get(Country, farm_context.country_id)
        if country is None:
            return None
        path = {"country_id": country.id}

    if any(value is not None and path.get(key) != value
           for key, value in provided.items()):
        return None
    return path


def _scope_matches(
    session: Session,
    scope: CropRotationRuleGeographicScope,
    farm_context: FarmContext | None,
    administrative_path: dict[str, int] | None,
) -> bool:
    if scope.scope_type is GeographicScopeType.GLOBAL:
        return True
    if scope.scope_type is GeographicScopeType.AGROECOLOGICAL_ZONE:
        return (
            farm_context is not None
            and farm_context.agroecological_zone_id == scope.agroecological_zone_id
            and session.get(AgroecologicalZone, scope.agroecological_zone_id) is not None
        )
    if administrative_path is None:
        return False

    scope_fields = {
        GeographicScopeType.COUNTRY: "country_id",
        GeographicScopeType.PROVINCE_STATE: "province_state_id",
        GeographicScopeType.DISTRICT: "district_id",
        GeographicScopeType.LOCALITY: "locality_id",
    }
    field = scope_fields.get(scope.scope_type)
    return field is not None and administrative_path.get(field) == getattr(scope, field)


def validate_crop_family_transition(
    session: Session,
    previous: list[tuple[Crop, CropVariety | None]],
    next_crop: Crop,
    next_variety: CropVariety | None,
    farm_context: FarmContext | None = None,
) -> ValidationCheck:
    if not previous:
        return missing_check(
            "CROP_FAMILY_ROTATION",
            "Crop-family sequence compatibility cannot be evaluated without prior crop history.",
            ["actual prior crop history"],
        )

    rules = list(
        session.scalars(
            select(CropRotationRule).options(
                selectinload(CropRotationRule.geographic_scopes)
            )
        )
    )
    selector_matched = [
        rule for rule in rules
        if any(_source_matches(rule, crop, variety) for crop, variety in previous)
        and _target_matches(rule, next_crop, next_variety)
    ]
    administrative_path = _farm_administrative_path(session, farm_context)
    matched = [
        rule for rule in selector_matched
        if any(
            _scope_matches(session, scope, farm_context, administrative_path)
            for scope in rule.geographic_scopes
        )
    ]
    if not matched:
        if selector_matched:
            has_farm_geography = farm_context is not None and any(
                value is not None
                for value in (
                    farm_context.country_id,
                    farm_context.province_state_id,
                    farm_context.district_id,
                    farm_context.locality_id,
                    farm_context.agroecological_zone_id,
                )
            )
            missing = (
                ["consistent stored country, province, district, or locality IDs"]
                if has_farm_geography and administrative_path is None
                else [
                    "an explicit GLOBAL or geographically matching rotation-rule scope"
                ]
            )
            return missing_check(
                "CROP_FAMILY_ROTATION",
                "No selector-matching rotation rule has a geographic scope that applies to this farm.",
                missing,
                inputs={
                    "candidate_rule_ids": [rule.id for rule in selector_matched],
                    "farm_geography": (
                        farm_context.model_dump(mode="json", exclude_none=True)
                        if farm_context else None
                    ),
                },
                limitations=[
                    "A rotation rule with no normalized geographic scope is not treated as GLOBAL.",
                    "Agroecological-zone scopes match only the same zone ID and are not administrative ancestors.",
                ],
            )
        return missing_check(
            "CROP_FAMILY_ROTATION",
            "No matching evidence-backed crop sequence rule is available.",
            ["VERIFIED or PROVISIONAL rotation rule for this crop transition"],
            inputs={
                "previous_crop_ids": [crop.id for crop, _ in previous],
                "next_crop_id": next_crop.id,
            },
            limitations=[
                "Crop-family repetition is not declared harmful without an evidenced rule."
            ],
        )

    statuses = []
    evidence_ids = []
    rule_ids = []
    for rule in matched:
        rule_ids.append(rule.id)
        if (
            rule.evidence_status not in SUPPORTED_EVIDENCE_STATUSES
            or rule.primary_evidence_id is None
        ):
            statuses.append(FeasibilityStatus.INSUFFICIENT_DATA)
            continue
        evidence_ids.append(rule.primary_evidence_id)
        mapped = ROTATION_STATUS_MAP.get((rule.compatibility_status or "").upper())
        if mapped is None:
            statuses.append(FeasibilityStatus.INSUFFICIENT_DATA)
        elif (
            mapped is FeasibilityStatus.FEASIBLE
            and rule.evidence_status is EvidenceStatus.PROVISIONAL
        ):
            statuses.append(FeasibilityStatus.CONDITIONALLY_FEASIBLE)
        else:
            statuses.append(mapped)
    if len(set(statuses)) > 1:
        status = FeasibilityStatus.INSUFFICIENT_DATA
        detail = "Matching rotation rules conflict or have mixed evidence states."
    else:
        status = statuses[0]
        detail = (
            "Matching, evidence-backed crop sequence rule evaluated."
            if status is not FeasibilityStatus.INSUFFICIENT_DATA
            else "Matching rotation records do not provide an interpretable supported result."
        )
    return ValidationCheck(
        check_code="CROP_FAMILY_ROTATION",
        status=status,
        detail=detail,
        inputs={
            "previous_crop_ids": [crop.id for crop, _ in previous],
            "next_crop_id": next_crop.id,
            "rule_ids": rule_ids,
            "declared_statuses": [rule.compatibility_status for rule in matched],
        },
        rules_applied=[
            "Only explicit crop, variety, or family selectors are matched.",
            "A rule applies only to its explicit GLOBAL scope or a matching normalized geographic scope; administrative parent scopes apply to stored descendants.",
            "Agroecological-zone scopes match only the same zone ID and are evaluated separately from administrative geography.",
            "Only evidenced rules with recognized compatibility labels affect feasibility.",
            "COMPATIBLE/SUITABLE, CONDITIONAL/CONDITIONALLY_COMPATIBLE, and INCOMPATIBLE/UNSUITABLE/NOT_RECOMMENDED/PROHIBITED are the recognized labels.",
        ],
        evidence_record_ids=sorted(set(evidence_ids)),
        missing_information=(
            ["A single, evidence-backed, interpretable rule outcome."]
            if status is FeasibilityStatus.INSUFFICIENT_DATA
            else []
        ),
        limitations=[
            "No family-rotation outcome is inferred from family names alone."
        ],
    )
