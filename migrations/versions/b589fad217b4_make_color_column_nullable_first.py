"""Make color column nullable first

Revision ID: b589fad217b4
Revises: a51305130893
Create Date: 2025-06-28 22:22:00.277878

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b589fad217b4"
down_revision = "a51305130893"
branch_labels = None
depends_on = None


def upgrade():
    # First, add the column as nullable
    op.add_column("category", sa.Column("color", sa.String(length=20), nullable=True))

    # Set default value for existing rows
    op.execute("UPDATE category SET color = '#6c757d' WHERE color IS NULL")

    # Now alter the column to be NOT NULL
    with op.batch_alter_table("category") as batch_op:
        batch_op.alter_column("color", nullable=False)


def downgrade():
    # Drop the color column
    with op.batch_alter_table("category") as batch_op:
        batch_op.drop_column("color")
