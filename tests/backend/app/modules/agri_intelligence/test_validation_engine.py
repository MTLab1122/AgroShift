from datetime import date

import pytest
from sqlalchemy.orm import sessionmaker

from backend.app.modules.agri_intelligence.db.base import Base
from backend.app.modules.agri_intelligence.db.engine import get_engine
from backend.app.modules.agri_intelligence.models import (
    AgroecologicalZone,
    Country,
    Crop,
    CropCalendar,
    CropRequirement,
    CropRotationRule,
    CropRotationRuleGeographicScope,
    CropVariety,
    District,
    EvidenceRecord,
    Locality,
    ProvinceState,
)
from backend.app.modules.agri_intelligence.models.enums import (
    EvidenceOriginType,
    EvidenceStatus,
    GeographicScopeType,
    RequirementType,
)
from backend.app.modules.agri_intelligence.schemas.validation import (
    CropHistoryItem,
    CropValidationRequest,
    FarmContext,
    FeasibilityStatus,
    SequenceValidationRequest,
)
from backend.app.modules.agri_intelligence.services.agricultural_validator import (
    AgriculturalValidator,
)


@pytest.fixture
def session(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    engine = get_engine()
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield test_session
    finally:
        test_session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _evidence(session):
    evidence = EvidenceRecord(
        source_type=EvidenceOriginType.DIRECTLY_MEASURED,
        statement="Synthetic test fixture; not agricultural evidence.",
    )
    session.add(evidence)
    session.flush()
    return evidence


def _geography(session):
    country = Country(name="Rotation test country")
    other_country = Country(name="Other rotation test country")
    session.add_all([country, other_country])
    session.flush()
    province = ProvinceState(country_id=country.id, name="Rotation test province")
    other_province = ProvinceState(
        country_id=other_country.id, name="Other rotation test province"
    )
    session.add_all([province, other_province])
    session.flush()
    district = District(province_state_id=province.id, name="Rotation test district")
    other_district = District(
        province_state_id=province.id, name="Other rotation test district"
    )
    session.add_all([district, other_district])
    session.flush()
    locality = Locality(district_id=district.id, name="Rotation test locality")
    session.add(locality)
    session.flush()
    return {
        "country": country,
        "other_country": other_country,
        "province": province,
        "other_province": other_province,
        "district": district,
        "other_district": other_district,
        "locality": locality,
    }


def _rotation_transition(
    session,
    *,
    scope_type=None,
    scope_values=None,
    farm_context=None,
    source_selector="crop",
    target_selector="crop",
):
    previous = Crop(slug="rotation-previous", crop_family="previous-family")
    next_crop = Crop(slug="rotation-next", crop_family="next-family")
    session.add_all([previous, next_crop])
    session.flush()
    previous_variety = CropVariety(crop_id=previous.id, name="Previous test variety")
    next_variety = CropVariety(crop_id=next_crop.id, name="Next test variety")
    session.add_all([previous_variety, next_variety])
    session.flush()
    evidence = _evidence(session)
    rule_values = {
        "previous_crop_id": previous.id if source_selector == "crop" else None,
        "previous_variety_id": (
            previous_variety.id if source_selector == "variety" else None
        ),
        "source_family": "previous-family" if source_selector == "family" else None,
        "next_crop_id": next_crop.id if target_selector == "crop" else None,
        "next_variety_id": next_variety.id if target_selector == "variety" else None,
        "target_family": "next-family" if target_selector == "family" else None,
        "compatibility_status": "COMPATIBLE",
        "confidence_level": 0.5,
        "evidence_status": EvidenceStatus.PROVISIONAL,
        "primary_evidence_id": evidence.id,
    }
    rule = CropRotationRule(**rule_values)
    if scope_type is not None:
        rule.geographic_scopes.append(
            CropRotationRuleGeographicScope(
                scope_type=scope_type,
                **(scope_values or {}),
            )
        )
    session.add(rule)
    session.flush()
    history = CropHistoryItem(
        crop_id=previous.id,
        variety_id=previous_variety.id,
        source_record_id="synthetic-rotation-history",
        evidence_record_ids=[evidence.id],
    )
    result = AgriculturalValidator(session).validate_sequence(
        SequenceValidationRequest(
            sequence=[
                {
                    "crop_id": next_crop.id,
                    "variety_id": next_variety.id,
                }
            ],
            prior_history=[history],
            farm_context=farm_context,
        )
    )
    return result.transition_results[0]


def test_validator_compares_only_supported_soil_and_matching_water_units(session):
    crop = Crop(slug="evidenced-test-crop", evidence_status=EvidenceStatus.UNKNOWN)
    session.add(crop)
    session.flush()
    evidence = _evidence(session)
    session.add_all(
        [
            CropRequirement(
                crop_id=crop.id,
                requirement_type=RequirementType.SOIL,
                soil_ph_min=6,
                soil_ph_max=7,
                evidence_status=EvidenceStatus.VERIFIED,
                primary_evidence_id=evidence.id,
            ),
            CropRequirement(
                crop_id=crop.id,
                requirement_type=RequirementType.WATER,
                water_requirement=10,
                water_requirement_unit="mm",
                water_requirement_basis="season",
                evidence_status=EvidenceStatus.VERIFIED,
                primary_evidence_id=evidence.id,
            ),
        ]
    )
    session.flush()

    result = AgriculturalValidator(session).validate_crop(
        CropValidationRequest(
            crop_id=crop.id,
            farm_context=FarmContext(
                farm_id="synthetic-farm",
                soil_ph=6.5,
                soil_type="not used for inference",
                water_available=8,
                water_unit="mm",
                water_basis="season",
            ),
        )
    )
    checks = {check.check_code: check for check in result.checks}
    assert checks["SOIL"].status is FeasibilityStatus.FEASIBLE
    assert checks["WATER"].status is FeasibilityStatus.INFEASIBLE
    assert result.status is FeasibilityStatus.INFEASIBLE


def test_soil_names_and_incompatible_water_bases_remain_insufficient(session):
    crop = Crop(slug="name-only-soil-crop")
    session.add(crop)
    session.flush()
    evidence = _evidence(session)
    session.add(
        CropRequirement(
            crop_id=crop.id,
            requirement_type=RequirementType.SOIL,
            soil_type="Synthetic soil name",
            evidence_status=EvidenceStatus.VERIFIED,
            primary_evidence_id=evidence.id,
        )
    )
    session.add(
        CropRequirement(
            crop_id=crop.id,
            requirement_type=RequirementType.WATER,
            water_requirement=1,
            water_requirement_unit="mm",
            water_requirement_basis="season",
            evidence_status=EvidenceStatus.VERIFIED,
            primary_evidence_id=evidence.id,
        )
    )
    session.flush()
    result = AgriculturalValidator(session).validate_crop(
        CropValidationRequest(
            crop_id=crop.id,
            farm_context=FarmContext(
                soil_type="Synthetic soil name",
                soil_ph=6.5,
                water_available=2,
                water_unit="m3",
                water_basis="season",
            ),
        )
    )
    checks = {check.check_code: check for check in result.checks}
    assert checks["SOIL"].status is FeasibilityStatus.INSUFFICIENT_DATA
    assert checks["WATER"].status is FeasibilityStatus.INSUFFICIENT_DATA


def test_calendar_and_duration_use_matching_geography_and_evidence(session):
    country = Country(name="Validation test country")
    crop = Crop(slug="calendar-evidenced-crop")
    session.add_all([country, crop])
    session.flush()
    evidence = _evidence(session)
    session.add(
        CropCalendar(
            crop_id=crop.id,
            country_id=country.id,
            season="Rabi",
            planting_start="11-01",
            planting_end="11-30",
            harvest_start="02-01",
            harvest_end="03-31",
            growing_duration_days=100,
            evidence_status=EvidenceStatus.VERIFIED,
            primary_evidence_id=evidence.id,
        )
    )
    session.flush()
    result = AgriculturalValidator(session).validate_crop(
        CropValidationRequest(
            crop_id=crop.id,
            upcoming_season="Rabi",
            farm_context=FarmContext(
                country_id=country.id,
                planting_date=date(2026, 11, 10),
                harvest_date=date(2027, 3, 10),
                season_duration_days=130,
            ),
        )
    )
    checks = {check.check_code: check for check in result.checks}
    assert checks["CALENDAR"].status is FeasibilityStatus.FEASIBLE
    assert checks["CROP_DURATION"].status is FeasibilityStatus.FEASIBLE


def test_rotation_rule_requires_evidence_and_recognized_status(session):
    previous = Crop(slug="previous-test-crop")
    next_crop = Crop(slug="next-test-crop")
    session.add_all([previous, next_crop])
    session.flush()
    evidence = _evidence(session)
    session.add(
        CropRotationRule(
            previous_crop_id=previous.id,
            next_crop_id=next_crop.id,
            compatibility_status="COMPATIBLE",
            confidence_level=0.5,
            evidence_status=EvidenceStatus.PROVISIONAL,
            primary_evidence_id=evidence.id,
            geographic_scopes=[
                CropRotationRuleGeographicScope(scope_type=GeographicScopeType.GLOBAL)
            ],
        )
    )
    session.flush()
    history = CropHistoryItem(
        crop_id=previous.id,
        source_record_id="synthetic-module01-record",
        evidence_record_ids=[evidence.id],
    )
    result = AgriculturalValidator(session).validate_sequence(
        SequenceValidationRequest(
            sequence=[{"crop_id": next_crop.id}],
            prior_history=[history],
        )
    )
    assert result.transition_results[0].status is FeasibilityStatus.CONDITIONALLY_FEASIBLE
    assert any("Module 01 farm data is not installed" in limitation
               for limitation in result.crop_results[0].limitations)


def test_rotation_district_scope_matches_same_district(session):
    geography = _geography(session)
    check = _rotation_transition(
        session,
        scope_type=GeographicScopeType.DISTRICT,
        scope_values={"district_id": geography["district"].id},
        farm_context=FarmContext(district_id=geography["district"].id),
    )

    assert check.status is FeasibilityStatus.CONDITIONALLY_FEASIBLE


def test_rotation_district_scope_does_not_match_another_district(session):
    geography = _geography(session)
    check = _rotation_transition(
        session,
        scope_type=GeographicScopeType.DISTRICT,
        scope_values={"district_id": geography["district"].id},
        farm_context=FarmContext(district_id=geography["other_district"].id),
    )

    assert check.status is FeasibilityStatus.INSUFFICIENT_DATA
    assert "CROP_FAMILY_ROTATION" == check.check_code


def test_rotation_province_scope_applies_to_consistent_descendant_locality(session):
    geography = _geography(session)
    check = _rotation_transition(
        session,
        scope_type=GeographicScopeType.PROVINCE_STATE,
        scope_values={"province_state_id": geography["province"].id},
        farm_context=FarmContext(
            country_id=geography["country"].id,
            province_state_id=geography["province"].id,
            district_id=geography["district"].id,
            locality_id=geography["locality"].id,
        ),
    )

    assert check.status is FeasibilityStatus.CONDITIONALLY_FEASIBLE


def test_rotation_locality_scope_matches_the_same_stored_locality(session):
    geography = _geography(session)
    check = _rotation_transition(
        session,
        scope_type=GeographicScopeType.LOCALITY,
        scope_values={"locality_id": geography["locality"].id},
        farm_context=FarmContext(locality_id=geography["locality"].id),
    )

    assert check.status is FeasibilityStatus.CONDITIONALLY_FEASIBLE


def test_rotation_scope_does_not_match_inconsistent_farm_hierarchy(session):
    geography = _geography(session)
    check = _rotation_transition(
        session,
        scope_type=GeographicScopeType.PROVINCE_STATE,
        scope_values={"province_state_id": geography["other_province"].id},
        farm_context=FarmContext(
            province_state_id=geography["other_province"].id,
            locality_id=geography["locality"].id,
        ),
    )

    assert check.status is FeasibilityStatus.INSUFFICIENT_DATA
    assert "consistent stored" in check.missing_information[0]


@pytest.mark.parametrize("matches", [True, False])
def test_rotation_zone_scope_matches_only_the_same_zone(session, matches):
    zone = AgroecologicalZone(name="Rotation test zone")
    other_zone = AgroecologicalZone(name="Other rotation test zone")
    session.add_all([zone, other_zone])
    session.flush()
    farm_zone_id = zone.id if matches else other_zone.id
    check = _rotation_transition(
        session,
        scope_type=GeographicScopeType.AGROECOLOGICAL_ZONE,
        scope_values={"agroecological_zone_id": zone.id},
        farm_context=FarmContext(agroecological_zone_id=farm_zone_id),
    )

    assert check.status is (
        FeasibilityStatus.CONDITIONALLY_FEASIBLE
        if matches
        else FeasibilityStatus.INSUFFICIENT_DATA
    )


def test_narrow_rotation_scope_does_not_match_without_farm_geography(session):
    geography = _geography(session)
    check = _rotation_transition(
        session,
        scope_type=GeographicScopeType.DISTRICT,
        scope_values={"district_id": geography["district"].id},
    )

    assert check.status is FeasibilityStatus.INSUFFICIENT_DATA
    assert "geographically matching" in check.missing_information[0]


def test_explicit_global_rotation_scope_matches_without_farm_geography(session):
    check = _rotation_transition(
        session,
        scope_type=GeographicScopeType.GLOBAL,
    )

    assert check.status is FeasibilityStatus.CONDITIONALLY_FEASIBLE


def test_rotation_rule_without_geographic_scope_is_not_global(session):
    check = _rotation_transition(session)

    assert check.status is FeasibilityStatus.INSUFFICIENT_DATA
    assert any("not treated as GLOBAL" in item for item in check.limitations)


@pytest.mark.parametrize(
    ("source_selector", "target_selector"),
    [("crop", "crop"), ("variety", "variety"), ("family", "family")],
)
def test_rotation_geography_does_not_change_crop_variety_or_family_matching(
    session, source_selector, target_selector
):
    check = _rotation_transition(
        session,
        scope_type=GeographicScopeType.GLOBAL,
        source_selector=source_selector,
        target_selector=target_selector,
    )

    assert check.status is FeasibilityStatus.CONDITIONALLY_FEASIBLE
