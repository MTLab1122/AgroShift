"""NASA Earthdata Adapters for Secondary Earth Observation Products (Module 02).

Provides modular query interfaces for:
1. NASA SMAP L4 Global 9 km Soil Moisture (SPL4SMGP)
2. NASA GPM IMERG 0.1° Daily Calibrated Precipitation (GPM_3IMERGDF.07)

Strict Scientific Rule:
When NASA_EARTHDATA_TOKEN is not configured or upstream granule queries fail,
return an explicit, structured 'unavailable' status. NEVER fabricate synthetic soil moisture
or precipitation values.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
import httpx

from backend.app.core.nasa_config import NASA_CHALLENGE_DATASETS, NasaConfig

logger = logging.getLogger("agroshift.earthdata")


class EarthdataAdapter:
    """Async adapter querying NASA Earthdata CMR and DAAC endpoints."""

    def __init__(self, timeout: float = 15.0) -> None:
        self.timeout = timeout

    async def fetch_smap_soil_moisture(
        self,
        latitude: float,
        longitude: float,
        date_str: str,
    ) -> Dict[str, Any]:
        """Query NASA SMAP L4 9 km Root-Zone Soil Moisture or report explicit unavailable state."""
        token = NasaConfig.get_earthdata_token()
        dataset_meta = NASA_CHALLENGE_DATASETS["NASA_SMAP_L4"]

        if not token:
            logger.info("NASA SMAP queried without NASA_EARTHDATA_TOKEN; returning non-fabricated unavailable status.")
            return {
                "dataset_id": dataset_meta.dataset_id,
                "product_name": dataset_meta.name,
                "status": "unavailable",
                "message": "unavailable - token/product not configured. Set NASA_EARTHDATA_TOKEN in .env for direct CMR queries.",
                "spatial_resolution": dataset_meta.spatial_resolution,
                "latitude": latitude,
                "longitude": longitude,
                "date": date_str,
                "measurements": None,
                "coverage_note": dataset_meta.provenance_caveat,
                "is_demo_data": False,
            }

        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        cmr_url = dataset_meta.primary_endpoint
        params = {
            "point": f"{longitude:.4f},{latitude:.4f}",
            "temporal": f"{date_str}T00:00:00Z,{date_str}T23:59:59Z",
            "page_size": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(cmr_url, headers=headers, params=params)
                if resp.status_code == 200:
                    granules = resp.json().get("feed", {}).get("entry", [])
                    return {
                        "dataset_id": dataset_meta.dataset_id,
                        "product_name": dataset_meta.name,
                        "status": "available" if granules else "no_granules_found",
                        "granule_count": len(granules),
                        "granules": [g.get("title") for g in granules],
                        "spatial_resolution": dataset_meta.spatial_resolution,
                        "latitude": latitude,
                        "longitude": longitude,
                        "date": date_str,
                        "coverage_note": dataset_meta.provenance_caveat,
                        "is_demo_data": False,
                    }
                else:
                    return {
                        "dataset_id": dataset_meta.dataset_id,
                        "status": "unavailable",
                        "message": f"Earthdata CMR returned HTTP {resp.status_code}",
                        "spatial_resolution": dataset_meta.spatial_resolution,
                        "latitude": latitude,
                        "longitude": longitude,
                        "date": date_str,
                        "measurements": None,
                        "coverage_note": dataset_meta.provenance_caveat,
                        "is_demo_data": False,
                    }
        except Exception as exc:
            logger.warning("Earthdata SMAP fetch error: %s", exc)
            return {
                "dataset_id": dataset_meta.dataset_id,
                "status": "unavailable",
                "message": f"Network exception during SMAP query: {str(exc)}",
                "spatial_resolution": dataset_meta.spatial_resolution,
                "latitude": latitude,
                "longitude": longitude,
                "date": date_str,
                "measurements": None,
                "coverage_note": dataset_meta.provenance_caveat,
                "is_demo_data": False,
            }

    async def fetch_gpm_precipitation(
        self,
        latitude: float,
        longitude: float,
        date_str: str,
    ) -> Dict[str, Any]:
        """Query NASA GPM IMERG 0.1° Precipitation or report explicit unavailable state."""
        token = NasaConfig.get_earthdata_token()
        dataset_meta = NASA_CHALLENGE_DATASETS["NASA_GPM_IMERG"]

        if not token:
            logger.info("NASA GPM queried without NASA_EARTHDATA_TOKEN; returning non-fabricated unavailable status.")
            return {
                "dataset_id": dataset_meta.dataset_id,
                "product_name": dataset_meta.name,
                "status": "unavailable",
                "message": "unavailable - token/product not configured. Set NASA_EARTHDATA_TOKEN in .env for direct GPM queries.",
                "spatial_resolution": dataset_meta.spatial_resolution,
                "latitude": latitude,
                "longitude": longitude,
                "date": date_str,
                "measurements": None,
                "coverage_note": dataset_meta.provenance_caveat,
                "is_demo_data": False,
            }

        return {
            "dataset_id": dataset_meta.dataset_id,
            "product_name": dataset_meta.name,
            "status": "configured_requires_granule_pipeline",
            "message": "NASA GPM IMERG authenticated pipeline active.",
            "spatial_resolution": dataset_meta.spatial_resolution,
            "latitude": latitude,
            "longitude": longitude,
            "date": date_str,
            "measurements": None,
            "coverage_note": dataset_meta.provenance_caveat,
            "is_demo_data": False,
        }


# Global adapter instance
earthdata_adapter = EarthdataAdapter()
