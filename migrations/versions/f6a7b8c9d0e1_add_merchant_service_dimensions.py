"""Add merchant service dimensions.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-03-08 13:10:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    with op.batch_alter_table("merchant", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "menu_focus",
                sa.String(length=50),
                nullable=True,
                comment="Optional menu or product focus classification for the merchant",
            )
        )
        batch_op.add_column(
            sa.Column(
                "cuisine",
                sa.String(length=100),
                nullable=True,
                comment="Optional cuisine classification aligned with restaurant cuisine values",
            )
        )
        batch_op.add_column(
            sa.Column(
                "service_level",
                sa.String(length=50),
                nullable=True,
                comment="Optional service style classification for the merchant",
            )
        )
        batch_op.create_index(batch_op.f("ix_merchant_menu_focus"), ["menu_focus"], unique=False)
        batch_op.create_index(batch_op.f("ix_merchant_cuisine"), ["cuisine"], unique=False)
        batch_op.create_index(batch_op.f("ix_merchant_service_level"), ["service_level"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("merchant", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_merchant_service_level"))
        batch_op.drop_index(batch_op.f("ix_merchant_cuisine"))
        batch_op.drop_index(batch_op.f("ix_merchant_menu_focus"))
        batch_op.drop_column("service_level")
        batch_op.drop_column("cuisine")
        batch_op.drop_column("menu_focus")
