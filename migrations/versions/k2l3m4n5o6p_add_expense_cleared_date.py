"""add expense cleared date

Revision ID: k2l3m4n5o6p
Revises: j1k2l3m4n5o6
Create Date: 2026-03-09 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "k2l3m4n5o6p"
down_revision = "j1k2l3m4n5o6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("expense", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "cleared_date",
                sa.Date(),
                nullable=True,
                comment="Optional cleared date used for financial reconciliation imports",
            )
        )
        batch_op.create_index(batch_op.f("ix_expense_cleared_date"), ["cleared_date"], unique=False)


def downgrade():
    with op.batch_alter_table("expense", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_expense_cleared_date"))
        batch_op.drop_column("cleared_date")
