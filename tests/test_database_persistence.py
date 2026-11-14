"""Isolated database persistence and migration verification for Module 01."""

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base
from backend.app.modules.farm_management import crud
from backend.app.modules.farm_management.schemas import (
    FarmCreate,
    FarmLocation,
    FarmBoundary,
    FarmUpdate,
    CropHistoryCreate,
    CropHistoryUpdate,
)


@pytest.fixture
def db_engine(tmp_path):
    database_path = tmp_path / "persistence-test.db"
    engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


def test_farm_and_crop_crud_persist_after_engine_restart(db_session, db_engine):
    # 1. Create Farm
    farm_in = FarmCreate(
        farm_id="farm-db-001",
        name="Charsadda River Organic Farm",
        owner_name="Waqas Ahmad",
        contact_phone="+92 313 1234567",
        preferred_language="ps",
        location=FarmLocation(
            latitude=34.1482,
            longitude=71.7406,
            district="Charsadda",
            province_or_region="Khyber Pakhtunkhwa",
            country="Pakistan",
            village_or_town="Tangi",
        ),
        boundary=FarmBoundary(
            type="Polygon",
            coordinates=[
                [
                    [71.738, 34.145],
                    [71.744, 34.145],
                    [71.743, 34.151],
                    [71.737, 34.150],
                    [71.738, 34.145],
                ]
            ],
        ),
        total_area_hectares=8.5,
        soil_type="sandy_loam",
        irrigation_source="river_lift",
        current_crops=["Maize"],
    )

    created_farm = crud.create_farm(db_session, farm_in)
    assert created_farm.farm_id == "farm-db-001"
    assert created_farm.name == "Charsadda River Organic Farm"
    assert created_farm.boundary is not None
    assert created_farm.boundary["type"] == "Polygon"

    # 2. Add Crop History
    crop_in = CropHistoryCreate(
        record_id="crop-db-001",
        crop_name="Maize",
        variety="30Y87",
        season="Kharif",
        year=2024,
        sowing_date="2024-06-15",
        harvest_date="2024-10-20",
        area_planted_hectares=8.5,
        yield_amount_kg=32000,
        status="harvested",
    )
    created_crop = crud.create_crop_record(db_session, "farm-db-001", crop_in)
    assert created_crop is not None
    assert created_crop.farm_id == "farm-db-001"

    # 3. Reopen a session to verify that committed records persist.
    db_session.close()
    db_engine.dispose()
    restarted_engine = create_engine(
        db_engine.url,
        connect_args={"check_same_thread": False},
    )
    try:
        Session = sessionmaker(bind=restarted_engine)
        with Session() as reopened_session:
            persisted_farm = crud.get_farm_by_id(reopened_session, "farm-db-001")
            assert persisted_farm is not None
            assert persisted_farm.boundary["type"] == "Polygon"

            # 4. Verify the farm relationship and crop listing.
            farm_crops = crud.get_crops_by_farm(reopened_session, "farm-db-001")
            assert len(farm_crops) == 1
            assert farm_crops[0].crop_name == "Maize"
            assert persisted_farm.crop_history[0].record_id == "crop-db-001"

            # 5. Update farm and crop records.
            updated_farm = crud.update_farm(
                reopened_session,
                "farm-db-001",
                FarmUpdate(name="Charsadda Updated Farm"),
            )
            assert updated_farm.name == "Charsadda Updated Farm"
            updated_crop = crud.update_crop_record(
                reopened_session,
                "farm-db-001",
                "crop-db-001",
                CropHistoryUpdate(status="growing", yield_amount_kg=None),
            )
            assert updated_crop.status == "growing"
            assert updated_crop.yield_amount_kg is None

            # 6. Crop deletion removes only the selected record.
            assert crud.delete_crop_record(
                reopened_session, "farm-db-001", "crop-db-001"
            ) is True
            assert crud.get_crops_by_farm(reopened_session, "farm-db-001") == []

            replacement_crop = crud.create_crop_record(
                reopened_session,
                "farm-db-001",
                CropHistoryCreate(crop_name="Wheat", season="Rabi", year=2025),
            )
            assert replacement_crop is not None

            # 7. Deleting a farm cascades to its crop-history records.
            del_success = crud.delete_farm(reopened_session, "farm-db-001")
            assert del_success is True
            assert crud.get_farm_by_id(reopened_session, "farm-db-001") is None
            assert crud.get_crops_by_farm(reopened_session, "farm-db-001") == []
    finally:
        restarted_engine.dispose()


def test_reject_crop_creation_for_missing_farm(db_session):
    crop_in = CropHistoryCreate(
        crop_name="Wheat",
        season="Rabi",
        year=2024,
    )
    # Attempting to assign crop to non-existent farm must fail safely
    result = crud.create_crop_record(db_session, "non-existent-farm-id", crop_in)
    assert result is None


def test_alembic_upgrade_matches_models_and_downgrade_removes_schema(tmp_path):
    database_path = tmp_path / "migration-test.db"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")

    command.upgrade(config, "head")

    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        inspector = inspect(engine)
        assert set(inspector.get_table_names()) >= {"farms", "crop_history"}
        foreign_keys = inspector.get_foreign_keys("crop_history")
        assert any(
            fk["referred_table"] == "farms"
            and fk["referred_columns"] == ["farm_id"]
            and fk["options"].get("ondelete") == "CASCADE"
            for fk in foreign_keys
        )

        from alembic.autogenerate import compare_metadata
        from alembic.migration import MigrationContext

        with engine.connect() as connection:
            migration_context = MigrationContext.configure(connection)
            assert compare_metadata(migration_context, Base.metadata) == []
    finally:
        engine.dispose()

    command.downgrade(config, "base")

    downgraded_engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    try:
        remaining_tables = set(inspect(downgraded_engine).get_table_names())
        assert "farms" not in remaining_tables
        assert "crop_history" not in remaining_tables
    finally:
        downgraded_engine.dispose()
