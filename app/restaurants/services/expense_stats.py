"""Service functions for calculating restaurant expense statistics."""

from typing import Any, Dict

from sqlalchemy import func, select

from app.expenses.models import Expense
from app.extensions import db


def calculate_expense_stats(restaurant_id: int, user_id: int) -> Dict[str, Any]:
    """Calculate expense statistics for a restaurant.

    Args:
        restaurant_id: The ID of the restaurant
        user_id: The ID of the user (for security)

    Returns:
        Dictionary containing expense statistics with the following keys:
        - visit_count: int - Number of visits to the restaurant
        - total_amount: float - Total amount spent at the restaurant
        - avg_per_visit: float - Average amount spent per visit
        - last_visit: Optional[datetime] - Date of the last visit, or None if no visits
    """
    stats = db.session.execute(
        select(
            func.count(Expense.id).label("visit_count"),
            func.sum(Expense.amount).label("total_amount"),
            func.max(Expense.date).label("last_visit"),
        ).where(Expense.restaurant_id == restaurant_id, Expense.user_id == user_id)
    ).first()

    avg_per_visit = 0.0
    if stats and stats.visit_count > 0 and stats.total_amount is not None:
        avg_per_visit = float(stats.total_amount) / stats.visit_count

    return {
        "visit_count": stats.visit_count if stats else 0,
        "total_amount": float(stats.total_amount) if stats and stats.total_amount else 0.0,
        "avg_per_visit": avg_per_visit,
        "last_visit": stats.last_visit if stats else None,
    }
