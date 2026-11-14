"""Add persistent Module 03 recommendation scenarios.

Revision ID: a2179c4a0f1b
Revises: 6afb33c45f08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a2179c4a0f1b"
down_revision: Union[str, None] = "6afb33c45f08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recommendation_scenarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scenario_id", sa.String(length=36), nullable=False),
        sa.Column("scenario_type", sa.String(length=40), nullable=False),
        sa.Column("farm_id", sa.String(length=128), nullable=False),
        sa.Column("crop_sequence", sa.JSON(), nullable=False),
        sa.Column("season_schedule", sa.JSON(), nullable=False),
        sa.Column("planting_harvest_windows", sa.JSON(), nullable=False),
        sa.Column("duration_days", sa.JSON(), nullable=False),
        sa.Column("feasibility_status", sa.String(length=32), nullable=False),
        sa.Column("validation_results", sa.JSON(), nullable=False),
        sa.Column("evidence_references", sa.JSON(), nullable=False),
        sa.Column("candidate_decisions", sa.JSON(), nullable=False),
        sa.Column("benefits", sa.JSON(), nullable=False),
        sa.Column("risks", sa.JSON(), nullable=False),
        sa.Column("constraints", sa.JSON(), nullable=False),
        sa.Column("limitations", sa.JSON(), nullable=False),
        sa.Column("missing_information", sa.JSON(), nullable=False),
        sa.Column("priorities", sa.JSON(), nullable=False),
        sa.Column("score", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("score_components", sa.JSON(), nullable=True),
        sa.Column("priority_weights", sa.JSON(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column(
            "engine_version",
            sa.String(length=40),
            server_default="module03-0.1.0",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "scenario_type IN ('EXISTING_PRACTICE', 'PULSE_INCLUSIVE', 'SOIL_COVER_FORAGE')",
            name="ck_recommendation_scenarios_type",
        ),
        sa.CheckConstraint(
            "feasibility_status IN ('FEASIBLE', 'CONDITIONALLY_FEASIBLE', 'INFEASIBLE', 'INSUFFICIENT_DATA')",
            name="ck_recommendation_scenarios_feasibility",
        ),
        sa.CheckConstraint(
            "score IS NULL OR score BETWEEN 0 AND 100",
            name="ck_recommendation_scenarios_score_range",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scenario_id"),
    )
    op.create_index(
        "ix_recommendation_scenarios_farm_created",
        "recommendation_scenarios",
        ["farm_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_recommendation_scenarios_farm_id",
        "recommendation_scenarios",
        ["farm_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_recommendation_scenarios_farm_id",
        table_name="recommendation_scenarios",
    )
    op.drop_index(
        "ix_recommendation_scenarios_farm_created",
        table_name="recommendation_scenarios",
    )
    op.drop_table("recommendation_scenarios")
