"""Phase 3 Verification Gate Tests: Farm-Input vs. Live NASA Comparison Engine.

Tests:
1. Peshawar Valley agronomic catalog accuracy and synonym normalization across all 9 crops.
2. FarmProfile schema compliance.
3. Contrasting dry vs. wet season climate comparisons for identical farm inputs.
4. Thermal stress day threshold counting using daily NASA observations.
5. Irrigation infrastructure reconciliation (rain_fed vs. canal/tube_well).
6. Monoculture rotation risk and nitrogen debt detection.
7. Strict JSON Schema conformity against shared canonical schemas.
"""

import json
from pathlib import Path
import pytest
from jsonschema import validate

from backend.app.modules.agro_engine.comparator import (
    compare_farm_to_climate,
    evaluate_rotation_monoculture,
)
from backend.app.modules.agro_engine.crop_catalog import (
    get_crop_profile,
    get_crops_by_season,
    get_legume_crops,
    list_supported_crops,
    normalize_crop_name,
)
from backend.app.modules.nasa_data.schemas import (
    AggregatesSummary,
    ClimateSummary,
    DailyRecord,
    MissingDataSummary,
    MonthlyAggregate,
    ParameterMetadata,
    SeasonalAggregate,
)
from backend.app.schemas.comparison import FarmVsNasaComparison
from backend.app.schemas.farm import CropHistoryEntry, FarmProfile

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


def test_crop_catalog_retrieval_and_normalization():
    """Verify all 9 mandated crops are present with accurate physiological benchmarks."""
    expected_crops = [
        "wheat",
        "maize",
        "rice",
        "sugarcane",
        "mustard",
        "chickpea",
        "lentil",
        "mung_bean",
        "berseem_clover",
    ]
    all_crops = list_supported_crops()
    assert len(all_crops) >= 9
    catalog_keys = [c.name for c in all_crops]
    for exp in expected_crops:
        assert exp in catalog_keys

    # Test synonym and regional Urdu/Pashto alias resolution
    assert normalize_crop_name("Gandum") == "wheat"
    assert normalize_crop_name("gehun") == "wheat"
    assert normalize_crop_name("Makai") == "maize"
    assert normalize_crop_name("Sholay") == "rice"
    assert normalize_crop_name("Kamand") == "sugarcane"
    assert normalize_crop_name("Sarson") == "mustard"
    assert normalize_crop_name("Chana") == "chickpea"
    assert normalize_crop_name("Masoor") == "lentil"
    assert normalize_crop_name("Moong") == "mung_bean"
    assert normalize_crop_name("Shaftal") == "berseem_clover"

    # Verify legume biological nitrogen fixation attributes
    legumes = get_legume_crops()
    legume_names = [l.name for l in legumes]
    assert "chickpea" in legume_names
    assert "lentil" in legume_names
    assert "mung_bean" in legume_names
    assert "berseem_clover" in legume_names

    for l in legumes:
        assert l.is_legume is True
        assert l.nitrogen_fixation_kg_ha > 0.0

    wheat = get_crop_profile("wheat")
    assert wheat is not None
    assert wheat.is_legume is False
    assert wheat.seasonal_water_demand_mm == 400.0
    assert wheat.critical_heat_threshold_c == 32.0


def test_farm_profile_schema_validation():
    """Verify FarmProfile Pydantic model parses valid input and enforces bounds."""
    farm = FarmProfile(
        farm_id="farm-peshawar-001",
        farm_name="Tariq Khan",
        latitude=34.0151,
        longitude=71.5249,
        area_value=5.0,
        area_unit="acres",
        soil_type="loamy",
        irrigation_type="canal",
        water_availability="medium",
        current_crop="wheat",
        season="Rabi",
        crop_history=[
            CropHistoryEntry(
                entry_id="hist-01",
                crop_name="maize",
                season="Kharif",
                year=2023,
                yield_value=40.0,
                yield_unit="maunds/acre",
            )
        ],
    )
    assert farm.farm_id == "farm-peshawar-001"
    assert farm.current_crop == "wheat"

    # Inverted coordinates must fail
    with pytest.raises(Exception):
        FarmProfile(
            farm_id="farm-bad",
            farm_name="Bad",
            latitude=150.0,  # Invalid latitude
            longitude=71.5249,
            area_value=5.0,
            area_unit="acres",
            soil_type="loamy",
            irrigation_type="canal",
            water_availability="medium",
            current_crop="wheat",
            season="Rabi",
        )


