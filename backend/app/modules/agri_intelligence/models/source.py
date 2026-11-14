from datetime import date

from sqlalchemy import Boolean, Date, Integer, String, Text, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base


class AgriculturalSource(Base):
    __tablename__ = "agricultural_sources"
    __table_args__ = (
        UniqueConstraint(
            "id", "all_crops_flag", name="uq_agricultural_sources_id_all_crops"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    all_crops_flag: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    organization: Mapped[str | None] = mapped_column(String(240), nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    publication_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    access_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    geographic_applicability: Mapped[str | None] = mapped_column(Text, nullable=True)
    crop_applicability: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_class: Mapped[str | None] = mapped_column(String(120), nullable=True)
    review_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    applicabilities: Mapped[list["SourceApplicability"]] = relationship(
        "SourceApplicability", back_populates="source", cascade="all, delete-orphan"
    )
    all_crops_applicability: Mapped["SourceAllCropsApplicability | None"] = relationship(
        "SourceAllCropsApplicability",
        back_populates="source",
        cascade="all, delete-orphan",
        uselist=False,
    )
    geographic_applicabilities: Mapped[list["SourceGeographicApplicability"]] = relationship(
        "SourceGeographicApplicability",
        back_populates="source",
        cascade="all, delete-orphan",
    )
    evidence_records: Mapped[list["EvidenceRecord"]] = relationship(
        "EvidenceRecord", back_populates="source", passive_deletes="all"
    )
    varieties: Mapped[list["CropVariety"]] = relationship(
        "CropVariety", back_populates="source"
    )
    calendars: Mapped[list["CropCalendar"]] = relationship(
        "CropCalendar", back_populates="calendar_source"
    )
    requirements: Mapped[list["CropRequirement"]] = relationship(
        "CropRequirement", back_populates="source"
    )
    rotation_rules: Mapped[list["CropRotationRule"]] = relationship(
        "CropRotationRule", back_populates="evidence_source"
    )
