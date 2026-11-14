"""Farm Inputs vs. Live NASA Earth Observation Comparison Engine.

Evaluates farmer-submitted parameters (crop, soil, irrigation, history) against
actual NASA POWER and satellite environmental observations to produce the canonical
FarmVsNasaComparison diagnostic and agronomic suitability metrics.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from backend.app.modules.agro_engine.crop_catalog import (
    CropAgronomicData,
    get_crop_profile,
    normalize_crop_name,
)
from backend.app.modules.nasa_data.schemas import (
    ClimateSummary,
    DailyRecord,
)
from backend.app.schemas.comparison import FarmVsNasaComparison
from backend.app.schemas.farm import FarmProfile


def _extract_observed_rainfall(
    climate_data: Union[ClimateSummary, Dict[str, Any]],
    explicit_daily: Optional[List[Any]] = None,
) -> float:
    """Extract total observed precipitation (PRECTOTCORR) from ClimateSummary or dict."""
    total_precip = 0.0

    # If DailyRecords are available, sum daily observations
    daily_records: List[Any] = explicit_daily or []
    if not daily_records:
        if isinstance(climate_data, ClimateSummary):
            daily_records = climate_data.daily_series or getattr(climate_data, "daily_records", []) or []
        elif isinstance(climate_data, dict):
            daily_records = climate_data.get("daily_series") or climate_data.get("daily_records") or []

    if daily_records:
        valid_readings = [
            d.values.get("PRECTOTCORR") if hasattr(d, "values") else d.get("values", {}).get("PRECTOTCORR")
            for d in daily_records
        ]
        summed = sum(v for v in valid_readings if v is not None and isinstance(v, (int, float)))
        if summed > 0.0:
            return round(float(summed), 2)

    # Fall back to aggregates if daily list not provided or empty
    aggregates = (
        climate_data.aggregates
        if isinstance(climate_data, ClimateSummary)
        else climate_data.get("aggregates", {})
    )
    if isinstance(aggregates, dict):
        monthly = aggregates.get("monthly", [])
    else:
        monthly = getattr(aggregates, "monthly", [])

    if monthly:
        month_sums = []
        for m in monthly:
            vals = m.values if hasattr(m, "values") else m.get("values", {})
            p_stat = vals.get("PRECTOTCORR")
            if p_stat is not None:
                p_sum = p_stat.sum if hasattr(p_stat, "sum") else p_stat.get("sum")
                if p_sum is not None:
                    month_sums.append(p_sum)
        if month_sums:
            return round(float(sum(month_sums)), 2)

    return round(total_precip, 2)


def _count_thermal_stress_days(
    climate_data: Union[ClimateSummary, Dict[str, Any]],
    critical_threshold_c: float,
    explicit_daily: Optional[List[Any]] = None,
) -> int:
    """Count observed days where T2M_MAX (or T2M) exceeded the crop's critical heat threshold."""
    daily_records: List[Any] = explicit_daily or []
    if not daily_records:
        if isinstance(climate_data, ClimateSummary):
            daily_records = climate_data.daily_series or getattr(climate_data, "daily_records", []) or []
        elif isinstance(climate_data, dict):
            daily_records = climate_data.get("daily_series") or climate_data.get("daily_records") or []

    stress_count = 0
    for d in daily_records:
        vals = d.values if hasattr(d, "values") else d.get("values", {})
        # Prefer T2M_MAX, fallback to T2M
        t_max = vals.get("T2M_MAX")
        if t_max is None:
            t_max = vals.get("T2M")

        if t_max is not None and isinstance(t_max, (int, float)) and t_max > critical_threshold_c:
            stress_count += 1

    return stress_count


