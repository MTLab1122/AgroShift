"""Canonical RecommendationSet and Scenario Schemas (Module 03).

Defines the output structure for crop-rotation scenarios and decision support.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.comparison import FarmVsNasaComparison


class CalendarEntry(BaseModel):
    """Seasonal window entry for a suggested crop."""

    model_config = ConfigDict(extra="forbid")

    crop: str = Field(..., description="Crop name")
    start_month: str = Field(..., description="Planting window month")
    harvest_month: str = Field(..., description="Harvest window month")
    duration_days: Optional[int] = Field(default=None, description="Typical growing duration in days")


class ScoreBreakdown(BaseModel):
    """Individual factor scores contributing to scenario evaluation."""

    model_config = ConfigDict(extra="forbid")

    climate_suitability: float = Field(..., ge=0.0, le=100.0)
    water_efficiency: float = Field(..., ge=0.0, le=100.0)
    soil_health_benefit: float = Field(..., ge=0.0, le=100.0)
    market_resilience: float = Field(..., ge=0.0, le=100.0)


class Scenario(BaseModel):
    """A single coherent crop rotation pathway."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(..., description="Unique scenario identifier")
    title: str = Field(..., description="Human-readable title")
    crop_sequence: List[str] = Field(..., min_length=1, description="Sequence of crops")
    seasonal_calendar: List[CalendarEntry] = Field(..., min_length=1)
    score: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    score_breakdown: ScoreBreakdown
    rationale: List[str] = Field(default_factory=list)
    benefits: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)


class ScenarioCatalog(BaseModel):
    """The 3 canonical scenarios mandated by AgroShift architecture."""

    model_config = ConfigDict(extra="forbid")

    baseline: Scenario
    pulse_inclusive: Scenario
    soil_cover: Scenario


class RecommendationSet(BaseModel):
    """Canonical recommendation set output for Module 03."""

    model_config = ConfigDict(extra="forbid")

    recommendation_id: str = Field(..., min_length=1)
    farm_id: str = Field(..., min_length=1)
    generated_at: str = Field(..., description="ISO 8601 UTC timestamp")
    input_snapshot: Dict[str, Any] = Field(..., description="Snapshot of user inputs")
    scenarios: ScenarioCatalog
    limitations: List[str] = Field(..., min_length=1)
    farm_vs_nasa_comparison: Optional[FarmVsNasaComparison] = Field(
        default=None,
        description="Structured comparison reconciling user inputs with actual NASA observations.",
    )
