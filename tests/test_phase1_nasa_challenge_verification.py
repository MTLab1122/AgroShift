"""Verification Gate for Phase 1: Challenge Resource Mapping, Environment Setup & Schema Alignment.

Verifies:
1. .env.example contains challenge-required variables.
2. nasa_config.py registers all NASA Space Apps 2026 challenge datasets.
3. FarmVsNasaComparison Pydantic schema validates correctly.
4. ClimateSummary and RecommendationSet integrate farm_vs_nasa_comparison.
5. JSON schemas in shared/schemas/ validate with FarmVsNasaComparison blocks.
"""

import json
from pathlib import Path
from jsonschema import Draft202012Validator, validate as jsonschema_validate
import pytest

from backend.app.core.nasa_config import (
    CHALLENGE_URL,
    NASA_CHALLENGE_DATASETS,
    NasaConfig,
)
from backend.app.schemas import (
    ClimateSummary,
    FarmVsNasaComparison,
    RecommendationSet,
)

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


def test_env_example_has_challenge_variables():
    """Verify .env.example defines POWER and secondary Earthdata tokens."""
    env_path = WORKSPACE_ROOT / ".env.example"
    assert env_path.is_file(), "Missing .env.example"
    content = env_path.read_text(encoding="utf-8")

    assert "NASA_POWER_BASE_URL=" in content
    assert "NASA_EARTHDATA_TOKEN=" in content
    assert "NASA_SMAP_ENDPOINT=" in content
    assert "NASA_GPM_ENDPOINT=" in content


def test_nasa_challenge_dataset_registry():
    """Verify nasa_config registers all challenge datasets and parameters."""
    assert "NASA_POWER_AG" in NASA_CHALLENGE_DATASETS
    power_meta = NASA_CHALLENGE_DATASETS["NASA_POWER_AG"]
    assert "T2M" in power_meta.parameter_codes
    assert "T2M_MAX" in power_meta.parameter_codes
    assert "T2M_MIN" in power_meta.parameter_codes
    assert "PRECTOTCORR" in power_meta.parameter_codes
    assert "RH2M" in power_meta.parameter_codes
    assert "ALLSKY_SFC_SW_DWN" in power_meta.parameter_codes

    assert "NASA_SMAP_L4" in NASA_CHALLENGE_DATASETS
    assert "NASA_GPM_IMERG" in NASA_CHALLENGE_DATASETS
    assert "spaceappschallenge.org" in CHALLENGE_URL


def test_farm_vs_nasa_comparison_pydantic_model():
    """Verify FarmVsNasaComparison validates correctly."""
    comparison = FarmVsNasaComparison(
        observed_rainfall_mm=124.5,
        expected_crop_water_need_mm=450.0,
        water_balance_status="severe_deficit",
        thermal_stress_days=14,
        irrigation_adequacy_note="Severe precipitation deficit of 325.5 mm detected. Canal irrigation buffer required.",
        data_mode="live",
    )
    dumped = comparison.model_dump()
    assert dumped["observed_rainfall_mm"] == 124.5
    assert dumped["water_balance_status"] == "severe_deficit"
    assert dumped["data_mode"] == "live"


def test_climate_summary_with_comparison_block():
    """Verify ClimateSummary accepts optional farm_vs_nasa_comparison block."""
    fixture_path = WORKSPACE_ROOT / "data" / "demo" / "climate.mock.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["farm_vs_nasa_comparison"] = {
        "observed_rainfall_mm": 218.0,
        "expected_crop_water_need_mm": 500.0,
        "water_balance_status": "moderate_deficit",
        "thermal_stress_days": 8,
        "irrigation_adequacy_note": "Moderate rainfall deficit observed. Sufficient canal irrigation availability mitigates risk.",
        "data_mode": "demo_fallback",
    }

    summary = ClimateSummary.model_validate(data)
    assert summary.farm_vs_nasa_comparison is not None
    assert summary.farm_vs_nasa_comparison.water_balance_status == "moderate_deficit"

    # Also validate against JSON schema
    schema_path = WORKSPACE_ROOT / "shared" / "schemas" / "climate.schema.json"
    with open(schema_path, "r", encoding="utf-8") as sf:
        schema = json.load(sf)
    Draft202012Validator.check_schema(schema)
    jsonschema_validate(instance=data, schema=schema)


