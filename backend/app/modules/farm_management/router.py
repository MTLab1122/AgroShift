"""FastAPI Router for Module 01: Farm Management & Location Intelligence.

Exposes RESTful endpoints for:
- Farms CRUD: GET /api/v1/farms, POST /api/v1/farms, GET /api/v1/farms/{id}, PUT /api/v1/farms/{id}, DELETE /api/v1/farms/{id}
- Crop History: GET /api/v1/farms/{id}/crops, POST /api/v1/farms/{id}/crops, PUT /api/v1/farms/{id}/crops/{crop_id}, DELETE /api/v1/farms/{id}/crops/{crop_id}
- Conversational Assistant: POST /api/v1/assistant/chat
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.modules.nasa_data.schemas import ApiError
from backend.app.modules.farm_management.assistant_service import assistant_service
from backend.app.modules.farm_management import crud
from backend.app.modules.farm_management.models import Farm, CropHistory
from backend.app.modules.farm_management.schemas import (
    FarmCreate,
    FarmUpdate,
    FarmResponse,
    FarmLocation,
    CropHistoryCreate,
    CropHistoryUpdate,
    CropHistoryResponse,
    AssistantChatRequest,
    AssistantChatResponse,
)

router = APIRouter(prefix="/api/v1", tags=["Farm Management & Location"])


def serialize_farm(farm: Farm) -> FarmResponse:
    loc = FarmLocation(
        latitude=farm.latitude,
        longitude=farm.longitude,
        elevation_meters=farm.elevation_meters,
        village_or_town=farm.village_or_town,
        district=farm.district,
        province_or_region=farm.province_or_region,
        country=farm.country,
    )
    return FarmResponse(
        farm_id=farm.farm_id,
        name=farm.name,
        owner_name=farm.owner_name,
        contact_phone=farm.contact_phone,
        preferred_language=farm.preferred_language,
        location=loc,
        boundary=farm.boundary,
        total_area_hectares=farm.total_area_hectares,
        soil_type=farm.soil_type,
        irrigation_source=farm.irrigation_source,
        water_availability=farm.water_availability,
        salinity_level=farm.salinity_level,
        current_crops=farm.current_crops,
        created_at=farm.created_at,
        updated_at=farm.updated_at,
    )


# ==============================================================================
# Farm Endpoints
# ==============================================================================

@router.get("/farms", response_model=List[FarmResponse], summary="List all registered farms")
def list_farms(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[FarmResponse]:
    db_farms = crud.get_farms(db, skip=skip, limit=limit)
    return [serialize_farm(f) for f in db_farms]


@router.post(
    "/farms",
    response_model=FarmResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new farm",
)
def create_farm(farm_in: FarmCreate, db: Session = Depends(get_db)) -> FarmResponse:
    if farm_in.farm_id:
        existing = crud.get_farm_by_id(db, farm_in.farm_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Farm with ID '{farm_in.farm_id}' already exists.",
            )
    created = crud.create_farm(db, farm_in)
    return serialize_farm(created)


@router.get("/farms/{farm_id}", response_model=FarmResponse, summary="Retrieve a farm by ID")
def get_farm(farm_id: str, db: Session = Depends(get_db)) -> FarmResponse:
    farm = crud.get_farm_by_id(db, farm_id)
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm with ID '{farm_id}' not found.",
        )
    return serialize_farm(farm)


@router.put("/farms/{farm_id}", response_model=FarmResponse, summary="Update farm details")
def update_farm(
    farm_id: str, farm_in: FarmUpdate, db: Session = Depends(get_db)
) -> FarmResponse:
    updated = crud.update_farm(db, farm_id, farm_in)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm with ID '{farm_id}' not found.",
        )
    return serialize_farm(updated)


@router.delete("/farms/{farm_id}", status_code=status.HTTP_200_OK, summary="Delete a farm")
def delete_farm(farm_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    success = crud.delete_farm(db, farm_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm with ID '{farm_id}' not found.",
        )
    return {"status": "success", "message": f"Farm '{farm_id}' deleted."}


# ==============================================================================
# Crop History Endpoints
# ==============================================================================

@router.get(
    "/farms/{farm_id}/crops",
    response_model=List[CropHistoryResponse],
    summary="List seasonal crop history for a farm",
)
def list_crops(farm_id: str, db: Session = Depends(get_db)) -> List[CropHistoryResponse]:
    farm = crud.get_farm_by_id(db, farm_id)
    if not farm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm with ID '{farm_id}' not found.",
        )
    crops = crud.get_crops_by_farm(db, farm_id)
    return [CropHistoryResponse.model_validate(c) for c in crops]


@router.post(
    "/farms/{farm_id}/crops",
    response_model=CropHistoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a crop history record",
)
def create_crop(
    farm_id: str, crop_in: CropHistoryCreate, db: Session = Depends(get_db)
) -> CropHistoryResponse:
    created = crud.create_crop_record(db, farm_id, crop_in)
    if not created:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Farm with ID '{farm_id}' not found.",
        )
    return CropHistoryResponse.model_validate(created)


@router.put(
    "/farms/{farm_id}/crops/{record_id}",
    response_model=CropHistoryResponse,
    summary="Update a crop history record",
)
def update_crop(
    farm_id: str,
    record_id: str,
    crop_in: CropHistoryUpdate,
    db: Session = Depends(get_db),
) -> CropHistoryResponse:
    updated = crud.update_crop_record(db, farm_id, record_id, crop_in)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crop record '{record_id}' for farm '{farm_id}' not found.",
        )
    return CropHistoryResponse.model_validate(updated)


@router.delete(
    "/farms/{farm_id}/crops/{record_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a crop history record",
)
def delete_crop(
    farm_id: str, record_id: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    success = crud.delete_crop_record(db, farm_id, record_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crop record '{record_id}' for farm '{farm_id}' not found.",
        )
    return {"status": "success", "message": f"Crop record '{record_id}' deleted."}


# ==============================================================================
# Conversational Assistant Endpoint
# ==============================================================================

@router.post(
    "/assistant/chat",
    response_model=AssistantChatResponse,
    summary="Conversational farm intake session step",
)
def assistant_chat(request: AssistantChatRequest) -> AssistantChatResponse:
    return assistant_service.process_turn(
        session_id=request.session_id,
        message=request.message,
        language=request.language,
        current_data=request.current_extracted,
    )
