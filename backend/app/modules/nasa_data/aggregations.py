"""Monthly & Seasonal Climate Aggregations Engine for Module 02.

Computes:
- Calendar monthly aggregates (YYYY-MM).
- Agro-ecological seasonal aggregates (Kharif: May-Oct, Rabi: Nov-Apr).
- Explicit scientific aggregation methods per parameter (mean for temperature/radiation/humidity, cumulative sum for precipitation).
- Transparent handling of null days without false 0-imputation (nulls skipped, valid days counted, null metric returned if all days missing).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from backend.app.modules.nasa_data.schemas import (
    AggregatesSummary,
    DailyRecord,
    MetricStatistics,
    MonthlyAggregate,
    SeasonalAggregate,
)

# Standard parameter aggregation methods
AGGREGATION_METHODS: Dict[str, str] = {
    "T2M": "mean",
    "T2M_MIN": "mean",
    "T2M_MAX": "mean",
    "PRECTOTCORR": "sum",
    "RH2M": "mean",
    "ALLSKY_SFC_SW_DWN": "mean",
}

PARAMETER_UNITS: Dict[str, str] = {
    "T2M": "°C",
    "T2M_MIN": "°C",
    "T2M_MAX": "°C",
    "PRECTOTCORR": "mm",
    "RH2M": "%",
    "ALLSKY_SFC_SW_DWN": "MJ/m^2/day",
}


def compute_metric_statistics(values: List[Optional[float]], method: str, unit: str) -> MetricStatistics:
    """Compute statistics for a collection of daily values, transparently skipping None.

    Returns null metrics if there are zero valid observations (NEVER returns synthetic 0).
    """
    valid_nums = [v for v in values if v is not None]
    if not valid_nums:
        return MetricStatistics(mean=None, sum=None, min=None, max=None, unit=unit)

    min_val = round(min(valid_nums), 2)
    max_val = round(max(valid_nums), 2)

    if method == "sum":
        sum_val = round(sum(valid_nums), 2)
        mean_val = round(sum_val / len(valid_nums), 2)
        return MetricStatistics(mean=mean_val, sum=sum_val, min=min_val, max=max_val, unit=f"{unit}/period")
    else:  # default to mean
        mean_val = round(sum(valid_nums) / len(valid_nums), 2)
        return MetricStatistics(mean=mean_val, sum=None, min=min_val, max=max_val, unit=unit)


def compute_monthly_aggregates(daily_records: List[DailyRecord]) -> List[MonthlyAggregate]:
    """Group daily records by YYYY-MM and compute monthly statistics."""
    if not daily_records:
        return []

    # Group by YYYY-MM
    grouped: Dict[str, List[DailyRecord]] = defaultdict(list)
    for rec in daily_records:
        month_key = rec.date[:7]
        grouped[month_key].append(rec)

    monthly_list: List[MonthlyAggregate] = []

    for month_key in sorted(grouped.keys()):
        records = grouped[month_key]
        total_days = len(records)

        # Discover all parameter codes present
        param_codes = set()
        for r in records:
            param_codes.update(r.values.keys())

        param_values: Dict[str, MetricStatistics] = {}
        min_valid_days = total_days

        for code in sorted(param_codes):
            vals = [r.values.get(code) for r in records]
            method = AGGREGATION_METHODS.get(code, "mean")
            unit = PARAMETER_UNITS.get(code, "units")
            stat = compute_metric_statistics(vals, method, unit)
            param_values[code] = stat

            valid_count = len([v for v in vals if v is not None])
            if valid_count < min_valid_days:
                min_valid_days = valid_count

        coverage = round(min_valid_days / total_days, 3) if total_days > 0 else 0.0

        monthly_list.append(
            MonthlyAggregate(
                period=month_key,
                aggregation_method="mean for temperature/humidity/radiation, cumulative sum for precipitation",
                total_days=total_days,
                valid_days=min_valid_days,
                coverage_ratio=coverage,
                values=param_values,
            )
        )

    return monthly_list


def determine_agricultural_season(date_str: str) -> str:
    """Classify date into agro-climatic season: Kharif (May-Oct) or Rabi (Nov-Apr)."""
    month = int(date_str[5:7])
    if 5 <= month <= 10:
        return "Kharif"
    else:
        return "Rabi"


def compute_seasonal_aggregates(daily_records: List[DailyRecord]) -> List[SeasonalAggregate]:
    """Group daily records by agricultural season (Kharif / Rabi) and compute aggregates."""
    if not daily_records:
        return []

    # Group records by (Season, Year or Span)
    season_groups: Dict[str, List[DailyRecord]] = defaultdict(list)
    for rec in daily_records:
        season_name = determine_agricultural_season(rec.date)
        season_groups[season_name].append(rec)

    seasonal_list: List[SeasonalAggregate] = []

    for season_name in sorted(season_groups.keys()):
        records = season_groups[season_name]
        total_days = len(records)
        dates = [r.date for r in records]
        start_span = min(dates)
        end_span = max(dates)
        period_label = f"{start_span} to {end_span}"

        param_codes = set()
        for r in records:
            param_codes.update(r.values.keys())

        param_values: Dict[str, MetricStatistics] = {}
        min_valid_days = total_days

        for code in sorted(param_codes):
            vals = [r.values.get(code) for r in records]
            method = AGGREGATION_METHODS.get(code, "mean")
            unit = PARAMETER_UNITS.get(code, "units")
            stat = compute_metric_statistics(vals, method, unit)
            param_values[code] = stat

            valid_count = len([v for v in vals if v is not None])
            if valid_count < min_valid_days:
                min_valid_days = valid_count

        coverage = round(min_valid_days / total_days, 3) if total_days > 0 else 0.0

        seasonal_list.append(
            SeasonalAggregate(
                season=season_name,
                period=period_label,
                aggregation_method="mean for temperature/humidity/radiation, cumulative sum for precipitation",
                total_days=total_days,
                valid_days=min_valid_days,
                coverage_ratio=coverage,
                values=param_values,
            )
        )

    return seasonal_list


def compute_all_aggregates(daily_records: List[DailyRecord]) -> AggregatesSummary:
    """Compute both monthly and seasonal aggregates for the normalized daily records."""
    monthly = compute_monthly_aggregates(daily_records)
    seasonal = compute_seasonal_aggregates(daily_records)
    return AggregatesSummary(monthly=monthly, seasonal=seasonal)