def test_recommendation_set_schema_with_comparison_block():
    """Verify RecommendationSet schema validates with farm_vs_nasa_comparison."""
    sample_rec = {
        "recommendation_id": "rec-peshawar-001",
        "farm_id": "farm-peshawar-001",
        "generated_at": "2026-11-14T12:00:00Z",
        "input_snapshot": {"current_crop": "Maize", "soil_type": "loamy"},
        "scenarios": {
            "baseline": {
                "scenario_id": "sc-base-1",
                "title": "Continuous Maize-Wheat",
                "crop_sequence": ["Maize", "Wheat"],
                "seasonal_calendar": [
                    {"crop": "Maize", "start_month": "May", "harvest_month": "August"},
                    {"crop": "Wheat", "start_month": "November", "harvest_month": "April"},
                ],
                "score": 68.0,
                "score_breakdown": {
                    "climate_suitability": 75.0,
                    "water_efficiency": 60.0,
                    "soil_health_benefit": 55.0,
                    "market_resilience": 82.0,
                },
                "rationale": ["Standard regional cereal rotation"],
                "benefits": ["Familiar market outlets"],
                "risks": ["High nitrogen depletion"],
                "assumptions": ["Canal irrigation remains operational"],
            },
            "pulse_inclusive": {
                "scenario_id": "sc-pulse-1",
                "title": "Maize - Chickpea Pulse Rotation",
                "crop_sequence": ["Maize", "Chickpea"],
                "seasonal_calendar": [
                    {"crop": "Maize", "start_month": "May", "harvest_month": "August"},
                    {"crop": "Chickpea", "start_month": "October", "harvest_month": "March"},
                ],
                "score": 84.5,
                "score_breakdown": {
                    "climate_suitability": 85.0,
                    "water_efficiency": 88.0,
                    "soil_health_benefit": 85.0,
                    "market_resilience": 80.0,
                },
                "rationale": ["Biological nitrogen fixation reduces synthetic fertilizer need"],
                "benefits": ["Improved soil organic matter"],
                "risks": ["Susceptibility to late frost during pod development"],
                "assumptions": ["Certified rhizobium inoculant accessible"],
            },
            "soil_cover": {
                "scenario_id": "sc-cover-1",
                "title": "Maize - Berseem Clover Cover & Fodder",
                "crop_sequence": ["Maize", "Berseem"],
                "seasonal_calendar": [
                    {"crop": "Maize", "start_month": "May", "harvest_month": "August"},
                    {"crop": "Berseem", "start_month": "September", "harvest_month": "April"},
                ],
                "score": 81.0,
                "score_breakdown": {
                    "climate_suitability": 80.0,
                    "water_efficiency": 72.0,
                    "soil_health_benefit": 92.0,
                    "market_resilience": 80.0,
                },
                "rationale": ["Multi-cut green fodder maintains canopy ground cover"],
                "benefits": ["Prevents topsoil erosion"],
                "risks": ["Higher total water consumption"],
                "assumptions": ["Local livestock fodder demand"],
            },
        },
        "limitations": [
            "Decision support model; requires local agricultural extension verification."
        ],
        "farm_vs_nasa_comparison": {
            "observed_rainfall_mm": 218.0,
            "expected_crop_water_need_mm": 500.0,
            "water_balance_status": "moderate_deficit",
            "thermal_stress_days": 8,
            "irrigation_adequacy_note": "Canal supply adequately compensates for rainfall deficit.",
            "data_mode": "live",
        },
    }

    # Validate with Pydantic
    rec = RecommendationSet.model_validate(sample_rec)
    assert rec.farm_vs_nasa_comparison is not None
    assert rec.farm_vs_nasa_comparison.observed_rainfall_mm == 218.0

    # Validate with JSON schema
    schema_path = WORKSPACE_ROOT / "shared" / "schemas" / "recommendation.schema.json"
    with open(schema_path, "r", encoding="utf-8") as sf:
        schema = json.load(sf)
    Draft202012Validator.check_schema(schema)
    jsonschema_validate(instance=sample_rec, schema=schema)
