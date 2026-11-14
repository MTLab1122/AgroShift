from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .api import get_db_session
from .repositories import RecommendationScenarioRepository, RecordNotFoundError
from .schemas.recommendations import (
    ExplanationRequest,
    ExplanationResult,
    RecommendationGenerationRequest,
    RecommendationGenerationResult,
    RecommendationScenarioRead,
    ScenarioComparisonRequest,
    ScenarioComparisonResult,
)
from .services.explanation_engine import ExplanationEngine
from .services.scenario_comparator import ScenarioComparator
from .services.scenario_generator import ScenarioGenerator


router = APIRouter(prefix="/api/v1/recommendations", tags=["Recommendations"])


@router.post("/generate", response_model=RecommendationGenerationResult)
def generate_recommendations(
    request: RecommendationGenerationRequest,
    session: Session = Depends(get_db_session),
):
    with session.begin():
        return ScenarioGenerator(session).generate(request)


@router.get(
    "/farm/{farm_id}",
    response_model=list[RecommendationScenarioRead],
)
def list_farm_scenarios(
    farm_id: str,
    offset: int = 0,
    limit: int = 100,
    session: Session = Depends(get_db_session),
):
    try:
        records = RecommendationScenarioRepository(session).list_for_farm(
            farm_id, offset=offset, limit=limit
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return records


@router.get("/{scenario_id}", response_model=RecommendationScenarioRead)
def get_recommendation(
    scenario_id: str,
    session: Session = Depends(get_db_session),
):
    try:
        return RecommendationScenarioRepository(session).get_by_scenario_id(scenario_id)
    except RecordNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation scenario not found",
        ) from exc


@router.post("/compare", response_model=ScenarioComparisonResult)
def compare_recommendations(
    request: ScenarioComparisonRequest,
    session: Session = Depends(get_db_session),
):
    try:
        with session.begin():
            return ScenarioComparator(session).compare(request)
    except RecordNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more recommendation scenarios were not found",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post("/explain", response_model=ExplanationResult)
def explain_recommendation(
    request: ExplanationRequest,
    session: Session = Depends(get_db_session),
):
    try:
        with session.begin():
            scenario = RecommendationScenarioRepository(session).get_by_scenario_id(
                request.scenario_id
            )
            result = ExplanationEngine().explain(scenario)
            scenario.explanation = result.explanation
            session.flush()
            return result
    except RecordNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation scenario not found",
        ) from exc
