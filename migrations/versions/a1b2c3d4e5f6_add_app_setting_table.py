"""Add app_setting table for global favicon config

Revision ID: a1b2c3d4e5f6
Revises: 2b7d4e1f9c3a
Create Date: 2026-03-07

"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "2b7d4e1f9c3a"
branch_labels = None
depends_on = None


def upgrade():
    # Use CURRENT_TIMESTAMP so migration works on both SQLite and PostgreSQL
    op.create_table(
        "app_setting",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Timestamp when the record was created",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="Timestamp when the record was last updated",
        ),
        sa.Column("key", sa.String(length=100), nullable=False, comment="Setting key"),
        sa.Column("value", sa.String(length=1000), nullable=True, comment="Setting value (JSON or string)"),
        sa.PrimaryKeyConstraint("id"),
        comment="Global app settings (favicon source, etc.)",
    )
    op.create_index(op.f("ix_app_setting_key"), "app_setting", ["key"], unique=True)


def downgrade():
    op.drop_index(op.f("ix_app_setting_key"), table_name="app_setting")
    op.drop_table("app_setting")
