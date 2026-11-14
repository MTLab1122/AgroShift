from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    false,
)
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base
from .enums import EvidenceStatus, enum_column


def _month_day_check(column: str, leap_flag: str) -> str:
    return f"""
    CASE
        WHEN {column} IS NULL THEN 1
        WHEN length({column}) != 5 OR substr({column}, 3, 1) != '-' THEN 0
        WHEN substr({column}, 1, 2) IN ('01', '03', '05', '07', '08', '10', '12')
             AND substr({column}, 4, 2) BETWEEN '01' AND '31' THEN 1
        WHEN substr({column}, 1, 2) IN ('04', '06', '09', '11')
             AND substr({column}, 4, 2) BETWEEN '01' AND '30' THEN 1
        WHEN substr({column}, 1, 2) = '02'
             AND substr({column}, 4, 2) BETWEEN '01' AND '28' THEN 1
        WHEN substr({column}, 1, 2) = '02' AND substr({column}, 4, 2) = '29'
             AND {leap_flag} = TRUE THEN 1
        ELSE 0
    END = 1
    """


def _cross_year_check(start: str, end: str, flag: str) -> str:
    return f"""
    CASE
        WHEN {start} IS NULL AND {end} IS NULL THEN
            CASE WHEN {flag} = FALSE THEN 1 ELSE 0 END
        WHEN {start} IS NOT NULL AND {end} IS NOT NULL THEN
            CASE
                WHEN {start} > {end} AND {flag} = TRUE THEN 1
                WHEN {start} <= {end} AND {flag} = FALSE THEN 1
                ELSE 0
            END
        ELSE 0
    END = 1
    """


def _validate_calendar_window(_mapper, _connection, target) -> None:
    for start_name, end_name, cross_name, leap_name in (
        ("planting_start", "planting_end", "plant_crosses_year", "plant_leap_year_allowed"),
        ("harvest_start", "harvest_end", "harvest_crosses_year", "harvest_leap_year_allowed"),
    ):
        start = getattr(target, start_name)
        end = getattr(target, end_name)
        crosses_year = bool(getattr(target, cross_name))
        leap_year_allowed = bool(getattr(target, leap_name))
        if (start is None) != (end is None):
            raise ValueError(f"{start_name} and {end_name} must be provided together")
        for field_name, month_day in ((start_name, start), (end_name, end)):
            if month_day is None:
                continue
            if month_day == "02-29" and not leap_year_allowed:
                raise ValueError(f"{field_name} cannot be February 29 without leap-year permission")
            if len(month_day) != 5 or month_day[2] != "-":
                raise ValueError(f"{field_name} must be a valid MM-DD value")
            try:
                validation_year = 2000 if leap_year_allowed else 2001
                datetime.strptime(f"{validation_year}-{month_day}", "%Y-%m-%d")
            except ValueError as exc:
                raise ValueError(f"{field_name} must be a valid MM-DD value") from exc
        if start is not None and end is not None:
            if crosses_year != (start > end):
                raise ValueError(f"{cross_name} does not match the associated date range")


