"""Comprehensive Acceptance Test Suite for Module 02: NASA Earth Observation & Climate Data Engine.

Validates the full Module 02 Acceptance Checklist from the AgroShift Architecture Specification:
1. Valid coordinates and dates are required; invalid requests fail before network access.
2. Parameter labels and units match source documentation.
3. No missing value is silently changed to 0 (strict null mapping for -999).
4. The same request is served from cache when appropriate.
5. Response includes source, product, coordinates, dates, retrieved_at and coverage note.
6. A network/API failure is shown as unavailable (ApiError), never disguised as live data.
"""

from unittest.mock import AsyncMock, patch
import httpx
import pytest
from httpx import ASGITransport

from backend.app.main import app
from backend.app.modules.nasa_data.normalizer import (
    VERIFIED_PARAMETERS,
    normalize_power_response,
)
from backend.app.modules.nasa_data.power_client import (
    InMemoryTtlCache,
    NasaPowerClient,
    NasaPowerClientError,
)
from backend.app.modules.nasa_data.schemas import (
    ApiError,
    ClimateRequest,
    ClimateSummary,
    DailyRecord,
)


# ==============================================================================
# Checklist Item 1: Valid coordinates & dates required; invalid requests fail before network
# ==============================================================================
@pytest.mark.asyncio
async def test_acceptance_criteria_1_pre_network_validation():
    """Verify coordinate and date validation rejects invalid inputs BEFORE any socket call."""
    client = NasaPowerClient()

    with patch.object(client, "_execute_request_with_retries", new_callable=AsyncMock) as mock_http:
        # Invalid Latitude: 95.0
        with pytest.raises(NasaPowerClientError) as exc_lat:
            await client.fetch_daily_point(
                farm_id="farm-test",
                latitude=95.0,
                longitude=71.5249,
                start_date="2024-05-01",
                end_date="2024-05-10",
            )
        assert exc_lat.value.api_error.error_code == "INVALID_COORDINATES"
        mock_http.assert_not_called()

        # Invalid Longitude: 185.0
        with pytest.raises(NasaPowerClientError) as exc_lon:
            await client.fetch_daily_point(
                farm_id="farm-test",
                latitude=34.0151,
                longitude=185.0,
                start_date="2024-05-01",
                end_date="2024-05-10",
            )
        assert exc_lon.value.api_error.error_code == "INVALID_COORDINATES"
        mock_http.assert_not_called()

        # Inverted Dates: start > end
        with pytest.raises(NasaPowerClientError) as exc_date:
            await client.fetch_daily_point(
                farm_id="farm-test",
                latitude=34.0151,
                longitude=71.5249,
                start_date="2024-05-15",
                end_date="2024-05-01",
            )
        assert exc_date.value.api_error.error_code == "INVALID_DATE_RANGE"
        mock_http.assert_not_called()

        # Date before 1981 archive start
        with pytest.raises(NasaPowerClientError) as exc_arch:
            await client.fetch_daily_point(
                farm_id="farm-test",
                latitude=34.0151,
                longitude=71.5249,
                start_date="1979-01-01",
                end_date="1979-01-10",
            )
        assert exc_arch.value.api_error.error_code == "INVALID_DATE_RANGE"
        mock_http.assert_not_called()


# ==============================================================================
# Checklist Item 2: Parameter labels and units match source documentation
# ==============================================================================
def test_acceptance_criteria_2_parameter_labels_and_units():
    """Verify verified parameters have exact scientific units and documented labels."""
    assert VERIFIED_PARAMETERS["T2M"]["unit"] == "°C"
    assert "Temperature" in VERIFIED_PARAMETERS["T2M"]["label"]

    assert VERIFIED_PARAMETERS["PRECTOTCORR"]["unit"] == "mm/day"
    assert "Precipitation" in VERIFIED_PARAMETERS["PRECTOTCORR"]["label"]

    assert VERIFIED_PARAMETERS["RH2M"]["unit"] == "%"
    assert "Humidity" in VERIFIED_PARAMETERS["RH2M"]["label"]

    assert VERIFIED_PARAMETERS["ALLSKY_SFC_SW_DWN"]["unit"] == "MJ/m^2/day"
    assert "Irradiance" in VERIFIED_PARAMETERS["ALLSKY_SFC_SW_DWN"]["label"]


