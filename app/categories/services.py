"""Category-specific service functions."""

from app.expenses.models import Category
from app.extensions import db


def get_categories_for_user(user_id):
    """Get all categories for a given user."""
    return Category.query.filter_by(user_id=user_id).all()


def ensure_default_categories_for_user(user_id):
    """Ensure a baseline set of categories exist for the given user.

    Creates common defaults marked as is_default=True when they are missing.
    """
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

    existing = {c.name for c in Category.query.filter_by(user_id=user_id).all()}
    created_any = False
    for cat in default_categories:
        if cat["name"] not in existing:
            db.session.add(
                Category(
                    user_id=user_id,
                    name=cat["name"],
                    description=cat.get("description"),
                    is_default=True,
                )
            )
            created_any = True

    if created_any:
        db.session.commit()


def create_category_for_user(user_id, data):
    """Create a new category for a given user."""
    category = Category(user_id=user_id, **data)
    db.session.add(category)
    db.session.commit()
    return category


def get_category_by_id_for_user(category_id, user_id):
    """Get a single category by ID for a given user."""
    return Category.query.filter_by(id=category_id, user_id=user_id).first_or_404()


def update_category_for_user(category, data):
    """Update a category for a given user."""
    for key, value in data.items():
        setattr(category, key, value)
    db.session.commit()
    return category


def delete_category_for_user(category):
    """Delete a category for a given user."""
    db.session.delete(category)
    db.session.commit()