def _compute_irrigation_supplement(
    rainfall_mm: float,
    crop_demand_mm: float,
    irrigation_type: str,
    water_availability: str,
) -> Tuple[float, float, str]:
    """Calculate effective water supplement from reported irrigation infrastructure.

    Returns:
        (irrigation_delivered_mm, total_effective_water_mm, status_category)
    """
    deficit_mm = max(0.0, crop_demand_mm - rainfall_mm)
    irr_norm = irrigation_type.lower().strip()
    avail_norm = water_availability.lower().strip()

    # Availability scaling factor
    avail_factors = {
        "high": 1.0,
        "medium": 0.65,
        "low": 0.30,
        "unknown": 0.50,
    }
    avail_factor = avail_factors.get(avail_norm, 0.50)

    # Irrigation efficiency and capacity limits
    if irr_norm in ("rain_fed", "barani"):
        delivered_mm = 0.0
    elif irr_norm in ("canal", "tube_well"):
        # Flood/basin surface delivery: can satisfy up to 85% of crop deficit with high availability
        delivered_mm = min(deficit_mm, crop_demand_mm * 0.85 * avail_factor)
    elif irr_norm in ("drip",):
        # Micro-irrigation: high application efficiency
        delivered_mm = min(deficit_mm, crop_demand_mm * 0.95 * avail_factor)
    elif irr_norm in ("sprinkler",):
        delivered_mm = min(deficit_mm, crop_demand_mm * 0.80 * avail_factor)
    else:
        # other / unknown
        delivered_mm = min(deficit_mm, crop_demand_mm * 0.60 * avail_factor)

    total_water = rainfall_mm + delivered_mm

    # Classify water balance status
    if rainfall_mm > crop_demand_mm * 1.30:
        status: Literal["severe_deficit", "moderate_deficit", "balanced", "excess_moisture"] = "excess_moisture"
    elif total_water >= crop_demand_mm * 0.85:
        status = "balanced"
    elif total_water >= crop_demand_mm * 0.50:
        status = "moderate_deficit"
    else:
        status = "severe_deficit"

    return round(delivered_mm, 2), round(total_water, 2), status


def _build_irrigation_note(
    crop_name: str,
    crop_demand_mm: float,
    observed_rainfall_mm: float,
    delivered_irrigation_mm: float,
    total_water_mm: float,
    water_status: str,
    irrigation_type: str,
    water_availability: str,
    soil_type: str,
    thermal_stress_days: int,
    crop_profile: Optional[CropAgronomicData],
) -> str:
    """Build a transparent, scientifically honest agronomic reconciliation narrative."""
    pct_covered = round((total_water_mm / max(crop_demand_mm, 1.0)) * 100.0, 1)
    rain_pct = round((observed_rainfall_mm / max(crop_demand_mm, 1.0)) * 100.0, 1)

    parts: List[str] = []

    # Precipitation vs Demand statement
    parts.append(
        f"NASA POWER observed {observed_rainfall_mm:.1f} mm precipitation, satisfying {rain_pct}% "
        f"of seasonal {crop_name.capitalize()} water requirement ({crop_demand_mm:.1f} mm)."
    )

    # Irrigation reconciliation
    if irrigation_type.lower() in ("rain_fed", "barani"):
        if water_status in ("severe_deficit", "moderate_deficit"):
            parts.append(
                f"With rain-fed (barani) cultivation and no supplemental irrigation, the parcel experiences a "
                f"{crop_demand_mm - observed_rainfall_mm:.1f} mm moisture deficit ({water_status.replace('_', ' ')}). "
                f"Transitioning to drought-resilient legumes (chickpea or lentil) is strongly advised."
            )
        elif water_status == "excess_moisture":
            parts.append(
                f"Precipitation significantly exceeded seasonal needs on {soil_type} soil. Ensure drainage to avoid waterlogging."
            )
        else:
            parts.append("Natural precipitation adequately met baseline crop demand without irrigation.")
    else:
        if water_status == "balanced":
            parts.append(
                f"Reported {irrigation_type} irrigation ({water_availability} availability) delivered an estimated "
                f"{delivered_irrigation_mm:.1f} mm, elevating total moisture to {total_water_mm:.1f} mm ({pct_covered}% adequacy)."
            )
        elif water_status == "moderate_deficit":
            parts.append(
                f"Reported {irrigation_type} irrigation provided {delivered_irrigation_mm:.1f} mm, but low-to-medium availability "
                f"leaves a residual {crop_demand_mm - total_water_mm:.1f} mm moisture deficit ({pct_covered}% adequacy)."
            )
        elif water_status == "severe_deficit":
            parts.append(
                f"Despite {irrigation_type} infrastructure, {water_availability} water availability supplied only "
                f"{delivered_irrigation_mm:.1f} mm against an acute {crop_demand_mm - observed_rainfall_mm:.1f} mm deficit. "
                f"High crop water-stress risk."
            )
        else:
            parts.append(
                f"High observed rainfall coupled with {soil_type} soil creates potential waterlogging conditions."
            )

    # Thermal stress statement
    if thermal_stress_days > 0:
        threshold = crop_profile.critical_heat_threshold_c if crop_profile else 35.0
        parts.append(
            f"Observed {thermal_stress_days} heat-stress day(s) exceeding {threshold:.1f}°C during the window; "
            f"timed irrigations or heat-tolerant rotations are recommended to mitigate yield loss."
        )

    return " ".join(parts)


