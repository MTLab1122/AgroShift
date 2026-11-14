import json
from pathlib import Path

from jsonschema import Draft202012Validator

from backend.app.schemas.farm import FarmProfile
from backend.app.schemas.recommendation import RecommendationSet

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "shared" / "schemas"
DEMO = ROOT / "data" / "demo"


def _validate_fixture(fixture_name: str, schema_name: str) -> dict:
    schema = json.loads((SCHEMAS / schema_name).read_text(encoding="utf-8"))
    fixture = json.loads((DEMO / fixture_name).read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(fixture)
    assert fixture["is_demo_data"] is True
    return fixture


def test_farm_demo_matches_shared_contract():
    farm = _validate_fixture("farm.demo.json", "farm.schema.json")
    FarmProfile.model_validate(farm)
    assert farm["farm_id"] == "farm-peshawar-001"


def test_climate_demo_matches_shared_contract():
    climate = _validate_fixture("climate.mock.json", "climate.schema.json")
    assert climate["farm_id"] == "farm-peshawar-001"


def test_recommendations_demo_matches_shared_contract():
    recommendations = _validate_fixture(
        "recommendations.demo.json", "recommendation.schema.json"
    )
    RecommendationSet.model_validate(recommendations)
    assert recommendations["farm_id"] == "farm-peshawar-001"
    assert set(recommendations["scenarios"]) == {
        "baseline",
        "pulse_inclusive",
        "soil_cover",
    }
