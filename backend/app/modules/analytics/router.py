"""FastAPI Router for Module 04: Analytics, Visualization & Reporting.

Endpoints:
- GET /api/v1/reports/csv: Export verified NASA daily climate time series as downloadable CSV.
- POST /api/v1/reports/summary: Generate complete printable advisory report JSON / HTML structure.
- GET /api/v1/analytics/trends: Aggregate seasonal trends comparing recent observations against historical normal.
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Query, Request, Response, status
from fastapi.responses import HTMLResponse, PlainTextResponse, Response as FastAPIResponse

from backend.app.core.gateway import gateway
from backend.app.core.middleware import get_request_id
from backend.app.modules.agro_engine.comparator import compare_farm_to_climate
from backend.app.modules.agro_engine.recommendation_engine import generate_recommendations
from backend.app.modules.nasa_data.power_client import NasaPowerClient
from backend.app.schemas.farm import FarmProfile
from backend.app.schemas.recommendation import RecommendationSet

logger = logging.getLogger("agroshift.analytics")
router = APIRouter(tags=["Analytics, Visualization & Reporting (Module 04)"])

power_client = NasaPowerClient()


@router.get(
    "/api/v1/reports/csv",
    summary="Export NASA Daily Environmental Data as CSV",
    response_class=PlainTextResponse,
)
async def export_climate_csv(
    request: Request,
    response: Response,
    farm_id: str = Query("farm-peshawar-001"),
    latitude: float = Query(34.0151),
    longitude: float = Query(71.5249),
    start_date: str = Query("2024-05-01"),
    end_date: str = Query("2024-05-15"),
    demo: bool = Query(False),
) -> FastAPIResponse:
    """Export daily NASA observations in standard CSV format with provenance metadata."""
    req_id = get_request_id(request)

    climate_summary, mode = await gateway.get_climate_summary(
        power_client=power_client,
        farm_id=farm_id,
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
        parameters=["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "ALLSKY_SFC_SW_DWN"],
        include_daily=True,
        force_demo=demo,
        request_id=req_id,
        response=response,
    )

    # Format CSV in-memory
    output = io.StringIO()
    writer = csv.writer(output)

    # Metadata headers
    writer.writerow(["# AGROSHIFT NASA EARTH OBSERVATION CLIMATE EXPORT"])
    writer.writerow(["# Source", climate_summary.source])
    writer.writerow(["# Product", climate_summary.product_or_dataset])
    writer.writerow(["# Coordinates", f"Lat: {latitude}, Lon: {longitude}"])
    writer.writerow(["# Window", f"{start_date} to {end_date}"])
    writer.writerow(["# Retrieved At", climate_summary.retrieved_at])
    writer.writerow(["# Coverage Note", climate_summary.coverage_note])
    writer.writerow(["# Data Mode", mode.value if hasattr(mode, "value") else str(mode)])
    writer.writerow([])

    # Table columns
    writer.writerow([
        "date",
        "temperature_mean_c",
        "temperature_max_c",
        "temperature_min_c",
        "precipitation_mm_day",
        "relative_humidity_pct",
        "solar_irradiance_mj_m2_day",
    ])

    # Rows
    for d in (climate_summary.daily_series or []):
        vals = d.values
        writer.writerow([
            d.date,
            vals.get("T2M") if vals.get("T2M") is not None else "",
            vals.get("T2M_MAX") if vals.get("T2M_MAX") is not None else "",
            vals.get("T2M_MIN") if vals.get("T2M_MIN") is not None else "",
            vals.get("PRECTOTCORR") if vals.get("PRECTOTCORR") is not None else "",
            vals.get("RH2M") if vals.get("RH2M") is not None else "",
            vals.get("ALLSKY_SFC_SW_DWN") if vals.get("ALLSKY_SFC_SW_DWN") is not None else "",
        ])

    csv_content = output.getvalue()
    filename = f"agroshift_nasa_data_{farm_id}_{start_date}_{end_date}.csv"

    return FastAPIResponse(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-AgroShift-Data-Mode": mode.value if hasattr(mode, "value") else str(mode),
        },
    )


@router.post(
    "/api/v1/reports/pdf",
    summary="Generate Printable Agricultural Advisory Report (HTML/Print)",
    response_class=HTMLResponse,
)
async def generate_advisory_pdf_report(
    request: Request,
    response: Response,
    farm_profile: FarmProfile = Body(...),
    demo: bool = Query(False),
) -> HTMLResponse:
    """Generate a clean, printable HTML advisory report styled for A4 paper and PDF printing."""
    req_id = get_request_id(request)

    # Fetch live NASA summary
    climate_summary, mode = await gateway.get_climate_summary(
        power_client=power_client,
        farm_id=farm_profile.farm_id,
        latitude=farm_profile.latitude,
        longitude=farm_profile.longitude,
        start_date="2024-05-01",
        end_date="2024-10-31",
        parameters=["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "ALLSKY_SFC_SW_DWN"],
        include_daily=True,
        force_demo=demo,
        request_id=req_id,
        response=response,
    )

    comparison = compare_farm_to_climate(farm_profile, climate_summary, data_mode=mode)
    recommendations = generate_recommendations(farm_profile, climate_summary, comparison, data_mode=mode)

    pulse = recommendations.scenarios.pulse_inclusive
    baseline = recommendations.scenarios.baseline
    cover = recommendations.scenarios.soil_cover

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>AgroShift Advisory Report — {farm_profile.farm_name}</title>
    <style>
        body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #1e293b; line-height: 1.5; padding: 30px; }}
        .header {{ border-bottom: 2px solid #059669; padding-bottom: 12px; margin-bottom: 24px; }}
        .title {{ font-size: 24px; font-weight: bold; color: #065f46; }}
        .subtitle {{ font-size: 13px; color: #64748b; margin-top: 4px; }}
        .section {{ margin-bottom: 20px; }}
        .section-title {{ font-size: 16px; font-weight: bold; color: #0f172a; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; margin-bottom: 8px; }}
        .grid {{ display: flex; gap: 16px; margin-bottom: 16px; }}
        .card {{ flex: 1; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px; font-size: 13px; }}
        .metric {{ font-size: 20px; font-weight: bold; color: #047857; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
        .badge-deficit {{ background: #fee2e2; color: #991b1b; }}
        .badge-balanced {{ background: #dcfce7; color: #166534; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 12px; }}
        th, td {{ border: 1px solid #cbd5e1; padding: 8px; text-align: left; }}
        th {{ background: #f1f5f9; }}
        .disclaimer {{ background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 6px; padding: 10px; font-size: 11px; color: #1e40af; margin-top: 24px; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="title">AgroShift Agricultural Advisory Report</div>
        <div class="subtitle">NASA Space Apps Challenge 2026 • Team InCir (Abasyn University Peshawar)</div>
        <div class="subtitle">Farm: <strong>{farm_profile.farm_name}</strong> ({farm_profile.farm_id}) | Coordinates: {farm_profile.latitude}°N, {farm_profile.longitude}°E | Date: {recommendations.generated_at[:10]}</div>
    </div>

    <div class="section">
        <div class="section-title">1. NASA Climate & Water Reconciliation</div>
        <div class="grid">
            <div class="card">
                <div>Observed NASA Precipitation</div>
                <div class="metric">{comparison.observed_rainfall_mm:.1f} mm</div>
                <div>Demand: {comparison.expected_crop_water_need_mm:.0f} mm ({farm_profile.current_crop.capitalize()})</div>
            </div>
            <div class="card">
                <div>Water Balance Status</div>
                <div class="metric"><span class="badge { 'badge-balanced' if comparison.water_balance_status == 'balanced' else 'badge-deficit' }">{comparison.water_balance_status.upper().replace('_', ' ')}</span></div>
                <div>Reported: {farm_profile.irrigation_type.capitalize()} ({farm_profile.water_availability} availability)</div>
            </div>
            <div class="card">
                <div>Thermal Stress Events</div>
                <div class="metric">{comparison.thermal_stress_days} days</div>
                <div>Above critical heat threshold</div>
            </div>
        </div>
        <div style="font-size: 12px; background: #f8fafc; padding: 10px; border-left: 4px solid #0284c7; border-radius: 4px;">
            <strong>Agronomic Analysis:</strong> {comparison.irrigation_adequacy_note}
        </div>
    </div>

    <div class="section">
        <div class="section-title">2. Priority-Scored Crop Rotation Pathways</div>
        <table>
            <thead>
                <tr>
                    <th>Pathway</th>
                    <th>Crop Sequence</th>
                    <th>Priority Score</th>
                    <th>Water Efficiency</th>
                    <th>Soil Health & N Benefit</th>
                    <th>Key Advantage</th>
                </tr>
            </thead>
            <tbody>
                <tr style="background: #f0fdf4;">
                    <td><strong>Recommended (Pulse)</strong></td>
                    <td>{' → '.join(pulse.crop_sequence).upper()}</td>
                    <td><strong>{pulse.score:.1f}/100</strong></td>
                    <td>{pulse.score_breakdown.water_efficiency}%</td>
                    <td>{pulse.score_breakdown.soil_health_benefit}%</td>
                    <td>{pulse.benefits[0]}</td>
                </tr>
                <tr>
                    <td><strong>Cover / Forage</strong></td>
                    <td>{' → '.join(cover.crop_sequence).upper()}</td>
                    <td><strong>{cover.score:.1f}/100</strong></td>
                    <td>{cover.score_breakdown.water_efficiency}%</td>
                    <td>{cover.score_breakdown.soil_health_benefit}%</td>
                    <td>{cover.benefits[0]}</td>
                </tr>
                <tr style="color: #64748b;">
                    <td><strong>Baseline Conventional</strong></td>
                    <td>{' → '.join(baseline.crop_sequence).upper()}</td>
                    <td>{baseline.score:.1f}/100</td>
                    <td>{baseline.score_breakdown.water_efficiency}%</td>
                    <td>{baseline.score_breakdown.soil_health_benefit}%</td>
                    <td>{baseline.rationale[0]}</td>
                </tr>
            </tbody>
        </table>
    </div>

    <div class="disclaimer">
        <strong>Scientific Provenance & Agronomic Disclaimer:</strong><br>
        NASA gridded satellite/reanalysis data (NASA POWER AG, MERRA-2) represents regional grid cells (~50 km × 50 km), not on-farm sensors. Recommendations are decision-support insights and do not constitute guaranteed yields or profits. Verify seed varieties and application rates with local Khyber Pakhtunkhwa Agriculture Extension officers.
    </div>
</body>
</html>"""

    return HTMLResponse(content=html_content)
