import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.app.modules.agri_intelligence.db.base import Base
from backend.app.modules.agri_intelligence.db.engine import get_engine
from backend.app.modules.agri_intelligence.models import (
    AgriculturalSource,
    AgroecologicalZone,
    Country,
    Crop,
    CropCalendar,
    CropRequirement,
    CropRotationRule,
    CropVariety,
    District,
    EvidenceRecord,
    Locality,
    ProvinceState,
    SourceAllCropsApplicability,
    SourceApplicability,
)
from backend.app.modules.agri_intelligence.models.enums import (
    ApplicabilityMode,
    EvidenceOriginType,
    EvidenceStatus,
    GeographicScopeType,
    RequirementType,
)
from backend.app.modules.agri_intelligence.repositories import (
    AgriculturalSourceRepository,
    AgroecologicalZoneGeographyRepository,
    AgroecologicalZoneRepository,
    CountryRepository,
    CropCalendarRepository,
    CropRepository,
    CropRequirementRepository,
    CropRotationRuleGeographicScopeRepository,
    CropRotationRuleRepository,
    DistrictRepository,
    EvidenceRecordRepository,
    LocalityRepository,
    ProvinceStateRepository,
    RecordNotFoundError,
)
from backend.app.modules.agri_intelligence.schemas import (
    AgriculturalSourceCreate,
    CropCalendarCreate,
    CropCalendarUpdate,
    CropCreate,
    CropRequirementCreate,
    CropRequirementUpdate,
    CropRotationRuleCreate,
    CropVarietyCreate,
    EvidenceRecordCreate,
    GeographicScopeInput,
    SourceApplicabilityInput,
)
from backend.app.modules.agri_intelligence.seeds import seed_all
from backend.app.modules.agri_intelligence.services import (
    AgriculturalResearchService,
    CropCalendarService,
    CropDatabaseService,
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


def test_crop_repository_crud_and_missing_record(session):
    repository = CropRepository(session)
    crop = repository.create(CropCreate(slug="sample-crop", common_name="Sample"))
    assert repository.get(crop.id).common_name == "Sample"
    assert repository.list(filters={"active": True}) == [crop]

    updated = repository.update(crop.id, {"common_name": "Updated"})
    assert updated.common_name == "Updated"
    repository.delete(crop.id)
    with pytest.raises(RecordNotFoundError):
        repository.get(crop.id)


def test_crop_update_revalidates_merged_non_nullable_fields(session):
    service = CropDatabaseService(session)
    crop = service.create_crop(CropCreate(slug="valid-crop"))
    with pytest.raises(ValidationError):
        service.update_crop(crop.id, {"active": None})
    assert service.get_crop(crop.id).active is True


def test_crop_variety_repository_crud_and_evidence_relationship(session):
    source = AgriculturalSourceRepository(session).create(
        AgriculturalSourceCreate(title="Synthetic evidence source")
    )
    evidence = EvidenceRecordRepository(session).create(
        EvidenceRecordCreate(
            source_id=source.id,
            source_type=EvidenceOriginType.PUBLISHED_SOURCE,
            statement="Synthetic test statement.",
        )
    )
    crop = CropRepository(session).create(CropCreate(slug="variety-crop"))
    service = CropDatabaseService(session)
    variety = service.create_variety(
        CropVarietyCreate(
            crop_id=crop.id,
            name="Synthetic variety",
            evidence_status=EvidenceStatus.PROVISIONAL,
            primary_evidence_id=evidence.id,
            evidence_record_ids=[evidence.id],
        )
    )
    assert service.get_variety(variety.id).crop_id == crop.id
    assert service.list_varieties(crop_id=crop.id) == [variety]
    assert variety.primary_evidence_id == evidence.id
    assert variety.evidence_records == [evidence]
    service.update_variety(variety.id, {"name": "Renamed synthetic variety"})
    assert service.get_variety(variety.id).name == "Renamed synthetic variety"
    service.delete_variety(variety.id)
    with pytest.raises(RecordNotFoundError):
        service.get_variety(variety.id)


def test_calendar_partial_update_validates_persisted_window(session):
    crop = CropRepository(session).create(CropCreate(slug="calendar-crop"))
    repository = CropCalendarRepository(session)
    calendar = repository.create(
        CropCalendarCreate(
            crop_id=crop.id,
            planting_start="03-01",
            planting_end="05-01",
        )
    )
    repository.update(calendar.id, CropCalendarUpdate(planting_start="04-01"))
    assert repository.get(calendar.id).planting_start == "04-01"

    with pytest.raises(ValidationError):
        repository.update(calendar.id, {"planting_start": "06-01"})
    assert repository.get(calendar.id).planting_start == "04-01"


def test_requirement_partial_update_validates_merged_measurement_group(session):
    crop = CropRepository(session).create(CropCreate(slug="requirement-crop"))
    repository = CropRequirementRepository(session)
    requirement = repository.create(
        CropRequirementCreate(
            crop_id=crop.id,
            requirement_type=RequirementType.WATER,
            water_requirement=10,
            water_requirement_unit="mm",
            water_requirement_basis="season",
        )
    )
    repository.update(requirement.id, {"water_requirement": 12})
    assert repository.get(requirement.id).water_requirement == 12

    with pytest.raises(ValidationError):
        repository.update(requirement.id, {"water_requirement_unit": None})


def test_source_applicability_switches_exclusively_to_all_crops(session):
    crop = CropRepository(session).create(CropCreate(slug="source-crop"))
    repository = AgriculturalSourceRepository(session)
    source = repository.create(
        AgriculturalSourceCreate(
            title="Synthetic source",
            applicabilities=[
                SourceApplicabilityInput(
                    applicability_mode=ApplicabilityMode.CROP,
                    crop_id=crop.id,
                )
            ],
        )
    )
    assert len(source.applicabilities) == 1
    with pytest.raises(ValidationError):
        repository.update(source.id, {"all_crops_flag": True})

    repository.update(
        source.id, {"all_crops_flag": True, "applicabilities": []}
    )
    session.expire_all()
    assert session.scalar(
        select(SourceApplicability.id).where(SourceApplicability.source_id == source.id)
    ) is None
    assert session.get(SourceAllCropsApplicability, source.id) is not None


def test_source_all_crops_is_seeded_as_only_applicability(session):
    repository = AgriculturalSourceRepository(session)
    source = repository.create(AgriculturalSourceCreate(all_crops_flag=True))
    assert source.all_crops_applicability is not None
    with pytest.raises(ValidationError):
        repository.update(
            source.id,
            {
                "all_crops_flag": True,
                "applicabilities": [
                    {
                        "applicability_mode": "FAMILY",
                        "family_name": "Synthetic family",
                    }
                ],
            },
        )


def test_research_service_preserves_evidence_and_geographic_traceability(session):
    research = AgriculturalResearchService(session)
    source = research.create_source(
        AgriculturalSourceCreate(
            title="Synthetic published source",
            publication_url="https://example.invalid/synthetic",
        )
    )
    country = CountryRepository(session).create({"name": "Test country"})
    evidence = research.create_evidence(
        EvidenceRecordCreate(
            source_id=source.id,
            source_type=EvidenceOriginType.PUBLISHED_SOURCE,
            statement="Synthetic test statement, not agricultural guidance.",
            geographic_scopes=[
                {
                    "scope_type": GeographicScopeType.COUNTRY,
                    "country_id": country.id,
                }
            ],
        )
    )
    assert evidence.source_id == source.id
    assert evidence.geographic_scopes[0].country_id == country.id

    updated = research.update_evidence(evidence.id, {"limitations": "Test limitation"})
    assert updated.limitations == "Test limitation"
    with pytest.raises(ValidationError):
        research.create_evidence(
            {
                "source_type": EvidenceOriginType.PUBLISHED_SOURCE,
                "statement": "Missing source",
            }
        )


def test_geography_repositories_and_calendar_service_filtering(session):
    country = CountryRepository(session).create({"name": "Test country"})
    province = ProvinceStateRepository(session).create(
        {"country_id": country.id, "name": "Test province"}
    )
    district = DistrictRepository(session).create(
        {"province_state_id": province.id, "name": "Test district"}
    )
    locality = LocalityRepository(session).create(
        {"district_id": district.id, "name": "Test locality"}
    )
    crop_service = CropDatabaseService(session)
    crop = crop_service.create_crop(CropCreate(slug="located-crop"))
    calendars = CropCalendarService(session)
    first = calendars.create(
        CropCalendarCreate(
            crop_id=crop.id,
            country_id=country.id,
            province_state_id=province.id,
            district_id=district.id,
            evidence_status=EvidenceStatus.UNKNOWN,
        )
    )
    calendars.create(
        CropCalendarCreate(crop_id=crop.id, evidence_status=EvidenceStatus.UNKNOWN)
    )
    assert calendars.list(district_id=district.id) == [first]
    assert locality.district_id == district.id


def test_rotation_and_zone_repositories_keep_geographic_relationships(session):
    country = CountryRepository(session).create({"name": "Scoped test country"})
    crop = CropRepository(session).create(CropCreate(slug="rotation-crop"))
    rotation_repository = CropRotationRuleRepository(session)
    rule = rotation_repository.create(
        CropRotationRuleCreate(
            previous_crop_id=crop.id,
            next_crop_id=crop.id,
            confidence_level=0,
            evidence_status=EvidenceStatus.UNKNOWN,
        )
    )
    scope = CropRotationRuleGeographicScopeRepository(session).create(
        {
            "crop_rotation_rule_id": rule.id,
            "scope_type": GeographicScopeType.COUNTRY,
            "country_id": country.id,
        }
    )
    rotation_repository.update(rule.id, {"geographic_scope_ids": [scope.id]})
    assert rotation_repository.get(rule.id).geographic_scopes == [scope]

    zone = AgroecologicalZoneRepository(session).create(
        {"name": "Synthetic test zone"}
    )
    association = AgroecologicalZoneGeographyRepository(session).create(
        {"agroecological_zone_id": zone.id, "country_id": country.id}
    )
    assert association.country_id == country.id


def test_seed_execution_is_repeatable_and_marks_unverified_data_unknown(session):
    first = seed_all(session)
    row_counts = (
        session.query(Crop).count(),
        session.query(CropCalendar).count(),
        session.query(CropRequirement).count(),
        session.query(AgriculturalSource).count(),
        session.query(ProvinceState).count(),
        session.query(CropVariety).count(),
        session.query(CropRotationRule).count(),
        session.query(AgroecologicalZone).count(),
    )
    second = seed_all(session)
    assert first.sources == 3
    assert first.crops == 8
    assert first.calendars == 8
    assert first.requirements == 40
    assert first.varieties == first.rotation_rules == first.agroecological_zones == 0
    assert all(value == 0 for value in second.__dict__.values())
    assert row_counts == (
        session.query(Crop).count(),
        session.query(CropCalendar).count(),
        session.query(CropRequirement).count(),
        session.query(AgriculturalSource).count(),
        session.query(ProvinceState).count(),
        session.query(CropVariety).count(),
        session.query(CropRotationRule).count(),
        session.query(AgroecologicalZone).count(),
    )
    assert all(
        crop.evidence_status is EvidenceStatus.UNKNOWN
        and crop.scientific_name is None
        for crop in session.scalars(select(Crop))
    )
    assert all(
        calendar.evidence_status is EvidenceStatus.UNKNOWN
        and calendar.planting_start is None
        and calendar.harvest_start is None
        for calendar in session.scalars(select(CropCalendar))
    )
    assert all(
        requirement.evidence_status is EvidenceStatus.UNKNOWN
        and requirement.primary_evidence_id is None
        for requirement in session.scalars(select(CropRequirement))
    )


def test_schemas_reject_incomplete_or_conflicting_inputs():
    with pytest.raises(ValidationError):
        CropRequirementCreate(
            crop_id=1,
            requirement_type=RequirementType.WATER,
            water_requirement=10,
        )
    with pytest.raises(ValidationError):
        CropRotationRuleCreate(confidence_level=0.5)
    with pytest.raises(ValidationError):
        GeographicScopeInput(
            scope_type=GeographicScopeType.DISTRICT,
            country_id=1,
        )
