from ..models import RecommendationScenario
from ..schemas.recommendations import ExplanationResult
from ..schemas.validation import FeasibilityStatus


class ExplanationEngine:
    def explain(self, scenario: RecommendationScenario) -> ExplanationResult:
        status = FeasibilityStatus(scenario.feasibility_status)
        parts = [
            f"Scenario {scenario.scenario_id} has feasibility status {status.value}."
        ]
        if status is FeasibilityStatus.INFEASIBLE:
            parts.append("A recorded hard constraint makes this scenario infeasible.")
        elif status is FeasibilityStatus.INSUFFICIENT_DATA:
            parts.append("The available data is insufficient to establish feasibility.")
        elif status is FeasibilityStatus.CONDITIONALLY_FEASIBLE:
            parts.append("Feasibility is conditional on the listed limitations and evidence.")
        else:
            parts.append("Recorded checks support feasibility within their stated scope.")
        if scenario.score is None:
            parts.append("No score is available because required supported components are missing.")
        else:
            parts.append(
                f"The deterministic weighted score is {scenario.score} out of 100."
            )
        if scenario.missing_information:
            parts.append(
                "Missing information: " + "; ".join(scenario.missing_information) + "."
            )
        if scenario.constraints:
            parts.append("Constraints: " + "; ".join(scenario.constraints) + ".")
        return ExplanationResult(
            scenario_id=scenario.scenario_id,
            feasibility_status=status,
            score=scenario.score,
            explanation=" ".join(parts),
            evidence_references=scenario.evidence_references,
            missing_information=scenario.missing_information,
            limitations=scenario.limitations,
        )
