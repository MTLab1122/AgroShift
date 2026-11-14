"""Phase 4 Verification Gate Test Suite: Recommendation Pipeline & Live NASA Comparator.

Verifies:
1. POST /api/v1/recommendations/generate with mock demo data produces canonical RecommendationSet.
2. POST /api/v1/recommendations/generate with live NASA POWER fetch produces real grounded comparisons.
3. POST /api/v1/analyze-farm alias endpoint functions identically.
4. All 3 scenarios (baseline, pulse_inclusive, soil_cover) are generated with composite scores and breakdowns.
5. Injected invalid farm profile coordinates fail with canonical ApiError.
6. JSON schema validation against shared/schemas/recommendation.schema.json.
"""

import json
from pathlib import Path
import httpx
from jsonschema import validate
import pytest
from httpx import ASGITransport

from backend.app.main import app
from backend.app.schemas.recommendation import RecommendationSet

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.asyncio
async def test_recommendations_generate_endpoint_demo_mode():
    """Verify POST /api/v1/recommendations/generate in demo mode produces valid RecommendationSet."""
    transport = ASGITransport(app=app)
    farm_payload = {
        "farm_id": "farm-peshawar-001",
        "farm_name": "Tariq Khan Barani Parcel",
        "latitude": 34.0151,
        "longitude": 71.5249,
        "area_value": 4.0,
        "area_unit": "acres",
        "soil_type": "sandy",
        "irrigation_type": "rain_fed",
        "water_availability": "low",
        "current_crop": "wheat",
        "season": "Rabi",
        "crop_history": [
            {
                "entry_id": "hist-1",
                "crop_name": "maize",
                "season": "Kharif",
                "year": 2023,
                "yield_value": 35.0,
                "yield_unit": "maunds/acre",
                "notes": "Low rainfall",
            }
        ],
    }

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/recommendations/generate",
            json=farm_payload,
            params={"demo": True, "start_date": "2024-05-01", "end_date": "2024-10-31"},
        )
        assert resp.status_code == 200
        data = resp.json()

        # Validate with Pydantic model
        rec_set = RecommendationSet.model_validate(data)
        assert rec_set.farm_id == "farm-peshawar-001"
        assert rec_set.scenarios.baseline is not None
        assert rec_set.scenarios.pulse_inclusive is not None
        assert rec_set.scenarios.soil_cover is not None
        assert rec_set.farm_vs_nasa_comparison is not None
        assert rec_set.farm_vs_nasa_comparison.expected_crop_water_need_mm == 400.0

        # Validate with JSON schema
        schema_path = WORKSPACE_ROOT / "shared" / "schemas" / "recommendation.schema.json"
        with open(schema_path, "r", encoding="utf-8") as f:
            rec_schema = json.load(f)
        validate(instance=data, schema=rec_schema)


@pytest.mark.asyncio
async def test_recommendations_generate_endpoint_live_nasa_mode():
    """Verify POST /api/v1/recommendations/generate retrieves live NASA data and produces comparison."""
    transport = ASGITransport(app=app)
    farm_payload = {
        "farm_id": "farm-peshawar-live",
        "farm_name": "Peshawar Live Investigation Parcel",
        "latitude": 34.0151,
        "longitude": 71.5249,
        "area_value": 5.0,
        "area_unit": "acres",
        "soil_type": "loamy",
        "irrigation_type": "canal",
        "water_availability": "high",
        "current_crop": "wheat",
        "season": "Rabi",
        "crop_history": [],
    }

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/recommendations/generate",
            json=farm_payload,
            params={"demo": False, "start_date": "2024-05-01", "end_date": "2024-05-03"},
        )
        assert resp.status_code == 200
        data = resp.json()

        rec_set = RecommendationSet.model_validate(data)
        assert rec_set.farm_id == "farm-peshawar-live"
        assert rec_set.farm_vs_nasa_comparison is not None
        # Observed rainfall from live NASA probe for May 1-3 is 1.03 mm
        assert rec_set.farm_vs_nasa_comparison.observed_rainfall_mm >= 1.0
        assert rec_set.farm_vs_nasa_comparison.data_mode == "live"
        assert rec_set.farm_vs_nasa_comparison.water_balance_status == "balanced"

        # Check score breakdown
        pulse_scen = rec_set.scenarios.pulse_inclusive
        assert pulse_scen.score > 0.0
        assert pulse_scen.score_breakdown.climate_suitability > 0.0
        assert pulse_scen.score_breakdown.water_efficiency > 0.0


@pytest.mark.asyncio
async def test_analyze_farm_alias_endpoint():
    """Verify POST /api/v1/analyze-farm functions as alias endpoint."""
    transport = ASGITransport(app=app)
    farm_payload = {
        "farm_id": "farm-alias-check",
        "farm_name": "Alias Test Parcel",
        "latitude": 34.0151,
        "longitude": 71.5249,
        "area_value": 2.5,
        "area_unit": "acres",
        "soil_type": "clay_loam",
        "irrigation_type": "tube_well",
        "water_availability": "medium",
        "current_crop": "maize",
        "season": "Kharif",
        "crop_history": [],
    }

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/analyze-farm",
            json=farm_payload,
            params={"demo": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        rec_set = RecommendationSet.model_validate(data)
        assert rec_set.farm_id == "farm-alias-check"
        assert rec_set.scenarios.baseline.crop_sequence[0] == "maize"


@pytest.mark.asyncio
async def test_recommendations_generate_rejects_invalid_coordinates():
    """Verify endpoint rejects invalid latitude > 90 with canonical ApiError."""
    transport = ASGITransport(app=app)
    bad_payload = {
        "farm_id": "farm-bad-lat",
        "farm_name": "Bad Coordinates Parcel",
        "latitude": 150.0,  # Invalid
        "longitude": 71.5249,
        "area_value": 5.0,
        "area_unit": "acres",
        "soil_type": "loamy",
        "irrigation_type": "canal",
        "water_availability": "high",
        "current_crop": "wheat",
        "season": "Rabi",
        "crop_history": [],
    }

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/recommendations/generate",
            json=bad_payload,
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["error_code"] == "INVALID_COORDINATES"
        assert "latitude" in data["message"].lower()
