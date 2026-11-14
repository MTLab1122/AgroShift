from typing import Any

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base
from .enums import EvidenceStatus, enum_column


class CropVariety(Base):
    __tablename__ = "crop_varieties"
    __table_args__ = (
        UniqueConstraint("id", "crop_id", name="uq_crop_varieties_id_crop"),
        CheckConstraint(
            "duration_days IS NULL OR duration_days >= 0",
            name="ck_crop_varieties_nonnegative_duration",
        ),
        CheckConstraint(
            """
            CASE
                WHEN evidence_status IN ('VERIFIED', 'PROVISIONAL') THEN
                    CASE WHEN primary_evidence_id IS NOT NULL THEN 1 ELSE 0 END
                ELSE 1
            END = 1
            """,
            name="ck_crop_varieties_evidence_requires_support",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crop_id: Mapped[int] = mapped_column(
        ForeignKey("crops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    maturity_class: Mapped[str | None] = mapped_column(String(120), nullable=True)
    regional_adaptation: Mapped[str | None] = mapped_column(String(500), nullable=True)
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_status: Mapped[EvidenceStatus] = mapped_column(
        enum_column(EvidenceStatus, "crop_variety_evidence_status"),
        nullable=False,
        default=EvidenceStatus.UNKNOWN,
        server_default=EvidenceStatus.UNKNOWN.value,
    )
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("agricultural_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON, nullable=True
    )
    primary_evidence_id: Mapped[int | None] = mapped_column(
        ForeignKey("evidence_records.id", ondelete="RESTRICT"), nullable=True
    )

    crop: Mapped["Crop"] = relationship("Crop", back_populates="varieties")
    source: Mapped["AgriculturalSource | None"] = relationship(
        "AgriculturalSource", back_populates="varieties"
    )
    primary_evidence: Mapped["EvidenceRecord | None"] = relationship(
        "EvidenceRecord", foreign_keys=[primary_evidence_id]
    )
    evidence_records: Mapped[list["EvidenceRecord"]] = relationship(
        "EvidenceRecord", secondary="crop_variety_evidence"
    )
    calendars: Mapped[list["CropCalendar"]] = relationship(
        "CropCalendar",
        back_populates="variety",
        overlaps="crop,calendars",
        passive_deletes="all",
    )
    requirements: Mapped[list["CropRequirement"]] = relationship(
        "CropRequirement",
        back_populates="variety",
        overlaps="crop,requirements",
        passive_deletes="all",
    )
    source_applicabilities: Mapped[list["SourceApplicability"]] = relationship(
        "SourceApplicability",
        foreign_keys="SourceApplicability.variety_id",
        passive_deletes="all",
    )
