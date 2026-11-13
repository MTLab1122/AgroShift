"""Phase 2 Verification Gate Test Suite for NASA POWER Daily API Client.

Confirms:
1. Invalid coordinates fail strictly pre-network with zero external HTTP calls.
2. Valid Peshawar coordinates (34.0151, 71.5249) fetch real NASA POWER JSON.
3. Second identical call serves directly from cache (is_cached=True).
4. Resilient retry on transient 5xx responses.
5. Upstream timeout cleanly maps to canonical ApiError.
"""

import asyncio
from unittest.mock import AsyncMock, patch
import httpx
import pytest

from backend.app.modules.nasa_data.power_client import (
    InMemoryTtlCache,
    NasaPowerClient,
    NasaPowerClientError,
)
from backend.app.modules.nasa_data.schemas import ApiError


@pytest.mark.asyncio
async def test_invalid_coordinates_fail_pre_network():
    """Ensure invalid coordinates fail fast with zero network calls."""
    client = NasaPowerClient()

    # Spy on _execute_request_with_retries to ensure it is NEVER called
    with patch.object(client, "_execute_request_with_retries", new_callable=AsyncMock) as mock_exec:
        with pytest.raises(NasaPowerClientError) as excinfo:
            await client.fetch_daily_point(
                farm_id="farm-peshawar-001",
                latitude=999.0,  # Invalid latitude
                longitude=71.5249,
                start_date="2024-05-01",
                end_date="2024-05-05",
            )
        assert excinfo.value.api_error.error_code == "INVALID_COORDINATES"
        assert excinfo.value.status_code == 422
        # Crucial check: Zero network calls made
        mock_exec.assert_not_called()


@pytest.mark.asyncio
async def test_invalid_dates_fail_pre_network():
    """Ensure inverted dates fail pre-network without dispatching HTTP calls."""
    client = NasaPowerClient()

    with patch.object(client, "_execute_request_with_retries", new_callable=AsyncMock) as mock_exec:
        with pytest.raises(NasaPowerClientError) as excinfo:
            await client.fetch_daily_point(
                farm_id="farm-peshawar-001",
                latitude=34.0151,
                longitude=71.5249,
                start_date="2024-05-10",
                end_date="2024-05-01",  # Inverted
            )
        assert excinfo.value.api_error.error_code == "INVALID_DATE_RANGE"
        mock_exec.assert_not_called()


@pytest.mark.asyncio
async def test_live_peshawar_fetch_and_subsequent_cache_hit():
    """Verify live fetch for Peshawar coordinates and verify deterministic caching."""
    client = NasaPowerClient(timeout=25.0)

    # Call 1: Live call to NASA POWER for short 3-day test range
    res1 = await client.fetch_daily_point(
        farm_id="farm-peshawar-001",
        latitude=34.0151,
        longitude=71.5249,
        start_date="2024-05-01",
        end_date="2024-05-03",
        parameters=["T2M", "PRECTOTCORR"],
    )

    assert res1["is_cached"] is False
    assert "raw_data" in res1
    raw = res1["raw_data"]
    assert "properties" in raw
    assert "parameter" in raw["properties"]
    assert "T2M" in raw["properties"]["parameter"]
    assert "PRECTOTCORR" in raw["properties"]["parameter"]
    # Check date keys in response: 20240501, 20240502, 20240503
    t2m_vals = raw["properties"]["parameter"]["T2M"]
    assert "20240501" in t2m_vals

    # Call 2: Identical call must be served from cache
    res2 = await client.fetch_daily_point(
        farm_id="farm-peshawar-001",
        latitude=34.0151,
        longitude=71.5249,
        start_date="2024-05-01",
        end_date="2024-05-03",
        parameters=["T2M", "PRECTOTCORR"],
    )

    assert res2["is_cached"] is True
    assert res2["raw_data"] == res1["raw_data"]
    assert res2["cache_key"] == res1["cache_key"]


@pytest.mark.asyncio
async def test_retry_on_transient_upstream_500():
    """Verify exponential backoff retry succeeds when upstream temporarily fails."""
    client = NasaPowerClient(max_retries=3, backoff_base=0.05)

    attempts = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            return httpx.Response(500, text="Internal Server Error")
        return httpx.Response(
            200,
            json={"properties": {"parameter": {"T2M": {"20240501": 25.0}}}},
        )

    transport = httpx.MockTransport(mock_handler)

    # Patch httpx.AsyncClient to use our mock transport
    original_client = httpx.AsyncClient

    def get_mock_client(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    with patch("httpx.AsyncClient", side_effect=get_mock_client):
        result = await client.fetch_daily_point(
            farm_id="farm-test",
            latitude=34.0151,
            longitude=71.5249,
            start_date="2024-05-01",
            end_date="2024-05-01",
            parameters=["T2M"],
            bypass_cache=True,
        )
        assert result["raw_data"]["properties"]["parameter"]["T2M"]["20240501"] == 25.0
        assert attempts == 2


@pytest.mark.asyncio
async def test_upstream_timeout_translation_to_api_error():
    """Verify timeouts are mapped to structured UPSTREAM_TIMEOUT ApiError."""
    client = NasaPowerClient(timeout=0.01, max_retries=2, backoff_base=0.01)

    def mock_timeout_handler(request: httpx.Request):
        raise httpx.ReadTimeout("Socket read timed out")

    transport = httpx.MockTransport(mock_timeout_handler)
    original_client = httpx.AsyncClient

    def get_mock_client(*args, **kwargs):
        kwargs["transport"] = transport
        return original_client(*args, **kwargs)

    with patch("httpx.AsyncClient", side_effect=get_mock_client):
        with pytest.raises(NasaPowerClientError) as excinfo:
            await client.fetch_daily_point(
                farm_id="farm-test",
                latitude=34.0151,
                longitude=71.5249,
                start_date="2024-05-01",
                end_date="2024-05-01",
                parameters=["T2M"],
                bypass_cache=True,
            )
        assert excinfo.value.api_error.error_code == "UPSTREAM_TIMEOUT"
        assert excinfo.value.status_code == 504
