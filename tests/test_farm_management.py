"""Module 01 Verification Suite: Farm Management & Location Intelligence.

Verifies:
1. GET /api/v1/farms lists pre-seeded Peshawar demo parcels.
2. GET /api/v1/farms/{farm_id} retrieves specific farm profile.
3. POST /api/v1/farms creates a new farm parcel with schema validation.
4. PUT /api/v1/farms/{farm_id} updates farm attributes.
5. POST /api/v1/farms/{farm_id}/crop-history appends historical cropping records.
6. DELETE /api/v1/farms/{farm_id} safely removes a parcel.
"""

import httpx
import pytest
from httpx import ASGITransport

from backend.app.main import app
from backend.app.schemas.farm import FarmProfile


@pytest.mark.asyncio
async def test_list_farms_returns_seeded_peshawar_parcels():
    """Verify pre-seeded farms in Peshawar Valley are listed."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/farms")
        assert resp.status_code == 200
        farms = resp.json()
        assert len(farms) >= 2
        farm_ids = [f["farm_id"] for f in farms]
        assert "farm-peshawar-001" in farm_ids
        assert "farm-peshawar-002" in farm_ids


@pytest.mark.asyncio
async def test_get_farm_by_id():
    """Verify retrieving specific farm by ID."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/farms/farm-peshawar-001")
        assert resp.status_code == 200
        data = resp.json()
        farm = FarmProfile.model_validate(data)
        assert farm.farm_id == "farm-peshawar-001"
        assert farm.latitude == 34.0151
        assert farm.soil_type == "sandy"
        assert len(farm.crop_history) >= 2


@pytest.mark.asyncio
async def test_create_update_and_delete_farm_lifecycle():
    """Verify full CRUD lifecycle for farm registration."""
    transport = ASGITransport(app=app)
    new_farm = {
        "farm_id": "farm-lifecycle-test-01",
        "farm_name": "Charsadda Citrus & Wheat Parcel",
        "latitude": 34.1485,
        "longitude": 71.7406,
        "area_value": 7.5,
        "area_unit": "acres",
        "soil_type": "clay_loam",
        "irrigation_type": "tube_well",
        "water_availability": "medium",
        "current_crop": "wheat",
        "season": "Rabi",
        "crop_history": [],
    }

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create
        res_create = await client.post("/api/v1/farms", json=new_farm)
        assert res_create.status_code == 201
        created = res_create.json()
        assert created["farm_id"] == "farm-lifecycle-test-01"

        # 2. Add Crop History
        new_entry = {
            "entry_id": "hist-new-1",
            "crop_name": "sugarcane",
            "season": "Annual",
            "year": 2022,
            "yield_value": 650.0,
            "yield_unit": "maunds/acre",
            "notes": "Excellent harvest",
        }
        res_hist = await client.post(
            "/api/v1/farms/farm-lifecycle-test-01/crop-history", json=new_entry
        )
        assert res_hist.status_code == 200
        hist_data = res_hist.json()
        assert len(hist_data["crop_history"]) == 1
        assert hist_data["crop_history"][0]["crop_name"] == "sugarcane"

        # 3. Update
        updated_payload = dict(new_farm)
        updated_payload["water_availability"] = "high"
        res_upd = await client.put(
            "/api/v1/farms/farm-lifecycle-test-01", json=updated_payload
        )
        assert res_upd.status_code == 200
        assert res_upd.json()["water_availability"] == "high"

        # 4. Delete
        res_del = await client.delete("/api/v1/farms/farm-lifecycle-test-01")
        assert res_del.status_code == 200
        assert res_del.json()["status"] == "deleted"

        # Verify not found after deletion
        res_get = await client.get("/api/v1/farms/farm-lifecycle-test-01")
        assert res_get.status_code == 404
