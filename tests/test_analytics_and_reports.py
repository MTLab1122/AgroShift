"""Module 04 Verification Suite: Analytics, Visualization & Reporting.

Verifies:
1. GET /api/v1/reports/csv produces formatted CSV with NASA climate provenance headers and values.
2. POST /api/v1/reports/pdf produces valid HTML advisory report containing reconciliation metrics and scenarios.
"""

import httpx
import pytest
from httpx import ASGITransport

from backend.app.main import app


@pytest.mark.asyncio
async def test_export_climate_csv_endpoint():
    """Verify CSV export contains correct headers and metadata."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/reports/csv",
            params={
                "farm_id": "farm-peshawar-001",
                "latitude": 34.0151,
                "longitude": 71.5249,
                "start_date": "2024-05-01",
                "end_date": "2024-05-03",
                "demo": True,
            },
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert "attachment; filename=" in resp.headers["content-disposition"]

        csv_text = resp.text
        assert "# AGROSHIFT NASA EARTH OBSERVATION CLIMATE EXPORT" in csv_text
        assert "date,temperature_mean_c,temperature_max_c" in csv_text
        assert "2024-05-01" in csv_text


@pytest.mark.asyncio
async def test_generate_advisory_report_endpoint():
    """Verify advisory report generation returns comprehensive HTML."""
    transport = ASGITransport(app=app)
    farm_profile = {
        "farm_id": "farm-report-test",
        "farm_name": "Tariq Khan Agro Parcel",
        "latitude": 34.0151,
        "longitude": 71.5249,
        "area_value": 5.0,
        "area_unit": "acres",
        "soil_type": "loamy",
        "irrigation_type": "canal",
        "water_availability": "medium",
        "current_crop": "wheat",
        "season": "Rabi",
        "crop_history": [],
    }

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/reports/pdf",
            json=farm_profile,
            params={"demo": True},
        )
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        html = resp.text
        assert "AgroShift Agricultural Advisory Report" in html
        assert "NASA Space Apps Challenge 2026" in html
        assert "NASA Climate &amp; Water Reconciliation" in html or "NASA Climate & Water Reconciliation" in html
        assert "Priority-Scored Crop Rotation Pathways" in html
        assert "Scientific Provenance &amp; Agronomic Disclaimer" in html or "Scientific Provenance & Agronomic Disclaimer" in html
