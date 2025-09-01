"""Merge tag tables and other migrations

Revision ID: b1009dde6b51
Revises: add_tags_tables, b1560cab2cb8
Create Date: 2025-09-01 12:16:21.748113

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b1009dde6b51"
down_revision = ("add_tags_tables", "b1560cab2cb8")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
