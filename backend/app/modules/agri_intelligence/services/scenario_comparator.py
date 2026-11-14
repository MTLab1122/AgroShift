from ..repositories import RecommendationScenarioRepository
from ..schemas.recommendations import (
    PriorityWeights,
    ScenarioComparisonItem,
    ScenarioComparisonRequest,
    ScenarioComparisonResult,
    ScoreComponents,
)
from ..schemas.validation import FeasibilityStatus
from .scoring_engine import ScoringEngine


class ScenarioComparator:
    def __init__(self, session, scoring_engine: ScoringEngine | None = None):
        self.session = session
        self.repository = RecommendationScenarioRepository(session)
        self.scoring_engine = scoring_engine or ScoringEngine()

    def compare(
        self, request: ScenarioComparisonRequest | dict
    ) -> ScenarioComparisonResult:
        if not isinstance(request, ScenarioComparisonRequest):
            request = ScenarioComparisonRequest.model_validate(request)
        if len(set(request.scenario_ids)) != len(request.scenario_ids):
            raise ValueError("scenario_ids must not contain duplicates")
        records = [
            self.repository.get_by_scenario_id(scenario_id)
            for scenario_id in request.scenario_ids
        ]
        priorities = [priority.value for priority in request.priorities]
        items = []
        for record in records:
            components = ScoreComponents.model_validate(record.score_components or {})
            result = self.scoring_engine.calculate(
                FeasibilityStatus(record.feasibility_status),
                components,
                request.weights,
            )
            record.score = result.score
            record.score_components = result.components.model_dump(mode="json")
            record.priority_weights = result.weights.model_dump(mode="json")
            record.priorities = priorities
            items.append(
                ScenarioComparisonItem(
                    scenario_id=record.scenario_id,
                    scenario_type=record.scenario_type,
                    feasibility_status=record.feasibility_status,
                    score=result.score,
                    score_components=result.components,
                    missing_components=result.missing_components,
                    priorities=request.priorities,
                    crop_sequence=record.crop_sequence,
                    missing_information=record.missing_information,
                    limitations=record.limitations,
                    evidence_references=record.evidence_references,
                )
            )
        all_rankable = all(
            item.score is not None
            and item.feasibility_status
            in {
                FeasibilityStatus.FEASIBLE,
                FeasibilityStatus.CONDITIONALLY_FEASIBLE,
            }
            for item in items
        )
        ranked = (
            [
                item.scenario_id
                for item in sorted(items, key=lambda item: item.score, reverse=True)
            ]
            if all_rankable else []
        )
        return ScenarioComparisonResult(
            items=items,
            ranked_scenario_ids=ranked,
            ranking_limitation=(
                None
                if all_rankable
                else "Scenarios with missing scores or hard infeasibility are not ranked."
            ),
        )
