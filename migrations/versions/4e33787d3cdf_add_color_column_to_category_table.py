"""Add color column to category table

Revision ID: 4e33787d3cdf
Revises: b589fad217b4
Create Date: 2025-06-28 22:22:35.311976

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "4e33787d3cdf"
down_revision = "b589fad217b4"
branch_labels = None
depends_on = None


def upgrade():
    # Add the column as nullable first
    with op.batch_alter_table("category") as batch_op:
        batch_op.add_column(
            sa.Column("color", sa.String(length=20), nullable=True, comment="Hex color code for the category")
        )

    # Set default value for existing rows
    op.execute("UPDATE category SET color = '#6c757d' WHERE color IS NULL")

    # Now alter the column to be NOT NULL
    with op.batch_alter_table("category") as batch_op:
        batch_op.alter_column("color", nullable=False)


def downgrade():
    # Drop the color column
    with op.batch_alter_table("category") as batch_op:
        batch_op.drop_column("color")
