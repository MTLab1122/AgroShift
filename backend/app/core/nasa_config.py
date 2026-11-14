"""NASA Space Apps Challenge 2026: Adapting Farms with NASA Data.

Configuration registry for official challenge resources and NASA Earth observation endpoints:
Challenge Reference: https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/?tab=resources
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

CHALLENGE_TITLE = "Adapting Farms with NASA Data"
CHALLENGE_URL = "https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/?tab=resources"
CHALLENGE_ORGANIZATION = "NASA Space Apps Challenge 2026"


class DatasetMetadata(BaseModel):
    """Specification of an authorized NASA Earth Observation product."""

    dataset_id: str
    name: str
    description: str
    primary_endpoint: str
    spatial_resolution: str
    temporal_resolution: str
    requires_auth: bool
    parameter_codes: List[str]
    provenance_caveat: str


# Registry of NASA Space Apps 2026 Challenge Datasets
NASA_CHALLENGE_DATASETS: Dict[str, DatasetMetadata] = {
    "NASA_POWER_AG": DatasetMetadata(
        dataset_id="NASA_POWER_AG",
        name="NASA POWER Daily Agroclimatology API",
        description="Daily meteorological and solar variables from MERRA-2, GEOS-FP-IT, and CERES for agriculture.",
        primary_endpoint=os.getenv(
            "NASA_POWER_BASE_URL",
            "https://power.larc.nasa.gov/api/temporal/daily/point",
        ),
        spatial_resolution="0.5° × 0.5° (~50 km × 50 km)",
        temporal_resolution="Daily (1981-present)",
        requires_auth=False,
        parameter_codes=[
            "T2M",
            "T2M_MAX",
            "T2M_MIN",
            "PRECTOTCORR",
            "RH2M",
            "ALLSKY_SFC_SW_DWN",
        ],
        provenance_caveat=(
            "Gridded NASA satellite and reanalysis data represents regional grid cells (~0.5° × 0.5°), "
            "not direct on-farm in-situ sensor measurements. Use for regional decision support and agro-climatic context."
        ),
    ),
    "NASA_SMAP_L4": DatasetMetadata(
        dataset_id="NASA_SMAP_L4",
        name="NASA SMAP L4 Surface & Root-Zone Soil Moisture",
        description="Assimilated satellite radiometer and Catchment Land Surface Model root-zone soil moisture.",
        primary_endpoint=os.getenv(
            "NASA_SMAP_ENDPOINT",
            "https://cmr.earthdata.nasa.gov/search/granules.json?short_name=SPL4SMGP",
        ),
        spatial_resolution="9 km EASE-Grid 2.0",
        temporal_resolution="3-hourly to daily",
        requires_auth=True,
        parameter_codes=["sm_rootzone", "sm_surface"],
        provenance_caveat=(
            "NASA SMAP L4 provides regional 9 km assimilations. Requires Earthdata Login token."
        ),
    ),
    "NASA_GPM_IMERG": DatasetMetadata(
        dataset_id="NASA_GPM_IMERG",
        name="NASA GPM IMERG Calibrated Daily Precipitation",
        description="Integrated Multi-satellitE Retrievals for GPM (IMERG) satellite precipitation constellation.",
        primary_endpoint=os.getenv(
            "NASA_GPM_ENDPOINT",
            "https://gpm1.gesdisc.eosdis.nasa.gov/data/GPM_L3/GPM_3IMERGDF.07",
        ),
        spatial_resolution="0.1° × 0.1° (~10 km × 10 km)",
        temporal_resolution="Daily (2000-present)",
        requires_auth=True,
        parameter_codes=["precipitationCal"],
        provenance_caveat=(
            "NASA GPM IMERG provides multi-satellite 0.1° gridded estimates. Requires Earthdata Bearer auth."
        ),
    ),
}


class NasaConfig:
    """Runtime configuration for NASA API integrations."""

    @classmethod
    def get_power_base_url(cls) -> str:
        return os.getenv(
            "NASA_POWER_BASE_URL",
            "https://power.larc.nasa.gov/api/temporal/daily/point",
        )

    @classmethod
    def get_earthdata_token(cls) -> Optional[str]:
        token = os.getenv("NASA_EARTHDATA_TOKEN", "").strip()
        return token if token else None

    @classmethod
    def get_timeout_seconds(cls) -> float:
        return float(os.getenv("NASA_POWER_TIMEOUT_SECONDS", "20.0"))

    @classmethod
    def get_cache_ttl_seconds(cls) -> int:
        return int(os.getenv("NASA_POWER_CACHE_TTL_SECONDS", "3600"))

    @classmethod
    def is_earthdata_configured(cls) -> bool:
        return cls.get_earthdata_token() is not None
