from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


class RecommendationScenario(Base):
    __tablename__ = "recommendation_scenarios"
    __table_args__ = (
        CheckConstraint(
            "scenario_type IN ('EXISTING_PRACTICE', 'PULSE_INCLUSIVE', 'SOIL_COVER_FORAGE')",
            name="ck_recommendation_scenarios_type",
        ),
        CheckConstraint(
            "feasibility_status IN ('FEASIBLE', 'CONDITIONALLY_FEASIBLE', 'INFEASIBLE', 'INSUFFICIENT_DATA')",
            name="ck_recommendation_scenarios_feasibility",
        ),
        CheckConstraint(
            "score IS NULL OR score BETWEEN 0 AND 100",
            name="ck_recommendation_scenarios_score_range",
        ),
        Index(
            "ix_recommendation_scenarios_farm_created",
            "farm_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    scenario_type: Mapped[str] = mapped_column(String(40), nullable=False)
    farm_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    crop_sequence: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    season_schedule: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    planting_harvest_windows: Mapped[list[dict]] = mapped_column(
        JSON, nullable=False, default=list
    )
    duration_days: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    feasibility_status: Mapped[str] = mapped_column(String(32), nullable=False)
    validation_results: Mapped[list[dict]] = mapped_column(
        JSON, nullable=False, default=list
    )
    evidence_references: Mapped[list[dict]] = mapped_column(
        JSON, nullable=False, default=list
    )
    candidate_decisions: Mapped[list[dict]] = mapped_column(
        JSON, nullable=False, default=list
    )
    benefits: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    risks: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    constraints: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    limitations: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    missing_information: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    priorities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    score_components: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    priority_weights: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    engine_version: Mapped[str] = mapped_column(
        String(40), nullable=False, default="module03-0.1.0", server_default="module03-0.1.0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
