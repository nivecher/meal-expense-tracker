"""add loyalty rewards tables

Revision ID: j1k2l3m4n5o6
Revises: i0j1k2l3m4n5
Create Date: 2026-03-08 22:35:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "j1k2l3m4n5o6"
down_revision = "i0j1k2l3m4n5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rewards_program",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("portal_url", sa.String(length=500), nullable=True),
        sa.Column("program_email", sa.String(length=120), nullable=True),
        sa.Column("program_phone", sa.String(length=30), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_rewards_program_user_name"),
        comment="User-owned rewards programs",
    )
    op.create_index(op.f("ix_rewards_program_name"), "rewards_program", ["name"], unique=False)
    op.create_index(op.f("ix_rewards_program_user_id"), "rewards_program", ["user_id"], unique=False)

    op.create_table(
        "rewards_account",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("rewards_program_id", sa.Integer(), nullable=False),
        sa.Column("membership_email", sa.String(length=120), nullable=True),
        sa.Column("membership_phone", sa.String(length=30), nullable=True),
        sa.Column("portal_username", sa.String(length=120), nullable=True),
        sa.Column("account_number", sa.String(length=120), nullable=True),
        sa.Column("tier_name", sa.String(length=120), nullable=True),
        sa.Column("points_balance", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False
        ),
        sa.ForeignKeyConstraint(["rewards_program_id"], ["rewards_program.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "rewards_program_id", name="uq_rewards_account_user_program"),
        comment="User account details for a rewards program",
    )
    op.create_index(
        op.f("ix_rewards_account_rewards_program_id"), "rewards_account", ["rewards_program_id"], unique=False
    )
    op.create_index(op.f("ix_rewards_account_user_id"), "rewards_account", ["user_id"], unique=False)

    op.create_table(
        "merchant_rewards_link",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("merchant_id", sa.Integer(), nullable=False),
        sa.Column("rewards_program_id", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False
        ),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchant.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rewards_program_id"], ["rewards_program.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "merchant_id", name="uq_merchant_rewards_link_user_merchant"),
        comment="User-scoped rewards program assignment for merchants",
    )
    op.create_index(
        op.f("ix_merchant_rewards_link_merchant_id"), "merchant_rewards_link", ["merchant_id"], unique=False
    )
    op.create_index(
        op.f("ix_merchant_rewards_link_rewards_program_id"),
        "merchant_rewards_link",
        ["rewards_program_id"],
        unique=False,
    )
    op.create_index(op.f("ix_merchant_rewards_link_user_id"), "merchant_rewards_link", ["user_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_merchant_rewards_link_user_id"), table_name="merchant_rewards_link")
    op.drop_index(op.f("ix_merchant_rewards_link_rewards_program_id"), table_name="merchant_rewards_link")
    op.drop_index(op.f("ix_merchant_rewards_link_merchant_id"), table_name="merchant_rewards_link")
    op.drop_table("merchant_rewards_link")

    op.drop_index(op.f("ix_rewards_account_user_id"), table_name="rewards_account")
    op.drop_index(op.f("ix_rewards_account_rewards_program_id"), table_name="rewards_account")
    op.drop_table("rewards_account")

    op.drop_index(op.f("ix_rewards_program_user_id"), table_name="rewards_program")
    op.drop_index(op.f("ix_rewards_program_name"), table_name="rewards_program")
    op.drop_table("rewards_program")
