"""Expenses blueprint."""

from flask import Blueprint

from app import db

from .models import Category

bp = Blueprint("expenses", __name__)


def init_default_categories():
    """Initialize default expense categories if they don't exist."""
    default_categories = [
        {"name": "Food", "description": "General food expenses"},
        {"name": "Drinks", "description": "Beverages and drinks"},
        {"name": "Groceries", "description": "Grocery shopping"},
        {"name": "Dining Out", "description": "Restaurant and takeout"},
        {"name": "Transportation", "description": "Transportation costs"},
        {"name": "Utilities", "description": "Bills and utilities"},
        {"name": "Entertainment", "description": "Movies, events, etc."},
        {"name": "Other", "description": "Miscellaneous expenses"},
    ]

    for category_data in default_categories:
        if not Category.query.filter_by(name=category_data["name"]).first():
            category = Category(name=category_data["name"], description=category_data["description"])
            db.session.add(category)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e


# Import routes after blueprint creation to avoid circular imports
from . import routes  # noqa: E402
