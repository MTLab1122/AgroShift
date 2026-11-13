"""FastAPI Router for Module 02: NASA Earth Observation & Climate Data Engine.

Exposes:
- GET /api/v1/climate/summary: Canonical ClimateSummary object with aggregates and provenance.
- GET /api/v1/climate/history: Detailed daily and monthly environmental time-series records.
- GET /api/v1/nasa/power: Diagnostic endpoint for cache inspection and raw upstream verification.
- GET /health: Health check endpoint compatible with Module 05.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse

from backend.app.modules.nasa_data.aggregations import (
    compute_all_aggregates,
    compute_monthly_aggregates,
)
from backend.app.modules.nasa_data.normalizer import (
    VERIFIED_PARAMETERS,
    normalize_power_response,
)
from backend.app.modules.nasa_data.power_client import (
    NasaPowerClient,
    NasaPowerClientError,
)
from backend.app.modules.nasa_data.schemas import (
    ApiError,
    ClimateRequest,
    ClimateSummary,
    DailyRecord,
    MonthlyAggregate,
    ParameterMetadata,
)

router = APIRouter(tags=["NASA Climate Data"])

# Global client singleton
power_client = NasaPowerClient()

FIXTURE_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "climate.mock.json"
)


def get_demo_summary() -> ClimateSummary:
    """Load local Peshawar Valley demo fixture."""
    if not FIXTURE_PATH.is_file():
        # Fallback to data/demo/climate.mock.json
        alt_path = Path(__file__).resolve().parents[4] / "data" / "demo" / "climate.mock.json"
        with open(alt_path, "r", encoding="utf-8") as f:
            return ClimateSummary.model_validate_json(f.read())
    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        return ClimateSummary.model_validate_json(f.read())


def parse_parameter_list(raw_params: Optional[str]) -> Optional[List[str]]:
    """Parse comma-separated parameter string into list of stripped uppercase codes."""
    if not raw_params:
        return None
    codes = [p.strip().upper() for p in raw_params.split(",") if p.strip()]
    return codes if codes else None


@router.get("/health", summary="Service Health Check")
async def health_check() -> Dict[str, Any]:
    """Basic service health check compatible with Module 05."""
    cache_size = await power_client.cache.size()
    return {
        "status": "healthy",
        "module": "Module 02 - NASA Earth Observation & Climate Data Engine",
        "cache_entries": cache_size,
    }


@router.get(
    "/api/v1/climate/summary",
    response_model=ClimateSummary,
    summary="Retrieve Normalized Climate Summary",
    responses={
        422: {"model": ApiError, "description": "Validation Error"},
        503: {"model": ApiError, "description": "Upstream NASA Service Unavailable"},
        504: {"model": ApiError, "description": "Upstream Timeout"},
    },
)
async def get_climate_summary(
    farm_id: str = Query(..., description="Unique identifier of the farm from Module 01"),
    latitude: float = Query(..., description="Latitude in decimal degrees (-90.0 to 90.0)"),
    longitude: float = Query(..., description="Longitude in decimal degrees (-180.0 to 180.0)"),
    start_date: str = Query(..., description="Start date in YYYY-MM-DD"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD"),
    parameters: Optional[str] = Query(
        None,
        description="Comma-separated parameter list (e.g., T2M,PRECTOTCORR,RH2M,ALLSKY_SFC_SW_DWN)",
    ),
    include_daily: bool = Query(
        False, description="Whether to include daily time series records"
    ),
    demo: bool = Query(False, description="Force mock Peshawar Valley demo data"),
) -> ClimateSummary:
    """Retrieve normalized NASA environmental data and climate aggregations."""
    request_id = f"req-{uuid.uuid4().hex[:8]}"

    # Fast path: demo mode
    if demo:
        demo_summary = get_demo_summary()
        if not include_daily:
            return demo_summary.model_copy(update={"daily_series": None})
        return demo_summary

    param_list = parse_parameter_list(parameters)

    # Pre-flight validation occurs inside fetch_daily_point
    power_res = await power_client.fetch_daily_point(
        farm_id=farm_id,
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
        parameters=param_list,
        request_id=request_id,
    )

    meta_params, daily_records, missing_data = normalize_power_response(
        raw_payload=power_res["raw_data"],
        start_date=start_date,
        end_date=end_date,
        requested_parameters=power_res["request_meta"]["parameters"],
    )

    aggregates = compute_all_aggregates(daily_records)

    coverage_note = (
        "Gridded NASA satellite and reanalysis data represents regional grid cells (~0.5° × 0.5° / ~50km × 50km resolution), "
        "not direct on-farm in-situ sensor measurements. Use for regional decision support and agro-climatic context."
    )

    return ClimateSummary(
        farm_id=farm_id,
        source="NASA POWER Daily API",
        product_or_dataset="MERRA-2 / GEOS-5 FP-IT / CERES SYN1deg via POWER AG community",
        latitude=round(latitude, 4),
        longitude=round(longitude, 4),
        start_date=start_date,
        end_date=end_date,
        parameters=meta_params,
        daily_series=daily_records if include_daily else None,
        aggregates=aggregates,
        missing_data=missing_data,
        retrieved_at=power_res["retrieved_at"],
        coverage_note=coverage_note,
        is_demo_data=False,
    )


@router.get(
    "/api/v1/climate/history",
    summary="Retrieve Detailed Time-Series History",
    responses={
        422: {"model": ApiError},
        503: {"model": ApiError},
    },
)
async def get_climate_history(
    farm_id: str = Query(..., description="Unique identifier of the farm"),
    latitude: float = Query(...),
    longitude: float = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    parameters: Optional[str] = Query(None),
    demo: bool = Query(False),
) -> Dict[str, Any]:
    """Retrieve daily time-series records and monthly aggregates for history table/charting."""
    summary = await get_climate_summary(
        farm_id=farm_id,
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
        parameters=parameters,
        include_daily=True,
        demo=demo,
    )

    return {
        "farm_id": summary.farm_id,
        "latitude": summary.latitude,
        "longitude": summary.longitude,
        "start_date": summary.start_date,
        "end_date": summary.end_date,
        "parameters": [p.model_dump() for p in summary.parameters],
        "daily_series": [d.model_dump() for d in (summary.daily_series or [])],
        "monthly_aggregates": [m.model_dump() for m in summary.aggregates.monthly],
        "coverage_note": summary.coverage_note,
        "is_demo_data": summary.is_demo_data,
        "retrieved_at": summary.retrieved_at,
    }


@router.get(
    "/api/v1/nasa/power",
    summary="Diagnostic NASA POWER Cache & Raw Inspector",
)
async def inspect_nasa_power(
    latitude: float = Query(...),
    longitude: float = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    parameters: Optional[str] = Query(None),
    bypass_cache: bool = Query(False),
) -> Dict[str, Any]:
    """Diagnostic route exposing cache status, upstream query metadata, and raw inspection."""
    request_id = f"diag-{uuid.uuid4().hex[:8]}"
    param_list = parse_parameter_list(parameters)

    power_res = await power_client.fetch_daily_point(
        farm_id="diagnostic-probe",
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
        parameters=param_list,
        request_id=request_id,
        bypass_cache=bypass_cache,
    )

    raw_prop = power_res["raw_data"].get("properties", {})
    raw_params = raw_prop.get("parameter", {})

    return {
        "status": "ok",
        "is_cached": power_res["is_cached"],
        "cache_key": power_res["cache_key"],
        "retrieved_at": power_res["retrieved_at"],
        "request_meta": power_res["request_meta"],
        "parameters_returned": list(raw_params.keys()),
        "sample_preview": {
            code: dict(list(dates.items())[:3]) for code, dates in raw_params.items()
        },
    }
