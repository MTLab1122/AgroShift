import asyncio
import json

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import create_engine

from backend.app.main import _cors_settings, app, handle_generic_exception
from backend.app.modules.agri_intelligence.api import get_db_session
from backend.app.modules.agri_intelligence.db.base import Base
from backend.app.modules.agri_intelligence.models import Crop


@pytest.fixture
def api_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, expire_on_commit=False)

    def override_session():
        with test_session() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    try:
        with test_session() as session:
            session.add(Crop(slug="api-test-crop", common_name="API test crop"))
            session.commit()
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_crop_read_and_calendar_endpoints_use_phase01_records(api_client):
    health = api_client.get("/health")
    assert health.status_code == 200

    crops_response = api_client.get("/api/v1/crops")
    assert crops_response.status_code == 200
    crop = crops_response.json()[0]
    assert crop["slug"] == "api-test-crop"
    assert crop["evidence_status"] == "UNKNOWN"

    details = api_client.get(f"/api/v1/crops/{crop['id']}")
    assert details.status_code == 200
    assert details.json()["id"] == crop["id"]
    calendars = api_client.get(f"/api/v1/crops/{crop['id']}/calendar")
    assert calendars.status_code == 200
    assert calendars.json() == []
    assert api_client.get("/api/v1/crops/9999").status_code == 404


def test_validation_endpoint_returns_insufficient_data_without_inventing_facts(api_client):
    response = api_client.post(
        "/api/v1/crops/validate",
        json={
            "crop_identifier": "missing-crop",
            "farm_context": {"farm_id": "caller-supplied-farm"},
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["crop_id"] is None
    assert result["missing_information"]

    invalid = api_client.post("/api/v1/crops/validate", json={})
    assert invalid.status_code == 422
    assert invalid.json()["error_code"] == "INVALID_REQUEST"


def test_recommendation_api_persists_unscored_scenarios_and_explains_gaps(api_client):
    generated = api_client.post(
        "/api/v1/recommendations/generate",
        json={
            "farm_id": "synthetic-api-farm",
            "scenario_types": ["EXISTING_PRACTICE", "SOIL_COVER_FORAGE"],
        },
    )
    assert generated.status_code == 200
    scenarios = generated.json()["scenarios"]
    assert len(scenarios) == 2
    assert all(item["score"] is None for item in scenarios)
    assert all(item["feasibility_status"] == "INSUFFICIENT_DATA" for item in scenarios)

    scenario_id = scenarios[0]["scenario_id"]
    assert api_client.get(f"/api/v1/recommendations/{scenario_id}").status_code == 200
    assert len(
        api_client.get(
            "/api/v1/recommendations/farm/synthetic-api-farm"
        ).json()
    ) == 2

    comparison = api_client.post(
        "/api/v1/recommendations/compare",
        json={"scenario_ids": [item["scenario_id"] for item in scenarios]},
    )
    assert comparison.status_code == 200
    assert comparison.json()["ranked_scenario_ids"] == []

    explanation = api_client.post(
        "/api/v1/recommendations/explain",
        json={"scenario_id": scenario_id},
    )
    assert explanation.status_code == 200
    assert "insufficient" in explanation.json()["explanation"].lower()


def test_cors_credentials_require_explicit_origins():
    assert _cors_settings("*") == (["*"], False)
    assert _cors_settings("https://example.test") == (
        ["https://example.test"],
        True,
    )
    with pytest.raises(ValueError):
        _cors_settings("*,https://example.test")


def test_unhandled_error_response_and_log_do_not_expose_exception_text(caplog):
    request = Request(
        {"type": "http", "method": "GET", "path": "/", "headers": []}
    )
    response = asyncio.run(
        handle_generic_exception(request, RuntimeError("sensitive test detail"))
    )

    payload = json.loads(response.body)
    assert response.status_code == 500
    assert payload["details"] is None
    assert "sensitive test detail" not in caplog.text
