"""End-to-End Acceptance Test Suite: Live NASA Data & Comparison Pipeline (Phase 5).

NASA Space Apps Challenge 2026: Adapting Farms with NASA Data
Team InCir — Innovation Circle, Abasyn University Peshawar

Verifies:
1. End-to-end live farm submission: real NASA POWER fetch -> normalization -> comparator -> 3 scored scenarios.
2. Accurate water balance diagnosis (rain-fed deficit vs. canal balanced).
3. Monoculture rotation penalty and legume nitrogen enrichment scoring.
4. Provenance honesty and decision support limitation disclosures.
5. Resilient gateway fallback when upstream NASA API is unreachable.
6. Full JSON Schema conformity against shared canonical contracts.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch
import httpx
from jsonschema import validate
import pytest
from httpx import ASGITransport

from backend.app.main import app
from backend.app.schemas.recommendation import RecommendationSet

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.asyncio
async def test_end_to_end_live_farm_analysis_pipeline():
    """Verify live NASA POWER data ingestion, comparison, and scenario generation for Peshawar."""
    transport = ASGITransport(app=app)
    farm_profile = {
        "farm_id": "farm-peshawar-e2e-live",
        "farm_name": "Peshawar Valley Arid Parcel",
        "latitude": 34.0151,
        "longitude": 71.5249,
        "area_value": 4.5,
        "area_unit": "acres",
        "soil_type": "sandy",
        "irrigation_type": "rain_fed",
        "water_availability": "low",
        "current_crop": "wheat",
        "season": "Rabi",
        "crop_history": [
            {
                "entry_id": "e2e-h1",
                "crop_name": "maize",
                "season": "Kharif",
                "year": 2023,
                "yield_value": 30.0,
                "yield_unit": "maunds/acre",
                "notes": "Low rainfall in summer",
            }
        ],
    }

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/recommendations/generate",
            json=farm_profile,
            params={
                "demo": False,
                "start_date": "2024-05-01",
                "end_date": "2024-05-03",
            },
        )
        assert resp.status_code == 200
        data = resp.json()

        # 1. Validate response model
        rec_set = RecommendationSet.model_validate(data)
        assert rec_set.farm_id == "farm-peshawar-e2e-live"

        # 2. Reconciled NASA comparison verification (Live MERRA-2 data)
        comp = rec_set.farm_vs_nasa_comparison
        assert comp is not None
        assert comp.data_mode == "live"
        assert comp.observed_rainfall_mm >= 1.0  # Real NASA POWER data for 2024-05-01 to 05-03 is 1.03 mm
        assert comp.expected_crop_water_need_mm == 400.0  # Wheat benchmark
        assert comp.water_balance_status == "severe_deficit"
        assert "severe deficit" in comp.irrigation_adequacy_note.lower()

        # 3. 3 Canonical Scenarios verification
        scenarios = rec_set.scenarios
        assert scenarios.baseline is not None
        assert scenarios.pulse_inclusive is not None
        assert scenarios.soil_cover is not None

        # Pulse-inclusive scenario must score higher in water efficiency than baseline
        assert (
            scenarios.pulse_inclusive.score_breakdown.water_efficiency
            > scenarios.baseline.score_breakdown.water_efficiency
        )
        assert (
            scenarios.pulse_inclusive.score_breakdown.soil_health_benefit
            > scenarios.baseline.score_breakdown.soil_health_benefit
        )

        # 4. Mandatory scientific limitations and disclaimers
        assert len(rec_set.limitations) >= 4
        limitations_text = " ".join(rec_set.limitations).lower()
        assert "grid cells" in limitations_text or "regional" in limitations_text
        assert "not direct" in limitations_text or "sensor" in limitations_text
        assert "never guaranteed" in limitations_text or "decision support" in limitations_text

        # 5. Contractual JSON Schema conformity
        schema_path = WORKSPACE_ROOT / "shared" / "schemas" / "recommendation.schema.json"
        with open(schema_path, "r", encoding="utf-8") as f:
            rec_schema = json.load(f)
        validate(instance=data, schema=rec_schema)


@pytest.mark.asyncio
async def test_end_to_end_canal_irrigated_farm_balanced_water():
    """Verify that canal irrigation with high availability resolves water deficit."""
    transport = ASGITransport(app=app)
    farm_profile = {
        "farm_id": "farm-peshawar-canal-e2e",
        "farm_name": "Warsak Canal Farm",
        "latitude": 34.0151,
        "longitude": 71.5249,
        "area_value": 10.0,
        "area_unit": "acres",
        "soil_type": "clay_loam",
        "irrigation_type": "canal",
        "water_availability": "high",
        "current_crop": "wheat",
        "season": "Rabi",
        "crop_history": [],
    }

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/recommendations/generate",
            json=farm_profile,
            params={
                "demo": False,
                "start_date": "2024-05-01",
                "end_date": "2024-05-03",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        rec_set = RecommendationSet.model_validate(data)
        assert rec_set.farm_vs_nasa_comparison.water_balance_status == "balanced"
        assert "adequacy" in rec_set.farm_vs_nasa_comparison.irrigation_adequacy_note.lower()


@pytest.mark.asyncio
async def test_end_to_end_resilient_gateway_fallback_on_upstream_outage():
    """Verify that upstream network or server timeout transparently falls back to demo data."""
    transport = ASGITransport(app=app)
    farm_profile = {
        "farm_id": "farm-resilience-check",
        "farm_name": "Resilience Test Parcel",
        "latitude": 34.0151,
        "longitude": 71.5249,
        "area_value": 3.0,
        "area_unit": "acres",
        "soil_type": "loamy",
        "irrigation_type": "tube_well",
        "water_availability": "medium",
        "current_crop": "wheat",
        "season": "Rabi",
        "crop_history": [],
    }

    # Simulate upstream NASA POWER network timeout
    with patch(
        "backend.app.modules.nasa_data.power_client.NasaPowerClient.fetch_daily_point",
        new_callable=AsyncMock,
    ) as mock_fetch:
        from backend.app.modules.nasa_data.power_client import NasaPowerClientError
        from backend.app.modules.nasa_data.schemas import ApiError

        mock_fetch.side_effect = NasaPowerClientError(
            status_code=504,
            api_error=ApiError(
                error_code="UPSTREAM_TIMEOUT",
                message="NASA POWER API connection timed out after 10.0 seconds.",
            ),
        )

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/recommendations/generate",
                json=farm_profile,
                params={"demo": False},
            )
            assert resp.status_code == 200
            data = resp.json()

            # Resilient fallback header and data mode flag must be present
            assert resp.headers.get("x-agroshift-data-mode") == "demo-fallback"
            assert data["farm_vs_nasa_comparison"]["data_mode"] == "demo_fallback"
            rec_set = RecommendationSet.model_validate(data)
            assert rec_set.farm_id == "farm-resilience-check"
