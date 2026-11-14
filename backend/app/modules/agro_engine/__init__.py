"""Agro-Intelligence and Crop Rotation Engine (Module 03)."""

from backend.app.modules.agro_engine.comparator import (
    compare_farm_to_climate,
    evaluate_rotation_monoculture,
)
from backend.app.modules.agro_engine.crop_catalog import (
    CropAgronomicData,
    get_crop_profile,
    get_crops_by_season,
    get_legume_crops,
    list_supported_crops,
    normalize_crop_name,
)
from backend.app.modules.agro_engine.recommendation_engine import (
    generate_recommendations,
)

__all__ = [
    "CropAgronomicData",
    "compare_farm_to_climate",
    "evaluate_rotation_monoculture",
    "generate_recommendations",
    "get_crop_profile",
    "get_crops_by_season",
    "get_legume_crops",
    "list_supported_crops",
    "normalize_crop_name",
]
