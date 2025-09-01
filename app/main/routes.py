"""
Main blueprint routes.

This module contains the route handlers for the main blueprint.
"""

import os
from datetime import datetime

from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func, select

from app.expenses.models import Expense
from app.extensions import db
from app.restaurants.models import Restaurant

from . import bp


@bp.route("/favicon.ico")
def favicon():
    """Serve the favicon.ico file.

    Returns:
        The favicon.ico file
    """
    return send_from_directory(
        os.path.join(current_app.root_path, "static/img/favicons"),
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@bp.route("/about")
def about():
    """Render the about page with version information.

    Returns:
        Rendered about page template with version data
    """
    from app._version import __version__

    return render_template("main/about.html", app_version=__version__)


@bp.route("/help")
def help_page():
    """Render the comprehensive help page.

    Returns:
        Rendered help page template with all feature information
    """
    # Import all the constants for displaying options
    from app.constants.categories import get_default_categories
    from app.constants.cuisines import get_cuisine_color, get_cuisine_constants
    from app.constants.meal_types import get_meal_type_constants

    # Get cuisine constants but override colors with centralized Bootstrap colors
    cuisines = get_cuisine_constants()
    for cuisine in cuisines:
        cuisine["color"] = get_cuisine_color(cuisine["name"])

    return render_template(
        "main/help.html", meal_types=get_meal_type_constants(), cuisines=cuisines, categories=get_default_categories()
    )


@bp.route("/terms")
def terms():
    """Render the terms of service page.

    Returns:
        Rendered terms of service template with current datetime
    """
    return render_template("main/terms.html", now=datetime.utcnow())


@bp.route("/privacy")
def privacy():
    """Render the privacy policy page.

    Returns:
        Rendered privacy policy template with current datetime
    """
    return render_template("main/privacy.html", now=datetime.utcnow())


@bp.route("/contact", methods=["GET", "POST"])
def contact():
    """Render the contact page and handle form submissions.

    Returns:
        Rendered contact template with form
    """
    from .forms import ContactForm

    form = ContactForm()

    if form.validate_on_submit():
        # In a real application, you would process the form here
        # For example, send an email or save to database
        flash("Thank you for your message! We will get back to you soon.", "success")
        return redirect(url_for("main.contact"))

    return render_template("main/contact.html", form=form)



@bp.route("/")
@login_required
def index():
    """Display the main dashboard with expense and restaurant summaries."""
    user_id = current_user.id

    # Get expense statistics
    expense_stats = db.session.execute(
        select(
            func.coalesce(func.count(Expense.id), 0).label("total_expenses"),
            func.coalesce(func.sum(Expense.amount), 0).label("total_spent"),
            func.coalesce(func.avg(Expense.amount), 0).label("avg_expense"),
            func.max(Expense.date).label("last_expense_date"),
        ).where(Expense.user_id == user_id)
    ).first()

    # Get restaurant statistics
    restaurant_stats = db.session.execute(
        select(func.coalesce(func.count(Restaurant.id), 0).label("total_restaurants")).where(
            Restaurant.user_id == user_id
        )
    ).first()

    # Get recent expenses (last 5)
    recent_expenses = db.session.execute(
        select(Expense, Restaurant.name.label("restaurant_name"), Restaurant.website.label("restaurant_website"))
        .outerjoin(Restaurant, Expense.restaurant_id == Restaurant.id)
        .where(Expense.user_id == user_id)
        .order_by(Expense.date.desc(), Expense.created_at.desc())
        .limit(5)
    ).all()

    # Get top restaurants by spending
    top_restaurants = db.session.execute(
        select(
            Restaurant.id,
            Restaurant.name,
            Restaurant.website,
            Restaurant.cuisine,
            func.count(Expense.id).label("visit_count"),
            func.sum(Expense.amount).label("total_spent"),
        )
        .join(Expense, Expense.restaurant_id == Restaurant.id)
        .where(Restaurant.user_id == user_id, Expense.user_id == user_id)
        .group_by(Restaurant.id, Restaurant.name, Restaurant.website, Restaurant.cuisine)
        .order_by(func.sum(Expense.amount).desc())
        .limit(5)
    ).all()

    # Import cuisine color function for template use
    from app.constants.cuisines import get_cuisine_color

    return render_template(
        "main/dashboard.html",
        expense_stats=expense_stats,
        restaurant_stats=restaurant_stats,
        recent_expenses=recent_expenses,
        top_restaurants=top_restaurants,
        get_cuisine_color=get_cuisine_color,
    )

