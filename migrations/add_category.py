"""Add category field to Expense model

Revision ID: add_category
Revises: 
Create Date: 2024-03-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_category'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add category column to expense table
    op.add_column('expense', sa.Column('category', sa.String(50), nullable=True))

def downgrade():
    # Remove category column from expense table
    op.drop_column('expense', 'category') 