def _build_mock_climate_summary(
    rainfall_mm: float,
    temperatures: list[float],
) -> ClimateSummary:
    """Helper to construct a deterministic ClimateSummary for testing."""
    daily_records = []
    for i, t in enumerate(temperatures):
        day_str = f"2024-05-{i+1:02d}"
        daily_records.append(
            DailyRecord(
                date=day_str,
                values={
                    "T2M": t,
                    "T2M_MAX": t + 2.5,
                    "T2M_MIN": t - 2.5,
                    "PRECTOTCORR": rainfall_mm / len(temperatures),
                    "RH2M": 50.0,
                    "ALLSKY_SFC_SW_DWN": 20.0,
                },
            )
        )

    summary = ClimateSummary(
        farm_id="farm-peshawar-001",
        source="NASA POWER Daily API",
        product_or_dataset="MERRA-2 via POWER AG",
        latitude=34.0151,
        longitude=71.5249,
        start_date="2024-05-01",
        end_date=f"2024-05-{len(temperatures):02d}",
        parameters=[
            ParameterMetadata(code="T2M", label="Temperature at 2 Meters", unit="°C"),
            ParameterMetadata(code="T2M_MAX", label="Maximum Temperature", unit="°C"),
            ParameterMetadata(code="T2M_MIN", label="Minimum Temperature", unit="°C"),
            ParameterMetadata(code="PRECTOTCORR", label="Precipitation", unit="mm/day"),
            ParameterMetadata(code="RH2M", label="Relative Humidity", unit="%"),
            ParameterMetadata(code="ALLSKY_SFC_SW_DWN", label="Solar Irradiance", unit="MJ/m^2/day"),
        ],
        aggregates=AggregatesSummary(
            monthly=[
                MonthlyAggregate(
                    period="2024-05",
                    aggregation_method="mean for temperature/humidity/radiation, sum for precipitation",
                    total_days=len(temperatures),
                    valid_days=len(temperatures),
                    coverage_ratio=1.0,
                    values={},
                )
            ],
            seasonal=[],
        ),
        missing_data=MissingDataSummary(
            total_days=len(temperatures),
            missing_days_by_parameter={"PRECTOTCORR": 0, "T2M": 0},
            has_gaps=False,
        ),
        retrieved_at="2026-11-14T10:00:00Z",
        coverage_note="Grid cell regional observation",
        daily_series=daily_records,
    )
    return summary


def test_dry_season_vs_wet_season_comparison_contrast():
    """Verify contrasting dry vs wet climate regimes generate distinct, accurate water diagnostics."""
    farm_input = {
        "current_crop": "wheat",
        "irrigation_type": "rain_fed",
        "water_availability": "low",
        "soil_type": "sandy",
    }

    # Case A: Dry Winter Drought (only 25 mm rain against 400 mm requirement)
    dry_climate = _build_mock_climate_summary(
        rainfall_mm=25.0,
        temperatures=[18.0, 19.0, 20.0],
    )
    comp_dry = compare_farm_to_climate(farm_input, dry_climate, data_mode="live")

    assert comp_dry.observed_rainfall_mm == 25.0
    assert comp_dry.expected_crop_water_need_mm == 400.0
    assert comp_dry.water_balance_status == "severe_deficit"
    assert "moisture deficit (severe deficit)" in comp_dry.irrigation_adequacy_note
    assert "chickpea or lentil" in comp_dry.irrigation_adequacy_note

    # Case B: Wet Monsoon (550 mm rain against 400 mm requirement)
    wet_climate = _build_mock_climate_summary(
        rainfall_mm=550.0,
        temperatures=[26.0, 27.0, 28.0],
    )
    comp_wet = compare_farm_to_climate(farm_input, wet_climate, data_mode="live")

    assert comp_wet.observed_rainfall_mm == 550.0
    assert comp_wet.expected_crop_water_need_mm == 400.0
    assert comp_wet.water_balance_status == "excess_moisture"
    assert "exceeded seasonal needs" in comp_wet.irrigation_adequacy_note


