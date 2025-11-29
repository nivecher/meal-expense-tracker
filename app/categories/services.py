"""Category-specific service functions."""

from flask import abort
from sqlalchemy import select

from app.expenses.models import Category
from app.extensions import db


def get_categories_for_user(user_id: int) -> list[Category]:
    """Get all categories for a given user."""
    stmt = select(Category).filter_by(user_id=user_id)
    return list(db.session.scalars(stmt).all())


def ensure_default_categories_for_user(user_id: int) -> None:
    """Ensure a baseline set of categories exist for the given user.

    Creates common defaults marked as is_default=True when they are missing.
    """
    from app.constants.categories import get_default_categories

    default_categories = get_default_categories()
    existing = {c.name for c in Category.query.filter_by(user_id=user_id).all()}
    created_any = False

    for cat in default_categories:
        if cat["name"] not in existing:
            db.session.add(
                Category(
                    user_id=user_id,
                    name=cat["name"],
                    description=cat.get("description"),
                    color=cat.get("color"),
                    icon=cat.get("icon"),
                    is_default=True,
                )
            )
            created_any = True

    if created_any:
        db.session.commit()


def create_category_for_user(user_id: int, data: dict) -> Category:
    """Create a new category for a given user."""
    category = Category(user_id=user_id, **data)
    db.session.add(category)
    db.session.commit()
    return category


def get_category_by_id_for_user(category_id: int, user_id: int) -> Category:
    """Get a single category by ID for a given user."""

    stmt = select(Category).filter_by(id=category_id, user_id=user_id)
    category = db.session.scalar(stmt)
    if category is None:
        abort(404, "Category not found")
    return category


def update_category_for_user(category: Category, data: dict) -> Category:
    """Update a category for a given user."""
    for key, value in data.items():
        setattr(category, key, value)
    db.session.commit()
    return category


def delete_category_for_user(category: Category) -> None:
    """Delete a category for a given user."""
    db.session.delete(category)
    db.session.commit()
