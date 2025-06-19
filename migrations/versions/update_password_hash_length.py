"""Update password_hash length

Revision ID: 1234567890ab
Revises: 2cf4cf562dc8
Create Date: 2025-06-16 07:14:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1234567890ab"
down_revision = "2cf4cf562dc8"
branch_labels = None
depends_on = None


def upgrade():
    # Update password_hash column to VARCHAR(256)
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.VARCHAR(length=128),
            type_=sa.String(length=256),
            existing_nullable=True,
        )


def downgrade():
    # Revert back to VARCHAR(128)
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.alter_column(
            "password_hash",
            existing_type=sa.String(length=256),
            type_=sa.VARCHAR(length=128),
            existing_nullable=True,
        )
