"""Add address and category fields to Restaurant model

Revision ID: add_restaurant_fields
Revises: add_category
Create Date: 2024-03-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_restaurant_fields'
down_revision = 'add_category'
branch_labels = None
depends_on = None

def upgrade():
    # Add address and category columns to restaurant table
    op.add_column('restaurant', sa.Column('address', sa.String(200), nullable=True))
    op.add_column('restaurant', sa.Column('category', sa.String(50), nullable=True))

def downgrade():
    # Remove address and category columns from restaurant table
    op.drop_column('restaurant', 'address')
    op.drop_column('restaurant', 'category') 