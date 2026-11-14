"""create_farms_and_crop_history_tables

Revision ID: 3eeb4f498ca3
Revises:
Create Date: 2026-11-14 13:49:56.200592

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3eeb4f498ca3'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "farms",
        sa.Column("farm_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("owner_name", sa.String(length=128), nullable=False),
        sa.Column("contact_phone", sa.String(length=32), nullable=False),
        sa.Column("preferred_language", sa.String(length=8), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("elevation_meters", sa.Float(), nullable=True),
        sa.Column("village_or_town", sa.String(length=128), nullable=True),
        sa.Column("district", sa.String(length=64), nullable=False),
        sa.Column("province_or_region", sa.String(length=64), nullable=False),
        sa.Column("country", sa.String(length=64), nullable=False),
        sa.Column("boundary_geojson", sa.Text(), nullable=True),
        sa.Column("total_area_hectares", sa.Float(), nullable=False),
        sa.Column("soil_type", sa.String(length=32), nullable=False),
        sa.Column("irrigation_source", sa.String(length=32), nullable=False),
        sa.Column("water_availability", sa.String(length=32), nullable=True),
        sa.Column("salinity_level", sa.String(length=32), nullable=True),
        sa.Column("current_crops_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.String(length=64), nullable=False),
        sa.PrimaryKeyConstraint("farm_id"),
    )
    op.create_table(
        "crop_history",
        sa.Column("record_id", sa.String(length=64), nullable=False),
        sa.Column("farm_id", sa.String(length=64), nullable=False),
        sa.Column("crop_name", sa.String(length=64), nullable=False),
        sa.Column("variety", sa.String(length=64), nullable=True),
        sa.Column("season", sa.String(length=32), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("sowing_date", sa.String(length=32), nullable=True),
        sa.Column("harvest_date", sa.String(length=32), nullable=True),
        sa.Column("area_planted_hectares", sa.Float(), nullable=True),
        sa.Column("yield_amount_kg", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["farm_id"], ["farms.farm_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("record_id"),
    )

    op.create_index("ix_farms_farm_id", "farms", ["farm_id"], unique=False)
    op.create_index("ix_farms_name", "farms", ["name"], unique=False)
    op.create_index("ix_farms_district", "farms", ["district"], unique=False)
    op.create_index("ix_farms_soil_type", "farms", ["soil_type"], unique=False)
    op.create_index("idx_farm_coords", "farms", ["latitude", "longitude"], unique=False)
    op.create_index(
        "idx_farm_district_prov",
        "farms",
        ["district", "province_or_region"],
        unique=False,
    )
    op.create_index(
        "ix_crop_history_record_id", "crop_history", ["record_id"], unique=False
    )
    op.create_index(
        "ix_crop_history_farm_id", "crop_history", ["farm_id"], unique=False
    )
    op.create_index(
        "ix_crop_history_crop_name", "crop_history", ["crop_name"], unique=False
    )
    op.create_index(
        "ix_crop_history_season", "crop_history", ["season"], unique=False
    )
    op.create_index("ix_crop_history_year", "crop_history", ["year"], unique=False)
    op.create_index(
        "idx_crop_farm_season_year",
        "crop_history",
        ["farm_id", "season", "year"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_crop_farm_season_year", table_name="crop_history")
    op.drop_index("ix_crop_history_year", table_name="crop_history")
    op.drop_index("ix_crop_history_season", table_name="crop_history")
    op.drop_index("ix_crop_history_crop_name", table_name="crop_history")
    op.drop_index("ix_crop_history_farm_id", table_name="crop_history")
    op.drop_index("ix_crop_history_record_id", table_name="crop_history")
    op.drop_index("idx_farm_district_prov", table_name="farms")
    op.drop_index("idx_farm_coords", table_name="farms")
    op.drop_index("ix_farms_soil_type", table_name="farms")
    op.drop_index("ix_farms_district", table_name="farms")
    op.drop_index("ix_farms_name", table_name="farms")
    op.drop_index("ix_farms_farm_id", table_name="farms")
    op.drop_table("crop_history")
    op.drop_table("farms")
