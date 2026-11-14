"""Main FastAPI application entry point for AgroShift Backend (Module 05 Hardened)."""

from __future__ import annotations

import logging
import os
import uuid
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.core.middleware import RequestTracingMiddleware, get_request_id
from backend.app.modules.agro_engine.router import router as agro_engine_router
from backend.app.modules.analytics.router import router as analytics_router
from backend.app.modules.farm_management.router import router as farm_management_router
from backend.app.modules.nasa_data.power_client import NasaPowerClientError
from backend.app.modules.nasa_data.router import router as nasa_data_router
from backend.app.modules.nasa_data.schemas import ApiError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agroshift.api")

app = FastAPI(
    title="AgroShift Backend API",
    version="1.0.0",
    description="Backend API and Climate Data Engine for AgroShift (NASA Space Apps Challenge 2026).",
)

# 1. CORS middleware configurable via environment
raw_cors = os.getenv("CORS_ORIGINS", "*")
cors_origins = [o.strip() for o in raw_cors.split(",") if o.strip()] if raw_cors != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Request tracing and telemetry middleware (outermost)
app.add_middleware(RequestTracingMiddleware)

# Register Module Routers (All 5 Modules Unified)
app.include_router(nasa_data_router)
app.include_router(agro_engine_router)
app.include_router(farm_management_router)
app.include_router(analytics_router)


@app.exception_handler(NasaPowerClientError)
async def handle_nasa_power_client_error(
    request: Request, exc: NasaPowerClientError
) -> JSONResponse:
    """Handle structured NASA POWER client exceptions with canonical ApiError."""
    req_id = get_request_id(request)
    logger.warning("NasaPowerClientError [%s]: %s", req_id, exc.api_error.message)

    # Ensure request_id is populated on ApiError
    error_payload = exc.api_error.model_copy(update={"request_id": req_id})

    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload.model_dump(),
        headers={"X-Request-ID": req_id},
    )


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Format FastAPI / Pydantic request parameter validation failures into canonical ApiError."""
    req_id = get_request_id(request)
    errors = exc.errors()
    first_err = errors[0] if errors else {}
    loc_tuple = first_err.get("loc", ())
    field = ".".join(str(l) for l in loc_tuple) if loc_tuple else "query"
    msg = first_err.get("msg", "Validation error")

    err_code = "INVALID_REQUEST"
    combined = f"{field} {msg}".lower()
    if "latitude" in combined or "longitude" in combined:
        err_code = "INVALID_COORDINATES"
    elif "date" in combined:
        err_code = "INVALID_DATE_RANGE"
    elif "parameter" in combined:
        err_code = "INVALID_PARAMETERS"

    clean_errors = [
        {
            "loc": [str(x) for x in e.get("loc", ())],
            "msg": e.get("msg", ""),
            "type": e.get("type", ""),
        }
        for e in errors
    ]

    api_err = ApiError(
        error_code=err_code,
        message=f"Validation error on '{field}': {msg}",
        details={"errors": clean_errors},
        request_id=req_id,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=api_err.model_dump(),
        headers={"X-Request-ID": req_id},
    )


@app.exception_handler(StarletteHTTPException)
async def handle_starlette_http_exception(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Format generic HTTP exceptions into canonical ApiError."""
    req_id = get_request_id(request)
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiError(
            error_code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
            details=None,
            request_id=req_id,
        ).model_dump(),
        headers={"X-Request-ID": req_id},
    )


@app.exception_handler(Exception)
async def handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all unhandled exception handler ensuring canonical ApiError response."""
    req_id = get_request_id(request)
    logger.exception("Unhandled server exception [%s]: %s", req_id, str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiError(
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected internal server error occurred.",
            details={"exception_type": type(exc).__name__},
            request_id=req_id,
        ).model_dump(),
        headers={"X-Request-ID": req_id},
    )
