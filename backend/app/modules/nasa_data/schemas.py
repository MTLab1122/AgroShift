"""Canonical Pydantic v2 schemas and pre-network validators for Module 02: NASA Earth Observation & Climate Data Engine.

Defines:
- ClimateSummary: Normalized environmental data contract with provenance, aggregations, and missing-data tracking.
- ApiError: Canonical API error envelope matching shared team specifications.
- ClimateRequest: Strict pre-network request validation for coordinates and date bounds.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import re
from typing import Any, Dict, List, Optional
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

# Standard NASA POWER earliest archive date for daily agroclimatology
NASA_POWER_EARLIEST_DATE = date(1981, 1, 1)

ISO_DATE_REGEX = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")
MONTH_REGEX = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class ApiError(BaseModel):
    """Standardized error envelope returned by all endpoints across AgroShift."""

    model_config = ConfigDict(extra="forbid")

    error_code: str = Field(
        ...,
        description="Standardized uppercase error code (e.g., INVALID_COORDINATES, UPSTREAM_TIMEOUT).",
        examples=["INVALID_COORDINATES", "INVALID_DATE_RANGE", "NASA_POWER_UNAVAILABLE"],
    )
    message: str = Field(
        ...,
        description="Human-readable explanation of what failed and how to remediate.",
        examples=["Latitude must be between -90.0 and 90.0 decimal degrees."],
    )
    details: Optional[Any] = Field(
        default=None,
        description="Optional structured contextual information or field validation hints.",
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Optional correlation ID for distributed tracing and log auditing.",
    )


class ParameterMetadata(BaseModel):
    """Metadata describing a single environmental observation parameter."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(
        ...,
        description="Exact NASA POWER parameter identifier (e.g. T2M, PRECTOTCORR).",
        examples=["T2M", "PRECTOTCORR", "RH2M", "ALLSKY_SFC_SW_DWN"],
    )
    label: str = Field(
        ...,
        description="Human-readable parameter name.",
        examples=["Temperature at 2 Meters", "Precipitation Corrected"],
    )
    unit: str = Field(
        ...,
        description="Scientific unit of measurement.",
        examples=["°C", "mm/day", "%", "MJ/m^2/day"],
    )


class DailyRecord(BaseModel):
    """Single-day observed environmental values.

    Missing or unobserved readings must be None (mapped to JSON null).
    NEVER replace missing values with 0.0 or synthetic guesses.
    """

    model_config = ConfigDict(extra="forbid")

    date: str = Field(
        ...,
        description="Observation date in ISO format (YYYY-MM-DD).",
        pattern=r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$",
        examples=["2024-05-01"],
    )
    values: Dict[str, Optional[float]] = Field(
        ...,
        description="Mapping of parameter code to observed measurement or null if missing.",
        examples=[{"T2M": 28.5, "PRECTOTCORR": 0.0, "RH2M": 45.2, "ALLSKY_SFC_SW_DWN": 22.8}],
    )


class MetricStatistics(BaseModel):
    """Statistical summary for a single parameter over an aggregation period."""

    model_config = ConfigDict(extra="forbid")

    mean: Optional[float] = Field(default=None, description="Arithmetic mean of valid daily observations.")
    sum: Optional[float] = Field(default=None, description="Cumulative sum of valid observations (e.g., precipitation).")
    min: Optional[float] = Field(default=None, description="Minimum valid value observed in the window.")
    max: Optional[float] = Field(default=None, description="Maximum valid value observed in the window.")
    unit: Optional[str] = Field(default=None, description="Measurement unit for the aggregated metric.")


class MonthlyAggregate(BaseModel):
    """Aggregated environmental metrics for a specific calendar month."""

    model_config = ConfigDict(extra="forbid")

    period: str = Field(
        ...,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="Target calendar month in YYYY-MM format.",
        examples=["2024-05"],
    )
    aggregation_method: str = Field(
        ...,
        description="Method used for calculating metrics (e.g. mean for temperature, sum for rainfall).",
        examples=["mean for temperature/humidity/radiation, sum for precipitation"],
    )
    total_days: int = Field(..., ge=1, le=31, description="Total calendar days in the month.")
    valid_days: int = Field(..., ge=0, le=31, description="Number of days with valid (non-null) data.")
    coverage_ratio: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Ratio of valid days to total calendar days (0.0 to 1.0).",
    )
    values: Dict[str, MetricStatistics] = Field(
        ...,
        description="Aggregated statistics per parameter.",
    )


class SeasonalAggregate(BaseModel):
    """Aggregated environmental metrics for an agro-ecological season (e.g., Kharif, Rabi)."""

    model_config = ConfigDict(extra="forbid")

    season: str = Field(
        ...,
        description="Name of the agricultural or climatic season.",
        examples=["Kharif", "Rabi", "Annual"],
    )
    period: str = Field(
        ...,
        description="Calendar span of the season (e.g., 2024-05 to 2024-10).",
        examples=["2024-05 to 2024-10"],
    )
    aggregation_method: str = Field(
        ...,
        description="Methodology used to summarize data over the seasonal duration.",
    )
    total_days: int = Field(..., ge=1, description="Total days in the seasonal window.")
    valid_days: int = Field(..., ge=0, description="Valid observation days.")
    coverage_ratio: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    values: Dict[str, MetricStatistics] = Field(
        ...,
        description="Aggregated statistics per parameter for the season.",
    )


