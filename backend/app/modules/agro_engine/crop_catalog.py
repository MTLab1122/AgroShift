"""Peshawar Valley & Khyber Pakhtunkhwa Agronomic Crop Reference Catalog.

Provides peer-reviewed baseline physiological and environmental requirements
for staple cereals, pulses, cash crops, and forages in the KP/Peshawar Valley
agro-climatic zone for NASA Earth observation cross-comparison.
"""

from __future__ import annotations

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class CropAgronomicData(BaseModel):
    """Agronomic benchmarks for a specific crop cultivar in the Peshawar Valley."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Canonical lowercase key (e.g. wheat, chickpea)")
    display_name: str = Field(..., description="English common name")
    urdu_name: str = Field(..., description="Urdu / Pashto local name")
    botanical_name: str = Field(..., description="Binomial botanical taxonomy")
    crop_family: Literal["poaceae", "fabaceae", "brassicaceae", "other"] = Field(
        ..., description="Taxonomic family for rotation disease-break calculations"
    )
    season: Literal["Rabi", "Kharif", "Zaid", "Annual"] = Field(
        ..., description="Primary agricultural season in KP"
    )
    typical_duration_days: int = Field(..., ge=45, le=365, description="Expected days to maturity")
    min_duration_days: int = Field(..., ge=30, le=365)
    max_duration_days: int = Field(..., ge=45, le=365)
    seasonal_water_demand_mm: float = Field(
        ..., ge=100.0, le=3000.0, description="Benchmark total crop water requirement (ETc in mm)"
    )
    min_water_mm: float = Field(..., ge=50.0)
    max_water_mm: float = Field(..., ge=150.0)
    optimal_temp_min_c: float = Field(..., description="Lower bound of optimal temperature range (°C)")
    optimal_temp_max_c: float = Field(..., description="Upper bound of optimal temperature range (°C)")
    critical_heat_threshold_c: float = Field(
        ..., description="Maximum temperature (°C) triggering heat stress/flowering abort"
    )
    base_temp_gdd_c: float = Field(
        default=5.0, description="Base temperature (°C) for Growing Degree Day (GDD) accumulation"
    )
    is_legume: bool = Field(default=False, description="Whether crop fixes atmospheric nitrogen")
    nitrogen_fixation_kg_ha: float = Field(
        default=0.0, ge=0.0, description="Estimated biological nitrogen fixation (kg N/ha)"
    )
    rooting_depth_cm: int = Field(..., ge=20, le=250, description="Effective rooting zone depth in cm")
    soil_compatibility: List[str] = Field(..., min_length=1, description="List of compatible soil types")
    drought_tolerance: Literal["high", "medium", "low"] = Field(..., description="Resistance to moisture deficit")
    waterlogging_tolerance: Literal["high", "medium", "low"] = Field(
        ..., description="Resistance to standing water/waterlogging"
    )
    description: str = Field(..., description="Agronomic summary and local cultivation context")


# Verified agronomic benchmarks for Peshawar Valley (Agro-Climatic Zone D, KP)
_PESHAWAR_CROP_CATALOG: Dict[str, CropAgronomicData] = {
    "wheat": CropAgronomicData(
        name="wheat",
        display_name="Wheat",
        urdu_name="گندم (Gandum)",
        botanical_name="Triticum aestivum",
        crop_family="poaceae",
        season="Rabi",
        typical_duration_days=140,
        min_duration_days=120,
        max_duration_days=160,
        seasonal_water_demand_mm=400.0,
        min_water_mm=350.0,
        max_water_mm=480.0,
        optimal_temp_min_c=12.0,
        optimal_temp_max_c=25.0,
        critical_heat_threshold_c=32.0,  # Terminal heat stress threshold during anthesis/grain filling
        base_temp_gdd_c=5.0,
        is_legume=False,
        nitrogen_fixation_kg_ha=0.0,
        rooting_depth_cm=120,
        soil_compatibility=["loamy", "clay_loam", "silty", "clay"],
        drought_tolerance="medium",
        waterlogging_tolerance="low",
        description="Major staple winter cereal in Peshawar Valley. Sensitive to terminal heat stress above 32°C in March-April.",
    ),
    "maize": CropAgronomicData(
        name="maize",
        display_name="Maize / Corn",
        urdu_name="مکئی (Makai)",
        botanical_name="Zea mays",
        crop_family="poaceae",
        season="Kharif",
        typical_duration_days=105,
        min_duration_days=90,
        max_duration_days=120,
        seasonal_water_demand_mm=550.0,
        min_water_mm=450.0,
        max_water_mm=680.0,
        optimal_temp_min_c=20.0,
        optimal_temp_max_c=32.0,
        critical_heat_threshold_c=38.0,  # Heat stress causing pollen desiccation during tasseling
        base_temp_gdd_c=10.0,
        is_legume=False,
        nitrogen_fixation_kg_ha=0.0,
        rooting_depth_cm=100,
        soil_compatibility=["loamy", "silty", "clay_loam"],
        drought_tolerance="low",
        waterlogging_tolerance="low",
        description="Key summer/monsoon cereal in KP. Requires adequate moisture during flowering and silking stages.",
    ),
    "rice": CropAgronomicData(
        name="rice",
        display_name="Rice (Paddy)",
        urdu_name="چاول / دھان (Sholay)",
        botanical_name="Oryza sativa",
        crop_family="poaceae",
        season="Kharif",
        typical_duration_days=130,
        min_duration_days=110,
        max_duration_days=150,
        seasonal_water_demand_mm=1200.0,
        min_water_mm=950.0,
        max_water_mm=1500.0,
        optimal_temp_min_c=22.0,
        optimal_temp_max_c=34.0,
        critical_heat_threshold_c=38.0,
        base_temp_gdd_c=10.0,
        is_legume=False,
        nitrogen_fixation_kg_ha=0.0,
        rooting_depth_cm=60,
        soil_compatibility=["clay", "clay_loam"],
        drought_tolerance="low",
        waterlogging_tolerance="high",
        description="High water-intensity crop cultivated in canal-irrigated pockets of Peshawar and Charsadda basin.",
    ),
    "sugarcane": CropAgronomicData(
        name="sugarcane",
        display_name="Sugarcane",
        urdu_name="کماد / گنا (Kamand)",
        botanical_name="Saccharum officinarum",
        crop_family="poaceae",
        season="Annual",
        typical_duration_days=330,
        min_duration_days=300,
        max_duration_days=365,
        seasonal_water_demand_mm=1800.0,
        min_water_mm=1500.0,
        max_water_mm=2300.0,
        optimal_temp_min_c=24.0,
        optimal_temp_max_c=38.0,
        critical_heat_threshold_c=42.0,
        base_temp_gdd_c=12.0,
        is_legume=False,
        nitrogen_fixation_kg_ha=0.0,
        rooting_depth_cm=180,
        soil_compatibility=["loamy", "clay_loam", "clay"],
        drought_tolerance="medium",
        waterlogging_tolerance="medium",
        description="Commercial annual cash crop dominating Peshawar/Mardan sugar mill catchments. Highly water and nutrient intensive.",
    ),
    "mustard": CropAgronomicData(
        name="mustard",
        display_name="Mustard / Rapeseed",
        urdu_name="سرسوں / توریا (Sarson)",
        botanical_name="Brassica napus / B. juncea",
        crop_family="brassicaceae",
        season="Rabi",
        typical_duration_days=110,
        min_duration_days=95,
        max_duration_days=125,
        seasonal_water_demand_mm=260.0,
        min_water_mm=200.0,
        max_water_mm=320.0,
        optimal_temp_min_c=12.0,
        optimal_temp_max_c=25.0,
        critical_heat_threshold_c=30.0,
        base_temp_gdd_c=5.0,
        is_legume=False,
        nitrogen_fixation_kg_ha=0.0,
        rooting_depth_cm=90,
        soil_compatibility=["sandy", "loamy", "silty", "clay_loam"],
        drought_tolerance="high",
        waterlogging_tolerance="low",
        description="Valuable winter oilseed with low water demand, excellent for crop diversification after summer maize.",
    ),
    "chickpea": CropAgronomicData(
        name="chickpea",
        display_name="Chickpea (Gram)",
        urdu_name="چنا (Chana)",
        botanical_name="Cicer arietinum",
        crop_family="fabaceae",
        season="Rabi",
        typical_duration_days=120,
        min_duration_days=105,
        max_duration_days=135,
        seasonal_water_demand_mm=240.0,
        min_water_mm=180.0,
        max_water_mm=300.0,
        optimal_temp_min_c=15.0,
        optimal_temp_max_c=26.0,
        critical_heat_threshold_c=32.0,
        base_temp_gdd_c=5.0,
        is_legume=True,
        nitrogen_fixation_kg_ha=75.0,
        rooting_depth_cm=100,
        soil_compatibility=["sandy", "loamy", "silty", "clay_loam"],
        drought_tolerance="high",
        waterlogging_tolerance="low",
        description="High-value winter pulse fixing 60-90 kg N/ha. Highly drought tolerant, requires well-drained soils.",
    ),
    "lentil": CropAgronomicData(
        name="lentil",
        display_name="Lentil",
        urdu_name="مسور (Masoor)",
        botanical_name="Lens culinaris",
        crop_family="fabaceae",
        season="Rabi",
        typical_duration_days=110,
        min_duration_days=95,
        max_duration_days=125,
        seasonal_water_demand_mm=220.0,
        min_water_mm=170.0,
        max_water_mm=280.0,
        optimal_temp_min_c=14.0,
        optimal_temp_max_c=25.0,
        critical_heat_threshold_c=30.0,
        base_temp_gdd_c=5.0,
        is_legume=True,
        nitrogen_fixation_kg_ha=55.0,
        rooting_depth_cm=75,
        soil_compatibility=["loamy", "silty", "clay_loam", "sandy"],
        drought_tolerance="high",
        waterlogging_tolerance="low",
        description="Nutritious cool-season pulse fixing atmospheric nitrogen and breaking cereal monoculture disease cycles.",
    ),
    "mung_bean": CropAgronomicData(
        name="mung_bean",
        display_name="Mung Bean (Green Gram)",
        urdu_name="مونگ (Moong)",
        botanical_name="Vigna radiata",
        crop_family="fabaceae",
        season="Kharif",
        typical_duration_days=75,
        min_duration_days=65,
        max_duration_days=90,
        seasonal_water_demand_mm=300.0,
        min_water_mm=240.0,
        max_water_mm=380.0,
        optimal_temp_min_c=25.0,
        optimal_temp_max_c=35.0,
        critical_heat_threshold_c=40.0,
        base_temp_gdd_c=10.0,
        is_legume=True,
        nitrogen_fixation_kg_ha=45.0,
        rooting_depth_cm=70,
        soil_compatibility=["sandy", "loamy", "silty", "clay_loam"],
        drought_tolerance="medium",
        waterlogging_tolerance="low",
        description="Fast-maturing summer legume ideal as a catch crop between wheat and maize, restoring soil fertility.",
    ),
    "berseem_clover": CropAgronomicData(
        name="berseem_clover",
        display_name="Berseem Clover (Egyptian Clover)",
        urdu_name="برسیم / شفتل (Shaftal)",
        botanical_name="Trifolium alexandrinum",
        crop_family="fabaceae",
        season="Rabi",
        typical_duration_days=180,
        min_duration_days=150,
        max_duration_days=210,
        seasonal_water_demand_mm=500.0,
        min_water_mm=400.0,
        max_water_mm=650.0,
        optimal_temp_min_c=14.0,
        optimal_temp_max_c=28.0,
        critical_heat_threshold_c=34.0,
        base_temp_gdd_c=5.0,
        is_legume=True,
        nitrogen_fixation_kg_ha=140.0,
        rooting_depth_cm=80,
        soil_compatibility=["loamy", "clay_loam", "clay", "silty"],
        drought_tolerance="low",
        waterlogging_tolerance="medium",
        description="Premier winter multi-cut green fodder fixing 120-160 kg N/ha, dramatically elevating soil organic carbon.",
    ),
}

# Local terminology and common spelling variation aliases
_SYNONYMS: Dict[str, str] = {
    "wheat": "wheat",
    "gandum": "wheat",
    "gehun": "wheat",
    "triticum": "wheat",
    "maize": "maize",
    "makai": "maize",
    "corn": "maize",
    "zea_mays": "maize",
    "rice": "rice",
    "paddy": "rice",
    "sholay": "rice",
    "basmati": "rice",
    "irri": "rice",
    "chawal": "rice",
    "sugarcane": "sugarcane",
    "cane": "sugarcane",
    "kamand": "sugarcane",
    "ganna": "sugarcane",
    "sugar_cane": "sugarcane",
    "mustard": "mustard",
    "sarson": "mustard",
    "toria": "mustard",
    "toriam": "mustard",
    "rapeseed": "mustard",
    "raya": "mustard",
    "chickpea": "chickpea",
    "chana": "chickpea",
    "gram": "chickpea",
    "chickpeas": "chickpea",
    "lentil": "lentil",
    "lentils": "lentil",
    "masoor": "lentil",
    "mung": "mung_bean",
    "mung_bean": "mung_bean",
    "moong": "mung_bean",
    "mash": "mung_bean",
    "green_gram": "mung_bean",
    "berseem": "berseem_clover",
    "berseem_clover": "berseem_clover",
    "shaftal": "berseem_clover",
    "clover": "berseem_clover",
    "egyptian_clover": "berseem_clover",
}


def normalize_crop_name(raw_name: str) -> str:
    """Normalize input crop name strings into canonical catalog keys.

    Handles case variations, punctuation, whitespace, and regional Urdu/Pashto transliterations.
    """
    clean = raw_name.strip().lower().replace("-", "_").replace(" ", "_")
    return _SYNONYMS.get(clean, clean)


def get_crop_profile(crop_name: str) -> Optional[CropAgronomicData]:
    """Retrieve full agronomic benchmark data for a given crop name or alias.

    Returns None if crop is not registered in the catalog.
    """
    canonical_key = normalize_crop_name(crop_name)
    return _PESHAWAR_CROP_CATALOG.get(canonical_key)


def list_supported_crops() -> List[CropAgronomicData]:
    """Return all agronomic profiles defined in the catalog."""
    return list(_PESHAWAR_CROP_CATALOG.values())


def get_crops_by_season(season: str) -> List[CropAgronomicData]:
    """Filter supported crops by target agricultural season (Rabi, Kharif, Zaid, Annual)."""
    target = season.strip().capitalize()
    return [c for c in _PESHAWAR_CROP_CATALOG.values() if c.season == target or c.season == "Annual"]


def get_legume_crops() -> List[CropAgronomicData]:
    """Return all biological nitrogen-fixing pulse and forage crops."""
    return [c for c in _PESHAWAR_CROP_CATALOG.values() if c.is_legume]
