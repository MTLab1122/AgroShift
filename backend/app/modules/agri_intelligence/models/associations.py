from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    false,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Table,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base
from ._constraints import geographic_scope_check
from .enums import ApplicabilityMode, GeographicScopeType, enum_column


class SourceApplicability(Base):
    __tablename__ = "source_applicabilities"
    __table_args__ = (
        CheckConstraint(
            """
            CASE
                WHEN applicability_mode = 'CROP' THEN
                    CASE WHEN all_crops_flag = FALSE
                         AND crop_id IS NOT NULL AND variety_id IS NULL
                         AND family_name IS NULL THEN 1 ELSE 0 END
                WHEN applicability_mode = 'VARIETY' THEN
                    CASE WHEN all_crops_flag = FALSE
                         AND crop_id IS NULL AND variety_id IS NOT NULL
                         AND family_name IS NULL THEN 1 ELSE 0 END
                WHEN applicability_mode = 'FAMILY' THEN
                    CASE WHEN all_crops_flag = FALSE
                         AND crop_id IS NULL AND variety_id IS NULL
                         AND family_name IS NOT NULL
                         AND length(trim(family_name)) > 0 THEN 1 ELSE 0 END
                ELSE 0
            END = 1
            """,
            name="ck_source_applicability_exclusive_selector",
        ),
        ForeignKeyConstraint(
            ["source_id", "all_crops_flag"],
            ["agricultural_sources.id", "agricultural_sources.all_crops_flag"],
            ondelete="CASCADE",
            name="fk_source_applicabilities_source_scope",
        ),
        UniqueConstraint(
            "source_id", "crop_id", name="uq_source_applicabilities_source_crop"
        ),
        UniqueConstraint(
            "source_id", "variety_id", name="uq_source_applicabilities_source_variety"
        ),
        UniqueConstraint(
            "source_id", "family_name", name="uq_source_applicabilities_source_family"
        ),
        Index("ix_source_applicabilities_source_mode", "source_id", "applicability_mode"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )
    applicability_mode: Mapped[ApplicabilityMode] = mapped_column(
        enum_column(ApplicabilityMode, "source_applicability_mode"), nullable=False
    )
    all_crops_flag: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    crop_id: Mapped[int | None] = mapped_column(
        ForeignKey("crops.id", ondelete="CASCADE"), nullable=True, index=True
    )
    variety_id: Mapped[int | None] = mapped_column(
        ForeignKey("crop_varieties.id", ondelete="CASCADE"), nullable=True, index=True
    )
    family_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    source: Mapped["AgriculturalSource"] = relationship(
        "AgriculturalSource", back_populates="applicabilities"
    )
    crop: Mapped["Crop | None"] = relationship(
        "Crop", foreign_keys=[crop_id], overlaps="source_applicabilities"
    )
    variety: Mapped["CropVariety | None"] = relationship(
        "CropVariety",
        foreign_keys=[variety_id],
        overlaps="source_applicabilities",
    )


class SourceAllCropsApplicability(Base):
    __tablename__ = "source_all_crops_applicabilities"
    __table_args__ = (
        CheckConstraint(
            "all_crops_flag = TRUE AND applicability_mode = 'ALL_CROPS'",
            name="ck_source_all_crops_mode",
        ),
        ForeignKeyConstraint(
            ["source_id", "all_crops_flag"],
            ["agricultural_sources.id", "agricultural_sources.all_crops_flag"],
            ondelete="CASCADE",
            name="fk_source_all_crops_source_scope",
        ),
    )

    source_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    all_crops_flag: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    applicability_mode: Mapped[ApplicabilityMode] = mapped_column(
        enum_column(ApplicabilityMode, "source_all_crops_mode"),
        nullable=False,
        default=ApplicabilityMode.ALL_CROPS,
        server_default=ApplicabilityMode.ALL_CROPS.value,
    )

    source: Mapped["AgriculturalSource"] = relationship(
        "AgriculturalSource", back_populates="all_crops_applicability"
    )


class SourceGeographicApplicability(Base):
    __tablename__ = "source_geographic_applicabilities"
    __table_args__ = (
        CheckConstraint(
            geographic_scope_check(include_farm=False),
            name="ck_source_geographic_applicability_scope",
        ),
        Index("ix_source_geographic_applicabilities_source", "source_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("agricultural_sources.id", ondelete="CASCADE"), nullable=False
    )
    scope_type: Mapped[GeographicScopeType] = mapped_column(
        enum_column(GeographicScopeType, "source_geographic_scope_type"),
        nullable=False,
    )
    country_id: Mapped[int | None] = mapped_column(
        ForeignKey("countries.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    province_state_id: Mapped[int | None] = mapped_column(
        ForeignKey("province_states.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    district_id: Mapped[int | None] = mapped_column(
        ForeignKey("districts.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    locality_id: Mapped[int | None] = mapped_column(
        ForeignKey("localities.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    agroecological_zone_id: Mapped[int | None] = mapped_column(
        ForeignKey("agroecological_zones.id", ondelete="RESTRICT"), nullable=True, index=True
    )

    source: Mapped["AgriculturalSource"] = relationship(
        "AgriculturalSource", back_populates="geographic_applicabilities"
    )


class AgroecologicalZoneGeography(Base):
    __tablename__ = "agroecological_zone_geographies"
    __table_args__ = (
        CheckConstraint(
            """
            CASE
                WHEN
                    CASE WHEN country_id IS NOT NULL THEN 1 ELSE 0 END
                  + CASE WHEN province_state_id IS NOT NULL THEN 1 ELSE 0 END
                  + CASE WHEN district_id IS NOT NULL THEN 1 ELSE 0 END
                  + CASE WHEN locality_id IS NOT NULL THEN 1 ELSE 0 END
                = 1
                THEN 1 ELSE 0
            END = 1
            """,
            name="ck_zone_geography_exactly_one_admin_area",
        ),
        Index("ix_zone_geographies_zone", "agroecological_zone_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agroecological_zone_id: Mapped[int] = mapped_column(
        ForeignKey("agroecological_zones.id", ondelete="CASCADE"), nullable=False
    )
    country_id: Mapped[int | None] = mapped_column(
        ForeignKey("countries.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    province_state_id: Mapped[int | None] = mapped_column(
        ForeignKey("province_states.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    district_id: Mapped[int | None] = mapped_column(
        ForeignKey("districts.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    locality_id: Mapped[int | None] = mapped_column(
        ForeignKey("localities.id", ondelete="RESTRICT"), nullable=True, index=True
    )

    agroecological_zone: Mapped["AgroecologicalZone"] = relationship(
        "AgroecologicalZone", back_populates="geographic_associations"
    )


class CropRotationRuleGeographicScope(Base):
    __tablename__ = "crop_rotation_rule_geographic_scopes"
    __table_args__ = (
        CheckConstraint(
            geographic_scope_check(include_farm=False),
            name="ck_rotation_rule_geographic_scope",
        ),
        Index("ix_rotation_rule_geographic_scopes_rule", "crop_rotation_rule_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    crop_rotation_rule_id: Mapped[int] = mapped_column(
        ForeignKey("crop_rotation_rules.id", ondelete="CASCADE"), nullable=False
    )
    scope_type: Mapped[GeographicScopeType] = mapped_column(
        enum_column(GeographicScopeType, "rotation_rule_geographic_scope_type"),
        nullable=False,
    )
    country_id: Mapped[int | None] = mapped_column(
        ForeignKey("countries.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    province_state_id: Mapped[int | None] = mapped_column(
        ForeignKey("province_states.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    district_id: Mapped[int | None] = mapped_column(
        ForeignKey("districts.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    locality_id: Mapped[int | None] = mapped_column(
        ForeignKey("localities.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    agroecological_zone_id: Mapped[int | None] = mapped_column(
        ForeignKey("agroecological_zones.id", ondelete="RESTRICT"), nullable=True, index=True
    )

    crop_rotation_rule: Mapped["CropRotationRule"] = relationship(
        "CropRotationRule", back_populates="geographic_scopes"
    )


class EvidenceGeographicScope(Base):
    __tablename__ = "evidence_geographic_scopes"
    __table_args__ = (
        CheckConstraint(
            geographic_scope_check(include_farm=True),
            name="ck_evidence_geographic_scope",
        ),
        Index("ix_evidence_geographic_scopes_record", "evidence_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("evidence_records.id", ondelete="CASCADE"), nullable=False
    )
    scope_type: Mapped[GeographicScopeType] = mapped_column(
        enum_column(GeographicScopeType, "evidence_geographic_scope_type"),
        nullable=False,
    )
    country_id: Mapped[int | None] = mapped_column(
        ForeignKey("countries.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    province_state_id: Mapped[int | None] = mapped_column(
        ForeignKey("province_states.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    district_id: Mapped[int | None] = mapped_column(
        ForeignKey("districts.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    locality_id: Mapped[int | None] = mapped_column(
        ForeignKey("localities.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    agroecological_zone_id: Mapped[int | None] = mapped_column(
        ForeignKey("agroecological_zones.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    farm_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)

    evidence: Mapped["EvidenceRecord"] = relationship(
        "EvidenceRecord", back_populates="geographic_scopes"
    )


crop_evidence = Table(
    "crop_evidence",
    Base.metadata,
    Column("crop_id", ForeignKey("crops.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "evidence_id",
        ForeignKey("evidence_records.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

crop_variety_evidence = Table(
    "crop_variety_evidence",
    Base.metadata,
    Column(
        "crop_variety_id",
        ForeignKey("crop_varieties.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "evidence_id",
        ForeignKey("evidence_records.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

crop_calendar_evidence = Table(
    "crop_calendar_evidence",
    Base.metadata,
    Column(
        "crop_calendar_id",
        ForeignKey("crop_calendars.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "evidence_id",
        ForeignKey("evidence_records.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

crop_requirement_evidence = Table(
    "crop_requirement_evidence",
    Base.metadata,
    Column(
        "crop_requirement_id",
        ForeignKey("crop_requirements.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "evidence_id",
        ForeignKey("evidence_records.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

crop_rotation_rule_evidence = Table(
    "crop_rotation_rule_evidence",
    Base.metadata,
    Column(
        "crop_rotation_rule_id",
        ForeignKey("crop_rotation_rules.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "evidence_id",
        ForeignKey("evidence_records.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
