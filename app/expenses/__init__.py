from flask import Blueprint

from app.extensions import db
from app.expenses.category import Category

bp = Blueprint("expenses", __name__, url_prefix="/expenses")


def init_default_categories():
    """Initialize default expense categories if they don't exist."""
    default_categories = [
        ("Dining", "Restaurant meals, takeout, coffee shops"),
        ("Groceries", "Grocery store purchases"),
        ("Entertainment", "Movies, concerts, events"),
        ("Transportation", "Public transit, taxis, rideshares"),
        ("Travel", "Hotels, flights, vacation expenses"),
        ("Utilities", "Bills and utilities"),
        ("Shopping", "Retail and online shopping"),
        ("Other", "Miscellaneous expenses"),
    ]

    for name, description in default_categories:
        if not Category.query.filter_by(name=name).first():
            category = Category(name=name, description=description)
            db.session.add(category)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error initializing default categories: {e}")


from app.expenses import routes  # noqa: E402
