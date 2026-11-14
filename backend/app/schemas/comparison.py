"""Canonical Farm vs. Live NASA Observation Comparison Schema.

Defines the diagnostic contract reconciling user-submitted farm profile
inputs against live NASA satellite and reanalysis observations.
"""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class FarmVsNasaComparison(BaseModel):
    """Comparison diagnostic evaluating farmer-submitted inputs against actual NASA observations."""

    model_config = ConfigDict(extra="forbid")

    observed_rainfall_mm: float = Field(
        ...,
        ge=0.0,
        description="Total observed precipitation from NASA POWER (PRECTOTCORR) over the period.",
    )
    expected_crop_water_need_mm: float = Field(
        ...,
        ge=0.0,
        description="Agronomically expected crop water requirement based on crop catalog.",
    )
    water_balance_status: Literal["severe_deficit", "moderate_deficit", "balanced", "excess_moisture"] = Field(
        ...,
        description="Water balance category: severe_deficit, moderate_deficit, balanced, or excess_moisture.",
        examples=["moderate_deficit", "severe_deficit", "balanced", "excess_moisture"],
    )
    thermal_stress_days: int = Field(
        ...,
        ge=0,
        description="Count of days where NASA T2M_MAX exceeded critical heat stress thresholds.",
    )
    irrigation_adequacy_note: str = Field(
        ...,
        description="Evaluation reconciling reported irrigation type/availability against observed precipitation deficit.",
    )
    data_mode: Literal["live", "demo_fallback", "demo_forced"] = Field(
        default="live",
        description="Indicates whether comparison was computed against live NASA observations or demo fallback.",
        examples=["live", "demo_fallback"],
    )
