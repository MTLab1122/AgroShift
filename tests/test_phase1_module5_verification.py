"""Phase 1 Verification Gate Test Suite for Module 05: Integration, Security & Gateway.

Verifies:
1. GET /api/v1/health reports per-module readiness, schemas, and diagnostics.
2. RequestTracingMiddleware injects X-Request-ID and X-Response-Time-Ms on all responses.
3. Preserves custom incoming X-Request-ID headers across request lifecycle.
4. ApiError responses contain matching request_id and X-Request-ID header.
5. Smart Gateway injects X-AgroShift-Data-Mode: live, demo-forced, and demo-fallback.
6. Simulated NASA 503 triggers transparent demo-fallback with is_demo_data=True.
7. Canonical schemas in shared/schemas/ are valid JSON Schema specifications.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch
import httpx
from httpx import ASGITransport
from jsonschema import Draft202012Validator
import pytest

from backend.app.core.gateway import HEADER_DATA_MODE, DataMode, gateway
from backend.app.main import app
from backend.app.modules.nasa_data.power_client import (
    NasaPowerClient,
    NasaPowerClientError,
)
from backend.app.modules.nasa_data.schemas import ApiError, ClimateSummary

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.asyncio
async def test_api_v1_health_deep_diagnostics():
    """Verify /api/v1/health returns complete 5-module readiness and diagnostics."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert "modules" in data

        modules = data["modules"]
        assert "module_01_farm" in modules
        assert modules["module_01_farm"]["owner"] == "Sana Jalal"

        assert "module_02_nasa" in modules
        assert modules["module_02_nasa"]["owner"] == "Muhammad Talha"

        assert "module_03_agro" in modules
        assert modules["module_03_agro"]["owner"] == "Hira Dawood"

        assert "module_04_analytics" in modules
        assert modules["module_04_analytics"]["owner"] == "Aqsa Faisal"

        assert "module_05_integration" in modules
        assert modules["module_05_integration"]["owner"] == "Sudais Ahmad"
        assert modules["module_05_integration"]["demo_fallback_available"] is True

        assert "diagnostics" in data
        assert len(data["diagnostics"]["canonical_schemas"]) == 4


@pytest.mark.asyncio
async def test_request_id_middleware_injection():
    """Verify X-Request-ID and X-Response-Time-Ms headers are injected on responses."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert "X-Request-ID" in resp.headers
        assert resp.headers["X-Request-ID"].startswith("req-")
        assert "X-Response-Time-Ms" in resp.headers
        float(resp.headers["X-Response-Time-Ms"])  # Must be numeric


@pytest.mark.asyncio
async def test_preserves_custom_incoming_request_id():
    """Verify incoming client X-Request-ID is preserved throughout the pipeline."""
    custom_trace_id = "trace-custom-judge-999"
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health", headers={"X-Request-ID": custom_trace_id})
        assert resp.status_code == 200
        assert resp.headers["X-Request-ID"] == custom_trace_id


@pytest.mark.asyncio
async def test_apierror_matches_request_id_header():
    """Verify validation error populates matching request_id in body and header."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/climate/summary",
            params={
                "farm_id": "farm-test",
                "latitude": 999.0,  # Invalid
                "longitude": 71.5249,
                "start_date": "2024-05-01",
                "end_date": "2024-05-05",
            },
        )
        assert resp.status_code == 422
        assert "X-Request-ID" in resp.headers
        hdr_id = resp.headers["X-Request-ID"]

        data = resp.json()
        api_err = ApiError.model_validate(data)
        assert api_err.request_id == hdr_id
        assert api_err.error_code == "INVALID_COORDINATES"


@pytest.mark.asyncio
async def test_gateway_data_mode_header_demo_forced():
    """Verify forced demo returns X-AgroShift-Data-Mode: demo-forced."""
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
        assert resp.headers.get(HEADER_DATA_MODE) == DataMode.DEMO_FORCED.value
        summary = ClimateSummary.model_validate(resp.json())
        assert summary.is_demo_data is True


@pytest.mark.asyncio
async def test_gateway_transparent_fallback_on_upstream_nasa_outage():
    """Verify gateway transparently falls back to demo fixture on simulated NASA 503 outage."""
    from backend.app.modules.nasa_data.router import power_client

    # Simulate upstream NASA POWER outage (HTTP 503)
    outage_error = NasaPowerClientError(
        api_error=ApiError(
            error_code="NASA_POWER_UNAVAILABLE",
            message="Simulated upstream NASA outage for testing gateway fallback.",
        ),
        status_code=503,
    )

    with patch.object(power_client, "_execute_request_with_retries", side_effect=outage_error):
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
                    "demo": False,  # Request live
                },
            )

            # Gateway should have caught 503 and returned 200 OK with demo fallback
            assert resp.status_code == 200
            assert resp.headers.get(HEADER_DATA_MODE) == DataMode.DEMO_FALLBACK.value
            assert resp.headers.get("X-AgroShift-Fallback-Reason") == "NASA_POWER_UNAVAILABLE"

            summary = ClimateSummary.model_validate(resp.json())
            assert summary.is_demo_data is True
            assert "[FALLBACK DEMO MODE]" in summary.coverage_note


def test_shared_schemas_are_valid_json_schema():
    """Ensure all shared schemas are valid JSON Schema Draft 2020-12 specifications."""
    schemas_dir = WORKSPACE_ROOT / "shared" / "schemas"
    schema_files = ["climate.schema.json", "farm.schema.json", "recommendation.schema.json", "error.schema.json"]

    for sf in schema_files:
        path = schemas_dir / sf
        assert path.is_file(), f"Missing schema file: {path}"
        with open(path, "r", encoding="utf-8") as f:
            schema = json.load(f)
        # Check that validator can compile the schema without raising SchemaError
        Draft202012Validator.check_schema(schema)
