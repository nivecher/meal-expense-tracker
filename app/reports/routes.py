"""Report-related routes for the application."""

from flask import render_template
from flask_login import current_user, login_required

from app.api.services import get_expenses_for_user, get_restaurants_for_user
from app.reports import bp


@bp.route("/")
@login_required
def index():
    """Show the reports dashboard."""
    expenses = get_expenses_for_user(current_user.id)
    restaurants = get_restaurants_for_user(current_user.id)
    return render_template("reports/index.html", expenses=expenses, restaurants=restaurants)


@bp.route("/expenses")
@login_required
def expense_report():
    """Generate an expense report."""
    return render_template("reports/expense_report.html")


@bp.route("/restaurants")
@login_required
def restaurant_report():
    """Generate a restaurant report."""
    return render_template("reports/restaurant_report.html")


@bp.route("/analytics")
@login_required
def analytics():
    """Show analytics dashboard."""
    return render_template("reports/analytics.html")
