"""
Main blueprint routes.

This module contains the route handlers for the main blueprint.
"""

import logging

from flask import render_template, request
from flask_login import current_user, login_required

from app import version
from app.expenses.services import (
    get_expense_filters,
    get_filter_options,
    get_user_expenses,
)

from . import bp

# HTTP exceptions are used in error handlers below


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
    logger = logging.getLogger(__name__)
    logger.info("Index route accessed by user: %s", current_user.id)

    try:
        # Debug: Log request args
        logger.debug("Request args: %s", dict(request.args))

        # Get filter parameters from request
        filters = get_expense_filters(request)
        logger.debug("Parsed filters: %s", filters)

        # Get expenses and total amount
        expenses, total_amount = get_user_expenses(current_user.id, filters)
        logger.debug("Retrieved %d expenses", len(expenses) if expenses else 0)

        # Get filter options
        filter_options = get_filter_options(current_user.id)
        logger.debug(
            "Retrieved filter options: %s",
            {
                "categories": len(filter_options.get("categories", [])),
                "meal_types": len(filter_options.get("meal_types", [])),
            },
        )

        # Prepare template variables
        template_vars = {
            "expenses": expenses or [],
            "total_amount": total_amount or 0.0,
            "search": request.args.get("search", ""),
            "meal_type": request.args.get("meal_type", ""),
            "category": request.args.get("category", ""),
            "start_date": request.args.get("start_date", ""),
            "end_date": request.args.get("end_date", ""),
            "sort_by": request.args.get("sort", "date"),
            "sort_order": request.args.get("order", "desc"),
            "meal_types": filter_options.get("meal_types", []),
            "categories": filter_options.get("categories", []),
            "request": request,  # Make request available in template
        }

        logger.debug("Rendering template with variables: %s", {k: type(v).__name__ for k, v in template_vars.items()})

        return render_template("main/index.html", **template_vars)

    except Exception:
        logger.exception("Error in index route")
        return (
            render_template(
                "errors/500.html",
                error="An error occurred while loading expenses. Please try again later.",
            ),
            500,
        )


@bp.app_errorhandler(404)
def not_found_error(error):
    """Handle 404 errors.

    Args:
        error: The error that was raised
    Returns:
        Rendered 404 error template
    """
    return render_template("errors/404.html"), 404


@bp.app_errorhandler(500)
def internal_error(error):
    """Handle 500 errors.
    Args:
        error: The error that was raised
    Returns:
        Rendered 500 error template
    """
    return render_template("errors/500.html", error=str(error)), 500
