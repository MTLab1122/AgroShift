from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base
from .enums import EvidenceStatus, enum_column


class Crop(Base):
    __tablename__ = "crops"
    __table_args__ = (
        CheckConstraint(
            """
            CASE
                WHEN evidence_status IN ('VERIFIED', 'PROVISIONAL') THEN
                    CASE WHEN primary_evidence_id IS NOT NULL THEN 1 ELSE 0 END
                ELSE 1
            END = 1
            """,
            name="ck_crops_evidence_requires_support",
        ),
        Index("ix_crops_family_category", "crop_family", "crop_category"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(160), nullable=False, unique=True)
    common_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    scientific_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    crop_family: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    crop_category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_legume: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    evidence_status: Mapped[EvidenceStatus] = mapped_column(
        enum_column(EvidenceStatus, "crop_evidence_status"),
        nullable=False,
        default=EvidenceStatus.UNKNOWN,
        server_default=EvidenceStatus.UNKNOWN.value,
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )
    primary_evidence_id: Mapped[int | None] = mapped_column(
        ForeignKey("evidence_records.id", ondelete="RESTRICT"), nullable=True
    )

    primary_evidence: Mapped["EvidenceRecord | None"] = relationship(
        "EvidenceRecord", foreign_keys=[primary_evidence_id]
    )
    evidence_records: Mapped[list["EvidenceRecord"]] = relationship(
        "EvidenceRecord", secondary="crop_evidence"
    )
    varieties: Mapped[list["CropVariety"]] = relationship(
        "CropVariety", back_populates="crop", passive_deletes="all"
    )
    calendars: Mapped[list["CropCalendar"]] = relationship(
        "CropCalendar",
        back_populates="crop",
        overlaps="variety,calendars",
        passive_deletes="all",
    )
    requirements: Mapped[list["CropRequirement"]] = relationship(
        "CropRequirement", back_populates="crop", passive_deletes="all"
    )
    previous_rotation_rules: Mapped[list["CropRotationRule"]] = relationship(
        "CropRotationRule",
        foreign_keys="CropRotationRule.previous_crop_id",
        passive_deletes="all",
    )
    next_rotation_rules: Mapped[list["CropRotationRule"]] = relationship(
        "CropRotationRule",
        foreign_keys="CropRotationRule.next_crop_id",
        passive_deletes="all",
    )
    source_applicabilities: Mapped[list["SourceApplicability"]] = relationship(
        "SourceApplicability",
        foreign_keys="SourceApplicability.crop_id",
        passive_deletes="all",
    )
