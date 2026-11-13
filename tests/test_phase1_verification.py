"""Phase 1 Verification Gate Test Suite.

Validates:
1. Canonical JSON Schema validation for data/demo/climate.mock.json.
2. Pydantic v2 ClimateSummary model validation and field integrity.
3. Strict pre-network request validation for coordinates, date intervals, and archive coverage.
4. ApiError canonical structure.
"""

from datetime import date
import json
from pathlib import Path
import pytest
from jsonschema import validate as jsonschema_validate
from pydantic import ValidationError

from backend.app.modules.nasa_data.schemas import (
    ApiError,
    ClimateRequest,
    ClimateSummary,
    NASA_POWER_EARLIEST_DATE,
)

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
MOCK_FIXTURE_PATH = WORKSPACE_ROOT / "data" / "demo" / "climate.mock.json"
JSON_SCHEMA_PATH = WORKSPACE_ROOT / "shared" / "schemas" / "climate.schema.json"


def test_mock_fixture_exists():
    """Ensure data/demo/climate.mock.json exists."""
    assert MOCK_FIXTURE_PATH.is_file(), f"Mock fixture missing at {MOCK_FIXTURE_PATH}"


def test_json_schema_exists():
    """Ensure shared/schemas/climate.schema.json exists."""
    assert JSON_SCHEMA_PATH.is_file(), f"JSON schema missing at {JSON_SCHEMA_PATH}"


def test_mock_fixture_validates_against_json_schema():
    """Verify data/demo/climate.mock.json validates against climate.schema.json."""
    with open(JSON_SCHEMA_PATH, "r", encoding="utf-8") as sf:
        schema = json.load(sf)
    with open(MOCK_FIXTURE_PATH, "r", encoding="utf-8") as df:
        data = json.load(df)

    # jsonschema.validate raises ValidationError if schema is violated
    jsonschema_validate(instance=data, schema=schema)


def test_mock_fixture_validates_against_pydantic_climate_summary():
    """Verify data/demo/climate.mock.json parses cleanly into Pydantic ClimateSummary."""
    with open(MOCK_FIXTURE_PATH, "r", encoding="utf-8") as df:
        raw_text = df.read()

    summary = ClimateSummary.model_validate_json(raw_text)

    # Core attribute verifications
    assert summary.farm_id == "farm-peshawar-001"
    assert summary.latitude == 34.0151
    assert summary.longitude == 71.5249
    assert summary.start_date == "2024-05-01"
    assert summary.end_date == "2024-10-31"
    assert summary.is_demo_data is True
    assert "gridded" in summary.coverage_note.lower()

    # Parameter code and unit checks
    param_codes = {p.code for p in summary.parameters}
    assert {"T2M", "PRECTOTCORR", "RH2M", "ALLSKY_SFC_SW_DWN"}.issubset(param_codes)

    # Aggregates integrity
    assert len(summary.aggregates.monthly) == 6
    assert len(summary.aggregates.seasonal) >= 1
    assert summary.aggregates.seasonal[0].season == "Kharif"

    # Missing data and null handling integrity (Zero fabrication)
    assert summary.missing_data.total_days == 184
    assert summary.missing_data.has_gaps is True
    assert summary.missing_data.missing_days_by_parameter["PRECTOTCORR"] == 1
    assert summary.missing_data.missing_days_by_parameter["RH2M"] == 2

    # Verify daily series contains deliberate nulls and they are not converted to 0
    assert summary.daily_series is not None
    gap_day_1 = next(d for d in summary.daily_series if d.date == "2024-06-15")
    assert gap_day_1.values["PRECTOTCORR"] is None
    assert gap_day_1.values["RH2M"] is None
    assert gap_day_1.values["T2M"] is not None  # Other params still exist

    gap_day_2 = next(d for d in summary.daily_series if d.date == "2024-08-20")
    assert gap_day_2.values["RH2M"] is None


