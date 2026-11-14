from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import Field, model_validator

from ._base import ReadSchema, Schema, UpdateSchema
from .validation import (
    CropHistoryItem,
    FarmContext,
    FeasibilityStatus,
)
from backend.app.modules.nasa_data.schemas import ClimateSummary


class ScenarioType(str, Enum):
    EXISTING_PRACTICE = "EXISTING_PRACTICE"
    PULSE_INCLUSIVE = "PULSE_INCLUSIVE"
    SOIL_COVER_FORAGE = "SOIL_COVER_FORAGE"


class FarmerPriority(str, Enum):
    WATER_CONSERVATION = "WATER_CONSERVATION"
    SOIL_HEALTH = "SOIL_HEALTH"
    CLIMATE_RESILIENCE = "CLIMATE_RESILIENCE"
    CROP_DIVERSITY = "CROP_DIVERSITY"
    OTHER = "OTHER"


class PriorityWeights(Schema):
    climate_water: Decimal = Field(default=Decimal("0.25"), ge=0)
    rotation: Decimal = Field(default=Decimal("0.25"), ge=0)
    diversity: Decimal = Field(default=Decimal("0.25"), ge=0)
    farmer_priority: Decimal = Field(default=Decimal("0.25"), ge=0)

    @model_validator(mode="after")
    def normalized(self):
        if sum(
            (
                self.climate_water,
                self.rotation,
                self.diversity,
                self.farmer_priority,
            ),
            Decimal("0"),
        ) != Decimal("1"):
            raise ValueError("Priority component weights must sum to 1")
        return self


class ScoreComponents(Schema):
    climate_water: Decimal | None = Field(default=None, ge=0, le=100)
    rotation: Decimal | None = Field(default=None, ge=0, le=100)
    diversity: Decimal | None = Field(default=None, ge=0, le=100)
    farmer_priority: Decimal | None = Field(default=None, ge=0, le=100)


class ScoringResult(Schema):
    score: Decimal | None = None
    status: FeasibilityStatus
    components: ScoreComponents
    weights: PriorityWeights
    missing_components: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class RecommendationGenerationRequest(Schema):
    farm_id: str = Field(min_length=1, max_length=128)
    farm_context: FarmContext | None = None
    crop_history: list[CropHistoryItem] = Field(default_factory=list)
    upcoming_season: str | None = Field(default=None, max_length=120)
    climate: ClimateSummary | None = None
    scenario_types: list[ScenarioType] = Field(
        default_factory=lambda: list(ScenarioType)
    )
    priorities: list[FarmerPriority] = Field(default_factory=list)
    other_priority_label: str | None = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def validate_request(self):
        if (
            self.farm_context is not None
            and self.farm_context.farm_id is not None
            and self.farm_context.farm_id != self.farm_id
        ):
            raise ValueError("farm_context.farm_id must match farm_id")
        if len(set(self.scenario_types)) != len(self.scenario_types):
            raise ValueError("scenario_types must not contain duplicates")
        if len(set(self.priorities)) != len(self.priorities):
            raise ValueError("priorities must not contain duplicates")
        if FarmerPriority.OTHER in self.priorities and not self.other_priority_label:
            raise ValueError("other_priority_label is required for OTHER priority")
        return self


class RecommendationScenarioCreate(Schema):
    scenario_id: str = Field(pattern=r"^[0-9a-fA-F-]{36}$")
    scenario_type: ScenarioType
    farm_id: str = Field(min_length=1, max_length=128)
    crop_sequence: list[dict] = Field(default_factory=list)
    season_schedule: list[dict] = Field(default_factory=list)
    planting_harvest_windows: list[dict] = Field(default_factory=list)
    duration_days: dict = Field(default_factory=dict)
    feasibility_status: FeasibilityStatus
    validation_results: list[dict] = Field(default_factory=list)
    evidence_references: list[dict] = Field(default_factory=list)
    candidate_decisions: list[dict] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    priorities: list[FarmerPriority] = Field(default_factory=list)
    score: Decimal | None = Field(default=None, ge=0, le=100)
    score_components: ScoreComponents | None = None
    priority_weights: PriorityWeights | None = None
    explanation: str | None = None
    engine_version: str = Field(default="module03-0.1.0", max_length=40)


class RecommendationScenarioUpdate(UpdateSchema):
    feasibility_status: FeasibilityStatus | None = None
    candidate_decisions: list[dict] | None = None
    benefits: list[str] | None = None
    risks: list[str] | None = None
    constraints: list[str] | None = None
    limitations: list[str] | None = None
    missing_information: list[str] | None = None
    priorities: list[FarmerPriority] | None = None
    score: Decimal | None = Field(default=None, ge=0, le=100)
    score_components: ScoreComponents | None = None
    priority_weights: PriorityWeights | None = None
    explanation: str | None = None


class RecommendationScenarioRead(ReadSchema):
    id: int
    scenario_id: str
    scenario_type: ScenarioType
    farm_id: str
    crop_sequence: list[dict]
    season_schedule: list[dict]
    planting_harvest_windows: list[dict]
    duration_days: dict
    feasibility_status: FeasibilityStatus
    validation_results: list[dict]
    evidence_references: list[dict]
    candidate_decisions: list[dict]
    benefits: list[str]
    risks: list[str]
    constraints: list[str]
    limitations: list[str]
    missing_information: list[str]
    priorities: list[str]
    score: Decimal | None
    score_components: dict | None
    priority_weights: dict | None
    explanation: str | None
    engine_version: str
    created_at: datetime


class RecommendationGenerationResult(Schema):
    farm_id: str
    scenarios: list[RecommendationScenarioRead] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ScenarioComparisonRequest(Schema):
    scenario_ids: list[str] = Field(min_length=2)
    weights: PriorityWeights = Field(default_factory=PriorityWeights)
    priorities: list[FarmerPriority] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_scenarios(self):
        if len(set(self.scenario_ids)) != len(self.scenario_ids):
            raise ValueError("scenario_ids must not contain duplicates")
        if len(set(self.priorities)) != len(self.priorities):
            raise ValueError("priorities must not contain duplicates")
        return self


class ScenarioComparisonItem(Schema):
    scenario_id: str
    scenario_type: ScenarioType
    feasibility_status: FeasibilityStatus
    score: Decimal | None
    score_components: ScoreComponents
    missing_components: list[str] = Field(default_factory=list)
    priorities: list[FarmerPriority] = Field(default_factory=list)
    crop_sequence: list[dict] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    evidence_references: list[dict] = Field(default_factory=list)


class ScenarioComparisonResult(Schema):
    items: list[ScenarioComparisonItem]
    ranked_scenario_ids: list[str] = Field(default_factory=list)
    ranking_limitation: str | None = None


class ExplanationRequest(Schema):
    scenario_id: str = Field(min_length=36, max_length=36)


class ExplanationResult(Schema):
    scenario_id: str
    feasibility_status: FeasibilityStatus
    score: Decimal | None
    explanation: str
    evidence_references: list[dict] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
