"""Re-apply RLS enablement on public tables.

Revision ID: 8b1d7c3e4f2a
Revises: 5f2c8e9a1d4b
Create Date: 2026-01-24 12:30:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "8b1d7c3e4f2a"
down_revision = "5f2c8e9a1d4b"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None

PUBLIC_TABLES = (
    "alembic_version",
    "api_cache",
    "user",
    "category",
    "tag",
    "restaurant",
    "expense",
    "expense_tag",
)


def _alter_rls(action: str) -> None:
    for table_name in PUBLIC_TABLES:
        if table_name == "user":
            qualified_name = 'public."user"'
        else:
            qualified_name = f"public.{table_name}"
        op.execute(f"ALTER TABLE IF EXISTS {qualified_name} {action} ROW LEVEL SECURITY")


def upgrade() -> None:
    _alter_rls("ENABLE")


def downgrade() -> None:
    _alter_rls("DISABLE")
