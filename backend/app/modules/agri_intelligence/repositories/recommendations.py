from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import RecommendationScenario
from ..schemas.recommendations import (
    RecommendationScenarioCreate,
    RecommendationScenarioUpdate,
)
from .base import RecordNotFoundError, Repository


class RecommendationScenarioRepository(Repository[RecommendationScenario]):
    def __init__(self, session: Session):
        super().__init__(
            session,
            RecommendationScenario,
            RecommendationScenarioCreate,
            RecommendationScenarioUpdate,
        )

    def get_by_scenario_id(self, scenario_id: str) -> RecommendationScenario:
        record = self.session.scalar(
            select(RecommendationScenario).where(
                RecommendationScenario.scenario_id == scenario_id
            )
        )
        if record is None:
            raise RecordNotFoundError(RecommendationScenario, scenario_id)
        return record

    def list_for_farm(
        self, farm_id: str, *, offset: int = 0, limit: int = 100
    ) -> list[RecommendationScenario]:
        if offset < 0 or limit < 1:
            raise ValueError("offset must be non-negative and limit must be positive")
        statement = (
            select(RecommendationScenario)
            .where(RecommendationScenario.farm_id == farm_id)
            .order_by(
                RecommendationScenario.created_at.desc(),
                RecommendationScenario.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return list(self.session.scalars(statement))
