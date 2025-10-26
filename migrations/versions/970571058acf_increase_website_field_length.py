"""increase_website_field_length

Revision ID: 970571058acf
Revises: d16deb28d5c0
Create Date: 2025-10-26 14:34:31.963920

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "970571058acf"
down_revision = "d16deb28d5c0"
branch_labels = None
depends_on = None


def upgrade():
    # Increase website field length from 200 to 500 characters
    with op.batch_alter_table("restaurant", schema=None) as batch_op:
        batch_op.alter_column(
            "website",
            existing_type=sa.String(length=200),
            type_=sa.String(length=500),
            existing_nullable=True,
            existing_comment="Restaurant website URL",
        )


def downgrade():
    # Revert website field length back to 200
    with op.batch_alter_table("restaurant", schema=None) as batch_op:
        batch_op.alter_column(
            "website",
            existing_type=sa.String(length=500),
            type_=sa.String(length=200),
            existing_nullable=True,
            existing_comment="Restaurant website URL",
        )