class AggregatesSummary(BaseModel):
    """Container for monthly and seasonal climate aggregations."""

    model_config = ConfigDict(extra="forbid")

    monthly: List[MonthlyAggregate] = Field(
        default_factory=list,
        description="List of monthly climate aggregations.",
    )
    seasonal: List[SeasonalAggregate] = Field(
        default_factory=list,
        description="List of seasonal climate aggregations.",
    )


class MissingDataSummary(BaseModel):
    """Detailed audit of observation completeness and data gaps."""

    model_config = ConfigDict(extra="forbid")

    total_days: int = Field(..., ge=1, description="Total calendar days in the queried interval.")
    missing_days_by_parameter: Dict[str, int] = Field(
        ...,
        description="Count of missing/null observation days for each parameter code.",
        examples=[{"T2M": 0, "PRECTOTCORR": 1, "RH2M": 2, "ALLSKY_SFC_SW_DWN": 0}],
    )
    has_gaps: bool = Field(
        ...,
        description="True if any parameter contains at least one missing observation day.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Optional human-readable notes detailing observed gaps or sensor outages.",
    )


class FarmVsNasaComparison(BaseModel):
    """Diagnostic comparison reconciling user farm inputs against actual NASA observations."""

    model_config = ConfigDict(extra="forbid")

    observed_rainfall_mm: float = Field(
        ...,
        ge=0.0,
        description="Total observed precipitation from NASA POWER (PRECTOTCORR) over the period.",
    )
    expected_crop_water_need_mm: float = Field(
        ...,
        ge=0.0,
        description="Agronomically expected crop water requirement based on crop catalog.",
    )
    water_balance_status: str = Field(
        ...,
        description="Water balance category: severe_deficit, moderate_deficit, balanced, or excess_moisture.",
        examples=["moderate_deficit", "severe_deficit", "balanced", "excess_moisture"],
    )
    thermal_stress_days: int = Field(
        ...,
        ge=0,
        description="Count of days where NASA T2M_MAX exceeded critical heat stress thresholds.",
    )
    irrigation_adequacy_note: str = Field(
        ...,
        description="Evaluation reconciling reported irrigation type/availability against observed precipitation deficit.",
    )
    data_mode: str = Field(
        default="live",
        description="Indicates whether comparison was computed against live NASA observations or demo fallback.",
        examples=["live", "demo_fallback"],
    )


class ClimateSummary(BaseModel):
    """Canonical climate context object produced by Module 02 for downstream modules (03, 04)."""

    model_config = ConfigDict(extra="forbid")

    farm_id: str = Field(
        ...,
        min_length=1,
        description="Stable farm identifier linked to Module 01 FarmProfile.",
        examples=["farm-peshawar-001"],
    )
    source: str = Field(
        ...,
        description="Primary data source attribution.",
        examples=["NASA POWER Daily API", "NASA POWER Daily API (Mock)"],
    )
    product_or_dataset: str = Field(
        ...,
        description="Specific satellite or assimilation model dataset name.",
        examples=["MERRA-2 / GEOS-5 FP-IT / CERES SYN1deg via POWER AG community"],
    )
    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="North/South coordinate in decimal degrees (-90 to 90).",
        examples=[34.0151],
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="East/West coordinate in decimal degrees (-180 to 180).",
        examples=[71.5249],
    )
    start_date: str = Field(
        ...,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$",
        description="Start date of observed window (YYYY-MM-DD).",
        examples=["2024-05-01"],
    )
    end_date: str = Field(
        ...,
        pattern=r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$",
        description="End date of observed window (YYYY-MM-DD).",
        examples=["2024-10-31"],
    )
    parameters: List[ParameterMetadata] = Field(
        ...,
        min_length=1,
        description="List of environmental parameters included with exact codes and units.",
    )
    daily_series: Optional[List[DailyRecord]] = Field(
        default=None,
        description="Optional full daily time-series sequence for charts and history views.",
    )
    aggregates: AggregatesSummary = Field(
        ...,
        description="Monthly and seasonal climate aggregates.",
    )
    missing_data: MissingDataSummary = Field(
        ...,
        description="Integrity audit of missing values and sentinel -999 conversions.",
    )
    retrieved_at: str = Field(
        ...,
        description="ISO 8601 UTC timestamp of retrieval or synthesis.",
        examples=["2026-11-13T17:30:00Z"],
    )
    coverage_note: str = Field(
        ...,
        min_length=20,
        description="Mandatory scientific honesty disclaimer clarifying regional satellite/reanalysis resolution.",
        examples=[
            "Gridded NASA satellite and reanalysis data represents regional grid cells (~0.5° × 0.5°), "
            "not direct on-farm in-situ sensor measurements. Use for regional decision support and agro-climatic context."
        ],
    )
    is_demo_data: bool = Field(
        default=False,
        description="Explicit flag: True when synthetic mock fixtures are returned; False for live NASA data.",
    )
    farm_vs_nasa_comparison: Optional[FarmVsNasaComparison] = Field(
        default=None,
        description="Diagnostic comparison reconciling user farm inputs against live NASA observations.",
    )

    @model_validator(mode="after")
    def validate_date_coherence(self) -> ClimateSummary:
        """Ensure start_date <= end_date and retrieved_at is parseable."""
        try:
            start_d = date.fromisoformat(self.start_date)
            end_d = date.fromisoformat(self.end_date)
        except ValueError as exc:
            raise ValueError(f"Invalid ISO date format: {exc}") from exc

        if start_d > end_d:
            raise ValueError(
                f"start_date ({self.start_date}) cannot be after end_date ({self.end_date})"
            )
        return self


