"""Report-related routes for the application."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List

from flask import render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func

from app.expenses import services as expense_services
from app.expenses.models import Expense
from app.extensions import db
from app.reports import bp
from app.restaurants import services as restaurant_services
from app.restaurants.models import Restaurant


@bp.route("/")
@login_required
def index() -> str:
    """Show the reports dashboard with statistics."""
    # Get date range from query parameters with validation
    try:
        days = int(request.args.get("days", 30))
        # Validate days is within reasonable range
        if days < 1 or days > 3650:  # Max 10 years
            days = 30
    except (ValueError, TypeError):
        days = 30

    start_date = datetime.now() - timedelta(days=days)

    # Get expenses and restaurants
    expenses = expense_services.get_expenses_for_user(current_user.id, start_date=start_date)
    restaurants = restaurant_services.get_restaurants_for_user(current_user.id)

    # Calculate dashboard statistics
    dashboard_stats = _calculate_dashboard_stats(expenses, restaurants, days)

    return render_template(
        "reports/index.html",
        expenses=expenses,
        restaurants=restaurants,
        dashboard_stats=dashboard_stats,
        days=days,
    )


@bp.route("/expenses")
@login_required
def expense_report() -> str:
    """Generate an expense report with data."""
    # Get date range from query parameters
    days = int(request.args.get("days", 30))
    start_date = datetime.now() - timedelta(days=days)

    # Get expenses for the date range
    expenses = expense_services.get_expenses_for_user(current_user.id, start_date=start_date)

    # Calculate statistics
    total_amount = float(sum(expense.amount for expense in expenses))
    avg_amount = total_amount / len(expenses) if expenses else 0

    # Group by category
    category_stats: dict[str, dict[str, int | Decimal]] = {}
    for expense in expenses:
        category_name = expense.category.name if expense.category else "Uncategorized"
        if category_name not in category_stats:
            category_stats[category_name] = {"count": 0, "total": Decimal(0)}
        category_stats[category_name]["count"] = int(category_stats[category_name]["count"]) + 1
        category_stats[category_name]["total"] = Decimal(category_stats[category_name]["total"]) + expense.amount

    return render_template(
        "reports/expense_report.html",
        expenses=expenses,
        total_amount=total_amount,
        avg_amount=avg_amount,
        category_stats=category_stats,
        days=days,
    )


@bp.route("/restaurants")
@login_required
def restaurant_report() -> str:
    """Generate a restaurant report with data."""
    restaurants = restaurant_services.get_restaurants_for_user(current_user.id)

    # Get expense counts per restaurant
    restaurant_stats = {}
    for restaurant in restaurants:
        expense_count = (
            db.session.query(func.count(Expense.id))
            .filter(Expense.restaurant_id == restaurant.id, Expense.user_id == current_user.id)
            .scalar()
        )

        total_spent = (
            db.session.query(func.sum(Expense.amount))
            .filter(Expense.restaurant_id == restaurant.id, Expense.user_id == current_user.id)
            .scalar()
            or 0
        )

        restaurant_stats[restaurant.id] = {
            "count": expense_count or 0,
            "total": float(total_spent) if total_spent else 0.0,
        }

    return render_template("reports/restaurant_report.html", restaurants=restaurants, restaurant_stats=restaurant_stats)


@bp.route("/analytics")
@login_required
def analytics() -> str:
    """Show analytics dashboard with data."""
    # Get date range
    days = int(request.args.get("days", 30))
    start_date = datetime.now() - timedelta(days=days)

    # Get expenses for analytics
    expenses = expense_services.get_expenses_for_user(current_user.id, start_date=start_date)

    # Calculate analytics data
    analytics_data = _calculate_analytics_data(expenses, days)

    return render_template("reports/analytics.html", analytics_data=analytics_data, days=days)


@bp.route("/expense-statistics")
@login_required
def expense_statistics() -> str:
    """Show expense statistics page."""
    # Get date range with validation
    try:
        days = int(request.args.get("days", 30))
        # Validate days is within reasonable range
        if days < 1 or days > 3650:  # Max 10 years
            days = 30
    except (ValueError, TypeError):
        days = 30

    start_date = datetime.now() - timedelta(days=days)

    # Get expenses
    expenses = expense_services.get_expenses_for_user(current_user.id, start_date=start_date)

    # Calculate statistics for template
    total_spent = sum(expense.amount for expense in expenses) if expenses else 0.0
    total_spending = total_spent  # Alias for template

    # Category spending as list of tuples (name, amount)
    category_stats = _calculate_category_stats(expenses)
    category_spending = [
        (name, data["total"])
        for name, data in sorted(category_stats.items(), key=lambda x: x[1]["total"], reverse=True)
    ]

    # Top expenses (sorted by amount, limit to 10)
    top_expenses = sorted(expenses, key=lambda x: x.amount, reverse=True)[:10] if expenses else []

    # Chart data for monthly trends
    monthly_data = _calculate_monthly_data(expenses)
    chart_labels = sorted(monthly_data.keys())
    chart_data_values = [monthly_data[month] for month in chart_labels]
    chart_data = {"labels": chart_labels, "data": chart_data_values}

    return render_template(
        "expenses/stats.html",
        days=days,
        total_spent=total_spent,
        total_spending=total_spending,
        category_spending=category_spending,
        top_expenses=top_expenses,
        chart_data=chart_data,
    )


def _calculate_analytics_data(expenses: list[Expense], days: int) -> dict[str, Any]:
    """Calculate analytics data for charts and insights."""
    if not expenses:
        return {
            "total_spent": 0,
            "avg_per_expense": 0,
            "expense_count": 0,
            "category_breakdown": {},
            "monthly_trends": {},
            "top_restaurants": {},
            "meal_type_breakdown": {},
        }

    total_spent = sum(expense.amount for expense in expenses)
    avg_per_expense = total_spent / len(expenses)

    # Category breakdown
    category_breakdown: dict[str, Decimal] = {}
    for expense in expenses:
        category_name = expense.category.name if expense.category else "Uncategorized"
        if category_name not in category_breakdown:
            category_breakdown[category_name] = Decimal(0)
        category_breakdown[category_name] += expense.amount

    # Monthly trends (last 6 months)
    monthly_trends: dict[str, float] = {}
    for i in range(6):
        month_start = datetime.now().replace(day=1) - timedelta(days=30 * i)
        month_end = month_start + timedelta(days=30)

        month_expenses = [e for e in expenses if month_start <= e.date <= month_end]
        month_total = sum(e.amount for e in month_expenses)

        month_key = month_start.strftime("%Y-%m")
        monthly_trends[month_key] = float(month_total)

    # Top restaurants
    restaurant_totals: dict[str, Decimal] = {}
    for expense in expenses:
        if expense.restaurant:
            restaurant_name = expense.restaurant.name
            if restaurant_name not in restaurant_totals:
                restaurant_totals[restaurant_name] = Decimal(0)
            restaurant_totals[restaurant_name] += expense.amount

    top_restaurants = dict[str, Decimal](sorted(restaurant_totals.items(), key=lambda x: x[1], reverse=True)[:5])

    # Meal type breakdown
    meal_type_breakdown: dict[str, Decimal] = {}
    for expense in expenses:
        meal_type = expense.meal_type or "Unknown"
        if meal_type not in meal_type_breakdown:
            meal_type_breakdown[meal_type] = Decimal(0)
        meal_type_breakdown[meal_type] += expense.amount

    return {
        "total_spent": float(total_spent),
        "avg_per_expense": float(avg_per_expense),
        "expense_count": len(expenses),
        "category_breakdown": category_breakdown,
        "monthly_trends": monthly_trends,
        "top_restaurants": top_restaurants,
        "meal_type_breakdown": meal_type_breakdown,
    }


def _calculate_comprehensive_stats(expenses: list[Expense], days: int) -> dict[str, Any]:
    """Calculate comprehensive statistics for the stats page."""
    if not expenses:
        return _get_empty_stats()

    total_spent = sum(expense.amount for expense in expenses)
    avg_per_expense = total_spent / len(expenses)
    avg_per_day = total_spent / days if days > 0 else 0

    category_stats = _calculate_category_stats(expenses)
    restaurant_stats = _calculate_restaurant_stats(expenses)
    monthly_data = _calculate_monthly_data(expenses)
    meal_type_stats = _calculate_meal_type_stats(expenses)

    return {
        "summary": {
            "total_expenses": len(expenses),
            "total_spent": float(total_spent),
            "avg_per_expense": float(avg_per_expense),
            "avg_per_day": float(avg_per_day),
        },
        "category_stats": _format_stats_list(category_stats),
        "restaurant_stats": _format_stats_list(restaurant_stats)[:10],
        "monthly_data": _format_monthly_data(monthly_data),
        "meal_type_stats": _format_stats_list(meal_type_stats),
    }


def _get_empty_stats() -> dict[str, Any]:
    """Return empty stats structure."""
    return {
        "summary": {"total_expenses": 0, "total_spent": 0, "avg_per_expense": 0, "avg_per_day": 0},
        "category_stats": [],
        "restaurant_stats": [],
        "monthly_data": [],
        "meal_type_stats": [],
    }


def _calculate_category_stats(expenses: list[Expense]) -> dict[str, Any]:
    """Calculate category statistics."""
    category_stats: dict[str, dict[str, int | Decimal]] = {}
    for expense in expenses:
        category_name = expense.category.name if expense.category else "Uncategorized"
        if category_name not in category_stats:
            category_stats[category_name] = {"count": 0, "total": Decimal(0)}
        count_val: int | Decimal = category_stats[category_name]["count"]
        total_val: int | Decimal = category_stats[category_name]["total"]
        category_stats[category_name]["count"] = int(count_val) + 1
        category_stats[category_name]["total"] = Decimal(str(total_val)) + expense.amount
    return category_stats


def _calculate_restaurant_stats(expenses: list[Expense]) -> dict[str, Any]:
    """Calculate restaurant statistics."""
    restaurant_stats: dict[str, dict[str, int | Decimal]] = {}
    for expense in expenses:
        if expense.restaurant:
            restaurant_name = expense.restaurant.name
            if restaurant_name not in restaurant_stats:
                restaurant_stats[restaurant_name] = {"count": 0, "total": Decimal(0)}
            count_val: int | Decimal = restaurant_stats[restaurant_name]["count"]
            total_val: int | Decimal = restaurant_stats[restaurant_name]["total"]
            restaurant_stats[restaurant_name]["count"] = int(count_val) + 1
            restaurant_stats[restaurant_name]["total"] = Decimal(str(total_val)) + expense.amount
    return restaurant_stats


def _calculate_monthly_data(expenses: list[Expense]) -> dict[str, Any]:
    """Calculate monthly data for charts."""
    monthly_data: dict[str, Decimal] = {}
    for expense in expenses:
        month_key = expense.date.strftime("%Y-%m")
        if month_key not in monthly_data:
            monthly_data[month_key] = Decimal(0)
        monthly_data[month_key] += expense.amount
    return monthly_data


def _calculate_meal_type_stats(expenses: list[Expense]) -> dict[str, Any]:
    """Calculate meal type statistics."""
    meal_type_stats: dict[str, dict[str, int | Decimal]] = {}
    for expense in expenses:
        meal_type = expense.meal_type or "Unknown"
        if meal_type not in meal_type_stats:
            meal_type_stats[meal_type] = {"count": 0, "total": Decimal(0)}
        count_val: int | Decimal = meal_type_stats[meal_type]["count"]
        total_val: int | Decimal = meal_type_stats[meal_type]["total"]
        meal_type_stats[meal_type]["count"] = int(count_val) + 1
        meal_type_stats[meal_type]["total"] = Decimal(str(total_val)) + expense.amount
    return meal_type_stats


def _format_stats_list(stats_dict: dict[str, Any]) -> list[dict[str, Any]]:
    """Format statistics dictionary into sorted list."""
    return [
        {"name": name, "count": data["count"], "total": float(data["total"])}
        for name, data in sorted(stats_dict.items(), key=lambda x: x[1]["total"], reverse=True)
    ]


def _format_monthly_data(monthly_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Format monthly data into sorted list."""
    return [{"month": month, "total": float(total)} for month, total in sorted(monthly_data.items())]


