from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base
from .enums import EvidenceOriginType, enum_column


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"
    __table_args__ = (
        CheckConstraint(
            """
            CASE
                WHEN source_type = 'PUBLISHED_SOURCE' THEN
                    CASE WHEN source_id IS NOT NULL THEN 1 ELSE 0 END
                ELSE 1
            END = 1
            """,
            name="ck_evidence_published_origin_requires_source",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("agricultural_sources.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    source_type: Mapped[EvidenceOriginType] = mapped_column(
        enum_column(EvidenceOriginType, "evidence_origin_type"), nullable=False
    )
    source_locator: Mapped[str | None] = mapped_column(String(500), nullable=True)
    statement: Mapped[str | None] = mapped_column(Text, nullable=True)
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)

    source: Mapped["AgriculturalSource | None"] = relationship(
        "AgriculturalSource", back_populates="evidence_records"
    )
    geographic_scopes: Mapped[list["EvidenceGeographicScope"]] = relationship(
        "EvidenceGeographicScope",
        back_populates="evidence",
        cascade="all, delete-orphan",
    )