# ==============================================================================
# Checklist Item 3: No missing value is silently changed to 0
# ==============================================================================
def test_acceptance_criteria_3_missing_data_integrity_no_zero_fabrication():
    """Verify NASA fill values (-999, -999.0) map strictly to None and never to 0.0."""
    raw_payload = {
        "properties": {
            "parameter": {
                "T2M": {"20240501": 25.0, "20240502": -999.0, "20240503": 0.0},
                "PRECTOTCORR": {"20240501": -999.0, "20240502": 0.0, "20240503": 15.0},
            }
        }
    }

    params, daily_records, missing_data = normalize_power_response(
        raw_payload=raw_payload,
        start_date="2024-05-01",
        end_date="2024-05-03",
    )

    # Day 1
    assert daily_records[0].values["T2M"] == 25.0
    assert daily_records[0].values["PRECTOTCORR"] is None  # -999.0 became None

    # Day 2
    assert daily_records[1].values["T2M"] is None  # -999.0 became None
    assert daily_records[1].values["PRECTOTCORR"] == 0.0  # true 0 preserved

    # Day 3
    assert daily_records[2].values["T2M"] == 0.0  # true freezing 0 preserved
    assert daily_records[2].values["PRECTOTCORR"] == 15.0

    # Missing counts
    assert missing_data.missing_days_by_parameter["T2M"] == 1
    assert missing_data.missing_days_by_parameter["PRECTOTCORR"] == 1
    assert missing_data.has_gaps is True


# ==============================================================================
# Checklist Item 4: The same request can be served from cache when appropriate
# ==============================================================================
@pytest.mark.asyncio
async def test_acceptance_criteria_4_caching_behavior():
    """Verify deterministic cache hit on repeated identical requests."""
    cache = InMemoryTtlCache(default_ttl=3600)
    client = NasaPowerClient(cache=cache)

    mock_resp = {
        "properties": {
            "parameter": {
                "T2M": {"20240501": 30.5},
                "PRECTOTCORR": {"20240501": 0.0},
            }
        }
    }

    with patch.object(
        client, "_execute_request_with_retries", new_callable=AsyncMock, return_value=mock_resp
    ) as mock_http:
        # Request 1: cache miss
        r1 = await client.fetch_daily_point(
            farm_id="farm-peshawar-001",
            latitude=34.0151,
            longitude=71.5249,
            start_date="2024-05-01",
            end_date="2024-05-01",
            parameters=["T2M", "PRECTOTCORR"],
        )
        assert r1["is_cached"] is False
        assert mock_http.call_count == 1

        # Request 2: identical parameters -> must be served from cache
        r2 = await client.fetch_daily_point(
            farm_id="farm-peshawar-001",
            latitude=34.0151,
            longitude=71.5249,
            start_date="2024-05-01",
            end_date="2024-05-01",
            parameters=["T2M", "PRECTOTCORR"],
        )
        assert r2["is_cached"] is True
        assert r2["raw_data"] == r1["raw_data"]
        # Crucial check: HTTP call count remained 1
        assert mock_http.call_count == 1


# ==============================================================================
# Checklist Item 5: Response includes source, product, coordinates, dates, retrieved_at, coverage_note
# ==============================================================================
@pytest.mark.asyncio
async def test_acceptance_criteria_5_provenance_and_metadata():
    """Verify complete provenance fields in the ClimateSummary API response."""
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
        summary = resp.json()

        assert summary["source"] != ""
        assert summary["product_or_dataset"] != ""
        assert summary["latitude"] == 34.0151
        assert summary["longitude"] == 71.5249
        assert summary["start_date"] == "2024-05-01"
        assert summary["end_date"] == "2024-10-31"
        assert "retrieved_at" in summary
        assert "coverage_note" in summary
        assert "gridded" in summary["coverage_note"].lower()
        assert len(summary["parameters"]) >= 2
        assert len(summary["aggregates"]["monthly"]) > 0
        assert len(summary["aggregates"]["seasonal"]) > 0


# ==============================================================================
# Checklist Item 6: Network/API failure shown as unavailable, never disguised as live data
# ==============================================================================
@pytest.mark.asyncio
async def test_acceptance_criteria_6_network_failure_is_api_error_never_synthetic():
    """Verify network failures or timeouts return structured ApiError and never invent synthetic data."""
    client = NasaPowerClient(timeout=1.0, max_retries=1)

    with patch.object(
        client,
        "_execute_request_with_retries",
        side_effect=NasaPowerClientError(
            api_error=ApiError(
                error_code="NASA_POWER_UNAVAILABLE",
                message="NASA POWER API connection failed.",
                details={"host": "power.larc.nasa.gov"},
            ),
            status_code=503,
        ),
    ):
        with pytest.raises(NasaPowerClientError) as exc_info:
            await client.fetch_daily_point(
                farm_id="farm-peshawar-001",
                latitude=34.0151,
                longitude=71.5249,
                start_date="2024-05-01",
                end_date="2024-05-05",
                bypass_cache=True,
            )

        err = exc_info.value.api_error
        assert err.error_code == "NASA_POWER_UNAVAILABLE"
        assert exc_info.value.status_code == 503
        assert "NASA POWER API connection failed" in err.message