class ClimateRequest(BaseModel):
    """Strict pre-network request validator for Module 02 endpoints.

    Validates coordinates and ISO date intervals BEFORE any external HTTP call
    is initiated to prevent upstream abuse and invalid queries.
    """

    model_config = ConfigDict(extra="forbid")

    farm_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Identifier of the farm requesting climate data.",
        examples=["farm-peshawar-001"],
    )
    latitude: float = Field(
        ...,
        description="Farm latitude in decimal degrees. Must be within [-90.0, 90.0].",
        examples=[34.0151],
    )
    longitude: float = Field(
        ...,
        description="Farm longitude in decimal degrees. Must be within [-180.0, 180.0].",
        examples=[71.5249],
    )
    start_date: str = Field(
        ...,
        description="Start date in ISO YYYY-MM-DD format.",
        examples=["2024-05-01"],
    )
    end_date: str = Field(
        ...,
        description="End date in ISO YYYY-MM-DD format.",
        examples=["2024-10-31"],
    )
    parameters: Optional[List[str]] = Field(
        default=None,
        description="Optional subset of parameters to fetch (default fetches standard suite: T2M, PRECTOTCORR, RH2M, ALLSKY_SFC_SW_DWN).",
        examples=[["T2M", "PRECTOTCORR"]],
    )
    include_daily: bool = Field(
        default=False,
        description="Whether to include daily time series records in the returned ClimateSummary.",
    )

    @field_validator("latitude")
    @classmethod
    def validate_latitude_bounds(cls, v: float) -> float:
        if v < -90.0 or v > 90.0:
            raise ValueError(
                f"Latitude {v} is out of bounds. Must be between -90.0 and 90.0 decimal degrees (N/S)."
            )
        return round(v, 6)

    @field_validator("longitude")
    @classmethod
    def validate_longitude_bounds(cls, v: float) -> float:
        if v < -180.0 or v > 180.0:
            raise ValueError(
                f"Longitude {v} is out of bounds. Must be between -180.0 and 180.0 decimal degrees (E/W)."
            )
        return round(v, 6)

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_iso_format(cls, v: str) -> str:
        if not ISO_DATE_REGEX.match(v):
            raise ValueError(f"Date '{v}' must match ISO format YYYY-MM-DD.")
        try:
            date.fromisoformat(v)
        except ValueError as exc:
            raise ValueError(f"Invalid calendar date '{v}': {exc}") from exc
        return v

    @model_validator(mode="after")
    def validate_date_range_and_power_coverage(self) -> ClimateRequest:
        start_d = date.fromisoformat(self.start_date)
        end_d = date.fromisoformat(self.end_date)

        if start_d > end_d:
            raise ValueError(
                f"start_date ({self.start_date}) cannot be later than end_date ({self.end_date})."
            )

        if start_d < NASA_POWER_EARLIEST_DATE:
            raise ValueError(
                f"start_date ({self.start_date}) precedes NASA POWER archive coverage start ({NASA_POWER_EARLIEST_DATE.isoformat()})."
            )

        # NASA POWER daily data has an assimilation latency of 2-5 days; dates far in the future cannot be retrieved
        today_utc = datetime.now(timezone.utc).date()
        if end_d > today_utc:
            raise ValueError(
                f"end_date ({self.end_date}) cannot be in the future (today is {today_utc.isoformat()})."
            )

        # Restrict parameters to supported codes if provided
        if self.parameters:
            allowed = {"T2M", "T2M_MIN", "T2M_MAX", "PRECTOTCORR", "RH2M", "ALLSKY_SFC_SW_DWN"}
            unknown = set(self.parameters) - allowed
            if unknown:
                raise ValueError(
                    f"Unsupported parameter(s): {sorted(unknown)}. Allowed parameters: {sorted(allowed)}."
                )

        return self
