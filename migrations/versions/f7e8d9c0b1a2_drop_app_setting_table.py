"""Drop app_setting table (unused; favicon config was never wired).

Revision ID: f7e8d9c0b1a2
Revises: e5f6a7b8c9d0
Create Date: 2026-03-08

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "f7e8d9c0b1a2"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS app_setting")


def downgrade() -> None:
    # Table was unused; no need to recreate.
    pass
