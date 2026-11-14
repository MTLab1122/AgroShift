import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import configure_mappers, sessionmaker

from backend.app.modules.agri_intelligence.db.base import Base
from backend.app.modules.agri_intelligence.db.engine import get_engine
from backend.app.modules.agri_intelligence.models import (
    AgriculturalSource,
    AgroecologicalZone,
    AgroecologicalZoneGeography,
    Country,
    Crop,
    CropCalendar,
    CropRequirement,
    CropRotationRule,
    CropRotationRuleGeographicScope,
    CropVariety,
    District,
    EvidenceGeographicScope,
    EvidenceRecord,
    Locality,
    ProvinceState,
    SourceApplicability,
    SourceAllCropsApplicability,
    SourceGeographicApplicability,
)
from backend.app.modules.agri_intelligence.models.enums import (
    ApplicabilityMode,
    EvidenceOriginType,
    EvidenceStatus,
    GeographicScopeType,
    RequirementType,
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


def _crop(session, slug="synthetic-crop", **values):
    crop = Crop(slug=slug, **values)
    session.add(crop)
    session.flush()
    return crop


def _evidence(session, source=None, source_type=EvidenceOriginType.FARMER_PROVIDED):
    evidence = EvidenceRecord(
        source=source,
        source_type=source_type,
        statement="Synthetic evidence fixture for software testing only.",
    )
    session.add(evidence)
    session.flush()
    return evidence


def test_model_imports_and_relationship_configuration():
    configure_mappers()
    assert Crop.__table__.c.slug.unique
    assert "varieties" in inspect(Crop).relationships
    assert "crop" in inspect(CropVariety).relationships
    assert "geographic_associations" in inspect(AgroecologicalZone).relationships
    assert "evidence_records" in inspect(CropRequirement).relationships


def test_required_original_fields_are_present():
    expected_columns = {
        Crop: {
            "id", "slug", "common_name", "scientific_name", "crop_family",
            "crop_category", "is_legume", "description", "active",
            "evidence_status", "metadata",
        },
        CropVariety: {
            "id", "crop_id", "name", "maturity_class", "regional_adaptation",
            "duration_days", "evidence_status", "source_id", "metadata",
        },
        CropCalendar: {
            "id", "crop_id", "variety_id", "country_id", "province_state_id",
            "district_id", "agroecological_zone_id", "region_label", "season",
            "planting_start", "planting_end", "harvest_start", "harvest_end",
            "growing_duration_days", "calendar_source_id", "confidence_level",
            "evidence_status", "notes",
        },
        CropRequirement: {
            "id", "crop_id", "variety_id", "requirement_type", "soil_type",
            "soil_ph_min", "soil_ph_max", "water_requirement",
            "water_requirement_unit", "water_requirement_basis", "temperature_min",
            "temperature_max", "salinity_tolerance", "additional_conditions",
            "source_id", "evidence_status", "limitations", "nutrient_n_value",
            "nutrient_n_unit", "nutrient_n_basis", "nutrient_p_value",
            "nutrient_p_unit", "nutrient_p_basis", "other_description",
            "other_measurement_basis",
        },
        AgriculturalSource: {
            "id", "organization", "title", "publication_url", "document_reference",
            "publication_date", "access_date", "source_type",
            "geographic_applicability", "crop_applicability", "evidence_class",
            "review_status", "limitations", "notes",
        },
        CropRotationRule: {
            "id", "previous_crop_id", "next_crop_id", "rule_type",
            "compatibility_status", "severity", "explanation", "geographic_scope",
            "evidence_source_id", "confidence_level", "evidence_status",
            "source_family", "target_family",
        },
    }
    for model, column_names in expected_columns.items():
        assert column_names <= set(model.__table__.columns.keys())


def test_crop_and_variety_metadata_round_trip_in_new_session(session):
    metadata = {
        "nested": {
            "items": [1, {"name": "synthetic", "active": True}],
            "details": {"note": "software test fixture"},
        },
        "flags": [False, None, "preserved"],
    }
    crop = _crop(session, metadata_json=metadata)
    variety = CropVariety(
        crop=crop,
        name="Synthetic metadata variety",
        metadata_json=metadata,
    )
    session.add(variety)
    session.commit()
    crop_id, variety_id = crop.id, variety.id
    engine = session.get_bind()
    session.close()

    with sessionmaker(bind=engine, expire_on_commit=False)() as reloaded_session:
        assert reloaded_session.get(Crop, crop_id).metadata_json == metadata
        assert reloaded_session.get(CropVariety, variety_id).metadata_json == metadata

    assert Crop.__table__.c.metadata.name == "metadata"
    assert CropVariety.__table__.c.metadata.name == "metadata"


def test_foreign_keys_are_enforced_by_sqlite(session):
    session.add(CropCalendar(crop_id=987654, evidence_status=EvidenceStatus.UNKNOWN))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_delete_behavior_matches_foreign_key_policy(session):
    crop = _crop(session)
    variety = CropVariety(crop=crop, name="Synthetic deletable variety")
    session.add(variety)
    session.commit()
    variety_id = variety.id
    session.delete(crop)
    session.commit()
    session.expire_all()
    assert session.get(CropVariety, variety_id) is None

    country = Country(name="Synthetic restricted country")
    session.add(country)
    session.flush()
    session.add(ProvinceState(country=country, name="Synthetic restricted province"))
    session.commit()
    session.delete(country)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    source = AgriculturalSource(title="Synthetic retained-evidence source")
    session.add(source)
    session.flush()
    _evidence(session, source, EvidenceOriginType.PUBLISHED_SOURCE)
    session.commit()
    session.delete(source)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_variety_must_match_crop_on_calendar_and_requirement(session):
    first_crop = _crop(session, "first-crop")
    second_crop = _crop(session, "second-crop")
    variety = CropVariety(crop=first_crop, name="Synthetic variety")
    session.add(variety)
    session.flush()

    session.add(
        CropCalendar(
            crop_id=second_crop.id,
            variety_id=variety.id,
            evidence_status=EvidenceStatus.UNKNOWN,
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_evidence_status_requires_evidence_but_not_reviewed_source(session):
    unreviewed_source = AgriculturalSource(
        title="Synthetic source fixture",
        review_status="UNREVIEWED",
    )
    session.add(unreviewed_source)
    session.flush()
    evidence = _evidence(
        session,
        source=unreviewed_source,
        source_type=EvidenceOriginType.PUBLISHED_SOURCE,
    )
    crop = Crop(
        slug="synthetic-supported-crop",
        evidence_status=EvidenceStatus.VERIFIED,
        primary_evidence=evidence,
    )
    session.add(crop)
    session.commit()
    assert crop.primary_evidence.source.review_status == "UNREVIEWED"

    unsupported = Crop(slug="synthetic-unsupported-crop", evidence_status=EvidenceStatus.PROVISIONAL)
    session.add(unsupported)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_all_evidence_status_values_are_supported(session):
    for status in EvidenceStatus:
        evidence = None
        if status in {EvidenceStatus.VERIFIED, EvidenceStatus.PROVISIONAL}:
            evidence = _evidence(session)
        _crop(
            session,
            f"status-{status.value.lower()}",
            evidence_status=status,
            primary_evidence=evidence,
        )
    session.commit()
    statuses = set(session.scalars(select(Crop.evidence_status)))
    assert statuses == set(EvidenceStatus)


def test_database_rejects_unrecognized_evidence_status(session):
    with pytest.raises(IntegrityError):
        session.execute(
            text(
                "INSERT INTO crops (slug, evidence_status) "
                "VALUES ('synthetic-invalid-status', 'REVIEWED')"
            )
        )
        session.commit()
    session.rollback()


def test_source_applicability_allows_multiple_narrow_entries(session):
    source = AgriculturalSource(title="Synthetic applicability fixture")
    crop_a = _crop(session, "crop-a")
    crop_b = _crop(session, "crop-b")
    variety = CropVariety(crop=crop_a, name="Synthetic applicability variety")
    session.add_all([source, variety])
    session.flush()

    source.applicabilities.extend(
        [
            SourceApplicability(
                applicability_mode=ApplicabilityMode.CROP,
                crop_id=crop_a.id,
            ),
            SourceApplicability(
                applicability_mode=ApplicabilityMode.CROP,
                crop_id=crop_b.id,
            ),
            SourceApplicability(
                applicability_mode=ApplicabilityMode.VARIETY,
                variety=variety,
            ),
            SourceApplicability(
                applicability_mode=ApplicabilityMode.FAMILY,
                family_name="synthetic-family",
            ),
        ]
    )
    session.commit()
    assert len(source.applicabilities) == 4



def test_all_crops_applicability_is_stored_alone(session):
    source = AgriculturalSource(
        title="Synthetic all-crops fixture",
        all_crops_flag=True,
        all_crops_applicability=SourceAllCropsApplicability(),
    )
    session.add(source)
    session.commit()
    assert source.all_crops_applicability is not None
    assert source.applicabilities == []


def test_all_crops_cannot_coexist_with_narrow_applicability(session):
    source = AgriculturalSource(
        title="Synthetic all-crops fixture",
        all_crops_flag=True,
        all_crops_applicability=SourceAllCropsApplicability(),
    )
    crop = _crop(session, "narrow-selector-crop")
    session.add(source)
    session.commit()

    with pytest.raises(IntegrityError):
        session.execute(
            SourceApplicability.__table__.insert().values(
                source_id=source.id,
                applicability_mode=ApplicabilityMode.CROP.value,
                crop_id=crop.id,
            )
        )
        session.commit()
    session.rollback()


def test_duplicate_source_applicability_entries_are_rejected(session):
    crop = _crop(session, "duplicate-selector-crop")
    source = AgriculturalSource(title="Synthetic duplicate fixture")
    source.applicabilities.extend(
        [
            SourceApplicability(
                applicability_mode=ApplicabilityMode.CROP,
                crop_id=crop.id,
            ),
            SourceApplicability(
                applicability_mode=ApplicabilityMode.FAMILY,
                family_name="synthetic-duplicate-family",
            ),
        ]
    )
    session.add(source)
    session.commit()

    for duplicate in (
        {
            "applicability_mode": ApplicabilityMode.CROP.value,
            "crop_id": crop.id,
        },
        {
            "applicability_mode": ApplicabilityMode.FAMILY.value,
            "family_name": "synthetic-duplicate-family",
        },
    ):
        with pytest.raises(IntegrityError):
            session.execute(
                SourceApplicability.__table__.insert().values(
                    source_id=source.id,
                    **duplicate,
                )
            )
            session.commit()
        session.rollback()

    all_crops_source = AgriculturalSource(
        title="Synthetic duplicate all-crops fixture",
        all_crops_flag=True,
        all_crops_applicability=SourceAllCropsApplicability(),
    )
    session.add(all_crops_source)
    session.commit()
    with pytest.raises(IntegrityError):
        session.execute(
            SourceAllCropsApplicability.__table__.insert().values(
                source_id=all_crops_source.id,
            )
        )
        session.commit()
    session.rollback()


def test_source_applicability_rejects_mixed_selectors(session):
    crop = _crop(session, "mixed-selector-crop")
    source = AgriculturalSource(title="Synthetic mixed selector fixture")
    session.add(source)
    session.flush()

    with pytest.raises(IntegrityError):
        session.execute(
            SourceApplicability.__table__.insert().values(
                source_id=source.id,
                applicability_mode=ApplicabilityMode.CROP.value,
                crop_id=crop.id,
                family_name="synthetic-family",
            )
        )
        session.commit()
    session.rollback()


def test_source_and_fact_geographic_scopes_are_explicit(session):
    source = AgriculturalSource(title="Synthetic scope fixture")
    session.add(source)
    session.flush()
    source.geographic_applicabilities.append(
        SourceGeographicApplicability(scope_type=GeographicScopeType.GLOBAL)
    )
    evidence = _evidence(session, source, EvidenceOriginType.PUBLISHED_SOURCE)
    evidence.geographic_scopes.append(
        EvidenceGeographicScope(scope_type=GeographicScopeType.GLOBAL)
    )
    session.commit()
    assert source.geographic_applicabilities[0].scope_type is GeographicScopeType.GLOBAL
    assert evidence.geographic_scopes[0].scope_type is GeographicScopeType.GLOBAL
    evidence.geographic_scopes.append(
        EvidenceGeographicScope(
            scope_type=GeographicScopeType.FARM,
            farm_id="synthetic-farm-id",
        )
    )
    session.commit()

    missing_scope_source = AgriculturalSource(title="Scope not specified")
    session.add(missing_scope_source)
    session.commit()
    assert missing_scope_source.geographic_applicabilities == []


def test_requirement_measurements_follow_type_and_nutrient_basis(session):
    crop = _crop(session)
    valid_nutrient = CropRequirement(
        crop=crop,
        requirement_type=RequirementType.NUTRIENT,
        nutrient_n_value=12,
        nutrient_n_unit="synthetic-unit",
        nutrient_n_basis="software test basis",
    )
    session.add(valid_nutrient)
    session.commit()

    unrelated = CropRequirement(
        crop=crop,
        requirement_type=RequirementType.WATER,
        water_requirement=10,
        water_requirement_unit="synthetic-unit",
        water_requirement_basis="software test basis",
        soil_ph_min=6,
    )
    session.add(unrelated)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_requirement_type_other_requires_description(session):
    crop = _crop(session)
    session.add(CropRequirement(crop=crop, requirement_type=RequirementType.OTHER))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_nutrient_measurement_requires_complete_value_unit_basis(session):
    crop = _crop(session)
    session.add(
        CropRequirement(
            crop=crop,
            requirement_type=RequirementType.NUTRIENT,
            nutrient_n_value=8,
            nutrient_n_unit="synthetic-unit",
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_calendar_leap_day_and_cross_year_rules(session):
    crop = _crop(session)
    valid = CropCalendar(
        crop=crop,
        planting_start="12-15",
        planting_end="02-29",
        plant_crosses_year=True,
        plant_leap_year_allowed=True,
        harvest_start="06-01",
        harvest_end="07-15",
        evidence_status=EvidenceStatus.UNKNOWN,
    )
    session.add(valid)
    session.commit()

    invalid_leap_day = CropCalendar(
        crop=crop,
        planting_start="02-29",
        planting_end="03-10",
        evidence_status=EvidenceStatus.UNKNOWN,
    )
    session.add(invalid_leap_day)
    with pytest.raises(ValueError, match="February 29"):
        session.commit()
    session.rollback()


@pytest.mark.parametrize(
    ("start_column", "end_column", "crosses_year_column"),
    [
        ("planting_start", "planting_end", "plant_crosses_year"),
        ("harvest_start", "harvest_end", "harvest_crosses_year"),
    ],
)
def test_calendar_database_rejects_incorrect_cross_year_flags(
    session, start_column, end_column, crosses_year_column
):
    crop = _crop(session)
    with pytest.raises(IntegrityError):
        session.execute(
            CropCalendar.__table__.insert().values(
                crop_id=crop.id,
                **{
                    start_column: "12-01",
                    end_column: "02-01",
                    crosses_year_column: False,
                },
            )
        )
        session.commit()
    session.rollback()


@pytest.mark.parametrize(
    ("start_column", "end_column", "leap_flag_column", "crosses_year_column"),
    [
        (
            "planting_start",
            "planting_end",
            "plant_leap_year_allowed",
            "plant_crosses_year",
        ),
        (
            "harvest_start",
            "harvest_end",
            "harvest_leap_year_allowed",
            "harvest_crosses_year",
        ),
    ],
)
def test_calendar_database_rejects_february_29_without_permission(
    session, start_column, end_column, leap_flag_column, crosses_year_column
):
    crop = _crop(session)
    with pytest.raises(IntegrityError):
        session.execute(
            CropCalendar.__table__.insert().values(
                crop_id=crop.id,
                **{
                    start_column: "02-29",
                    end_column: "03-10",
                    leap_flag_column: False,
                    crosses_year_column: False,
                },
            )
        )
        session.commit()
    session.rollback()


def test_calendar_database_accepts_cross_year_and_leap_year_windows(session):
    crop = _crop(session)
    session.execute(
        CropCalendar.__table__.insert().values(
            crop_id=crop.id,
            planting_start="11-01",
            planting_end="02-15",
            plant_crosses_year=True,
            harvest_start="12-01",
            harvest_end="03-01",
            harvest_crosses_year=True,
        )
    )
    session.commit()

    session.execute(
        CropCalendar.__table__.insert().values(
            crop_id=crop.id,
            planting_start="02-29",
            planting_end="03-10",
            plant_leap_year_allowed=True,
            harvest_start="11-01",
            harvest_end="02-29",
            harvest_crosses_year=True,
            harvest_leap_year_allowed=True,
        )
    )
    session.commit()


def test_calendar_orm_rejects_incorrect_cross_year_flag(session):
    crop = _crop(session)
    session.add(
        CropCalendar(
            crop=crop,
            planting_start="12-01",
            planting_end="02-01",
            plant_crosses_year=False,
            evidence_status=EvidenceStatus.UNKNOWN,
        )
    )
    with pytest.raises(ValueError, match="plant_crosses_year"):
        session.commit()
    session.rollback()


def test_rotation_selectors_are_exclusive_and_confidence_is_bounded(session):
    crop = _crop(session)
    valid = CropRotationRule(
        previous_crop_id=crop.id,
        target_family="synthetic-family",
        confidence_level=0.5,
    )
    session.add(valid)
    session.commit()

    invalid_selectors = CropRotationRule(
        previous_crop_id=crop.id,
        source_family="ambiguous-family",
        next_crop_id=crop.id,
        confidence_level=0.5,
    )
    session.add(invalid_selectors)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    invalid_confidence = CropRotationRule(
        source_family="synthetic-family",
        next_crop_id=crop.id,
        confidence_level=1.1,
    )
    session.add(invalid_confidence)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_administrative_and_agroecological_geographies_remain_independent(session):
    country = Country(name="Synthetic country")
    session.add(country)
    session.flush()
    province = ProvinceState(country=country, name="Synthetic province")
    session.add(province)
    session.flush()
    first_district = District(province_state=province, name="Synthetic district one")
    second_district = District(province_state=province, name="Synthetic district two")
    session.add_all([first_district, second_district])
    session.flush()
    locality = Locality(district=first_district, name="Synthetic locality")
    zone = AgroecologicalZone(name="Synthetic zone")
    session.add_all([locality, zone])
    session.flush()
    zone.geographic_associations.extend(
        [
            AgroecologicalZoneGeography(district_id=first_district.id),
            AgroecologicalZoneGeography(district_id=second_district.id),
        ]
    )
    session.commit()

    assert locality.district.province_state.country is country
    assert {area.district_id for area in zone.geographic_associations} == {
        first_district.id,
        second_district.id,
    }
    assert not hasattr(zone, "district_id")
    rule = CropRotationRule(
        previous_crop_id=None,
        source_family="synthetic-family",
        next_crop_id=None,
        target_family="synthetic-target-family",
        confidence_level=0.4,
    )
    rule.geographic_scopes.append(
        CropRotationRuleGeographicScope(
            scope_type=GeographicScopeType.AGROECOLOGICAL_ZONE,
            agroecological_zone_id=zone.id,
        )
    )
    session.add(rule)
    session.commit()
    assert rule.geographic_scopes[0].agroecological_zone_id == zone.id


def test_calendar_administrative_references_must_match_hierarchy(session):
    country_a = Country(name="Synthetic hierarchy country A")
    country_b = Country(name="Synthetic hierarchy country B")
    session.add_all([country_a, country_b])
    session.flush()
    province_a = ProvinceState(country=country_a, name="Synthetic hierarchy province A")
    province_b = ProvinceState(country=country_b, name="Synthetic hierarchy province B")
    session.add_all([province_a, province_b])
    session.flush()
    district_a = District(province_state=province_a, name="Synthetic hierarchy district A")
    district_b = District(province_state=province_b, name="Synthetic hierarchy district B")
    session.add_all([district_a, district_b])
    crop = _crop(session, "hierarchy-calendar-crop")
    session.flush()

    table = CropCalendar.__table__
    session.execute(table.insert().values(crop_id=crop.id, country_id=country_a.id))
    session.execute(
        table.insert().values(crop_id=crop.id, province_state_id=province_a.id)
    )
    session.execute(
        table.insert().values(
            crop_id=crop.id,
            country_id=country_a.id,
            province_state_id=province_a.id,
            district_id=district_a.id,
        )
    )
    session.commit()

    invalid_scopes = (
        {
            "country_id": country_b.id,
            "province_state_id": province_a.id,
        },
        {
            "province_state_id": province_b.id,
            "district_id": district_a.id,
        },
        {"district_id": district_a.id},
    )
    for scope in invalid_scopes:
        with pytest.raises(IntegrityError):
            session.execute(table.insert().values(crop_id=crop.id, **scope))
            session.commit()
        session.rollback()


def test_schema_is_created_on_sqlite_and_constraints_are_present(session):
    engine = session.get_bind()
    inspector = inspect(engine)
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1

    expected_tables = {
        "crops",
        "crop_varieties",
        "crop_calendars",
        "crop_requirements",
        "agricultural_sources",
        "crop_rotation_rules",
        "crop_rotation_rule_geographic_scopes",
        "countries",
        "province_states",
        "districts",
        "localities",
        "agroecological_zones",
        "evidence_records",
        "source_applicabilities",
        "source_all_crops_applicabilities",
        "source_geographic_applicabilities",
        "evidence_geographic_scopes",
        "crop_evidence",
        "crop_variety_evidence",
        "crop_calendar_evidence",
        "crop_requirement_evidence",
        "crop_rotation_rule_evidence",
    }
    assert expected_tables <= set(inspector.get_table_names())
    applicability_columns = {
        column["name"]: column for column in inspector.get_columns("source_applicabilities")
    }
    all_crops_flag = applicability_columns["all_crops_flag"]
    assert all_crops_flag["nullable"] is False
    assert all_crops_flag["default"] is not None
    source = AgriculturalSource(title="Synthetic default fixture")
    crop = Crop(slug="synthetic-default-fixture")
    session.add_all([source, crop])
    session.flush()
    session.execute(
        SourceApplicability.__table__.insert().values(
            source_id=source.id,
            applicability_mode=ApplicabilityMode.CROP.value,
            crop_id=crop.id,
        )
    )
    session.commit()
    assert session.scalar(select(SourceApplicability.all_crops_flag)) is False
    crop_checks = {constraint["name"] for constraint in inspector.get_check_constraints("crops")}
    assert "ck_crops_evidence_requires_support" in crop_checks
