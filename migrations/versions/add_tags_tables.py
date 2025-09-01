"""Add tag and expense_tag tables for custom expense labels

Revision ID: add_tags_tables
Revises: 9b7f3c7b97be
Create Date: 2025-09-01 11:55:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "add_tags_tables"
down_revision = "9b7f3c7b97be"
branch_labels = None
depends_on = None


def upgrade():
    # Create tag table
    op.create_table(
        "tag",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "name", sa.String(length=50), nullable=False, comment="Name of the tag (unique per user, Jira-style)"
        ),
        sa.Column(
            "color", sa.String(length=20), nullable=False, comment="Hex color code for the tag badge (e.g., #6c757d)"
        ),
        sa.Column("description", sa.Text(), nullable=True, comment="Description of the tag"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="Reference to the user who owns this tag"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
            comment="Timestamp when the record was created",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
            comment="Timestamp when the record was last updated",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "user_id", name="uix_tag_name_user"),
        comment="Custom tags for organizing expenses",
    )

    # Create indexes for tag table
    with op.batch_alter_table("tag", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_tag_name"), ["name"], unique=False)
        batch_op.create_index(batch_op.f("ix_tag_user_id"), ["user_id"], unique=False)

    # Create expense_tag association table
    op.create_table(
        "expense_tag",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("expense_id", sa.Integer(), nullable=False, comment="Reference to the expense"),
        sa.Column("tag_id", sa.Integer(), nullable=False, comment="Reference to the tag"),
        sa.Column("added_by", sa.Integer(), nullable=False, comment="User who added this tag to the expense"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
            comment="Timestamp when the record was created",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
            comment="Timestamp when the record was last updated",
        ),
        sa.ForeignKeyConstraint(["expense_id"], ["expense.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tag.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["added_by"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("expense_id", "tag_id", name="uix_expense_tag"),
        comment="Association table for expense-tag relationships",
    )

    # Create indexes for expense_tag table
    with op.batch_alter_table("expense_tag", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_expense_tag_expense_id"), ["expense_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_expense_tag_tag_id"), ["tag_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_expense_tag_added_by"), ["added_by"], unique=False)


def downgrade():
    # Drop expense_tag table first (due to foreign key constraints)
    with op.batch_alter_table("expense_tag", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_expense_tag_added_by"))
        batch_op.drop_index(batch_op.f("ix_expense_tag_tag_id"))
        batch_op.drop_index(batch_op.f("ix_expense_tag_expense_id"))

    op.drop_table("expense_tag")

    # Drop tag table
    with op.batch_alter_table("tag", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_tag_user_id"))
        batch_op.drop_index(batch_op.f("ix_tag_name"))

    op.drop_table("tag")
