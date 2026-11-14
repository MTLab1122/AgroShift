"""Test suite for Module 01: Farm Management & Location Intelligence."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database import Base, get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


def test_create_and_get_farm():
    payload = {
        "farm_id": "test-peshawar-99",
        "name": "Peshawar Organic Test Farm",
        "owner_name": "Hamza Tariq",
        "contact_phone": "+92 345 1112233",
        "preferred_language": "ps",
        "location": {
            "latitude": 34.0151,
            "longitude": 71.5249,
            "district": "Peshawar",
            "province_or_region": "Khyber Pakhtunkhwa",
            "country": "Pakistan",
        },
        "boundary": {
            "type": "Polygon",
            "coordinates": [
                [
                    [71.522, 34.013],
                    [71.528, 34.013],
                    [71.528, 34.017],
                    [71.522, 34.017],
                    [71.522, 34.013],
                ]
            ],
        },
        "total_area_hectares": 12.5,
        "soil_type": "alluvial_clay",
        "irrigation_source": "canal",
        "current_crops": ["Wheat", "Sugarcane"],
    }

    # Create Farm
    res = client.post("/api/v1/farms", json=payload)
    assert res.status_code == 201

    # Fetch Farm
    res_get = client.get("/api/v1/farms/test-peshawar-99")
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["name"] == "Peshawar Organic Test Farm"
    assert data["location"]["latitude"] == 34.0151
    assert data["total_area_hectares"] == 12.5


def test_reject_invalid_coordinates():
    payload = {
        "name": "Bad Coordinates Farm",
        "owner_name": "Test",
        "contact_phone": "03001234567",
        "preferred_language": "en",
        "location": {
            "latitude": 125.0,  # Invalid latitude > 90
            "longitude": 71.5249,
            "district": "Peshawar",
            "province_or_region": "KP",
        },
        "total_area_hectares": 5.0,
    }
    res = client.post("/api/v1/farms", json=payload)
    assert res.status_code == 422
    err = res.json()
    assert err["error_code"] == "INVALID_COORDINATES"


def test_crop_history_crud():
    farm_id = "crop-test-farm"
    farm_payload = {
        "farm_id": farm_id,
        "name": "Crop History Test Farm",
        "owner_name": "Test Owner",
        "contact_phone": "+92 300 0000000",
        "location": {
            "latitude": 34.0151,
            "longitude": 71.5249,
            "district": "Peshawar",
            "province_or_region": "Khyber Pakhtunkhwa",
        },
        "total_area_hectares": 5.0,
    }
    assert client.post("/api/v1/farms", json=farm_payload).status_code == 201

    # Create, list, update, and delete a crop record.
    crop_payload = {
        "crop_name": "Maize",
        "variety": "Azam",
        "season": "Kharif",
        "year": 2024,
        "sowing_date": "2024-06-10",
        "harvest_date": "2024-10-01",
        "area_planted_hectares": 6.0,
        "yield_amount_kg": 24000,
        "status": "harvested",
    }
    res = client.post(f"/api/v1/farms/{farm_id}/crops", json=crop_payload)
    assert res.status_code == 201
    created = res.json()
    record_id = created["record_id"]
    assert created["crop_name"] == "Maize"

    # List crops
    res_list = client.get(f"/api/v1/farms/{farm_id}/crops")
    assert res_list.status_code == 200
    records = res_list.json()
    assert len(records) == 1

    res_update = client.put(
        f"/api/v1/farms/{farm_id}/crops/{record_id}",
        json={"status": "growing", "notes": "Updated in test"},
    )
    assert res_update.status_code == 200
    assert res_update.json()["status"] == "growing"
    assert res_update.json()["notes"] == "Updated in test"

    # Delete crop
    res_del = client.delete(f"/api/v1/farms/{farm_id}/crops/{record_id}")
    assert res_del.status_code == 200
    assert client.get(f"/api/v1/farms/{farm_id}/crops").json() == []


def test_assistant_chat_multilingual():
    # English
    en_res = client.post(
        "/api/v1/assistant/chat",
        json={
            "session_id": "test-session-1",
            "message": "My farm is in Peshawar and has 15 acres with canal irrigation",
            "language": "en",
        },
    )
    assert en_res.status_code == 200
    en_data = en_res.json()
    assert "total_area_hectares" in en_data["extracted_farm"]
    assert en_data["extracted_farm"]["irrigation_source"] == "canal"

    # Urdu
    ur_res = client.post(
        "/api/v1/assistant/chat",
        json={
            "session_id": "test-session-2",
            "message": "میرا فارم پشاور میں ہے اور نہر کا پانی ہے",
            "language": "ur",
        },
    )
    assert ur_res.status_code == 200
    ur_data = ur_res.json()
    assert ur_data["language"] == "ur"
    assert ur_data["extracted_farm"]["irrigation_source"] == "canal"