def test_thermal_stress_day_counting():
    """Verify daily temperatures above critical thresholds trigger heat stress count."""
    farm_input = {
        "current_crop": "wheat",  # critical heat threshold is 32.0°C
        "irrigation_type": "canal",
        "water_availability": "high",
        "soil_type": "loamy",
    }

    # Temperatures: T2M_MAX will be T2M + 2.5
    # T2M=28.0 -> T2M_MAX=30.5 (under 32.0)
    # T2M=30.0 -> T2M_MAX=32.5 (EXCEEDS 32.0 -> stress)
    # T2M=33.0 -> T2M_MAX=35.5 (EXCEEDS 32.0 -> stress)
    # T2M=25.0 -> T2M_MAX=27.5 (under 32.0)
    climate = _build_mock_climate_summary(
        rainfall_mm=100.0,
        temperatures=[28.0, 30.0, 33.0, 25.0],
    )
    comp = compare_farm_to_climate(farm_input, climate)

    assert comp.thermal_stress_days == 2
    assert "2 heat-stress day(s) exceeding 32.0°C" in comp.irrigation_adequacy_note


def test_irrigation_reconciliation():
    """Verify that reported canal irrigation with high availability mitigates moisture deficit."""
    # Farm with canal + high availability
    farm_irrigated = {
        "current_crop": "wheat",  # 400 mm demand
        "irrigation_type": "canal",
        "water_availability": "high",
        "soil_type": "loamy",
    }
    climate = _build_mock_climate_summary(
        rainfall_mm=120.0,
        temperatures=[20.0, 21.0, 22.0],
    )
    comp = compare_farm_to_climate(farm_irrigated, climate)

    # Rainfall is 120 mm. With canal + high availability, delivered irrigation meets remaining demand
    assert comp.water_balance_status == "balanced"
    assert "adequacy" in comp.irrigation_adequacy_note


def test_rotation_monoculture_and_nitrogen_debt_detection():
    """Verify monoculture cereal repetition is flagged and legume breaks rewarded."""
    # Continuous cereal sequence: Wheat -> Maize -> Wheat
    cereal_history = [
        CropHistoryEntry(entry_id="h1", crop_name="maize", season="Kharif", year=2023),
        CropHistoryEntry(entry_id="h2", crop_name="wheat", season="Rabi", year=2022),
    ]
    eval_cereal = evaluate_rotation_monoculture("wheat", cereal_history)
    assert eval_cereal["consecutive_cereal_seasons"] == 3
    assert eval_cereal["monoculture_risk"] is True
    assert eval_cereal["nitrogen_debt_warning"] is True
    assert eval_cereal["rotation_penalty_points"] > 0

    # Legume break sequence: Wheat -> Chickpea
    legume_history = [
        CropHistoryEntry(entry_id="h1", crop_name="chickpea", season="Rabi", year=2023),
    ]
    eval_legume = evaluate_rotation_monoculture("wheat", legume_history)
    assert eval_legume["has_legume_break"] is True
    assert eval_legume["monoculture_risk"] is False


def test_comparison_json_schema_conformity():
    """Verify FarmVsNasaComparison serializes strictly according to shared/schemas/climate.schema.json."""
    farm_input = {
        "current_crop": "wheat",
        "irrigation_type": "canal",
        "water_availability": "high",
        "soil_type": "loamy",
    }
    climate = _build_mock_climate_summary(
        rainfall_mm=150.0,
        temperatures=[20.0, 22.0],
    )
    comp = compare_farm_to_climate(farm_input, climate, data_mode="live")
    comp_dict = comp.model_dump()

    # Load JSON schema definition
    schema_path = WORKSPACE_ROOT / "shared" / "schemas" / "climate.schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        climate_schema = json.load(f)

    comp_schema = climate_schema["$defs"]["FarmVsNasaComparison"]
    # Validate against schema sub-definition
    validate(instance=comp_dict, schema=comp_schema)
    assert comp_dict["data_mode"] == "live"
    assert comp_dict["water_balance_status"] in [
        "severe_deficit",
        "moderate_deficit",
        "balanced",
        "excess_moisture",
    ]