class CropCalendar(Base):
    __tablename__ = "crop_calendars"
    __table_args__ = (
        ForeignKeyConstraint(
            ["variety_id", "crop_id"],
            ["crop_varieties.id", "crop_varieties.crop_id"],
            ondelete="RESTRICT",
            name="fk_crop_calendars_variety_crop",
        ),
        ForeignKeyConstraint(
            ["province_state_id", "country_id"],
            ["province_states.id", "province_states.country_id"],
            ondelete="RESTRICT",
            name="fk_crop_calendars_province_country",
        ),
        ForeignKeyConstraint(
            ["district_id", "province_state_id"],
            ["districts.id", "districts.province_state_id"],
            ondelete="RESTRICT",
            name="fk_crop_calendars_district_province",
        ),
        CheckConstraint(
            "district_id IS NULL OR province_state_id IS NOT NULL",
            name="ck_crop_calendars_district_requires_province",
        ),
        CheckConstraint(
            "growing_duration_days IS NULL OR growing_duration_days >= 0",
            name="ck_crop_calendars_nonnegative_duration",
        ),
        CheckConstraint(
            "confidence_level IS NULL OR confidence_level BETWEEN 0 AND 1",
            name="ck_crop_calendars_confidence_range",
        ),
        CheckConstraint(
            _month_day_check("planting_start", "plant_leap_year_allowed"),
            name="ck_crop_calendars_planting_start_month_day",
        ),
        CheckConstraint(
            _month_day_check("planting_end", "plant_leap_year_allowed"),
            name="ck_crop_calendars_planting_end_month_day",
        ),
        CheckConstraint(
            _month_day_check("harvest_start", "harvest_leap_year_allowed"),
            name="ck_crop_calendars_harvest_start_month_day",
        ),
        CheckConstraint(
            _month_day_check("harvest_end", "harvest_leap_year_allowed"),
            name="ck_crop_calendars_harvest_end_month_day",
        ),
        CheckConstraint(
            _cross_year_check("planting_start", "planting_end", "plant_crosses_year"),
            name="ck_crop_calendars_plant_cross_year_matches_range",
        ),
        CheckConstraint(
            _cross_year_check("harvest_start", "harvest_end", "harvest_crosses_year"),
            name="ck_crop_calendars_harvest_cross_year_matches_range",
        ),
        CheckConstraint(
            """
            CASE
                WHEN evidence_status IN ('VERIFIED', 'PROVISIONAL') THEN
                    CASE WHEN primary_evidence_id IS NOT NULL THEN 1 ELSE 0 END
                ELSE 1
            END = 1
            """,
            name="ck_crop_calendars_evidence_requires_support",
        ),
        Index("ix_crop_calendars_crop_region", "crop_id", "country_id", "province_state_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crop_id: Mapped[int] = mapped_column(
        ForeignKey("crops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    variety_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    country_id: Mapped[int | None] = mapped_column(
        ForeignKey("countries.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    province_state_id: Mapped[int | None] = mapped_column(
        ForeignKey("province_states.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    district_id: Mapped[int | None] = mapped_column(
        ForeignKey("districts.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    agroecological_zone_id: Mapped[int | None] = mapped_column(
        ForeignKey("agroecological_zones.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    region_label: Mapped[str | None] = mapped_column(String(240), nullable=True)
    season: Mapped[str | None] = mapped_column(String(120), nullable=True)
    planting_start: Mapped[str | None] = mapped_column(String(5), nullable=True)
    planting_end: Mapped[str | None] = mapped_column(String(5), nullable=True)
    harvest_start: Mapped[str | None] = mapped_column(String(5), nullable=True)
    harvest_end: Mapped[str | None] = mapped_column(String(5), nullable=True)
    plant_crosses_year: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default=false()
    )
    harvest_crosses_year: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default=false()
    )
    plant_leap_year_allowed: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default=false()
    )
    harvest_leap_year_allowed: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default=false()
    )
    growing_duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calendar_source_id: Mapped[int | None] = mapped_column(
        ForeignKey("agricultural_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    confidence_level: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    evidence_status: Mapped[EvidenceStatus] = mapped_column(
        enum_column(EvidenceStatus, "crop_calendar_evidence_status"),
        nullable=False,
        default=EvidenceStatus.UNKNOWN,
        server_default=EvidenceStatus.UNKNOWN.value,
    )
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    primary_evidence_id: Mapped[int | None] = mapped_column(
        ForeignKey("evidence_records.id", ondelete="RESTRICT"), nullable=True
    )

    crop: Mapped["Crop"] = relationship(
        "Crop", back_populates="calendars", overlaps="variety,calendars"
    )
    variety: Mapped["CropVariety | None"] = relationship(
        "CropVariety",
        back_populates="calendars",
        foreign_keys=[variety_id, crop_id],
        overlaps="crop,calendars",
    )
    country: Mapped["Country | None"] = relationship(
        "Country", foreign_keys=[country_id]
    )
    province_state: Mapped["ProvinceState | None"] = relationship(
        "ProvinceState", foreign_keys=[province_state_id]
    )
    district: Mapped["District | None"] = relationship(
        "District", foreign_keys=[district_id]
    )
    agroecological_zone: Mapped["AgroecologicalZone | None"] = relationship(
        "AgroecologicalZone"
    )
    calendar_source: Mapped["AgriculturalSource | None"] = relationship(
        "AgriculturalSource", back_populates="calendars"
    )
    primary_evidence: Mapped["EvidenceRecord | None"] = relationship(
        "EvidenceRecord", foreign_keys=[primary_evidence_id]
    )
    evidence_records: Mapped[list["EvidenceRecord"]] = relationship(
        "EvidenceRecord", secondary="crop_calendar_evidence"
    )


sqlalchemy_event.listen(CropCalendar, "before_insert", _validate_calendar_window)
sqlalchemy_event.listen(CropCalendar, "before_update", _validate_calendar_window)
