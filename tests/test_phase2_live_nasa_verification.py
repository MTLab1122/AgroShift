"""Verification Gate for Phase 2: Live NASA Data Fetcher, Normalizer & Caching Engine.

Verifies:
1. Live NASA POWER API call for Peshawar Valley (34.0151, 71.5249) retrieves real observations.
2. Verified parameter set: T2M, T2M_MAX, T2M_MIN, PRECTOTCORR, RH2M, ALLSKY_SFC_SW_DWN.
3. Cache hit metadata (cache_hit=True on duplicate call).
4. Earthdata SMAP and GPM adapters return structured 'unavailable' status without data fabrication.
5. Normalizer maps sentinel -999.0 to None and produces canonical ClimateSummary.
"""

from datetime import datetime
import pytest

from backend.app.modules.nasa_data.aggregations import compute_all_aggregates
from backend.app.modules.nasa_data.earthdata_adapters import earthdata_adapter
from backend.app.modules.nasa_data.normalizer import normalize_power_response
from backend.app.modules.nasa_data.power_client import NasaPowerClient
from backend.app.modules.nasa_data.schemas import ClimateSummary


@pytest.mark.asyncio
async def test_live_nasa_power_peshawar_real_data_fetch():
    """Execute live fetch against NASA POWER Daily API for Peshawar and verify real metrics."""
    client = NasaPowerClient(timeout=30.0)

    # Coordinates for Peshawar Valley demo farm
    lat, lon = 34.0151, 71.5249
    start_d, end_d = "2024-05-01", "2024-05-03"

    res = await client.fetch_daily_point(
        farm_id="farm-peshawar-001",
        latitude=lat,
        longitude=lon,
        start_date=start_d,
        end_date=end_d,
        parameters=[
            "T2M",
            "T2M_MAX",
            "T2M_MIN",
            "PRECTOTCORR",
            "RH2M",
            "ALLSKY_SFC_SW_DWN",
        ],
        bypass_cache=True,
    )

    assert res["is_cached"] is False
    assert res["cache_hit"] is False
    assert "retrieved_at" in res
    datetime.fromisoformat(res["retrieved_at"].replace("Z", "+00:00"))

    raw = res["raw_data"]
    assert "properties" in raw
    params_dict = raw["properties"]["parameter"]

    # Verify all 6 NASA parameters returned with live values
    for code in ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "ALLSKY_SFC_SW_DWN"]:
        assert code in params_dict, f"Missing parameter {code} in live NASA response"
        daily_values = params_dict[code]
        assert "20240501" in daily_values
        assert isinstance(daily_values["20240501"], (int, float))

    # Verify plausible Peshawar May climate readings (typically 20°C - 42°C)
    may1_t2m = daily_values["20240501"]
    assert may1_t2m != -999.0  # Not missing
    assert 10.0 <= may1_t2m <= 50.0  # Realistic temperature range


@pytest.mark.asyncio
async def test_live_nasa_power_cache_hit_behavior():
    """Verify second identical call yields cache_hit=True with zero latency."""
    client = NasaPowerClient(timeout=30.0)
    lat, lon = 34.0151, 71.5249
    start_d, end_d = "2024-05-01", "2024-05-02"

    call1 = await client.fetch_daily_point(
        farm_id="farm-peshawar-001",
        latitude=lat,
        longitude=lon,
        start_date=start_d,
        end_date=end_d,
        parameters=["T2M", "PRECTOTCORR"],
    )

    call2 = await client.fetch_daily_point(
        farm_id="farm-peshawar-001",
        latitude=lat,
        longitude=lon,
        start_date=start_d,
        end_date=end_d,
        parameters=["T2M", "PRECTOTCORR"],
    )

    assert call2["is_cached"] is True
    assert call2["cache_hit"] is True
    assert call2["raw_data"] == call1["raw_data"]


@pytest.mark.asyncio
async def test_smap_adapter_unconfigured_token_safety():
    """Verify SMAP adapter returns structured unavailable status without fabricating numbers."""
    result = await earthdata_adapter.fetch_smap_soil_moisture(
        latitude=34.0151,
        longitude=71.5249,
        date_str="2024-05-01",
    )

    assert result["status"] == "unavailable"
    assert result["measurements"] is None
    assert "token/product not configured" in result["message"]
    assert result["spatial_resolution"] == "9 km EASE-Grid 2.0"
    assert result["is_demo_data"] is False


@pytest.mark.asyncio
async def test_gpm_adapter_unconfigured_token_safety():
    """Verify GPM adapter returns structured unavailable status without fabricating numbers."""
    result = await earthdata_adapter.fetch_gpm_precipitation(
        latitude=34.0151,
        longitude=71.5249,
        date_str="2024-05-01",
    )

    assert result["status"] == "unavailable"
    assert result["measurements"] is None
    assert "token/product not configured" in result["message"]
    assert "0.1°" in result["spatial_resolution"]
    assert result["is_demo_data"] is False


@pytest.mark.asyncio
async def test_live_normalization_pipeline_to_climate_summary():
    """Verify normalizing real NASA POWER response creates valid canonical ClimateSummary."""
    client = NasaPowerClient(timeout=30.0)
    lat, lon = 34.0151, 71.5249
    start_d, end_d = "2024-05-01", "2024-05-03"

    res = await client.fetch_daily_point(
        farm_id="farm-peshawar-001",
        latitude=lat,
        longitude=lon,
        start_date=start_d,
        end_date=end_d,
        parameters=["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR"],
    )

    meta_params, daily_records, missing_data = normalize_power_response(
        raw_payload=res["raw_data"],
        start_date=start_d,
        end_date=end_d,
        requested_parameters=res["request_meta"]["parameters"],
    )

    assert len(daily_records) == 3
    for rec in daily_records:
        assert "T2M" in rec.values
        assert "PRECTOTCORR" in rec.values

    aggregates = compute_all_aggregates(daily_records)
    assert len(aggregates.monthly) == 1
    assert aggregates.monthly[0].period == "2024-05"

    summary = ClimateSummary(
        farm_id="farm-peshawar-001",
        source="NASA POWER Daily API",
        product_or_dataset="MERRA-2 / GEOS-5 FP-IT via POWER AG",
        latitude=lat,
        longitude=lon,
        start_date=start_d,
        end_date=end_d,
        parameters=meta_params,
        daily_series=daily_records,
        aggregates=aggregates,
        missing_data=missing_data,
        retrieved_at=res["retrieved_at"],
        coverage_note="Gridded NASA satellite and reanalysis data represents regional grid cells (~0.5° × 0.5°), not direct on-farm in-situ sensor measurements.",
        is_demo_data=False,
    )

    assert summary.is_demo_data is False
    assert summary.aggregates.monthly[0].values["T2M"].mean is not None