def _calculate_dashboard_stats(expenses: list[Expense], restaurants: list[Restaurant], days: int) -> dict[str, Any]:
    """Calculate dashboard statistics.

    Args:
        expenses: List of expense objects
        restaurants: List of restaurant objects
        days: Number of days in the date range

    Returns:
        Dictionary with dashboard statistics
    """
    total_expenses = len(expenses)
    total_restaurants = len(restaurants)

    # Calculate expense totals
    total_spent = sum(expense.amount for expense in expenses) if expenses else 0.0
    avg_per_expense = total_spent / total_expenses if total_expenses > 0 else 0.0
    avg_per_day = total_spent / days if days > 0 else 0.0

    # Top categories
    category_totals: dict[str, Decimal] = {}
    for expense in expenses:
        category_name = expense.category.name if expense.category else "Uncategorized"
        if category_name not in category_totals:
            category_totals[category_name] = Decimal(0)
        category_totals[category_name] += expense.amount

    top_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:5]

    # Top restaurants by expense count
    restaurant_counts: dict[str, int] = {}
    for expense in expenses:
        if expense.restaurant:
            restaurant_name = expense.restaurant.name
            if restaurant_name not in restaurant_counts:
                restaurant_counts[restaurant_name] = 0
            restaurant_counts[restaurant_name] += 1

    top_restaurants = sorted(restaurant_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "summary": {
            "total_expenses": total_expenses,
            "total_restaurants": total_restaurants,
            "total_spent": float(total_spent),
            "avg_per_expense": float(avg_per_expense),
            "avg_per_day": float(avg_per_day),
        },
        "top_categories": [{"name": name, "total": float(total)} for name, total in top_categories],
        "top_restaurants": [{"name": name, "count": count} for name, count in top_restaurants],
    }
