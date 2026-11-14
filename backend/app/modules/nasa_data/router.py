"""FastAPI Router for Module 02 & Module 05: Climate Data Engine & Integration Gateway.

Exposes:
- GET /health & GET /api/v1/health: Deep readiness and module health inspector.
- GET /api/v1/climate/summary: Canonical ClimateSummary with resilient gateway fallback.
- GET /api/v1/climate/history: Detailed daily and monthly environmental time-series records.
- GET /api/v1/nasa/power: Diagnostic endpoint for cache inspection and raw upstream verification.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import JSONResponse

from backend.app.core.gateway import gateway
from backend.app.core.middleware import get_request_id
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

router = APIRouter(tags=["NASA Climate Data & Integration"])

# Global client singleton
power_client = NasaPowerClient()


def parse_parameter_list(raw_params: Optional[str]) -> Optional[List[str]]:
    """Parse comma-separated parameter string into list of stripped uppercase codes."""
    if not raw_params:
        return None
    codes = [p.strip().upper() for p in raw_params.split(",") if p.strip()]
    return codes if codes else None


async def get_system_health_report() -> Dict[str, Any]:
    """Compile deep diagnostics and module readiness report."""
    cache_size = await power_client.cache.size()
    demo_ready = gateway.is_demo_fixture_available()

    return {
        "status": "healthy",
        "version": "1.0.0",
        "schema_version": "2026.1",
        "cache_entries": cache_size,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "modules": {
            "module_01_farm": {
                "name": "Farm Management & Location Intelligence",
                "owner": "Sana Jalal",
                "status": "ready",
                "contract": "FarmProfile",
                "branch": "feature/farm-module",
            },
            "module_02_nasa": {
                "name": "NASA Earth Observation & Climate Engine",
                "owner": "Muhammad Talha",
                "status": "ready",
                "contract": "ClimateSummary",
                "branch": "feature/nasa-data",
                "upstream_source": "NASA POWER Daily API (AG community)",
                "cache_entries": cache_size,
                "cache_ttl_seconds": power_client.cache.default_ttl,
            },
            "module_03_agro": {
                "name": "Agro Intelligence & Crop Rotation Engine",
                "owner": "Hira Dawood",
                "status": "ready",
                "contract": "RecommendationSet",
                "branch": "feature/agro-engine",
            },
            "module_04_analytics": {
                "name": "Analytics, Visualization & Reporting",
                "owner": "Aqsa Faisal",
                "status": "ready",
                "contract": "ScenarioComparison",
                "branch": "feature/analytics",
            },
            "module_05_integration": {
                "name": "Integration, Security, QA & Deployment",
                "owner": "Sudais Ahmad",
                "status": "ready",
                "branch": "feature/integration",
                "gateway_mode": "active",
                "demo_fallback_available": demo_ready,
            },
        },
        "diagnostics": {
            "nasa_power_url": power_client.base_url,
            "cache_entries": cache_size,
            "demo_fixture_available": demo_ready,
            "canonical_schemas": [
                "farm.schema.json",
                "climate.schema.json",
                "recommendation.schema.json",
                "error.schema.json",
            ],
        },
    }


@router.get("/health", summary="Basic Service Health Check")
async def health_check() -> Dict[str, Any]:
    """Compatibility health check endpoint."""
    return await get_system_health_report()


@router.get("/api/v1/health", summary="Deep Readiness & Module Diagnostics")
async def deep_health_check() -> Dict[str, Any]:
    """Deep readiness and per-module diagnostic inspector."""
    return await get_system_health_report()


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
    request: Request,
    response: Response,
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
    """Retrieve normalized NASA environmental data and climate aggregations with resilient gateway fallback."""
    req_id = get_request_id(request)
    param_list = parse_parameter_list(parameters)

    summary, mode = await gateway.get_climate_summary(
        power_client=power_client,
        farm_id=farm_id,
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
        parameters=param_list,
        include_daily=include_daily,
        force_demo=demo,
        request_id=req_id,
        response=response,
    )

    return summary


@router.get(
    "/api/v1/climate/history",
    summary="Retrieve Detailed Time-Series History",
    responses={
        422: {"model": ApiError},
        503: {"model": ApiError},
    },
)
async def get_climate_history(
    request: Request,
    response: Response,
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
        request=request,
        response=response,
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
    request: Request,
    latitude: float = Query(...),
    longitude: float = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    parameters: Optional[str] = Query(None),
    bypass_cache: bool = Query(False),
) -> Dict[str, Any]:
    """Diagnostic route exposing cache status, upstream query metadata, and raw inspection."""
    req_id = get_request_id(request)
    param_list = parse_parameter_list(parameters)

    power_res = await power_client.fetch_daily_point(
        farm_id="diagnostic-probe",
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
        parameters=param_list,
        request_id=req_id,
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
