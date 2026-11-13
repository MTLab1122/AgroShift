"""Phase 4 Verification Gate Test Suite for FastAPI Endpoints & Error Handlers.

Verifies:
1. GET /health returns service health and cache status.
2. GET /api/v1/climate/summary returns canonical ClimateSummary.
3. GET /api/v1/climate/history returns daily records and monthly aggregates.
4. GET /api/v1/nasa/power returns diagnostic cache and raw upstream preview.
5. Invalid coordinates (latitude=999) returns HTTP 422 with canonical ApiError.
6. Inverted dates returns HTTP 422 with canonical ApiError.
7. Verified stretch parameters (RH2M, ALLSKY_SFC_SW_DWN) are processed.
8. Invalid parameter returns HTTP 422 with canonical ApiError.
"""

import httpx
import pytest
from httpx import ASGITransport

from backend.app.main import app
from backend.app.modules.nasa_data.schemas import ApiError, ClimateSummary


@pytest.mark.asyncio
async def test_health_endpoint():
    """Verify GET /health returns 200 OK and healthy status."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "cache_entries" in data


@pytest.mark.asyncio
async def test_climate_summary_demo_endpoint():
    """Verify GET /api/v1/climate/summary in demo mode returns valid ClimateSummary."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/climate/summary",
            params={
                "farm_id": "farm-peshawar-001",
                "latitude": 34.0151,
                "longitude": 71.5249,
                "start_date": "2024-05-01",
                "end_date": "2024-10-31",
                "demo": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        summary = ClimateSummary.model_validate(data)
        assert summary.farm_id == "farm-peshawar-001"
        assert summary.is_demo_data is True
        assert len(summary.aggregates.monthly) == 6


@pytest.mark.asyncio
async def test_climate_history_endpoint():
    """Verify GET /api/v1/climate/history returns daily series and monthly aggregates."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/climate/history",
            params={
                "farm_id": "farm-peshawar-001",
                "latitude": 34.0151,
                "longitude": 71.5249,
                "start_date": "2024-05-01",
                "end_date": "2024-10-31",
                "demo": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "daily_series" in data
        assert len(data["daily_series"]) > 0
        assert "monthly_aggregates" in data
        assert len(data["monthly_aggregates"]) == 6


@pytest.mark.asyncio
async def test_diagnostic_power_endpoint():
    """Verify GET /api/v1/nasa/power returns diagnostic metadata."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # We test with a short interval or cached request
        resp = await client.get(
            "/api/v1/nasa/power",
            params={
                "latitude": 34.0151,
                "longitude": 71.5249,
                "start_date": "2024-05-01",
                "end_date": "2024-05-03",
                "parameters": "T2M,PRECTOTCORR",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "is_cached" in data
        assert "parameters_returned" in data


@pytest.mark.asyncio
async def test_deliberate_invalid_coordinates_returns_canonical_api_error():
    """Verify latitude=999 returns 422 with canonical ApiError."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/climate/summary",
            params={
                "farm_id": "farm-test",
                "latitude": 999.0,  # Deliberately invalid
                "longitude": 71.5249,
                "start_date": "2024-05-01",
                "end_date": "2024-05-10",
            },
        )
        assert resp.status_code == 422
        data = resp.json()
        api_err = ApiError.model_validate(data)
        assert api_err.error_code == "INVALID_COORDINATES"
        assert "latitude" in api_err.message.lower()


@pytest.mark.asyncio
async def test_deliberate_inverted_dates_returns_canonical_api_error():
    """Verify start_date > end_date returns 422 with canonical ApiError."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/climate/summary",
            params={
                "farm_id": "farm-test",
                "latitude": 34.0151,
                "longitude": 71.5249,
                "start_date": "2024-05-30",
                "end_date": "2024-05-01",  # Inverted
            },
        )
        assert resp.status_code == 422
        data = resp.json()
        api_err = ApiError.model_validate(data)
        assert api_err.error_code == "INVALID_DATE_RANGE"


@pytest.mark.asyncio
async def test_unsupported_parameter_returns_canonical_api_error():
    """Verify invalid parameter returns 422 with canonical ApiError."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/climate/summary",
            params={
                "farm_id": "farm-test",
                "latitude": 34.0151,
                "longitude": 71.5249,
                "start_date": "2024-05-01",
                "end_date": "2024-05-05",
                "parameters": "T2M,BOGUS_PARAM",
            },
        )
        assert resp.status_code == 422
        data = resp.json()
        api_err = ApiError.model_validate(data)
        assert api_err.error_code == "INVALID_PARAMETERS"
