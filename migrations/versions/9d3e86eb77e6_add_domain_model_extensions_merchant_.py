"""Add domain model extensions: Merchant, Visit, Receipt entities and extend Restaurant/Expense

Revision ID: 9d3e86eb77e6
Revises: c1d4a8f9e2b7
Create Date: 2026-02-21 17:04:33.739760

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "9d3e86eb77e6"
down_revision = "c1d4a8f9e2b7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "merchant",
        sa.Column("name", sa.String(length=100), nullable=False, comment="Name of the merchant/brand"),
        sa.Column(
            "category",
            sa.String(length=50),
            nullable=True,
            comment="Optional category classification (e.g., fast_food, casual_dining, coffee_shop)",
        ),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        comment="Restaurant brands and franchises",
    )
    with op.batch_alter_table("merchant", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_merchant_name"), ["name"], unique=False)
        batch_op.create_index(batch_op.f("ix_merchant_category"), ["category"], unique=False)

    op.create_table(
        "visit",
        sa.Column("restaurant_id", sa.Integer(), nullable=False, comment="Reference to the restaurant visited"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="Reference to the user who made this visit"),
        sa.Column(
            "datetime_start",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="When the visit started",
        ),
        sa.Column("datetime_end", sa.DateTime(timezone=True), nullable=True, comment="When the visit ended"),
        sa.Column(
            "visit_type",
            sa.String(length=20),
            nullable=True,
            comment="Type of visit (dine_in, pickup, delivery, drive_thru, unknown)",
        ),
        sa.Column("notes", sa.Text(), nullable=True, comment="Optional notes about the visit"),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
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
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurant.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        comment="Restaurant visits independent of spending",
    )
    with op.batch_alter_table("visit", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_visit_restaurant_id"), ["restaurant_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_visit_user_id"), ["user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_visit_datetime_start"), ["datetime_start"], unique=False)
        batch_op.create_index(batch_op.f("ix_visit_visit_type"), ["visit_type"], unique=False)

    op.create_table(
        "receipt",
        sa.Column("expense_id", sa.Integer(), nullable=True, comment="Optional link to an expense"),
        sa.Column("restaurant_id", sa.Integer(), nullable=True, comment="Optional link to a restaurant"),
        sa.Column("visit_id", sa.Integer(), nullable=True, comment="Optional link to a visit"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="Reference to the user who owns this receipt"),
        sa.Column("file_uri", sa.String(length=255), nullable=False, comment="S3 path to the receipt file"),
        sa.Column(
            "receipt_type",
            sa.String(length=20),
            nullable=True,
            comment="Type of receipt (paper, email, app, pdf, unknown)",
        ),
        sa.Column(
            "ocr_total", sa.Numeric(precision=10, scale=2), nullable=True, comment="Total amount extracted via OCR"
        ),
        sa.Column("ocr_tax", sa.Numeric(precision=10, scale=2), nullable=True, comment="Tax amount extracted via OCR"),
        sa.Column("ocr_tip", sa.Numeric(precision=10, scale=2), nullable=True, comment="Tip amount extracted via OCR"),
        sa.Column(
            "ocr_confidence",
            sa.Numeric(precision=5, scale=4),
            nullable=True,
            comment="Confidence score for OCR extraction",
        ),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
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
        sa.ForeignKeyConstraint(["expense_id"], ["expense.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["restaurant_id"], ["restaurant.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["visit_id"], ["visit.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        comment="Structured receipt data with OCR information",
    )
    with op.batch_alter_table("receipt", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_receipt_expense_id"), ["expense_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_receipt_restaurant_id"), ["restaurant_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_receipt_visit_id"), ["visit_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_receipt_user_id"), ["user_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_receipt_receipt_type"), ["receipt_type"], unique=False)

    with op.batch_alter_table("expense", schema=None) as batch_op:
        batch_op.add_column(sa.Column("visit_id", sa.Integer(), nullable=True, comment="Optional reference to a visit"))
        batch_op.create_index(batch_op.f("ix_expense_visit_id"), ["visit_id"], unique=False)
        batch_op.create_foreign_key("fk_expense_visit", "visit", ["visit_id"], ["id"], ondelete="SET NULL")

    with op.batch_alter_table("restaurant", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("merchant_id", sa.Integer(), nullable=True, comment="Optional reference to the merchant/brand")
        )
        batch_op.create_index(batch_op.f("ix_restaurant_merchant_id"), ["merchant_id"], unique=False)
        batch_op.create_foreign_key("fk_restaurant_merchant", "merchant", ["merchant_id"], ["id"], ondelete="SET NULL")

    # ### end Alembic commands ###
    # NOTE: For any new public tables, enable RLS and add policies here.


def downgrade():
    with op.batch_alter_table("restaurant", schema=None) as batch_op:
        batch_op.drop_constraint("fk_restaurant_merchant", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_restaurant_merchant_id"))
        batch_op.drop_column("merchant_id")

    with op.batch_alter_table("expense", schema=None) as batch_op:
        batch_op.drop_constraint("fk_expense_visit", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_expense_visit_id"))
        batch_op.drop_column("visit_id")

    with op.batch_alter_table("receipt", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_receipt_receipt_type"))
        batch_op.drop_index(batch_op.f("ix_receipt_user_id"))
        batch_op.drop_index(batch_op.f("ix_receipt_visit_id"))
        batch_op.drop_index(batch_op.f("ix_receipt_restaurant_id"))
        batch_op.drop_index(batch_op.f("ix_receipt_expense_id"))
    op.drop_table("receipt")

    with op.batch_alter_table("visit", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_visit_visit_type"))
        batch_op.drop_index(batch_op.f("ix_visit_datetime_start"))
        batch_op.drop_index(batch_op.f("ix_visit_user_id"))
        batch_op.drop_index(batch_op.f("ix_visit_restaurant_id"))
    op.drop_table("visit")

    with op.batch_alter_table("merchant", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_merchant_category"))
        batch_op.drop_index(batch_op.f("ix_merchant_name"))
    op.drop_table("merchant")
