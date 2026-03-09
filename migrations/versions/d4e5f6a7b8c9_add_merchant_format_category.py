"""Add format_category to merchant.

Revision ID: d4e5f6a7b8c9
Revises: 2b7d4e1f9c3a
Create Date: 2026-03-08 11:30:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "2b7d4e1f9c3a"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    with op.batch_alter_table("merchant", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "format_category",
                sa.String(length=50),
                nullable=True,
                comment="Optional physical or operational format classification for the merchant",
            )
        )
        batch_op.create_index(batch_op.f("ix_merchant_format_category"), ["format_category"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("merchant", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_merchant_format_category"))
        batch_op.drop_column("format_category")