def test_valid_climate_request():
    """Verify a valid pre-network ClimateRequest passes validation cleanly."""
    req = ClimateRequest(
        farm_id="farm-peshawar-001",
        latitude=34.0151,
        longitude=71.5249,
        start_date="2024-05-01",
        end_date="2024-10-31",
        parameters=["T2M", "PRECTOTCORR"],
        include_daily=True,
    )
    assert req.latitude == 34.0151
    assert req.longitude == 71.5249
    assert req.farm_id == "farm-peshawar-001"


@pytest.mark.parametrize(
    "invalid_lat",
    [90.1, -90.1, 180.0, -999.0],
)
def test_climate_request_rejects_invalid_latitude(invalid_lat):
    """Ensure latitude outside [-90.0, 90.0] is rejected pre-network."""
    with pytest.raises(ValidationError) as excinfo:
        ClimateRequest(
            farm_id="test-farm",
            latitude=invalid_lat,
            longitude=71.5249,
            start_date="2024-05-01",
            end_date="2024-10-31",
        )
    assert "Latitude" in str(excinfo.value) or "less than or equal" in str(excinfo.value)


@pytest.mark.parametrize(
    "invalid_lon",
    [180.1, -180.1, 360.0, -999.0],
)
def test_climate_request_rejects_invalid_longitude(invalid_lon):
    """Ensure longitude outside [-180.0, 180.0] is rejected pre-network."""
    with pytest.raises(ValidationError) as excinfo:
        ClimateRequest(
            farm_id="test-farm",
            latitude=34.0151,
            longitude=invalid_lon,
            start_date="2024-05-01",
            end_date="2024-10-31",
        )
    assert "Longitude" in str(excinfo.value) or "less than or equal" in str(excinfo.value)


def test_climate_request_rejects_inverted_dates():
    """Ensure start_date > end_date is cleanly caught and rejected."""
    with pytest.raises(ValidationError) as excinfo:
        ClimateRequest(
            farm_id="test-farm",
            latitude=34.0151,
            longitude=71.5249,
            start_date="2024-10-31",
            end_date="2024-05-01",
        )
    assert "cannot be later than end_date" in str(excinfo.value)


def test_climate_request_rejects_date_before_nasa_power_archive():
    """Ensure dates preceding NASA POWER 1981 archive are rejected pre-network."""
    with pytest.raises(ValidationError) as excinfo:
        ClimateRequest(
            farm_id="test-farm",
            latitude=34.0151,
            longitude=71.5249,
            start_date="1975-01-01",
            end_date="1975-12-31",
        )
    assert "precedes NASA POWER archive coverage" in str(excinfo.value)


def test_climate_request_rejects_invalid_iso_format():
    """Ensure malformed date strings fail fast."""
    with pytest.raises(ValidationError) as excinfo:
        ClimateRequest(
            farm_id="test-farm",
            latitude=34.0151,
            longitude=71.5249,
            start_date="05/01/2024",
            end_date="2024-10-31",
        )
    assert "must match ISO format" in str(excinfo.value)


def test_climate_request_rejects_unsupported_parameter():
    """Ensure unknown parameter codes are rejected pre-network."""
    with pytest.raises(ValidationError) as excinfo:
        ClimateRequest(
            farm_id="test-farm",
            latitude=34.0151,
            longitude=71.5249,
            start_date="2024-05-01",
            end_date="2024-10-31",
            parameters=["T2M", "FABRICATED_PARAM"],
        )
    assert "Unsupported parameter" in str(excinfo.value)


def test_canonical_api_error_model():
    """Verify ApiError matches shared schema contract."""
    err = ApiError(
        error_code="INVALID_COORDINATES",
        message="Latitude must be between -90.0 and 90.0 decimal degrees.",
        details={"latitude": 95.0, "valid_range": [-90.0, 90.0]},
        request_id="req-12345",
    )
    dumped = err.model_dump()
    assert dumped["error_code"] == "INVALID_COORDINATES"
    assert dumped["message"] == "Latitude must be between -90.0 and 90.0 decimal degrees."
    assert dumped["details"]["latitude"] == 95.0
    assert dumped["request_id"] == "req-12345"
