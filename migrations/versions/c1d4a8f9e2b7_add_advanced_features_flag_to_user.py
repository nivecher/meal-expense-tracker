"""Add advanced features flag to user.

Revision ID: c1d4a8f9e2b7
Revises: 8b1d7c3e4f2a
Create Date: 2026-02-21 10:15:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c1d4a8f9e2b7"
down_revision = "8b1d7c3e4f2a"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "advanced_features_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
                comment="Whether the user has advanced features enabled",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("advanced_features_enabled")
