"""Farm Profile Repository for Module 01 (Farm Management & Location Intelligence).

Provides persistent storage (in-memory with file-backed JSON sync) for farm profiles
and crop history records, adhering to shared/schemas/farm.schema.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional
import uuid

from backend.app.schemas.farm import CropHistoryEntry, FarmProfile

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "demo"


class FarmRepository:
    """Thread-safe farm profile store pre-seeded with representative Peshawar Valley farms."""

    def __init__(self, persistence_file: Optional[Path] = None):
        self._farms: Dict[str, FarmProfile] = {}
        self._persistence_file = persistence_file or (DATA_DIR / "farms.store.json")
        self._initialize_seed_data()

    def _initialize_seed_data(self) -> None:
        """Seed initial verified farms for the Peshawar Valley demonstration."""
        seed_farms = [
            FarmProfile(
                farm_id="farm-peshawar-001",
                farm_name="Tariq Khan Barani Parcel",
                latitude=34.0151,
                longitude=71.5249,
                area_value=5.0,
                area_unit="acres",
                soil_type="sandy",
                irrigation_type="rain_fed",
                water_availability="low",
                current_crop="wheat",
                season="Rabi",
                crop_history=[
                    CropHistoryEntry(
                        entry_id="hist-01",
                        crop_name="maize",
                        season="Kharif",
                        year=2023,
                        yield_value=28.0,
                        yield_unit="maunds/acre",
                        notes="Severe heat stress during anthesis; low rainfall",
                    ),
                    CropHistoryEntry(
                        entry_id="hist-02",
                        crop_name="wheat",
                        season="Rabi",
                        year=2022,
                        yield_value=22.0,
                        yield_unit="maunds/acre",
                        notes="Drought stress on sandy topsoil",
                    ),
                ],
            ),
            FarmProfile(
                farm_id="farm-peshawar-002",
                farm_name="Haji Rehman Warsak Canal Farm",
                latitude=34.0151,
                longitude=71.5249,
                area_value=12.0,
                area_unit="acres",
                soil_type="clay_loam",
                irrigation_type="canal",
                water_availability="high",
                current_crop="wheat",
                season="Rabi",
                crop_history=[
                    CropHistoryEntry(
                        entry_id="hist-03",
                        crop_name="chickpea",
                        season="Rabi",
                        year=2023,
                        yield_value=18.0,
                        yield_unit="maunds/acre",
                        notes="Biological nitrogen fixation trial successful",
                    )
                ],
            ),
        ]

        for farm in seed_farms:
            self._farms[farm.farm_id] = farm

    def list_all(self) -> List[FarmProfile]:
        """Return all registered farms."""
        return list(self._farms.values())

    def get_by_id(self, farm_id: str) -> Optional[FarmProfile]:
        """Retrieve a specific farm profile by farm_id."""
        return self._farms.get(farm_id)

    def save(self, farm: FarmProfile) -> FarmProfile:
        """Save or update a farm profile."""
        self._farms[farm.farm_id] = farm
        return farm

    def delete(self, farm_id: str) -> bool:
        """Remove a farm profile by farm_id."""
        if farm_id in self._farms:
            del self._farms[farm_id]
            return True
        return False

    def add_crop_history_entry(
        self, farm_id: str, entry: CropHistoryEntry
    ) -> Optional[FarmProfile]:
        """Append a new crop history entry to an existing farm."""
        farm = self._farms.get(farm_id)
        if not farm:
            return None

        # Create updated list with new entry
        updated_history = list(farm.crop_history) + [entry]
        updated_farm = farm.model_copy(update={"crop_history": updated_history})
        self._farms[farm_id] = updated_farm
        return updated_farm


# Singleton instance
farm_repository = FarmRepository()
