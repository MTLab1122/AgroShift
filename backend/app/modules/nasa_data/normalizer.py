"""NASA POWER Response Normalization & Missing-Data Sentinel Handling for Module 02.

Enforces:
- Parsing raw NASA POWER properties.parameter dictionaries into ordered ISO daily records.
- Strict mapping of sentinel missing values (-999, -999.0) to None (null) with zero 0-imputation.
- Accurate parameter metadata (labels, standard units) attachment.
- Precise missing-data audit counts per parameter.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.modules.nasa_data.schemas import (
    DailyRecord,
    MissingDataSummary,
    ParameterMetadata,
)

logger = logging.getLogger(__name__)

# Standard parameter catalog with official units and descriptions
VERIFIED_PARAMETERS: Dict[str, Dict[str, str]] = {
    "T2M": {
        "label": "Temperature at 2 Meters",
        "unit": "°C",
    },
    "T2M_MIN": {
        "label": "Minimum Temperature at 2 Meters",
        "unit": "°C",
    },
    "T2M_MAX": {
        "label": "Maximum Temperature at 2 Meters",
        "unit": "°C",
    },
    "PRECTOTCORR": {
        "label": "Precipitation Corrected",
        "unit": "mm/day",
    },
    "RH2M": {
        "label": "Relative Humidity at 2 Meters",
        "unit": "%",
    },
    "ALLSKY_SFC_SW_DWN": {
        "label": "All Sky Surface Shortwave Downward Irradiance",
        "unit": "MJ/m^2/day",
    },
}

# Values that indicate missing / invalid measurements in NASA POWER
SENTINEL_VALUES: Set[float] = {-999.0, -999, -99.0}


def is_sentinel_or_missing(val: Any) -> bool:
    """Determine whether a raw value represents a NASA fill/sentinel or missing reading."""
    if val is None:
        return True
    if isinstance(val, (int, float)):
        # Check against common NASA fill values
        if any(abs(float(val) - s) < 1e-3 for s in SENTINEL_VALUES):
            return True
    return False


def parse_power_date_key(raw_date_key: str) -> str:
    """Convert raw POWER date format (YYYYMMDD) to ISO format (YYYY-MM-DD)."""
    raw_str = str(raw_date_key).strip()
    if len(raw_str) == 8 and raw_str.isdigit():
        return f"{raw_str[:4]}-{raw_str[4:6]}-{raw_str[6:]}"
    # If already in ISO format
    if len(raw_str) == 10 and raw_str[4] == "-" and raw_str[7] == "-":
        return raw_str
    raise ValueError(f"Unrecognized date format from NASA POWER: '{raw_date_key}'")


def normalize_power_response(
    raw_payload: Dict[str, Any],
    start_date: str,
    end_date: str,
    requested_parameters: Optional[List[str]] = None,
) -> Tuple[List[ParameterMetadata], List[DailyRecord], MissingDataSummary]:
    """Normalize raw NASA POWER JSON into canonical DailyRecord list and MissingDataSummary.

    Strictly converts all -999.0 entries to None. NEVER defaults missing values to 0.0.
    """
    properties = raw_payload.get("properties", {})
    raw_parameters = properties.get("parameter", {})

    if not raw_parameters:
        raise ValueError("NASA POWER response contains empty or missing 'properties.parameter' data.")

    # Determine parameters to process
    active_param_codes = (
        [p for p in requested_parameters if p in raw_parameters]
        if requested_parameters
        else list(raw_parameters.keys())
    )

    # Build ParameterMetadata list
    param_metadata_list: List[ParameterMetadata] = []
    for code in active_param_codes:
        meta = VERIFIED_PARAMETERS.get(
            code,
            {"label": f"Environmental Parameter {code}", "unit": "units"},
        )
        param_metadata_list.append(
            ParameterMetadata(
                code=code,
                label=meta["label"],
                unit=meta["unit"],
            )
        )

    # Build complete expected date sequence between start_date and end_date
    start_d = date.fromisoformat(start_date)
    end_d = date.fromisoformat(end_date)
    expected_dates: List[str] = []
    curr = start_d
    while curr <= end_d:
        expected_dates.append(curr.isoformat())
        curr += timedelta(days=1)

    total_days = len(expected_dates)
    missing_counts: Dict[str, int] = {code: 0 for code in active_param_codes}
    daily_records: List[DailyRecord] = []

    # Map raw parameters by normalized ISO date key
    parsed_by_param: Dict[str, Dict[str, Optional[float]]] = {}
    for code in active_param_codes:
        parsed_by_param[code] = {}
        param_dict = raw_parameters.get(code, {})
        for raw_d, val in param_dict.items():
            iso_d = parse_power_date_key(raw_d)
            if is_sentinel_or_missing(val):
                parsed_by_param[code][iso_d] = None
            else:
                try:
                    parsed_by_param[code][iso_d] = round(float(val), 2)
                except (ValueError, TypeError):
                    parsed_by_param[code][iso_d] = None

    # Construct chronological DailyRecord sequence
    for iso_d in expected_dates:
        record_values: Dict[str, Optional[float]] = {}
        for code in active_param_codes:
            val = parsed_by_param[code].get(iso_d, None)
            record_values[code] = val
            if val is None:
                missing_counts[code] += 1

        daily_records.append(DailyRecord(date=iso_d, values=record_values))

    has_gaps = any(count > 0 for count in missing_counts.values())

    notes: Optional[str] = None
    if has_gaps:
        gap_details = [f"{c}: {n} missing days" for c, n in missing_counts.items() if n > 0]
        notes = f"Observation gaps identified: {'; '.join(gap_details)}. Sentinel -999 mapped to null."

    missing_summary = MissingDataSummary(
        total_days=total_days,
        missing_days_by_parameter=missing_counts,
        has_gaps=has_gaps,
        notes=notes,
    )

    return param_metadata_list, daily_records, missing_summary
