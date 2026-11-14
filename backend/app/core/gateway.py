"""Smart Live-to-Demo Fallback Gateway for AgroShift (Module 05).

Provides:
- Resilient routing of module queries to live services with automated fallback to verified demo fixtures.
- Strict isolation of validation errors (client 422 errors fail immediately and never silently fall back).
- Automated injection of X-AgroShift-Data-Mode ('live' vs 'demo-fallback' vs 'demo-forced').
- Provenance transparency ensuring fallback fixtures carry is_demo_data=True and explicit annotations.
"""

from __future__ import annotations

from enum import Enum
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Response

from backend.app.modules.nasa_data.aggregations import compute_all_aggregates
from backend.app.modules.nasa_data.normalizer import normalize_power_response
from backend.app.modules.nasa_data.power_client import (
    NasaPowerClient,
    NasaPowerClientError,
)
from backend.app.modules.nasa_data.schemas import (
    ClimateSummary,
)

logger = logging.getLogger("agroshift.gateway")


class DataMode(str, Enum):
    LIVE = "live"
    DEMO_FALLBACK = "demo-fallback"
    DEMO_FORCED = "demo-forced"


HEADER_DATA_MODE = "X-AgroShift-Data-Mode"
HEADER_FALLBACK_REASON = "X-AgroShift-Fallback-Reason"


class IntegrationGateway:
    """Central resilience gateway orchestrating live module calls and contract-compliant demo fallbacks."""

    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        self.workspace_root = (
            workspace_root
            if workspace_root is not None
            else Path(__file__).resolve().parents[3]
        )
        self.demo_dir = self.workspace_root / "data" / "demo"
        self._cached_demo_climate: Optional[ClimateSummary] = None

    def load_demo_climate_fixture(self) -> ClimateSummary:
        """Load and cache canonical Peshawar Valley demo climate fixture."""
        if self._cached_demo_climate is not None:
            return self._cached_demo_climate.model_copy(deep=True)

        primary_path = self.demo_dir / "climate.mock.json"
        alt_path = (
            self.workspace_root
            / "backend"
            / "app"
            / "modules"
            / "nasa_data"
            / "fixtures"
            / "climate.mock.json"
        )

        target = primary_path if primary_path.is_file() else alt_path
        if not target.is_file():
            raise FileNotFoundError(f"Missing required demo fixture at {target}")

        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)

        summary = ClimateSummary.model_validate(data)
        self._cached_demo_climate = summary
        return summary.model_copy(deep=True)

    def is_demo_fixture_available(self) -> bool:
        """Check whether local demo fixtures are present and valid."""
        try:
            self.load_demo_climate_fixture()
            return True
        except Exception as exc:
            logger.error("Demo fixture check failed: %s", exc)
            return False

    async def get_climate_summary(
        self,
        power_client: NasaPowerClient,
        farm_id: str,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
        parameters: Optional[List[str]] = None,
        include_daily: bool = False,
        force_demo: bool = False,
        request_id: Optional[str] = None,
        response: Optional[Response] = None,
    ) -> Tuple[ClimateSummary, DataMode]:
        """Fetch climate data with automatic transparent fallback if NASA POWER is unreachable.

        Crucial rule: Pre-flight validation errors (422) are NEVER masked by demo fallback.
        Only upstream connectivity/timeout/5xx errors trigger transparent fallback.
        """
        # Case 1: Explicit demo requested
        if force_demo:
            demo_summary = self.load_demo_climate_fixture()
            if not include_daily:
                demo_summary = demo_summary.model_copy(update={"daily_series": None})

            if response is not None:
                response.headers[HEADER_DATA_MODE] = DataMode.DEMO_FORCED.value

            return demo_summary, DataMode.DEMO_FORCED

        # Case 2: Attempt live fetch with pre-flight check
        try:
            power_res = await power_client.fetch_daily_point(
                farm_id=farm_id,
                latitude=latitude,
                longitude=longitude,
                start_date=start_date,
                end_date=end_date,
                parameters=parameters,
                request_id=request_id,
            )

            meta_params, daily_records, missing_data = normalize_power_response(
                raw_payload=power_res["raw_data"],
                start_date=start_date,
                end_date=end_date,
                requested_parameters=power_res["request_meta"]["parameters"],
            )

            aggregates = compute_all_aggregates(daily_records)

            coverage_note = (
                "Gridded NASA satellite and reanalysis data represents regional grid cells (~0.5° × 0.5° / ~50km × 50km resolution), "
                "not direct on-farm in-situ sensor measurements. Use for regional decision support and agro-climatic context."
            )

            summary = ClimateSummary(
                farm_id=farm_id,
                source="NASA POWER Daily API",
                product_or_dataset="MERRA-2 / GEOS-5 FP-IT / CERES SYN1deg via POWER AG community",
                latitude=round(latitude, 4),
                longitude=round(longitude, 4),
                start_date=start_date,
                end_date=end_date,
                parameters=meta_params,
                daily_series=daily_records if include_daily else None,
                aggregates=aggregates,
                missing_data=missing_data,
                retrieved_at=power_res["retrieved_at"],
                coverage_note=coverage_note,
                is_demo_data=False,
            )

            if response is not None:
                response.headers[HEADER_DATA_MODE] = DataMode.LIVE.value

            return summary, DataMode.LIVE

        except NasaPowerClientError as client_exc:
            # Client validation errors (422, 400) MUST NOT be masked
            if client_exc.status_code in (400, 422):
                raise

            # Upstream timeouts (504), network failures, or 503 triggers smart fallback
            logger.warning(
                "Upstream NASA POWER error [%s: %s]. Activating demo-fallback for request_id=%s",
                client_exc.api_error.error_code,
                client_exc.api_error.message,
                request_id,
            )

            fallback_summary = self.load_demo_climate_fixture()
            # Update request-specific identifiers while clearly tagging demo status
            fallback_summary = fallback_summary.model_copy(
                update={
                    "farm_id": farm_id,
                    "latitude": round(latitude, 4),
                    "longitude": round(longitude, 4),
                    "is_demo_data": True,
                    "coverage_note": (
                        f"[FALLBACK DEMO MODE] Upstream NASA POWER was temporarily unreachable ({client_exc.api_error.error_code}). "
                        "Displaying verified synthetic Peshawar Valley demo baseline. "
                        + fallback_summary.coverage_note
                    ),
                    "daily_series": fallback_summary.daily_series if include_daily else None,
                }
            )

            if response is not None:
                response.headers[HEADER_DATA_MODE] = DataMode.DEMO_FALLBACK.value
                response.headers[HEADER_FALLBACK_REASON] = client_exc.api_error.error_code

            return fallback_summary, DataMode.DEMO_FALLBACK


# Global singleton instance
gateway = IntegrationGateway()
