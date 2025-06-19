"""
Service layer for main blueprint.

This module contains the business logic for the main blueprint,
separated from the route handlers for better organization and testability.
"""

from datetime import datetime
from typing import Any, Dict, List, Tuple

from flask import Request
from sqlalchemy.orm import Query

from app import db
from app.expenses.models import Expense
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


def get_user_expenses(
    user_id: int, filters: Dict[str, Any]
) -> Tuple[List[Expense], float]:
    """Get expenses for a user with the given filters.

    Args:
        user_id: The ID of the user
        filters: Dictionary of filter parameters

    Returns:
        Tuple of (expenses, total_amount)
    """
    # Base query
    query = Expense.query.filter_by(user_id=user_id)

    # Apply filters
    query = apply_filters(query, filters)

    # Apply sorting
    query = apply_sorting(query, filters["sort_by"], filters["sort_order"])

    # Execute query
    expenses = query.all()

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
        db.session.query(Expense.meal_type)
        .filter(Expense.user_id == user_id, Expense.meal_type != "")
        .distinct()
        .all()
    )

    categories = (
        db.session.query(Expense.category)
        .filter(Expense.user_id == user_id, Expense.category != "")
        .distinct()
        .all()
    )

    return {
        "meal_types": [m[0] for m in meal_types],
        "categories": [c[0] for c in categories],
    }


def apply_filters(query: Query, filters: Dict[str, Any]) -> Query:
    """Apply filters to the query.

    Args:
        query: The SQLAlchemy query
        filters: Dictionary of filter parameters

    Returns:
        The modified query with filters applied
    """
    if filters["search"]:
        query = query.join(Restaurant).filter(
            db.or_(
                Restaurant.name.ilike(f"%{filters['search']}%"),
                Restaurant.address.ilike(f"%{filters['search']}%"),
                Expense.notes.ilike(f"%{filters['search']}%"),
            )
        )

    if filters["meal_type"]:
        query = query.filter(Expense.meal_type == filters["meal_type"])

    if filters["category"]:
        query = query.filter(Expense.category == filters["category"])

    if filters["start_date"]:
        start_date = datetime.strptime(filters["start_date"], "%Y-%m-%d").date()
        query = query.filter(Expense.date >= start_date)

    if filters["end_date"]:
        end_date = datetime.strptime(filters["end_date"], "%Y-%m-%d").date()
        query = query.filter(Expense.date <= end_date)

    return query


def apply_sorting(query: Query, sort_by: str, sort_order: str) -> Query:
    """Apply sorting to the query.

    Args:
        query: The SQLAlchemy query
        sort_by: Field to sort by
        sort_order: Sort order ('asc' or 'desc')

    Returns:
        The modified query with sorting applied
    """
    sort_field = None

    if sort_by == "date":
        sort_field = Expense.date
    elif sort_by == "amount":
        sort_field = Expense.amount
    elif sort_by == "meal_type":
        sort_field = Expense.meal_type
    elif sort_by == "category":
        sort_field = Expense.category
    elif sort_by == "restaurant":
        return query.join(Restaurant).order_by(
            Restaurant.name.desc() if sort_order == "desc" else Restaurant.name.asc()
        )

    if sort_field:
        return query.order_by(
            sort_field.desc() if sort_order == "desc" else sort_field.asc()
        )

    return query
