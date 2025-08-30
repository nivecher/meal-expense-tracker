"""
Service layer for main blueprint.

This module contains the business logic for the main blueprint,
separated from the route handlers for better organization and testability.
"""

from datetime import datetime
from typing import Any, Dict, List, Tuple

from flask import Request
from sqlalchemy import or_, select

from app.expenses.models import Category, Expense
from app.extensions import db
from app.restaurants.models import Restaurant


def get_expense_filters(request: Request) -> Dict[str, Any]:
    """Extract and validate filter parameters from the request.

    Args:
        request: The Flask request object

    Returns:
        Dict containing filter parameters
    """
    return {
        "search": request.args.get("search", "").strip(),
        "meal_type": request.args.get("meal_type", "").strip(),
        "category": request.args.get("category", "").strip(),
        "start_date": request.args.get("start_date", "").strip(),
        "end_date": request.args.get("end_date", "").strip(),
        "sort_by": request.args.get("sort", "date"),
        "sort_order": request.args.get("order", "desc"),
    }


def get_user_expenses(user_id: int, filters: Dict[str, Any]) -> Tuple[List[Expense], float]:
    """Get expenses for a user with the given filters.

    Args:
        user_id: The ID of the user
        filters: Dictionary of filter parameters

    Returns:
        Tuple of (expenses, total_amount)
    """
    # Base query
    stmt = select(Expense).where(Expense.user_id == user_id)

    # Apply filters
    stmt = apply_filters(stmt, filters)

    # Apply sorting
    stmt = apply_sorting(stmt, filters["sort_by"], filters["sort_order"])

    # Execute query
    result = db.session.execute(stmt)
    expenses = result.scalars().all()

    # Calculate total
    total_amount = sum(expense.amount for expense in expenses) if expenses else 0.0

    return expenses, total_amount


def get_filter_options(user_id: int) -> Dict[str, List[str]]:
    """Get filter options (meal types and categories) for the current user.

    Args:
        user_id: The ID of the user

    Returns:
        Dictionary containing filter options
    """
    # Get unique meal types and categories for filter dropdowns
    meal_types = (
        db.session.query(Expense.meal_type).filter(Expense.user_id == user_id, Expense.meal_type != "").distinct().all()
    )

    # Get unique categories through the relationship
    categories = (
        db.session.query(Category.name)
        .join(Expense, Expense.category_id == Category.id)
        .filter(Expense.user_id == user_id)
        .distinct()
        .all()
    )

    return {
        "meal_types": [m[0] for m in meal_types if m[0]],  # Filter out None values
        "categories": [c[0] for c in categories if c[0]],  # Filter out None values
    }


def apply_filters(stmt, filters: Dict[str, Any]):
    """Apply filters to the query with comprehensive search across text fields.

    Args:
        stmt: The SQLAlchemy select statement
        filters: Dictionary of filter parameters

    Returns:
        The modified select statement with filters applied
    """
    # Always join restaurant and category tables for search (using outer joins to include expenses without these)
    stmt = stmt.join(Expense.restaurant, isouter=True)
    stmt = stmt.join(Expense.category, isouter=True)
    # Apply search filter across all text-based fields
    if filters["search"]:
        search_term = f"%{filters['search']}%"
        stmt = stmt.where(
            or_(
                # Restaurant fields
                Restaurant.name.ilike(search_term),
                Restaurant.address.ilike(search_term),
                # Expense fields
                Expense.notes.ilike(search_term),
                Expense.meal_type.ilike(search_term),
                # Category fields
                Category.name.ilike(search_term),
            )
        )

    # Apply meal type filter
    if filters["meal_type"]:
        stmt = stmt.where(Expense.meal_type == filters["meal_type"])

    # Apply category filter
    if filters["category"]:
        stmt = stmt.where(Category.name == filters["category"])

    # Apply date range filters with proper error handling
    if filters["start_date"]:
        try:
            start_date = datetime.strptime(filters["start_date"], "%Y-%m-%d").date()
            stmt = stmt.where(Expense.date >= start_date)
        except (ValueError, TypeError):
            # Log the error but don't fail the query
            pass

    if filters["end_date"]:
        try:
            end_date = datetime.strptime(filters["end_date"], "%Y-%m-%d").date()
            stmt = stmt.where(Expense.date <= end_date)
        except (ValueError, TypeError):
            # Log the error but don't fail the query
            pass

    return stmt


def apply_sorting(stmt, sort_by: str, sort_order: str):
    """Apply sorting to the query.

    Args:
        stmt: The SQLAlchemy select statement
        sort_by: Field to sort by
        sort_order: Sort order ('asc' or 'desc')

    Returns:
        The modified select statement with sorting applied
    """
    sort_field = None
    is_desc = sort_order.lower() == "desc"

    if sort_by == "date":
        sort_field = Expense.date
    elif sort_by == "amount":
        sort_field = Expense.amount
    elif sort_by == "meal_type":
        sort_field = Expense.meal_type
    elif sort_by == "category":
        # Sort by category name through the relationship
        stmt = stmt.join(Expense.category)
        sort_field = Category.name
    elif sort_by == "restaurant":
        return stmt.order_by(Restaurant.name.desc() if is_desc else Restaurant.name.asc())

    if sort_field:
        return stmt.order_by(sort_field.desc() if is_desc else sort_field.asc())

    return stmt
