"""AgroShift Recommendation Engine (Module 03).

Generates explainable, priority-scored crop-rotation pathways grounded in live
NASA Earth observations and farmer-reported constraints.
Scoring formula:
    S = W1 * C + W2 * R + W3 * D + W4 * P
where:
    W1 = 0.35 (Climate & Water Suitability C)
    W2 = 0.25 (Rotation & Disease Break R)
    W3 = 0.25 (Soil Health & Nitrogen Enrichment D)
    W4 = 0.15 (Economic Resilience & Penalty Mitigation P)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

from backend.app.modules.agro_engine.comparator import (
    compare_farm_to_climate,
    evaluate_rotation_monoculture,
)
from backend.app.modules.agro_engine.crop_catalog import (
    get_crop_profile,
    normalize_crop_name,
)
from backend.app.modules.nasa_data.schemas import ClimateSummary
from backend.app.schemas.comparison import FarmVsNasaComparison
from backend.app.schemas.farm import FarmProfile
from backend.app.schemas.recommendation import (
    CalendarEntry,
    RecommendationSet,
    Scenario,
    ScenarioCatalog,
    ScoreBreakdown,
)


def _compute_priority_score(
    climate_suitability: float,
    water_efficiency: float,
    soil_health: float,
    market_resilience: float,
) -> Tuple[float, ScoreBreakdown]:
    """Calculate the weighted composite recommendation priority score S."""
    w1, w2, w3, w4 = 0.35, 0.25, 0.25, 0.15
    total = (
        (w1 * climate_suitability)
        + (w2 * water_efficiency)
        + (w3 * soil_health)
        + (w4 * market_resilience)
    )
    score = round(max(0.0, min(100.0, total)), 1)
    breakdown = ScoreBreakdown(
        climate_suitability=round(climate_suitability, 1),
        water_efficiency=round(water_efficiency, 1),
        soil_health_benefit=round(soil_health, 1),
        market_resilience=round(market_resilience, 1),
    )
    return score, breakdown


def generate_recommendations(
    farm_profile: Union[FarmProfile, Dict[str, Any]],
    climate_summary: Union[ClimateSummary, Dict[str, Any]],
    comparison: Optional[FarmVsNasaComparison] = None,
    data_mode: str = "live",
) -> RecommendationSet:
    """Produce the canonical 3-scenario RecommendationSet grounded in live NASA comparison data."""
    # Ensure FarmVsNasaComparison exists
    if comparison is None:
        comparison = compare_farm_to_climate(
            farm_profile=farm_profile,
            climate_summary=climate_summary,
            data_mode=data_mode,  # type: ignore
        )

    # Normalize farm inputs
    if isinstance(farm_profile, FarmProfile):
        farm_id = farm_profile.farm_id
        current_crop = farm_profile.current_crop
        irrigation_type = farm_profile.irrigation_type
        water_avail = farm_profile.water_availability
        soil_type = farm_profile.soil_type
        crop_history = farm_profile.crop_history
        input_snapshot = farm_profile.model_dump()
    else:
        farm_id = farm_profile.get("farm_id", "farm-unknown")
        current_crop = farm_profile.get("current_crop", "wheat")
        irrigation_type = farm_profile.get("irrigation_type", "canal")
        water_avail = farm_profile.get("water_availability", "medium")
        soil_type = farm_profile.get("soil_type", "loamy")
        crop_history = farm_profile.get("crop_history", [])
        input_snapshot = dict(farm_profile)

    # Historical rotation check
    monoculture_audit = evaluate_rotation_monoculture(current_crop, crop_history)
    has_monoculture_risk = monoculture_audit["monoculture_risk"]
    is_severe_deficit = comparison.water_balance_status == "severe_deficit"
    is_excess_moisture = comparison.water_balance_status == "excess_moisture"
    thermal_stress = comparison.thermal_stress_days

    # ==========================================
    # SCENARIO 1: BASELINE (Current Practice / Cereal Repetition)
    # ==========================================
    base_climate = 65.0
    base_water = 50.0
    base_soil = 45.0
    base_market = 75.0

    if is_severe_deficit:
        base_water -= 25.0
        base_climate -= 15.0
    if has_monoculture_risk:
        base_soil -= 20.0
        base_climate -= 10.0
    if thermal_stress > 2:
        base_climate -= 10.0

    base_score, base_breakdown = _compute_priority_score(
        climate_suitability=max(20.0, base_climate),
        water_efficiency=max(20.0, base_water),
        soil_health=max(20.0, base_soil),
        market_resilience=base_market,
    )

    baseline_scenario = Scenario(
        scenario_id="scenario-baseline-01",
        title="Baseline Continuation (Conventional Cereal Rotation)",
        crop_sequence=[current_crop, "maize" if current_crop.lower() == "wheat" else "wheat"],
        seasonal_calendar=[
            CalendarEntry(
                crop=current_crop,
                start_month="November" if current_crop.lower() == "wheat" else "June",
                harvest_month="April" if current_crop.lower() == "wheat" else "October",
                duration_days=140,
            ),
            CalendarEntry(
                crop="maize" if current_crop.lower() == "wheat" else "wheat",
                start_month="July" if current_crop.lower() == "wheat" else "November",
                harvest_month="October" if current_crop.lower() == "wheat" else "April",
                duration_days=105,
            ),
        ],
        score=base_score,
        score_breakdown=base_breakdown,
        rationale=[
            f"Continues existing farmer practice of rotating {current_crop} with secondary staple cereal.",
            f"Reflects current baseline irrigation access ({irrigation_type}) and reported market familiarity.",
        ],
        benefits=[
            "Familiar management practices with established local grain market off-take in KP.",
            "Utilizes standard farm machinery and available commercial fertilizer blends.",
        ],
        risks=[
            f"Vulnerable to observed {comparison.water_balance_status.replace('_', ' ')} under current climate conditions.",
            "Exacerbates cereal monoculture disease risk and persistent topsoil nitrogen depletion.",
        ],
        assumptions=[
            f"Assumes continuous supply of irrigation water via {irrigation_type}.",
            "Assumes synthetic nitrogen fertilizer (urea/DAP) remains accessible and cost-effective.",
        ],
    )

    # ==========================================
    # SCENARIO 2: PULSE-INCLUSIVE (Nitrogen-Fixing & Water-Saving)
    # ==========================================
    pulse_crop = "chickpea" if current_crop.lower() in ("wheat", "barley") else "mung_bean"
    pulse_prof = get_crop_profile(pulse_crop)
    n_fixed = pulse_prof.nitrogen_fixation_kg_ha if pulse_prof else 60.0

    pulse_climate = 85.0
    pulse_water = 88.0
    pulse_soil = 90.0
    pulse_market = 80.0

    if is_severe_deficit:
        pulse_water += 7.0  # Legumes thrive under moisture constraints
        pulse_climate += 5.0
    if has_monoculture_risk:
        pulse_soil += 5.0  # Breaks pest and root-rot cycle

    pulse_score, pulse_breakdown = _compute_priority_score(
        climate_suitability=min(98.0, pulse_climate),
        water_efficiency=min(98.0, pulse_water),
        soil_health=min(98.0, pulse_soil),
        market_resilience=pulse_market,
    )

    pulse_scenario = Scenario(
        scenario_id="scenario-pulse-inclusive-02",
        title=f"Pulse-Inclusive Diversification ({pulse_crop.replace('_', ' ').capitalize()} Rotation)",
        crop_sequence=[current_crop, pulse_crop],
        seasonal_calendar=[
            CalendarEntry(
                crop=current_crop,
                start_month="November",
                harvest_month="April",
                duration_days=140,
            ),
            CalendarEntry(
                crop=pulse_crop,
                start_month="May" if pulse_crop == "mung_bean" else "October",
                harvest_month="July" if pulse_crop == "mung_bean" else "March",
                duration_days=pulse_prof.typical_duration_days if pulse_prof else 80,
            ),
        ],
        score=pulse_score,
        score_breakdown=pulse_breakdown,
        rationale=[
            f"Integrates biological nitrogen-fixing {pulse_crop.replace('_', ' ')} to offset {comparison.water_balance_status.replace('_', ' ')}.",
            f"Biological nitrogen fixation restores ~{n_fixed:.0f} kg N/ha, significantly reducing expensive synthetic urea demand.",
        ],
        benefits=[
            f"Reduces seasonal irrigation water demand by up to 35% compared to baseline cereal monoculture.",
            f"Breaks chronic soil pathogen and weed cycles identified in crop history analysis.",
            "High local market demand for pulses across Peshawar and KP wholesale markets.",
        ],
        risks=[
            "Sensitive to waterlogging on heavy clay soils during unexpected torrential rainfall.",
            "Requires careful post-harvest storage management to avoid bruchid beetle infestation.",
        ],
        assumptions=[
            "Assumes seed availability of certified pulse varieties (e.g. NIFA-Chana or Ramzan mung bean).",
            "Assumes adequate field drainage during pre-monsoon showers.",
        ],
    )

    # ==========================================
    # SCENARIO 3: SOIL-COVER / CLIMATE-RESILIENT (Berseem / Mustard Cover)
    # ==========================================
    cover_crop = "berseem_clover" if irrigation_type.lower() != "rain_fed" else "mustard"
    cover_prof = get_crop_profile(cover_crop)

    cover_climate = 82.0
    cover_water = 75.0 if cover_crop == "berseem_clover" else 92.0
    cover_soil = 95.0
    cover_market = 82.0

    if is_severe_deficit and cover_crop == "mustard":
        cover_water += 6.0
    if thermal_stress > 2:
        cover_climate -= 5.0

    cover_score, cover_breakdown = _compute_priority_score(
        climate_suitability=cover_climate,
        water_efficiency=cover_water,
        soil_health=cover_soil,
        market_resilience=cover_market,
    )

    soil_cover_scenario = Scenario(
        scenario_id="scenario-soil-cover-03",
        title=f"Soil Regeneration & Forage Pathway ({cover_crop.replace('_', ' ').capitalize()})",
        crop_sequence=[current_crop, cover_crop],
        seasonal_calendar=[
            CalendarEntry(
                crop=current_crop,
                start_month="May",
                harvest_month="September",
                duration_days=110,
            ),
            CalendarEntry(
                crop=cover_crop,
                start_month="October",
                harvest_month="April",
                duration_days=cover_prof.typical_duration_days if cover_prof else 160,
            ),
        ],
        score=cover_score,
        score_breakdown=cover_breakdown,
        rationale=[
            f"Deploys {cover_crop.replace('_', ' ')} as high-biomass soil protective cover and green manure.",
            "Dramatically enhances soil organic matter (SOM) and water-retention capacity on KP soils.",
        ],
        benefits=[
            "Yields multiple green fodder cuttings for livestock integration or high-value winter market sale.",
            "Protects vulnerable topsoil against wind and water erosion during dry transition periods.",
            "Improves soil hydraulic conductivity and moisture retention for subsequent cropping seasons.",
        ],
        risks=[
            "Berseem requires frequent light irrigations; unsuitable for strictly rain-fed arid parcels.",
            "Labor intensive harvesting if managing multiple fodder cuttings.",
        ],
        assumptions=[
            "Assumes local livestock access or strong farm-gate demand for green fodder/oilseed.",
            "Assumes seedbed preparation is timed prior to early autumn temperature drops.",
        ],
    )

    catalog = ScenarioCatalog(
        baseline=baseline_scenario,
        pulse_inclusive=pulse_scenario,
        soil_cover=soil_cover_scenario,
    )

    recommendation_set = RecommendationSet(
        recommendation_id=f"rec-{uuid.uuid4().hex[:8]}",
        farm_id=farm_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        input_snapshot=input_snapshot,
        scenarios=catalog,
        limitations=[
            "Recommendations provide algorithmic decision support based on regional NASA gridded observations (~0.5° × 0.5° grid cells).",
            "Values do not represent direct in-situ farm sensor readings; consult local Khyber Pakhtunkhwa Agriculture Extension officers prior to field implementation.",
            "Crop yields and economic margins depend on localized micro-climate, seed quality, and pest pressures.",
            "Yield claims are decision-support estimates and are never guaranteed.",
        ],
        farm_vs_nasa_comparison=comparison,
    )

    return recommendation_set
