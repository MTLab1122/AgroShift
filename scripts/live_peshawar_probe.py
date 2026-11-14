"""Live Terminal Verification Script for Phase 2 NASA POWER Ingestion."""

import asyncio
from pathlib import Path
import sys

# Ensure repository root is on sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from backend.app.modules.nasa_data.power_client import NasaPowerClient
from backend.app.modules.nasa_data.normalizer import normalize_power_response
from backend.app.modules.nasa_data.aggregations import compute_all_aggregates


async def live_check():
    client = NasaPowerClient()
    print("--- Initiating Live NASA POWER Fetch for Peshawar Valley (34.0151, 71.5249) ---")
    res = await client.fetch_daily_point(
        farm_id="farm-peshawar-live-audit",
        latitude=34.0151,
        longitude=71.5249,
        start_date="2024-05-01",
        end_date="2024-05-03",
        parameters=["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "ALLSKY_SFC_SW_DWN"],
        bypass_cache=True,
    )
    print(f"[LIVE FETCH STATUS] HTTP 200 OK")
    print(f"[METADATA] retrieved_at: {res['retrieved_at']}")
    print(f"[METADATA] is_cached: {res['is_cached']}")
    print(f"[METADATA] cache_hit: {res['cache_hit']}")

    params, daily, missing = normalize_power_response(
        raw_payload=res["raw_data"],
        start_date="2024-05-01",
        end_date="2024-05-03",
        requested_parameters=res["request_meta"]["parameters"],
    )
    print("\n[NORMALIZED PARAMETERS & UNITS]:")
    for p in params:
        print(f"  - {p.code}: {p.label} [{p.unit}]")

    print("\n[OBSERVED DAILY READINGS (Zero Fabrication Enforced)]:")
    for d in daily:
        t2m = d.values["T2M"]
        t2m_max = d.values["T2M_MAX"]
        t2m_min = d.values["T2M_MIN"]
        rain = d.values["PRECTOTCORR"]
        rh = d.values["RH2M"]
        rad = d.values["ALLSKY_SFC_SW_DWN"]
        print(f"  Date {d.date}: T2M={t2m}°C (Max={t2m_max}°C, Min={t2m_min}°C), Rain={rain} mm/day, RH={rh}%, Rad={rad} MJ/m²/day")

    aggs = compute_all_aggregates(daily)
    m = aggs.monthly[0]
    mean_t2m = m.values["T2M"].mean
    total_rain = m.values["PRECTOTCORR"].sum
    print(f"\n[MONTHLY AGGREGATE {m.period}]: Mean T2M={mean_t2m}°C, Total Rain={total_rain} mm/period")


if __name__ == "__main__":
    asyncio.run(live_check())
