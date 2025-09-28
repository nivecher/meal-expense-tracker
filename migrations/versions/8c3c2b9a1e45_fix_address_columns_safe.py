"""Safely ensure restaurant address_line_1 and address_line_2 columns exist
Revision ID: 8c3c2b9a1e45
Revises: 42985d8e0812
Create Date: 2025-09-28 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8c3c2b9a1e45"
down_revision = "42985d8e0812"
branch_labels = None
depends_on = None


def _get_columns(inspector, table_name):
    try:
        return [c["name"] for c in inspector.get_columns(table_name)]
    except Exception:
        return []


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "restaurant" not in inspector.get_table_names():
        return

    current_cols = _get_columns(inspector, "restaurant")

    with op.batch_alter_table("restaurant") as batch_op:
        # Ensure address_line_1 exists
        if "address_line_1" not in current_cols:
            if "address" in current_cols:
                # Rename legacy 'address' -> 'address_line_1'
                batch_op.alter_column(
                    "address",
                    new_column_name="address_line_1",
                    existing_type=sa.String(length=200),
                    existing_nullable=True,
                    existing_comment=None,
                )
            else:
                batch_op.add_column(
                    sa.Column(
                        "address_line_1",
                        sa.String(length=200),
                        nullable=True,
                        comment="Primary street address",
                    )
                )

        # Refresh columns after potential rename
        current_cols = _get_columns(inspector, "restaurant")

        # Ensure address_line_2 exists
        if "address_line_2" not in current_cols:
            if "address2" in current_cols:
                # Rename legacy 'address2' -> 'address_line_2'
                batch_op.alter_column(
                    "address2",
                    new_column_name="address_line_2",
                    existing_type=sa.String(length=200),
                    existing_nullable=True,
                    existing_comment=None,
                )
            else:
                batch_op.add_column(
                    sa.Column(
                        "address_line_2",
                        sa.String(length=200),
                        nullable=True,
                        comment="Secondary address (apartment/suite/unit)",
                    )
                )


def downgrade():
    # Best-effort revert: rename back if possible
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "restaurant" not in inspector.get_table_names():
        return

    cols = _get_columns(inspector, "restaurant")

    with op.batch_alter_table("restaurant") as batch_op:
        if "address_line_2" in cols and "address2" not in cols:
            batch_op.alter_column(
                "address_line_2",
                new_column_name="address2",
                existing_type=sa.String(length=200),
                existing_nullable=True,
                existing_comment=None,
            )
        cols = _get_columns(inspector, "restaurant")
        if "address_line_1" in cols and "address" not in cols:
            batch_op.alter_column(
                "address_line_1",
                new_column_name="address",
                existing_type=sa.String(length=200),
                existing_nullable=True,
                existing_comment=None,
            )
