"""Phase 3 Verification Gate Test Suite for Normalizer and Aggregations.

Verifies:
1. Sentinel -999.0 and fill values strictly converted to None (never 0.0).
2. Edge cases: All-missing months result in None statistics (zero 0-imputation).
3. Partial-missing months correctly calculate mean/sum over valid days and record valid_days/coverage_ratio.
4. MissingDataSummary accurately tallies missing days and sets has_gaps=True.
5. End-to-end normalization and aggregation compiles into a valid ClimateSummary.
"""

import json
from datetime import date, timedelta
import pytest

from backend.app.modules.nasa_data.aggregations import (
    compute_all_aggregates,
    compute_monthly_aggregates,
    compute_seasonal_aggregates,
)
from backend.app.modules.nasa_data.normalizer import (
    is_sentinel_or_missing,
    normalize_power_response,
    parse_power_date_key,
)
from backend.app.modules.nasa_data.schemas import (
    ClimateSummary,
    DailyRecord,
)


def test_sentinel_detection():
    """Verify exact identification of NASA fill values."""
    assert is_sentinel_or_missing(-999.0) is True
    assert is_sentinel_or_missing(-999) is True
    assert is_sentinel_or_missing(-99.0) is True
    assert is_sentinel_or_missing(None) is True

    # Real zero is a valid observation (e.g., 0.0 mm rainfall, 0.0 °C freezing)
    assert is_sentinel_or_missing(0.0) is False
    assert is_sentinel_or_missing(0) is False
    assert is_sentinel_or_missing(25.4) is False
    assert is_sentinel_or_missing(-5.2) is False


def test_power_date_parsing():
    """Ensure YYYYMMDD is converted to ISO YYYY-MM-DD."""
    assert parse_power_date_key("20240501") == "2024-05-01"
    assert parse_power_date_key(20240501) == "2024-05-01"
    assert parse_power_date_key("2024-05-01") == "2024-05-01"

    with pytest.raises(ValueError):
        parse_power_date_key("invalid-date-format")


def test_normalizer_sentinel_to_none_conversion():
    """Verify raw -999.0 values are converted to None, while 0.0 is preserved."""
    raw_payload = {
        "properties": {
            "parameter": {
                "T2M": {
                    "20240501": 25.5,
                    "20240502": -999.0,  # Missing sentinel
                    "20240503": 0.0,  # Legitimate freezing zero
                },
                "PRECTOTCORR": {
                    "20240501": 0.0,  # Legitimate dry day
                    "20240502": -999.0,  # Missing sentinel
                    "20240503": 12.4,  # Rainy day
                },
            }
        }
    }

    params, daily_records, missing_summary = normalize_power_response(
        raw_payload=raw_payload,
        start_date="2024-05-01",
        end_date="2024-05-03",
    )

    assert len(daily_records) == 3

    # Day 1: normal
    assert daily_records[0].values["T2M"] == 25.5
    assert daily_records[0].values["PRECTOTCORR"] == 0.0

    # Day 2: sentinel must become None, NEVER 0.0
    assert daily_records[1].values["T2M"] is None
    assert daily_records[1].values["PRECTOTCORR"] is None

    # Day 3: true zero preserved
    assert daily_records[2].values["T2M"] == 0.0
    assert daily_records[2].values["PRECTOTCORR"] == 12.4

    # Missing counts
    assert missing_summary.total_days == 3
    assert missing_summary.missing_days_by_parameter["T2M"] == 1
    assert missing_summary.missing_days_by_parameter["PRECTOTCORR"] == 1
    assert missing_summary.has_gaps is True


def test_all_missing_month_yields_none_aggregates():
    """Verify an entire month of missing data yields None statistics, never 0.0."""
    # Create an entire month of 31 days with all -999.0 for PRECTOTCORR
    raw_payload = {
        "properties": {
            "parameter": {
                "PRECTOTCORR": {
                    f"202405{d:02d}": -999.0 for d in range(1, 32)
                },
                "T2M": {
                    f"202405{d:02d}": 30.0 for d in range(1, 32)
                },
            }
        }
    }

    params, daily_records, missing_summary = normalize_power_response(
        raw_payload=raw_payload,
        start_date="2024-05-01",
        end_date="2024-05-31",
    )

    monthly = compute_monthly_aggregates(daily_records)
    assert len(monthly) == 1
    m = monthly[0]
    assert m.period == "2024-05"
    assert m.total_days == 31

    # PRECTOTCORR was completely missing
    prec_stat = m.values["PRECTOTCORR"]
    assert prec_stat.sum is None, "All-missing sum must be None, NOT 0.0!"
    assert prec_stat.mean is None, "All-missing mean must be None, NOT 0.0!"
    assert prec_stat.min is None
    assert prec_stat.max is None

    # T2M had valid data
    t2m_stat = m.values["T2M"]
    assert t2m_stat.mean == 30.0


