"""FastAPI Router for Module 03: Agro Intelligence & Crop Rotation Engine.

Exposes:
- POST /api/v1/recommendations/generate: Generates explainable, priority-scored crop rotation recommendations.
- POST /api/v1/analyze-farm: Comprehensive farm assessment reconciling inputs with live NASA climate data.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Body, Query, Request, Response

from backend.app.core.gateway import gateway
from backend.app.core.middleware import get_request_id
from backend.app.modules.agro_engine.comparator import compare_farm_to_climate
from backend.app.modules.agro_engine.recommendation_engine import generate_recommendations
from backend.app.modules.nasa_data.power_client import NasaPowerClient
from backend.app.modules.nasa_data.schemas import ApiError
from backend.app.schemas.farm import FarmProfile
from backend.app.schemas.recommendation import RecommendationSet

logger = logging.getLogger("agroshift.agro_engine")
router = APIRouter(tags=["Agro Intelligence & Crop Rotation"])

power_client = NasaPowerClient()


def _resolve_default_season_dates(season: str) -> tuple[str, str]:
    """Provide verified historical NASA POWER observation windows matching target season."""
    s = season.strip().capitalize()
    if s == "Kharif":
        return "2024-05-01", "2024-10-31"
    elif s == "Rabi":
        return "2023-11-01", "2024-04-30"
    else:
        # Default 6-month baseline
        return "2024-05-01", "2024-10-31"


@router.post(
    "/api/v1/recommendations/generate",
    response_model=RecommendationSet,
    summary="Generate Grounded Crop Rotation Recommendations",
    responses={
        422: {"model": ApiError, "description": "Validation Error"},
        503: {"model": ApiError, "description": "NASA Service Unavailable"},
    },
)
async def generate_crop_recommendations(
    request: Request,
    response: Response,
    farm_profile: FarmProfile = Body(..., description="Canonical FarmProfile submission"),
    start_date: Optional[str] = Query(None, description="Optional custom observation window start (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Optional custom observation window end (YYYY-MM-DD)"),
    demo: bool = Query(False, description="Force demo mock data fallback"),
) -> RecommendationSet:
    """Retrieve live NASA observations for farm coordinates, compare inputs, and return scored rotation recommendations."""
    req_id = get_request_id(request)

    # 1. Resolve date window
    if not start_date or not end_date:
        default_start, default_end = _resolve_default_season_dates(farm_profile.season)
        start_date = start_date or default_start
        end_date = end_date or default_end

    logger.info(
        "Generating recommendations [%s] for farm '%s' at (%s, %s) [%s to %s]",
        req_id,
        farm_profile.farm_id,
        farm_profile.latitude,
        farm_profile.longitude,
        start_date,
        end_date,
    )

    # 2. Retrieve live NASA POWER Climate Summary via gateway
    climate_summary, data_mode = await gateway.get_climate_summary(
        power_client=power_client,
        farm_id=farm_profile.farm_id,
        latitude=farm_profile.latitude,
        longitude=farm_profile.longitude,
        start_date=start_date,
        end_date=end_date,
        parameters=["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "ALLSKY_SFC_SW_DWN"],
        include_daily=True,
        force_demo=demo,
        request_id=req_id,
        response=response,
    )

    # 3. Reconcile farmer inputs against actual NASA observations
    comparison = compare_farm_to_climate(
        farm_profile=farm_profile,
        climate_summary=climate_summary,
        data_mode=data_mode,
    )

    # 4. Generate explainable, priority-scored recommendations
    recommendations = generate_recommendations(
        farm_profile=farm_profile,
        climate_summary=climate_summary,
        comparison=comparison,
        data_mode=data_mode,
    )

    return recommendations


@router.post(
    "/api/v1/analyze-farm",
    response_model=RecommendationSet,
    summary="Comprehensive Farm Profile Analysis & Rotation Recommendations",
)
async def analyze_farm_profile(
    request: Request,
    response: Response,
    farm_profile: FarmProfile = Body(...),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    demo: bool = Query(False),
) -> RecommendationSet:
    """Alias endpoint for complete farm profile analysis and recommendation generation."""
    return await generate_crop_recommendations(
        request=request,
        response=response,
        farm_profile=farm_profile,
        start_date=start_date,
        end_date=end_date,
        demo=demo,
    )
