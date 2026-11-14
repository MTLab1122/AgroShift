"""AgroShift Central Canonical Schemas Package."""

from backend.app.modules.nasa_data.schemas import (
    ApiError,
    ClimateRequest,
    ClimateSummary,
    DailyRecord,
    MissingDataSummary,
    MonthlyAggregate,
    ParameterMetadata,
    SeasonalAggregate,
)
from backend.app.schemas.comparison import FarmVsNasaComparison
from backend.app.schemas.farm import CropHistoryEntry, FarmProfile
from backend.app.schemas.recommendation import (
    CalendarEntry,
    RecommendationSet,
    Scenario,
    ScenarioCatalog,
    ScoreBreakdown,
)

__all__ = [
    "ApiError",
    "CalendarEntry",
    "ClimateRequest",
    "ClimateSummary",
    "CropHistoryEntry",
    "DailyRecord",
    "FarmProfile",
    "FarmVsNasaComparison",
    "MissingDataSummary",
    "MonthlyAggregate",
    "ParameterMetadata",
    "RecommendationSet",
    "Scenario",
    "ScenarioCatalog",
    "ScoreBreakdown",
    "SeasonalAggregate",
]
