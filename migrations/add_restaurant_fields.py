"""Initial migration: Add address and category fields to Restaurant model and category field to Expense model."""

import sqlalchemy as sa
from alembic import op  # type: ignore


def upgrade():
    # Add address and category columns to restaurant table
    op.add_column("restaurant", sa.Column("address", sa.String(200), nullable=True))
    op.add_column("restaurant", sa.Column("category", sa.String(50), nullable=True))
    # Add category column to expense table
    op.add_column("expense", sa.Column("category", sa.String(50), nullable=True))


def downgrade():
    # Remove address and category columns from restaurant table
    op.drop_column("restaurant", "address")
    op.drop_column("restaurant", "category")
    # Remove category column from expense table
    op.drop_column("expense", "category")
