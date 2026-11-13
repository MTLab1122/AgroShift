"""NASA POWER Daily API Client for Module 02.

Provides asynchronous data retrieval from the NASA POWER Daily API with:
- Strict pre-network coordinate and date boundary validation.
- Exponential backoff retry policy for transient 429/5xx and network dropouts.
- Standardized translation of network/upstream faults into ApiError structures.
- In-memory deterministic TTL caching with rounded coordinates and parameter keys.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
import logging
import random
import time
from typing import Any, Dict, List, Optional, Tuple
import httpx
from pydantic import ValidationError

from backend.app.modules.nasa_data.schemas import (
    ApiError,
    ClimateRequest,
)

logger = logging.getLogger(__name__)

NASA_POWER_DAILY_POINT_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
DEFAULT_PARAMETERS = ["T2M", "PRECTOTCORR", "RH2M", "ALLSKY_SFC_SW_DWN"]
DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_CACHE_TTL_SECONDS = 3600  # 1 hour


class NasaPowerClientError(Exception):
    """Exception raised for client or upstream errors, wrapping a canonical ApiError."""

    def __init__(self, api_error: ApiError, status_code: int = 500) -> None:
        super().__init__(api_error.message)
        self.api_error = api_error
        self.status_code = status_code


class InMemoryTtlCache:
    """Thread-safe in-memory cache with Time-To-Live expiration."""

    def __init__(self, default_ttl: int = DEFAULT_CACHE_TTL_SECONDS) -> None:
        self.default_ttl = default_ttl
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            expires_at, data = entry
            if time.time() > expires_at:
                del self._store[key]
                return None
            return data

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        async with self._lock:
            effective_ttl = ttl if ttl is not None else self.default_ttl
            self._store[key] = (time.time() + effective_ttl, value)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    async def size(self) -> int:
        async with self._lock:
            # Clean expired items on size query
            now = time.time()
            keys_to_del = [k for k, (exp, _) in self._store.items() if exp <= now]
            for k in keys_to_del:
                del self._store[k]
            return len(self._store)


class NasaPowerClient:
    """Async client for NASA POWER Agroclimatology (AG) Daily Point API."""

    def __init__(
        self,
        base_url: str = NASA_POWER_DAILY_POINT_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = 3,
        backoff_base: float = 1.0,
        cache: Optional[InMemoryTtlCache] = None,
        cache_ttl: int = DEFAULT_CACHE_TTL_SECONDS,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.cache = cache if cache is not None else InMemoryTtlCache(default_ttl=cache_ttl)

    @staticmethod
    def generate_cache_key(
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
        parameters: List[str],
    ) -> str:
        """Deterministic cache key based on 4-decimal rounded coordinates, date window, and sorted params."""
        lat_rounded = round(latitude, 4)
        lon_rounded = round(longitude, 4)
        sorted_params = ",".join(sorted(parameters))
        return f"power:{lat_rounded}:{lon_rounded}:{start_date}:{end_date}:{sorted_params}"

    def validate_pre_flight(
        self,
        farm_id: str,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
        parameters: Optional[List[str]] = None,
        request_id: Optional[str] = None,
    ) -> ClimateRequest:
        """Enforce strict pre-network coordinate and date boundary checking.

        Raises NasaPowerClientError(ApiError) BEFORE any network access if invalid.
        """
        try:
            return ClimateRequest(
                farm_id=farm_id,
                latitude=latitude,
                longitude=longitude,
                start_date=start_date,
                end_date=end_date,
                parameters=parameters,
            )
        except ValidationError as err:
            first_err = err.errors()[0]
            loc_tuple = first_err.get("loc", ())
            field = ".".join(str(loc) for loc in loc_tuple) if loc_tuple else "root"
            msg = first_err.get("msg", "")
            err_code = "INVALID_REQUEST"
            combined_text = f"{field} {msg}".lower()
            if "latitude" in combined_text:
                err_code = "INVALID_COORDINATES"
            elif "longitude" in combined_text:
                err_code = "INVALID_COORDINATES"
            elif "date" in combined_text:
                err_code = "INVALID_DATE_RANGE"
            elif "parameter" in combined_text:
                err_code = "INVALID_PARAMETERS"

            raise NasaPowerClientError(
                api_error=ApiError(
                    error_code=err_code,
                    message=f"Validation failed on field '{field}': {msg}",
                    details={
                        "field": field,
                        "type": str(first_err.get("type", "value_error")),
                    },
                    request_id=request_id,
                ),
                status_code=422,
            ) from err

    async def fetch_daily_point(
        self,
        farm_id: str,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
        parameters: Optional[List[str]] = None,
        request_id: Optional[str] = None,
        bypass_cache: bool = False,
    ) -> Dict[str, Any]:
        """Fetch daily environmental observations from NASA POWER API.

        Returns a dictionary containing:
        - raw_data: parsed JSON payload from NASA POWER
        - is_cached: boolean flag indicating if served from cache
        - retrieved_at: ISO timestamp
        - request_meta: metadata of the validated query
        """
        # Step 1: Pre-flight validation (strictly pre-network)
        validated = self.validate_pre_flight(
            farm_id=farm_id,
            latitude=latitude,
            longitude=longitude,
            start_date=start_date,
            end_date=end_date,
            parameters=parameters,
            request_id=request_id,
        )

        effective_params = (
            sorted(validated.parameters) if validated.parameters else sorted(DEFAULT_PARAMETERS)
        )

        # Step 2: Check cache
        cache_key = self.generate_cache_key(
            latitude=validated.latitude,
            longitude=validated.longitude,
            start_date=validated.start_date,
            end_date=validated.end_date,
            parameters=effective_params,
        )

        if not bypass_cache:
            cached_entry = await self.cache.get(cache_key)
            if cached_entry is not None:
                logger.info("Serving NASA POWER response from cache for key: %s", cache_key)
                return {
                    "raw_data": cached_entry["data"],
                    "is_cached": True,
                    "retrieved_at": cached_entry["retrieved_at"],
                    "cache_key": cache_key,
                    "request_meta": {
                        "farm_id": farm_id,
                        "latitude": validated.latitude,
                        "longitude": validated.longitude,
                        "start_date": validated.start_date,
                        "end_date": validated.end_date,
                        "parameters": effective_params,
                    },
                }

        # Step 3: Format query parameters for NASA POWER Daily Point
        # NASA POWER expects dates in YYYYMMDD without dashes
        start_power_fmt = validated.start_date.replace("-", "")
        end_power_fmt = validated.end_date.replace("-", "")

        query_params = {
            "parameters": ",".join(effective_params),
            "community": "AG",
            "longitude": f"{validated.longitude:.4f}",
            "latitude": f"{validated.latitude:.4f}",
            "start": start_power_fmt,
            "end": end_power_fmt,
            "format": "JSON",
        }

        # Step 4: Network dispatch with exponential backoff retry policy
        raw_data = await self._execute_request_with_retries(query_params, request_id)

        retrieval_timestamp = datetime.now(timezone.utc).isoformat()

        # Step 5: Store in cache
        await self.cache.set(
            cache_key,
            {"data": raw_data, "retrieved_at": retrieval_timestamp},
        )

        return {
            "raw_data": raw_data,
            "is_cached": False,
            "retrieved_at": retrieval_timestamp,
            "cache_key": cache_key,
            "request_meta": {
                "farm_id": farm_id,
                "latitude": validated.latitude,
                "longitude": validated.longitude,
                "start_date": validated.start_date,
                "end_date": validated.end_date,
                "parameters": effective_params,
            },
        }

    async def _execute_request_with_retries(
        self, query_params: Dict[str, str], request_id: Optional[str]
    ) -> Dict[str, Any]:
        """Perform HTTP GET with exponential backoff on transient errors (429, 5xx, timeouts)."""
        attempt = 0
        last_exception: Optional[Exception] = None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while attempt < self.max_retries:
                attempt += 1
                try:
                    logger.debug(
                        "Dispatching NASA POWER GET attempt %d/%d with params: %s",
                        attempt,
                        self.max_retries,
                        query_params,
                    )
                    response = await client.get(self.base_url, params=query_params)

                    # Success
                    if response.status_code == 200:
                        try:
                            return response.json()
                        except Exception as parse_exc:
                            raise NasaPowerClientError(
                                api_error=ApiError(
                                    error_code="INVALID_UPSTREAM_RESPONSE",
                                    message="NASA POWER returned unparseable or non-JSON content.",
                                    details={"content_preview": response.text[:200]},
                                    request_id=request_id,
                                ),
                                status_code=502,
                            ) from parse_exc

                    # Client error 400 (Bad request parameters) - do not retry
                    if response.status_code == 400:
                        raise NasaPowerClientError(
                            api_error=ApiError(
                                error_code="NASA_POWER_BAD_REQUEST",
                                message="NASA POWER rejected the request parameters.",
                                details={"response_body": response.text},
                                request_id=request_id,
                            ),
                            status_code=400,
                        )

                    # Transient statuses eligible for retry: 429 (Rate Limit) or 5xx (Server error)
                    if response.status_code in (429, 500, 502, 503, 504):
                        if attempt < self.max_retries:
                            backoff = (self.backoff_base * (2 ** (attempt - 1))) + random.uniform(
                                0.1, 0.5
                            )
                            logger.warning(
                                "NASA POWER returned HTTP %d on attempt %d; sleeping %.2fs before retry.",
                                response.status_code,
                                attempt,
                                backoff,
                            )
                            await asyncio.sleep(backoff)
                            continue
                        else:
                            err_code = (
                                "NASA_POWER_RATE_LIMIT"
                                if response.status_code == 429
                                else "NASA_POWER_UNAVAILABLE"
                            )
                            raise NasaPowerClientError(
                                api_error=ApiError(
                                    error_code=err_code,
                                    message=f"NASA POWER API returned HTTP {response.status_code} after {attempt} attempts.",
                                    details={"http_status": response.status_code, "body": response.text[:300]},
                                    request_id=request_id,
                                ),
                                status_code=503,
                            )

                    # Other unexpected status codes
                    raise NasaPowerClientError(
                        api_error=ApiError(
                            error_code="UPSTREAM_HTTP_ERROR",
                            message=f"NASA POWER API returned unexpected HTTP status {response.status_code}.",
                            details={"status_code": response.status_code},
                            request_id=request_id,
                        ),
                        status_code=502,
                    )

                except httpx.TimeoutException as texc:
                    last_exception = texc
                    if attempt < self.max_retries:
                        backoff = (self.backoff_base * (2 ** (attempt - 1))) + random.uniform(0.1, 0.3)
                        logger.warning(
                            "NASA POWER connection timed out on attempt %d; retrying in %.2fs",
                            attempt,
                            backoff,
                        )
                        await asyncio.sleep(backoff)
                        continue
                    else:
                        raise NasaPowerClientError(
                            api_error=ApiError(
                                error_code="UPSTREAM_TIMEOUT",
                                message=f"NASA POWER request timed out after {self.timeout}s and {attempt} attempts.",
                                details={"timeout_seconds": self.timeout},
                                request_id=request_id,
                            ),
                            status_code=504,
                        ) from texc

                except httpx.TransportError as net_exc:
                    last_exception = net_exc
                    if attempt < self.max_retries:
                        backoff = (self.backoff_base * (2 ** (attempt - 1))) + random.uniform(0.1, 0.3)
                        logger.warning(
                            "NASA POWER transport failure (%s) on attempt %d; retrying in %.2fs",
                            type(net_exc).__name__,
                            attempt,
                            backoff,
                        )
                        await asyncio.sleep(backoff)
                        continue
                    else:
                        raise NasaPowerClientError(
                            api_error=ApiError(
                                error_code="NETWORK_CONNECTION_ERROR",
                                message="Failed to establish network connection to NASA POWER API.",
                                details={"exception": str(net_exc)},
                                request_id=request_id,
                            ),
                            status_code=503,
                        ) from net_exc

        # Fallback if loop ends unexpectedly
        raise NasaPowerClientError(
            api_error=ApiError(
                error_code="NASA_POWER_UNAVAILABLE",
                message="NASA POWER service is currently unavailable.",
                details={"last_exception": str(last_exception)},
                request_id=request_id,
            ),
            status_code=503,
        )
