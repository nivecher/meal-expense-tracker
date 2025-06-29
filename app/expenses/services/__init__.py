"""Service functions for expense-related operations."""

from datetime import datetime
from typing import Any, Dict, List, Tuple

from sqlalchemy import func, or_

from app import db
from app.expenses.models import Category, Expense


def _parse_date_filter(date_str: str) -> Any:
    """Parse a date string into a date object.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        datetime.date object if parsing succeeds, None otherwise
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _parse_numeric_filter(value: Any) -> Any:
    """Parse a numeric filter value into a float.

    Args:
        value: Value to parse

    Returns:
        float if parsing succeeds, None otherwise
    """
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _get_base_filters(args) -> Dict[str, Any]:
    """Extract base filter parameters from request args.

    Args:
        args: Request args

    Returns:
        Dictionary of raw filter values
    """
    return {
        "start_date": args.get("start_date", type=str),
        "end_date": args.get("end_date", type=str),
        "category_id": args.get("category_id", type=int),
        "min_amount": args.get("min_amount", type=float),
        "max_amount": args.get("max_amount", type=float),
        "search": args.get("search", type=str),
    }


def _process_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
    """Process and validate filter parameters.

    Args:
        filters: Dictionary of raw filter values

    Returns:
        Dictionary of processed filter values
    """
    processed = {}

    # Process date filters
    processed["start_date"] = _parse_date_filter(filters["start_date"])
    processed["end_date"] = _parse_date_filter(filters["end_date"])

    # Process numeric filters
    min_amount = _parse_numeric_filter(filters["min_amount"])
    max_amount = _parse_numeric_filter(filters["max_amount"])

    if min_amount is not None:
        processed["min_amount"] = min_amount
    if max_amount is not None:
        processed["max_amount"] = max_amount

    # Add other filters if they have values
    if filters.get("category_id"):
        processed["category_id"] = filters["category_id"]
    if filters.get("search"):
        processed["search"] = filters["search"]

    return processed


def _get_request_args(request_obj):
    """Extract request arguments from the request object.

    Args:
        request_obj: The Flask request object or request.args

    Returns:
        Request arguments
    """
    return request_obj.args if hasattr(request_obj, "args") else request_obj


def get_expense_filters(request_obj) -> Dict[str, Any]:
    """Extract and validate filter parameters from the request.

    This is a thin wrapper that coordinates the filter processing pipeline.

    Args:
        request_obj: The Flask request object or request.args

    Returns:
        Dictionary containing processed filter parameters
    """
    args = _get_request_args(request_obj)
    filters = _get_base_filters(args)
    return _process_filters(filters)


def get_user_expenses(user_id: int, filters: Dict[str, Any]) -> Tuple[List[Expense], float]:
    """Get expenses for a user with optional filtering.

    Args:
        user_id: ID of the user
        filters: Dictionary of filter parameters

    Returns:
        Tuple of (expenses, total_amount)
    """
    # Create base query
    query = Expense.query.filter_by(user_id=user_id)

    # Apply filters
    if filters.get("start_date") is not None:
        query = query.filter(Expense.date >= filters["start_date"])
    if filters.get("end_date") is not None:
        query = query.filter(Expense.date <= filters["end_date"])
    if "category_id" in filters:
        query = query.filter_by(category_id=filters["category_id"])
    if "min_amount" in filters:
        min_amount = (
            float(filters["min_amount"])
            if not isinstance(filters["min_amount"], (int, float))
            else filters["min_amount"]
        )
        query = query.filter(Expense.amount >= min_amount)
    if "max_amount" in filters:
        max_amount = (
            float(filters["max_amount"])
            if not isinstance(filters["max_amount"], (int, float))
            else filters["max_amount"]
        )
        query = query.filter(Expense.amount <= max_amount)
    if "search" in filters and filters["search"]:
        search = f"%{filters['search']}%"
        # Import Restaurant model here to avoid circular imports
        from app.restaurants.models import Restaurant

        # Create a subquery to find matching restaurant IDs
        matching_restaurant_ids = db.session.query(Restaurant.id).filter(Restaurant.name.ilike(search))

        # Then filter expenses where either notes match or restaurant_id is in the matching restaurants
        query = query.filter(or_(Expense.notes.ilike(search), Expense.restaurant_id.in_(matching_restaurant_ids)))

    # Get total amount - create a subquery and select the sum
    subq = query.subquery()
    total_amount = db.session.scalar(db.select(func.sum(subq.c.amount))) or 0.0
    total_amount = float(total_amount)

    # Get paginated expenses
    expenses = query.order_by(Expense.date.desc()).all()

    return expenses, total_amount


def get_filter_options(user_id: int) -> Dict[str, Any]:
    """Get options for filter dropdowns.

    Args:
        user_id: ID of the user

    Returns:
        Dictionary containing filter options
    """
    # Get categories for dropdown
    categories = Category.query.order_by(Category.name).all()
    # Get min and max dates for date range
    date_range = db.session.query(func.min(Expense.date), func.max(Expense.date)).filter_by(user_id=user_id).first()
    min_date, max_date = date_range if date_range else (None, None)

    return {
        "categories": categories,
        "min_date": min_date,
        "max_date": max_date,
    }
