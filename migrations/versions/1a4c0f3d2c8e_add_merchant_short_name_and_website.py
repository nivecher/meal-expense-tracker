"""Add merchant short name and website

Revision ID: 1a4c0f3d2c8e
Revises: 9d3e86eb77e6
Create Date: 2026-02-21 20:12:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "1a4c0f3d2c8e"
down_revision = "9d3e86eb77e6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("merchant", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "short_name",
                sa.String(length=100),
                nullable=True,
                comment="Optional short display name used in restaurant display names",
            )
        )
        batch_op.add_column(
            sa.Column(
                "website",
                sa.String(length=500),
                nullable=True,
                comment="Merchant website URL",
            )
        )


def downgrade():
    with op.batch_alter_table("merchant", schema=None) as batch_op:
        batch_op.drop_column("website")
        batch_op.drop_column("short_name")
