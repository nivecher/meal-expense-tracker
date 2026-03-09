"""Add merchant favicon_url

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-07

"""

from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("merchant", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "favicon_url",
                sa.String(length=500),
                nullable=True,
                comment="Optional explicit favicon URL; takes precedence over website-derived favicon",
            )
        )


def downgrade():
    with op.batch_alter_table("merchant", schema=None) as batch_op:
        batch_op.drop_column("favicon_url")
