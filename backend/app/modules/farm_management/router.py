"""FastAPI Router for Module 01: Farm Management & Location Intelligence.

Endpoints:
- POST /api/v1/farms: Register a new farm profile.
- GET /api/v1/farms: List all registered farms.
- GET /api/v1/farms/{farm_id}: Retrieve a specific farm profile.
- PUT /api/v1/farms/{farm_id}: Update an existing farm profile.
- DELETE /api/v1/farms/{farm_id}: Safely delete a farm profile.
- POST /api/v1/farms/{farm_id}/crop-history: Add a historical crop entry.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from fastapi import APIRouter, Body, HTTPException, Path, Request, status

from backend.app.core.middleware import get_request_id
from backend.app.modules.farm_management.repository import farm_repository
from backend.app.modules.nasa_data.schemas import ApiError
from backend.app.schemas.farm import CropHistoryEntry, FarmProfile

logger = logging.getLogger("agroshift.farm_management")
router = APIRouter(prefix="/api/v1/farms", tags=["Farm Management (Module 01)"])


@router.post(
    "",
    response_model=FarmProfile,
    status_code=status.HTTP_201_CREATED,
    summary="Register a New Farm Profile",
    responses={
        409: {"model": ApiError, "description": "Farm already exists"},
        422: {"model": ApiError, "description": "Validation Error"},
    },
)
async def create_farm(
    request: Request,
    farm: FarmProfile = Body(..., description="Canonical FarmProfile object"),
) -> FarmProfile:
    """Create a new farm profile in the system."""
    req_id = get_request_id(request)
    existing = farm_repository.get_by_id(farm.farm_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Farm with ID '{farm.farm_id}' already exists.",
        )

    saved = farm_repository.save(farm)
    logger.info("Farm registered [%s]: %s (%s)", req_id, saved.farm_id, saved.farm_name)
    return saved


@router.get(
    "",
    response_model=List[FarmProfile],
    summary="List All Registered Farms",
)
async def list_farms() -> List[FarmProfile]:
    """Retrieve all available farm profiles."""
    return farm_repository.list_all()


@router.get(
    "/{farm_id}",
    response_model=FarmProfile,
    summary="Retrieve Farm Profile by ID",
    responses={
        404: {"model": ApiError, "description": "Farm not found"},
    },
)
async def get_farm(
    farm_id: str = Path(..., description="Unique farm identifier"),
) -> FarmProfile:
    """Get a specific farm profile."""
    farm = farm_repository.get_by_id(farm_id)
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm with ID '{farm_id}' was not found.",
        )
    return farm


@router.put(
    "/{farm_id}",
    response_model=FarmProfile,
    summary="Update Farm Profile",
    responses={
        404: {"model": ApiError, "description": "Farm not found"},
    },
)
async def update_farm(
    farm_id: str = Path(...),
    farm_update: FarmProfile = Body(...),
) -> FarmProfile:
    """Update existing farm profile."""
    existing = farm_repository.get_by_id(farm_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm with ID '{farm_id}' was not found.",
        )

    # Ensure farm_id coherence
    if farm_update.farm_id != farm_id:
        farm_update = farm_update.model_copy(update={"farm_id": farm_id})

    saved = farm_repository.save(farm_update)
    return saved


@router.delete(
    "/{farm_id}",
    summary="Delete Farm Profile",
    responses={
        404: {"model": ApiError, "description": "Farm not found"},
    },
)
async def delete_farm(
    farm_id: str = Path(...),
) -> Dict[str, Any]:
    """Delete a farm profile."""
    deleted = farm_repository.delete(farm_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm with ID '{farm_id}' was not found.",
        )
    return {"status": "deleted", "farm_id": farm_id}


@router.post(
    "/{farm_id}/crop-history",
    response_model=FarmProfile,
    summary="Add Historical Crop Entry to Farm",
    responses={
        404: {"model": ApiError, "description": "Farm not found"},
    },
)
async def add_crop_history(
    farm_id: str = Path(...),
    entry: CropHistoryEntry = Body(...),
) -> FarmProfile:
    """Append a historical crop record to a farm profile."""
    updated = farm_repository.add_crop_history_entry(farm_id, entry)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm with ID '{farm_id}' was not found.",
        )
    return updated
