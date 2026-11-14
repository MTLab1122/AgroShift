from decimal import Decimal, ROUND_HALF_UP

from ..schemas.recommendations import (
    PriorityWeights,
    ScoreComponents,
    ScoringResult,
)
from ..schemas.validation import FeasibilityStatus


class ScoringEngine:
    def calculate(
        self,
        feasibility_status: FeasibilityStatus,
        components: ScoreComponents | None,
        weights: PriorityWeights | None = None,
    ) -> ScoringResult:
        weights = weights or PriorityWeights()
        components = components or ScoreComponents()
        if feasibility_status is FeasibilityStatus.INFEASIBLE:
            return ScoringResult(
                score=None,
                status=feasibility_status,
                components=components,
                weights=weights,
                limitations=["Hard infeasibility cannot be overridden by a score."],
            )
        if feasibility_status is FeasibilityStatus.INSUFFICIENT_DATA:
            return ScoringResult(
                score=None,
                status=feasibility_status,
                components=components,
                weights=weights,
                limitations=["Scoring is withheld while feasibility data is insufficient."],
            )
        values = components.model_dump()
        weight_values = weights.model_dump()
        missing = [
            name for name, weight in weight_values.items()
            if weight > 0 and values[name] is None
        ]
        if missing:
            return ScoringResult(
                score=None,
                status=feasibility_status,
                components=components,
                weights=weights,
                missing_components=missing,
                limitations=[
                    "No missing component value is imputed or inferred."
                ],
            )
        score = sum(
            (values[name] or Decimal("0")) * weight
            for name, weight in weight_values.items()
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return ScoringResult(
            score=score,
            status=feasibility_status,
            components=components,
            weights=weights,
        )
