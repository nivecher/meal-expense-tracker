"""Merge merchant migration heads.

Revision ID: e5f6a7b8c9d0
Revises: 24d15401b757, d4e5f6a7b8c9
Create Date: 2026-03-08 11:55:00.000000

"""

# revision identifiers, used by Alembic.
revision = "e5f6a7b8c9d0"
down_revision = ("24d15401b757", "d4e5f6a7b8c9")
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
