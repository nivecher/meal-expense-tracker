"""Merge latest Alembic heads.

Revision ID: g8h9i0j1k2l3
Revises: f6a7b8c9d0e1, f7e8d9c0b1a2
Create Date: 2026-03-08 14:05:00.000000

"""

# revision identifiers, used by Alembic.
revision = "g8h9i0j1k2l3"
down_revision = ("f6a7b8c9d0e1", "f7e8d9c0b1a2")
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
