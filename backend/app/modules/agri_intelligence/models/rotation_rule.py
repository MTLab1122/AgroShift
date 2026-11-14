from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base
from .enums import EvidenceStatus, enum_column


class CropRotationRule(Base):
    __tablename__ = "crop_rotation_rules"
    __table_args__ = (
        CheckConstraint(
            """
            CASE
                WHEN
                    CASE WHEN previous_crop_id IS NOT NULL THEN 1 ELSE 0 END
                  + CASE WHEN previous_variety_id IS NOT NULL THEN 1 ELSE 0 END
                  + CASE WHEN source_family IS NOT NULL
                              AND length(trim(source_family)) > 0 THEN 1 ELSE 0 END
                = 1
                THEN 1 ELSE 0
            END = 1
            """,
            name="ck_rotation_rule_source_selector_exclusive",
        ),
        CheckConstraint(
            """
            CASE
                WHEN
                    CASE WHEN next_crop_id IS NOT NULL THEN 1 ELSE 0 END
                  + CASE WHEN next_variety_id IS NOT NULL THEN 1 ELSE 0 END
                  + CASE WHEN target_family IS NOT NULL
                              AND length(trim(target_family)) > 0 THEN 1 ELSE 0 END
                = 1
                THEN 1 ELSE 0
            END = 1
            """,
            name="ck_rotation_rule_target_selector_exclusive",
        ),
        CheckConstraint(
            "confidence_level BETWEEN 0 AND 1",
            name="ck_rotation_rule_confidence_range",
        ),
        CheckConstraint(
            """
            CASE
                WHEN evidence_status IN ('VERIFIED', 'PROVISIONAL') THEN
                    CASE WHEN primary_evidence_id IS NOT NULL THEN 1 ELSE 0 END
                ELSE 1
            END = 1
            """,
            name="ck_rotation_rule_evidence_requires_support",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    previous_crop_id: Mapped[int | None] = mapped_column(
        ForeignKey("crops.id", ondelete="CASCADE"), nullable=True, index=True
    )
    next_crop_id: Mapped[int | None] = mapped_column(
        ForeignKey("crops.id", ondelete="CASCADE"), nullable=True, index=True
    )
    previous_variety_id: Mapped[int | None] = mapped_column(
        ForeignKey("crop_varieties.id", ondelete="CASCADE"), nullable=True, index=True
    )
    next_variety_id: Mapped[int | None] = mapped_column(
        ForeignKey("crop_varieties.id", ondelete="CASCADE"), nullable=True, index=True
    )
    source_family: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    target_family: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    rule_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    compatibility_status: Mapped[str | None] = mapped_column(String(120), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(120), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    geographic_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_source_id: Mapped[int | None] = mapped_column(
        ForeignKey("agricultural_sources.id", ondelete="SET NULL"), nullable=True, index=True
    )
    confidence_level: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    evidence_status: Mapped[EvidenceStatus] = mapped_column(
        enum_column(EvidenceStatus, "crop_rotation_rule_evidence_status"),
        nullable=False,
        default=EvidenceStatus.UNKNOWN,
        server_default=EvidenceStatus.UNKNOWN.value,
    )
    primary_evidence_id: Mapped[int | None] = mapped_column(
        ForeignKey("evidence_records.id", ondelete="RESTRICT"), nullable=True
    )

    previous_crop: Mapped["Crop | None"] = relationship(
        "Crop", foreign_keys=[previous_crop_id], back_populates="previous_rotation_rules"
    )
    next_crop: Mapped["Crop | None"] = relationship(
        "Crop", foreign_keys=[next_crop_id], back_populates="next_rotation_rules"
    )
    previous_variety: Mapped["CropVariety | None"] = relationship(
        "CropVariety", foreign_keys=[previous_variety_id]
    )
    next_variety: Mapped["CropVariety | None"] = relationship(
        "CropVariety", foreign_keys=[next_variety_id]
    )
    evidence_source: Mapped["AgriculturalSource | None"] = relationship(
        "AgriculturalSource", back_populates="rotation_rules"
    )
    primary_evidence: Mapped["EvidenceRecord | None"] = relationship(
        "EvidenceRecord", foreign_keys=[primary_evidence_id]
    )
    evidence_records: Mapped[list["EvidenceRecord"]] = relationship(
        "EvidenceRecord", secondary="crop_rotation_rule_evidence"
    )
    geographic_scopes: Mapped[list["CropRotationRuleGeographicScope"]] = relationship(
        "CropRotationRuleGeographicScope",
        back_populates="crop_rotation_rule",
        cascade="all, delete-orphan",
    )
