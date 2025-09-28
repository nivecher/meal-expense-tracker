"""Safely ensure restaurant misc columns (price_level, primary_type, latitude, longitude)

Revision ID: 1a2b3c4d5e67
Revises: 8c3c2b9a1e45
Create Date: 2025-09-28 00:10:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1a2b3c4d5e67"
down_revision = "8c3c2b9a1e45"
branch_labels = None
depends_on = None


def _get_columns(inspector, table_name):
    try:
        return [c["name"] for c in inspector.get_columns(table_name)]
    except Exception:
        return []


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "restaurant" not in inspector.get_table_names():
        return

    cols = _get_columns(inspector, "restaurant")

    with op.batch_alter_table("restaurant") as batch_op:
        if "price_level" not in cols:
            batch_op.add_column(
                sa.Column(
                    "price_level",
                    sa.Integer(),
                    nullable=True,
                    comment="Price level from Google Places (0=Free, 1=$1-10, 2=$11-30, 3=$31-60, 4=$61+)",
                )
            )

        cols = _get_columns(inspector, "restaurant")

        if "primary_type" not in cols:
            batch_op.add_column(sa.Column("primary_type", sa.String(length=100), nullable=True))

        cols = _get_columns(inspector, "restaurant")

        if "latitude" not in cols:
            batch_op.add_column(
                sa.Column("latitude", sa.Float(), nullable=True, comment="Restaurant latitude coordinate")
            )

        cols = _get_columns(inspector, "restaurant")

        if "longitude" not in cols:
            batch_op.add_column(
                sa.Column("longitude", sa.Float(), nullable=True, comment="Restaurant longitude coordinate")
            )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "restaurant" not in inspector.get_table_names():
        return

    cols = _get_columns(inspector, "restaurant")

    with op.batch_alter_table("restaurant") as batch_op:
        if "longitude" in cols:
            batch_op.drop_column("longitude")
        cols = _get_columns(inspector, "restaurant")
        if "latitude" in cols:
            batch_op.drop_column("latitude")
        cols = _get_columns(inspector, "restaurant")
        if "primary_type" in cols:
            batch_op.drop_column("primary_type")
        cols = _get_columns(inspector, "restaurant")
        if "price_level" in cols:
            batch_op.drop_column("price_level")
