"""Live Terminal Demonstration Script for Phase 3 Farm-vs-NASA Comparison Engine."""

import asyncio
from pathlib import Path
import sys

# Ensure repository root is on sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from backend.app.modules.agro_engine.comparator import (
    compare_farm_to_climate,
    evaluate_rotation_monoculture,
)
from backend.app.modules.agro_engine.crop_catalog import get_crop_profile
from backend.app.modules.nasa_data.aggregations import compute_all_aggregates
from backend.app.modules.nasa_data.normalizer import normalize_power_response
from backend.app.modules.nasa_data.power_client import NasaPowerClient
from backend.app.modules.nasa_data.schemas import (
    ClimateSummary,
    MissingDataSummary,
)
from backend.app.schemas.farm import CropHistoryEntry, FarmProfile


async def main():
    print("=" * 78)
    print("AGROSHIFT PHASE 3: LIVE NASA OBSERVATIONS VS. FARM PROFILE COMPARISON")
    print("=" * 78)

    # 1. Fetch live NASA POWER observations for Peshawar Valley
    lat, lon = 34.0151, 71.5249
    start_date = "2024-05-01"
    end_date = "2024-05-05"
    client = NasaPowerClient()

    print(f"\n[STEP 1] Fetching live NASA POWER Daily data for Peshawar ({lat}, {lon})...")
    raw_res = await client.fetch_daily_point(
        farm_id="farm-peshawar-demo",
        latitude=lat,
        longitude=lon,
        start_date=start_date,
        end_date=end_date,
        parameters=["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "ALLSKY_SFC_SW_DWN"],
    )

    params_meta, daily_records, missing_summary = normalize_power_response(
        raw_payload=raw_res["raw_data"],
        start_date=start_date,
        end_date=end_date,
        requested_parameters=raw_res["request_meta"]["parameters"],
    )
    aggs = compute_all_aggregates(daily_records)

    climate_summary = ClimateSummary(
        farm_id="farm-peshawar-demo",
        source="NASA POWER Daily API",
        product_or_dataset="MERRA-2 via POWER AG",
        latitude=lat,
        longitude=lon,
        start_date=start_date,
        end_date=end_date,
        parameters=params_meta,
        aggregates=aggs,
        missing_data=missing_summary,
        retrieved_at=raw_res["retrieved_at"],
        coverage_note="Gridded NASA satellite & reanalysis data represents regional grid cells (~0.5° × 0.5°).",
        daily_series=daily_records,
    )
    print(f" -> Fetched {len(daily_records)} daily observations successfully.")
    for d in daily_records:
        t_max = d.values.get("T2M_MAX")
        precip = d.values.get("PRECTOTCORR")
        print(f"    Date {d.date}: T2M_MAX={t_max}°C, Rain={precip} mm/day")

    # 2. Define Farmer Profile A: Rain-fed Barani Wheat Parcel
    farm_a = FarmProfile(
        farm_id="farm-peshawar-barani",
        farm_name="Tariq Khan Barani Parcel",
        latitude=lat,
        longitude=lon,
        area_value=4.0,
        area_unit="acres",
        soil_type="sandy",
        irrigation_type="rain_fed",
        water_availability="low",
        current_crop="wheat",
        season="Rabi",
        crop_history=[
            CropHistoryEntry(entry_id="h1", crop_name="maize", season="Kharif", year=2023),
            CropHistoryEntry(entry_id="h2", crop_name="wheat", season="Rabi", year=2022),
        ],
    )

    # 3. Define Farmer Profile B: Canal Irrigated Parcel
    farm_b = FarmProfile(
        farm_id="farm-peshawar-canal",
        farm_name="Haji Rehman Canal Parcel",
        latitude=lat,
        longitude=lon,
        area_value=8.0,
        area_unit="acres",
        soil_type="clay_loam",
        irrigation_type="canal",
        water_availability="high",
        current_crop="wheat",
        season="Rabi",
        crop_history=[
            CropHistoryEntry(entry_id="h1", crop_name="chickpea", season="Rabi", year=2023),
        ],
    )

    # 4. Run Comparison Engine
    print("\n[STEP 2] Running Comparator for Farm A (Rain-fed Barani)...")
    comp_a = compare_farm_to_climate(farm_a, climate_summary, data_mode="live")
    rot_a = evaluate_rotation_monoculture(farm_a.current_crop, farm_a.crop_history)

    print("--- Farm A Comparison Result ---")
    print(f"  Observed Rain: {comp_a.observed_rainfall_mm} mm")
    print(f"  Crop Water Demand: {comp_a.expected_crop_water_need_mm} mm")
    print(f"  Water Balance Status: {comp_a.water_balance_status}")
    print(f"  Thermal Stress Days: {comp_a.thermal_stress_days}")
    print(f"  Adequacy Note: {comp_a.irrigation_adequacy_note}")
    print(f"  Monoculture Risk: {rot_a['monoculture_risk']} (Consecutive Cereals: {rot_a['consecutive_cereal_seasons']})")
    print(f"  Nitrogen Debt Warning: {rot_a['nitrogen_debt_warning']}")

    print("\n[STEP 3] Running Comparator for Farm B (Canal Irrigated)...")
    comp_b = compare_farm_to_climate(farm_b, climate_summary, data_mode="live")
    rot_b = evaluate_rotation_monoculture(farm_b.current_crop, farm_b.crop_history)

    print("--- Farm B Comparison Result ---")
    print(f"  Observed Rain: {comp_b.observed_rainfall_mm} mm")
    print(f"  Crop Water Demand: {comp_b.expected_crop_water_need_mm} mm")
    print(f"  Water Balance Status: {comp_b.water_balance_status}")
    print(f"  Thermal Stress Days: {comp_b.thermal_stress_days}")
    print(f"  Adequacy Note: {comp_b.irrigation_adequacy_note}")
    print(f"  Legume Break Present: {rot_b['has_legume_break']}")
    print(f"  Monoculture Risk: {rot_b['monoculture_risk']}")

    print("\n" + "=" * 78)
    print("PHASE 3 VERIFICATION COMPLETE: ALL OBSERVATIONS GROUNDED IN REAL NASA DATA")
    print("=" * 78)


if __name__ == "__main__":
    asyncio.run(main())
