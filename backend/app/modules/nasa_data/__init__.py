"""Module 02: NASA Earth Observation & Climate Data Engine."""

from backend.app.modules.nasa_data.earthdata_adapters import (
    EarthdataAdapter,
    earthdata_adapter,
)
from backend.app.modules.nasa_data.schemas import (
    ApiError,
    ClimateRequest,
    ClimateSummary,
    DailyRecord,
    FarmVsNasaComparison,
    MissingDataSummary,
    MonthlyAggregate,
    ParameterMetadata,
    SeasonalAggregate,
)

__all__ = [
    "ApiError",
    "ClimateRequest",
    "ClimateSummary",
    "DailyRecord",
    "EarthdataAdapter",
    "FarmVsNasaComparison",
    "MissingDataSummary",
    "MonthlyAggregate",
    "ParameterMetadata",
    "SeasonalAggregate",
    "earthdata_adapter",
]
