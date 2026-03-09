"""drop restaurant is_chain column

Revision ID: i0j1k2l3m4n5
Revises: h9i0j1k2l3m4
Create Date: 2026-03-08 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "i0j1k2l3m4n5"
down_revision = "h9i0j1k2l3m4"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("restaurant", schema=None) as batch_op:
        batch_op.drop_column("is_chain")


def downgrade():
    with op.batch_alter_table("restaurant", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_chain",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
                comment="Whether it's a chain restaurant",
            )
        )
