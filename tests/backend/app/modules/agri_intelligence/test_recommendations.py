from decimal import Decimal

import pytest
from sqlalchemy.orm import sessionmaker

from backend.app.modules.agri_intelligence.db.base import Base
from backend.app.modules.agri_intelligence.db.engine import get_engine
from backend.app.modules.agri_intelligence.models.enums import EvidenceStatus
from backend.app.modules.agri_intelligence.repositories import (
    RecommendationScenarioRepository,
)
from backend.app.modules.agri_intelligence.schemas.recommendations import (
    PriorityWeights,
    RecommendationGenerationRequest,
    RecommendationScenarioCreate,
    ScenarioComparisonRequest,
    ScoreComponents,
)
from backend.app.modules.agri_intelligence.schemas.validation import FeasibilityStatus
from backend.app.modules.agri_intelligence.seeds import seed_all
from backend.app.modules.agri_intelligence.services.explanation_engine import (
    ExplanationEngine,
)
from backend.app.modules.agri_intelligence.services.scenario_comparator import (
    ScenarioComparator,
)
from backend.app.modules.agri_intelligence.services.scenario_generator import (
    ScenarioGenerator,
)
from backend.app.modules.agri_intelligence.services.scoring_engine import ScoringEngine


@pytest.fixture
def session(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    engine = get_engine()
    Base.metadata.create_all(engine)
    test_session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield test_session
    finally:
        test_session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_scoring_requires_all_weighted_components_and_respects_hard_constraints():
    engine = ScoringEngine()
    weights = PriorityWeights(
        climate_water=Decimal("0.4"),
        rotation=Decimal("0.3"),
        diversity=Decimal("0.2"),
        farmer_priority=Decimal("0.1"),
    )
    complete = ScoreComponents(
        climate_water=80,
        rotation=70,
        diversity=60,
        farmer_priority=90,
    )
    scored = engine.calculate(FeasibilityStatus.FEASIBLE, complete, weights)
    assert scored.score == Decimal("74.00")

    missing = engine.calculate(
        FeasibilityStatus.CONDITIONALLY_FEASIBLE,
        ScoreComponents(climate_water=80),
        weights,
    )
    assert missing.score is None
    assert len(missing.missing_components) == 3

    infeasible = engine.calculate(
        FeasibilityStatus.INFEASIBLE,
        complete,
        weights,
    )
    assert infeasible.score is None


def test_generation_persists_unknown_scenarios_without_auto_selecting_candidates(session):
    seed_all(session)
    result = ScenarioGenerator(session).generate(
        RecommendationGenerationRequest(farm_id="caller-supplied-farm")
    )
    assert len(result.scenarios) == 5
    assert all(
        item.feasibility_status is FeasibilityStatus.INSUFFICIENT_DATA
        and item.score is None
        for item in result.scenarios
    )
    pulse_scenarios = [
        item for item in result.scenarios
        if item.scenario_type.value == "PULSE_INCLUSIVE"
    ]
    assert len(pulse_scenarios) == 3
    assert all(
        item.candidate_decisions[0]["decision"] == "NOT_AUTOMATICALLY_SELECTED"
        for item in pulse_scenarios
    )
    assert any("Module 01 actual crop history" in item.missing_information
               for item in result.scenarios
               if item.scenario_type.value == "EXISTING_PRACTICE")

    session.commit()
    scenario_id = pulse_scenarios[0].scenario_id
    engine = session.get_bind()
    session.close()
    with sessionmaker(bind=engine, expire_on_commit=False)() as reloaded:
        stored = RecommendationScenarioRepository(reloaded).get_by_scenario_id(
            scenario_id
        )
        assert stored.score is None
        assert stored.feasibility_status == "INSUFFICIENT_DATA"
        assert stored.crop_sequence


def test_comparator_ranks_only_complete_supported_scores_and_explains_inputs(session):
    repository = RecommendationScenarioRepository(session)
    components = {
        "climate_water": "80",
        "rotation": "70",
        "diversity": "60",
        "farmer_priority": "90",
    }
    one = repository.create(
        RecommendationScenarioCreate(
            scenario_id="00000000-0000-4000-8000-000000000001",
            scenario_type="PULSE_INCLUSIVE",
            farm_id="compare-farm",
            feasibility_status=FeasibilityStatus.FEASIBLE,
            score_components=ScoreComponents.model_validate(components),
        )
    )
    two = repository.create(
        RecommendationScenarioCreate(
            scenario_id="00000000-0000-4000-8000-000000000002",
            scenario_type="EXISTING_PRACTICE",
            farm_id="compare-farm",
            feasibility_status=FeasibilityStatus.INSUFFICIENT_DATA,
        )
    )
    request = ScenarioComparisonRequest(
        scenario_ids=[one.scenario_id, two.scenario_id],
        weights=PriorityWeights(
            climate_water=Decimal("0.4"),
            rotation=Decimal("0.3"),
            diversity=Decimal("0.2"),
            farmer_priority=Decimal("0.1"),
        ),
    )
    result = ScenarioComparator(session).compare(request)
    assert one.score == Decimal("74.00")
    assert two.score is None
    assert result.ranked_scenario_ids == []
    assert result.ranking_limitation

    explained = ExplanationEngine().explain(two)
    assert "INSUFFICIENT_DATA" in explained.explanation
    assert explained.score is None