def test_partial_missing_month_aggregates_correctly():
    """Verify month with 2 missing days out of 10 calculates sums/means correctly."""
    records = []
    # 10 days in May: 8 days with 5.0 mm rain, 2 days missing (None)
    for day in range(1, 11):
        ds = f"2024-05-{day:02d}"
        val = None if day in (3, 7) else 5.0
        records.append(DailyRecord(date=ds, values={"PRECTOTCORR": val, "T2M": 25.0}))

    monthly = compute_monthly_aggregates(records)
    assert len(monthly) == 1
    m = monthly[0]
    assert m.total_days == 10
    assert m.valid_days == 8
    assert m.coverage_ratio == 0.8

    # 8 valid days * 5.0 = 40.0 sum
    prec_stat = m.values["PRECTOTCORR"]
    assert prec_stat.sum == 40.0
    assert prec_stat.mean == 5.0
    assert prec_stat.min == 5.0
    assert prec_stat.max == 5.0


def test_seasonal_aggregation_classification():
    """Verify classification into Kharif (May-Oct) and Rabi (Nov-Apr)."""
    records = [
        DailyRecord(date="2024-05-15", values={"T2M": 32.0, "PRECTOTCORR": 10.0}),
        DailyRecord(date="2024-07-20", values={"T2M": 35.0, "PRECTOTCORR": 50.0}),
        DailyRecord(date="2024-11-10", values={"T2M": 18.0, "PRECTOTCORR": 0.0}),
        DailyRecord(date="2024-12-05", values={"T2M": 14.0, "PRECTOTCORR": 5.0}),
    ]

    seasonal = compute_seasonal_aggregates(records)
    season_names = {s.season for s in seasonal}
    assert "Kharif" in season_names
    assert "Rabi" in season_names

    kharif_s = next(s for s in seasonal if s.season == "Kharif")
    assert kharif_s.total_days == 2
    assert kharif_s.values["PRECTOTCORR"].sum == 60.0
    assert kharif_s.values["T2M"].mean == 33.5


def test_full_pipeline_produces_valid_climate_summary():
    """Verify normalizing raw NASA payload and aggregating yields a strictly valid ClimateSummary."""
    raw_payload = {
        "properties": {
            "parameter": {
                "T2M": {"20240501": 28.0, "20240502": 29.0},
                "PRECTOTCORR": {"20240501": 0.0, "20240502": -999.0},
            }
        }
    }

    params, daily_records, missing_data = normalize_power_response(
        raw_payload=raw_payload,
        start_date="2024-05-01",
        end_date="2024-05-02",
    )
    aggregates = compute_all_aggregates(daily_records)

    summary = ClimateSummary(
        farm_id="farm-peshawar-001",
        source="NASA POWER Daily API",
        product_or_dataset="MERRA-2 / GEOS-5 FP-IT via POWER AG",
        latitude=34.0151,
        longitude=71.5249,
        start_date="2024-05-01",
        end_date="2024-05-02",
        parameters=params,
        daily_series=daily_records,
        aggregates=aggregates,
        missing_data=missing_data,
        retrieved_at="2026-11-14T00:00:00Z",
        coverage_note="Gridded NASA satellite and reanalysis data represents regional grid cells (~0.5° × 0.5°), not direct on-farm in-situ sensor measurements.",
        is_demo_data=False,
    )

    assert summary.farm_id == "farm-peshawar-001"
    assert summary.missing_data.has_gaps is True
    assert summary.aggregates.monthly[0].values["PRECTOTCORR"].sum == 0.0
    assert summary.daily_series[1].values["PRECTOTCORR"] is None
