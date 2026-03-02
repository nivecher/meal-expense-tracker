"""Add location_name to restaurant

Revision ID: 2b7d4e1f9c3a
Revises: 1a4c0f3d2c8e
Create Date: 2026-02-21 22:10:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "2b7d4e1f9c3a"
down_revision = "1a4c0f3d2c8e"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("restaurant", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "location_name",
                sa.String(length=100),
                nullable=True,
                comment="Optional location/branch name used for display when available",
            )
        )


def downgrade():
    with op.batch_alter_table("restaurant", schema=None) as batch_op:
        batch_op.drop_column("location_name")
