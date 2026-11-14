from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base
from .enums import EvidenceStatus, RequirementType, enum_column


_SOIL_FIELDS = {"soil_type", "soil_ph_min", "soil_ph_max"}
_WATER_FIELDS = {"water_requirement", "water_requirement_unit", "water_requirement_basis"}
_TEMPERATURE_FIELDS = {"temperature_min", "temperature_max"}
_SALINITY_FIELDS = {"salinity_tolerance"}
_NUTRIENT_FIELDS = {
    "nutrient_n_value",
    "nutrient_n_unit",
    "nutrient_n_basis",
    "nutrient_p_value",
    "nutrient_p_unit",
    "nutrient_p_basis",
}
_MEASUREMENT_FIELDS = (
    _SOIL_FIELDS
    | _WATER_FIELDS
    | _TEMPERATURE_FIELDS
    | _SALINITY_FIELDS
    | _NUTRIENT_FIELDS
    | {"other_description", "other_measurement_basis"}
)


def _null_fields(fields: set[str]) -> str:
    return " AND ".join(f"{field} IS NULL" for field in sorted(fields))


def _all_or_none(fields: tuple[str, ...]) -> str:
    all_null = " AND ".join(f"{field} IS NULL" for field in fields)
    all_set = " AND ".join(f"{field} IS NOT NULL" for field in fields)
    return f"(({all_null}) OR ({all_set}))"


def _requirement_type_check() -> str:
    branches = {
        RequirementType.SOIL.value: _null_fields(_MEASUREMENT_FIELDS - _SOIL_FIELDS),
        RequirementType.WATER.value: (
            f"{_null_fields(_MEASUREMENT_FIELDS - _WATER_FIELDS)} AND "
            f"{_all_or_none(('water_requirement', 'water_requirement_unit', 'water_requirement_basis'))}"
        ),
        RequirementType.TEMPERATURE.value: (
            f"{_null_fields(_MEASUREMENT_FIELDS - _TEMPERATURE_FIELDS)} AND "
            f"{_all_or_none(('temperature_min', 'temperature_max'))}"
        ),
        RequirementType.SALINITY.value: _null_fields(_MEASUREMENT_FIELDS - _SALINITY_FIELDS),
        RequirementType.NUTRIENT.value: (
            f"{_null_fields(_MEASUREMENT_FIELDS - _NUTRIENT_FIELDS)} AND "
            f"{_all_or_none(('nutrient_n_value', 'nutrient_n_unit', 'nutrient_n_basis'))} AND "
            f"{_all_or_none(('nutrient_p_value', 'nutrient_p_unit', 'nutrient_p_basis'))}"
        ),
        RequirementType.OTHER.value: (
            f"{_null_fields(_MEASUREMENT_FIELDS - {'other_description', 'other_measurement_basis'})} "
            "AND other_description IS NOT NULL AND length(trim(other_description)) > 0"
        ),
    }
    return "CASE " + " ".join(
        f"WHEN requirement_type = '{value}' THEN CASE WHEN {condition} THEN 1 ELSE 0 END"
        for value, condition in branches.items()
    ) + " ELSE 0 END = 1"


class CropRequirement(Base):
    __tablename__ = "crop_requirements"
    __table_args__ = (
        ForeignKeyConstraint(
            ["variety_id", "crop_id"],
            ["crop_varieties.id", "crop_varieties.crop_id"],
            ondelete="RESTRICT",
            name="fk_crop_requirements_variety_crop",
        ),
        CheckConstraint(_requirement_type_check(), name="ck_crop_requirements_type_fields"),
        CheckConstraint(
            "soil_ph_min IS NULL OR soil_ph_min BETWEEN 0 AND 14",
            name="ck_crop_requirements_ph_min_range",
        ),
        CheckConstraint(
            "soil_ph_max IS NULL OR soil_ph_max BETWEEN 0 AND 14",
            name="ck_crop_requirements_ph_max_range",
        ),
        CheckConstraint(
            "soil_ph_min IS NULL OR soil_ph_max IS NULL OR soil_ph_min <= soil_ph_max",
            name="ck_crop_requirements_ph_order",
        ),
        CheckConstraint(
            "temperature_min IS NULL OR temperature_max IS NULL OR temperature_min <= temperature_max",
            name="ck_crop_requirements_temperature_order",
        ),
        CheckConstraint(
            """
            CASE
                WHEN evidence_status IN ('VERIFIED', 'PROVISIONAL') THEN
                    CASE WHEN primary_evidence_id IS NOT NULL THEN 1 ELSE 0 END
                ELSE 1
            END = 1
            """,
            name="ck_crop_requirements_evidence_requires_support",
        ),
        Index("ix_crop_requirements_crop_type", "crop_id", "requirement_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crop_id: Mapped[int] = mapped_column(
        ForeignKey("crops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    variety_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    requirement_type: Mapped[RequirementType] = mapped_column(
        enum_column(RequirementType, "crop_requirement_type"), nullable=False
    )
    soil_type: Mapped[str | None] = mapped_column(String(160), nullable=True)
    soil_ph_min: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    soil_ph_max: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    water_requirement: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    water_requirement_unit: Mapped[str | None] = mapped_column(String(80), nullable=True)
    water_requirement_basis: Mapped[str | None] = mapped_column(String(160), nullable=True)
    temperature_min: Mapped[Decimal | None] = mapped_column(Numeric(7, 3), nullable=True)
    temperature_max: Mapped[Decimal | None] = mapped_column(Numeric(7, 3), nullable=True)
    salinity_tolerance: Mapped[str | None] = mapped_column(String(240), nullable=True)
    additional_conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("agricultural_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    evidence_status: Mapped[EvidenceStatus] = mapped_column(
        enum_column(EvidenceStatus, "crop_requirement_evidence_status"),
        nullable=False,
        default=EvidenceStatus.UNKNOWN,
        server_default=EvidenceStatus.UNKNOWN.value,
    )
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)
    nutrient_n_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    nutrient_n_unit: Mapped[str | None] = mapped_column(String(80), nullable=True)
    nutrient_n_basis: Mapped[str | None] = mapped_column(String(160), nullable=True)
    nutrient_p_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    nutrient_p_unit: Mapped[str | None] = mapped_column(String(80), nullable=True)
    nutrient_p_basis: Mapped[str | None] = mapped_column(String(160), nullable=True)
    other_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    other_measurement_basis: Mapped[str | None] = mapped_column(String(160), nullable=True)
    primary_evidence_id: Mapped[int | None] = mapped_column(
        ForeignKey("evidence_records.id", ondelete="RESTRICT"), nullable=True
    )

    crop: Mapped["Crop"] = relationship(
        "Crop", back_populates="requirements", overlaps="variety,requirements"
    )
    variety: Mapped["CropVariety | None"] = relationship(
        "CropVariety",
        back_populates="requirements",
        foreign_keys=[variety_id, crop_id],
        overlaps="crop,requirements",
    )
    source: Mapped["AgriculturalSource | None"] = relationship(
        "AgriculturalSource", back_populates="requirements"
    )
    primary_evidence: Mapped["EvidenceRecord | None"] = relationship(
        "EvidenceRecord", foreign_keys=[primary_evidence_id]
    )
    evidence_records: Mapped[list["EvidenceRecord"]] = relationship(
        "EvidenceRecord", secondary="crop_requirement_evidence"
    )
