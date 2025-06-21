"""Initial migration

Revision ID: 0001_initial_migration
Revises:
Create Date: 2025-06-20 23:30:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001_initial_migration"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create user table
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )

    # Create any other tables needed by your application
    # For example:
    # op.create_table('expense',
    #     sa.Column('id', sa.Integer(), nullable=False),
    #     sa.Column('user_id', sa.Integer(), nullable=False),
    #     sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
    #     sa.Column('description', sa.String(length=200), nullable=True),
    #     sa.Column('date', sa.Date(), nullable=False),
    #     sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    #     sa.PrimaryKeyConstraint('id')
    # )


def downgrade():
    # Drop tables in reverse order of creation
    # op.drop_table('expense')
    op.drop_table("user")
