"""
Main blueprint routes.

This module contains the route handlers for the main blueprint.
"""

from flask import render_template, request
from flask_login import current_user, login_required

from app import version
from . import bp
from .services import (
    get_expense_filters,
    get_user_expenses,
    get_filter_options,
)


@bp.route("/about")
@login_required
def about():
    """Render the about page.

    Returns:
        Rendered about page template
    """
    return render_template("main/about.html", app_version=version["app"])


@bp.route("/")
@login_required
def index():
    """Render the main index page with expense list and filters.

    Returns:
        Rendered index page template with expenses and filter options
    """
    # Get filter parameters from request
    filters = get_expense_filters(request)

    try:
        # Get expenses and total amount
        expenses, total_amount = get_user_expenses(current_user.id, filters)

        # Get filter options
        filter_options = get_filter_options(current_user.id)

        return render_template(
            "main/index.html",
            expenses=expenses,
            total_amount=total_amount,
            **filters,  # Pass all filter values to template
            **filter_options,  # Pass filter options
        )
    except Exception as e:
        # Log the error and show a user-friendly message
        from flask import current_app

        current_app.logger.error(f"Error loading expenses: {str(e)}")
        return (
            render_template(
                "errors/500.html",
                error=(
                    "An error occurred while loading expenses. "
                    "Please try again later."
                ),
            ),
            500,
        )