def evaluate_rotation_monoculture(
    current_crop: str,
    crop_history: List[Any],
) -> Dict[str, Any]:
    """Analyze crop history for monoculture repetition, legume breaks, and soil health debt.

    Returns:
        Dict with consecutive_poaceae_count, has_legume_break, nitrogen_debt_warning, and rotation_score.
    """
    curr_norm = normalize_crop_name(current_crop)
    curr_prof = get_crop_profile(curr_norm)
    curr_family = curr_prof.crop_family if curr_prof else "other"

    consecutive_same_family = 1 if curr_family == "poaceae" else 0
    has_legume_in_history = curr_prof.is_legume if curr_prof else False

    # Trace backward through history
    for entry in crop_history:
        entry_crop = (
            entry.crop_name if hasattr(entry, "crop_name") else entry.get("crop_name", "")
        )
        hist_norm = normalize_crop_name(entry_crop)
        hist_prof = get_crop_profile(hist_norm)

        if hist_prof and hist_prof.is_legume:
            has_legume_in_history = True

        if hist_prof and hist_prof.crop_family == "poaceae" and curr_family == "poaceae":
            consecutive_same_family += 1
        else:
            break

    # Monoculture fatigue warning
    monoculture_risk = consecutive_same_family >= 2
    rotation_penalty = min(consecutive_same_family * 15.0, 45.0)

    return {
        "consecutive_cereal_seasons": consecutive_same_family,
        "monoculture_risk": monoculture_risk,
        "has_legume_break": has_legume_in_history,
        "nitrogen_debt_warning": not has_legume_in_history,
        "rotation_penalty_points": rotation_penalty,
    }


def compare_farm_to_climate(
    farm_profile: Union[FarmProfile, Dict[str, Any]],
    climate_summary: Union[ClimateSummary, Dict[str, Any]],
    daily_records: Optional[List[Any]] = None,
    data_mode: Literal["live", "demo_fallback", "demo_forced"] = "live",
) -> FarmVsNasaComparison:
    """Compare farmer-submitted inputs against NASA climate observations.

    Reconciles crop water demand, observed precipitation, reported irrigation capability,
    and thermal threshold crossings into the canonical FarmVsNasaComparison model.
    """
    # Extract farm parameters
    if isinstance(farm_profile, FarmProfile):
        current_crop = farm_profile.current_crop
        irrigation_type = farm_profile.irrigation_type
        water_availability = farm_profile.water_availability
        soil_type = farm_profile.soil_type
    else:
        current_crop = farm_profile.get("current_crop", "wheat")
        irrigation_type = farm_profile.get("irrigation_type", "canal")
        water_availability = farm_profile.get("water_availability", "medium")
        soil_type = farm_profile.get("soil_type", "loamy")

    # Agronomic lookup
    crop_prof = get_crop_profile(current_crop)
    expected_water_demand = (
        crop_prof.seasonal_water_demand_mm if crop_prof else 400.0
    )
    heat_threshold = (
        crop_prof.critical_heat_threshold_c if crop_prof else 32.0
    )

    # Precipitation and thermal calculations
    observed_rain = _extract_observed_rainfall(climate_summary, explicit_daily=daily_records)
    thermal_stress_days = _count_thermal_stress_days(
        climate_summary, heat_threshold, explicit_daily=daily_records
    )

    # Irrigation and water balance
    delivered_irr, total_water, water_status = _compute_irrigation_supplement(
        rainfall_mm=observed_rain,
        crop_demand_mm=expected_water_demand,
        irrigation_type=irrigation_type,
        water_availability=water_availability,
    )

    # Narrative note
    adequacy_note = _build_irrigation_note(
        crop_name=current_crop,
        crop_demand_mm=expected_water_demand,
        observed_rainfall_mm=observed_rain,
        delivered_irrigation_mm=delivered_irr,
        total_water_mm=total_water,
        water_status=water_status,
        irrigation_type=irrigation_type,
        water_availability=water_availability,
        soil_type=soil_type,
        thermal_stress_days=thermal_stress_days,
        crop_profile=crop_prof,
    )

    # Normalize data_mode
    raw_mode = data_mode.value if hasattr(data_mode, "value") else str(data_mode)
    clean_mode: Literal["live", "demo_fallback", "demo_forced"] = "live"
    norm_str = raw_mode.replace("-", "_").lower()
    if norm_str in ("live", "demo_fallback", "demo_forced"):
        clean_mode = norm_str  # type: ignore

    return FarmVsNasaComparison(
        observed_rainfall_mm=observed_rain,
        expected_crop_water_need_mm=expected_water_demand,
        water_balance_status=water_status,
        thermal_stress_days=thermal_stress_days,
        irrigation_adequacy_note=adequacy_note,
        data_mode=clean_mode,
    )
