"""Request Tracing & Structured Telemetry Middleware for AgroShift (Module 05).

Provides:
- X-Request-ID propagation: preserves incoming trace header or assigns a cryptographically unique identifier.
- Structured request/response telemetry with high-precision duration tracking.
- Response header injection (X-Request-ID, X-Response-Time-Ms).
- State binding for consistent ApiError request_id population.
"""

from __future__ import annotations

import logging
import time
from typing import Callable
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("agroshift.telemetry")


def get_request_id(request: Request) -> str:
    """Retrieve or generate correlation request ID bound to current request state."""
    if hasattr(request.state, "request_id") and request.state.request_id:
        return str(request.state.request_id)
    header_val = request.headers.get("X-Request-ID")
    if header_val:
        return header_val.strip()
    return f"req-{uuid.uuid4().hex[:12]}"


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """FastAPI / Starlette middleware attaching trace IDs and logging execution metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Determine request ID
        req_id = request.headers.get("X-Request-ID")
        if not req_id or not req_id.strip():
            req_id = f"req-{uuid.uuid4().hex[:12]}"
        else:
            req_id = req_id.strip()

        # Bind to request state so downstream routers & exception handlers can access it
        request.state.request_id = req_id

        start_time = time.perf_counter()

        try:
            response: Response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "Request failed | method=%s path=%s duration_ms=%.2f request_id=%s",
                request.method,
                request.url.path,
                duration_ms,
                req_id,
            )
            raise

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Inject tracing headers
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Response-Time-Ms"] = str(duration_ms)

        # Log structured audit line
        logger.info(
            "HTTP %s %s -> %d (%.2f ms) | request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            req_id,
        )

        return response
