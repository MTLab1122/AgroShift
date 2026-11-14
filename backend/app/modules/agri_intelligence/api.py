from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .db.session import SessionLocal
from .repositories import (
    CropCalendarRepository,
    CropRepository,
    RecordNotFoundError,
)
from .schemas import CropCalendarRead, CropRead
from .schemas.validation import (
    CropValidationRequest,
    CropValidationResult,
    FarmValidationRequest,
    FarmValidationResult,
    SequenceValidationRequest,
    SequenceValidationResult,
)
from .schemas._base import read_model
from .services.agricultural_validator import AgriculturalValidator


router = APIRouter(tags=["Agricultural Intelligence"])


def get_db_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session


def _crop_read(crop) -> CropRead:
    return read_model(
        crop,
        CropRead,
        evidence_record_ids=[record.id for record in crop.evidence_records],
        variety_ids=[record.id for record in crop.varieties],
        calendar_ids=[record.id for record in crop.calendars],
        requirement_ids=[record.id for record in crop.requirements],
    )


def _calendar_read(calendar) -> CropCalendarRead:
    return read_model(
        calendar,
        CropCalendarRead,
        evidence_record_ids=[record.id for record in calendar.evidence_records],
    )


@router.get("/api/v1/crops", response_model=list[CropRead])
def list_crops(
    active: bool | None = True,
    session: Session = Depends(get_db_session),
):
    filters = {} if active is None else {"active": active}
    return [
        _crop_read(crop)
        for crop in CropRepository(session).list(filters=filters)
    ]


@router.get("/api/v1/crops/{crop_id}", response_model=CropRead)
def get_crop(crop_id: int, session: Session = Depends(get_db_session)):
    try:
        crop = CropRepository(session).get(crop_id)
    except RecordNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crop not found",
        ) from exc
    return _crop_read(crop)


@router.get("/api/v1/crops/{crop_id}/calendar", response_model=list[CropCalendarRead])
def get_crop_calendars(crop_id: int, session: Session = Depends(get_db_session)):
    try:
        CropRepository(session).get(crop_id)
    except RecordNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crop not found",
        ) from exc
    calendars = CropCalendarRepository(session).list(filters={"crop_id": crop_id})
    return [_calendar_read(calendar) for calendar in calendars]


@router.post("/api/v1/crops/validate", response_model=CropValidationResult)
def validate_crop(
    request: CropValidationRequest,
    session: Session = Depends(get_db_session),
):
    return AgriculturalValidator(session).validate_crop(request)


@router.post(
    "/api/v1/agriculture/validate-farm",
    response_model=FarmValidationResult,
)
def validate_farm(
    request: FarmValidationRequest,
    session: Session = Depends(get_db_session),
):
    return AgriculturalValidator(session).validate_farm(request)


@router.post(
    "/api/v1/agriculture/validate-sequence",
    response_model=SequenceValidationResult,
)
def validate_sequence(
    request: SequenceValidationRequest,
    session: Session = Depends(get_db_session),
):
    return AgriculturalValidator(session).validate_sequence(request)
