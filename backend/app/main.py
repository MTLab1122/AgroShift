"""Main FastAPI application entry point for AgroShift Backend."""

from __future__ import annotations

import logging
import uuid
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.modules.nasa_data.power_client import NasaPowerClientError
from backend.app.modules.nasa_data.router import router as nasa_data_router
from backend.app.modules.nasa_data.schemas import ApiError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AgroShift Backend API",
    version="0.1.0",
    description="Backend API and Climate Data Engine for AgroShift (NASA Space Apps Challenge 2026).",
)

# CORS middleware for local frontend development (Next.js)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Module 02 Router
app.include_router(nasa_data_router)


@app.exception_handler(NasaPowerClientError)
async def handle_nasa_power_client_error(
    request: Request, exc: NasaPowerClientError
) -> JSONResponse:
    """Handle structured NASA POWER client exceptions with canonical ApiError."""
    logger.warning("NasaPowerClientError caught: %s", exc.api_error.message)
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.api_error.model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Format FastAPI / Pydantic request parameter validation failures into ApiError."""
    req_id = f"val-{uuid.uuid4().hex[:8]}"
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
    )


@app.exception_handler(StarletteHTTPException)
async def handle_starlette_http_exception(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Format generic HTTP exceptions into canonical ApiError."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiError(
            error_code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
            details=None,
            request_id=f"http-{uuid.uuid4().hex[:8]}",
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all unhandled exception handler ensuring canonical ApiError response."""
    req_id = f"err-{uuid.uuid4().hex[:8]}"
    logger.exception("Unhandled server exception [%s]: %s", req_id, str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ApiError(
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected internal server error occurred.",
            details={"exception_type": type(exc).__name__},
            request_id=req_id,
        ).model_dump(),
    )
