"""Add merchant description.

Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l3
Create Date: 2026-03-08 15:35:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "h9i0j1k2l3m4"
down_revision = "g8h9i0j1k2l3"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    with op.batch_alter_table("merchant", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "description",
                sa.Text(),
                nullable=True,
                comment="Optional merchant description or summary",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("merchant", schema=None) as batch_op:
        batch_op.drop_column("description")
