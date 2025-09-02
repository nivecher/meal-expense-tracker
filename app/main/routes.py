"""
Main blueprint routes.

This module contains the route handlers for the main blueprint.
"""

import os
from datetime import datetime

from flask import (
    Response,
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

from app.expenses.models import Expense, Tag
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


# TODO test code
@bp.route("/test/static/<path:filename>")
def test_static(filename):
    """Test route to verify static file serving.

    Args:
        filename: Name of the file to serve from static folder

    Returns:
        The requested static file
    """
    # Debug information
    static_folder = current_app.static_folder
    full_path = os.path.join(static_folder, filename)
    exists = os.path.exists(full_path)

    # Log debug information
    current_app.logger.info(f"Static folder: {static_folder}")
    current_app.logger.info(f"Requested file: {filename}")
    current_app.logger.info(f"Full path: {full_path}")
    current_app.logger.info(f"File exists: {exists}")

    if not exists:
        return f"File not found: {full_path}", 404

    return send_from_directory(static_folder, filename)


@bp.route("/debug/routes")
def debug_routes():
    """Debug endpoint to list all registered routes."""
    from flask import current_app

    output = []
    for rule in current_app.url_map.iter_rules():
        methods = ",".join(rule.methods)
        line = f"{rule.endpoint}: {rule.rule} [{methods}]"
        output.append(line)

    return "<br>".join(sorted(output))


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


# TODO debug (remove)
@bp.route("/api/config/google-maps-key")
def get_google_maps_key():
    """Return the Google Maps API key.

    Returns:
        JSON response containing the Google Maps API key or an error message
    """
    key = current_app.config.get("GOOGLE_MAPS_API_KEY")
    if not key:
        return jsonify({"error": "Google Maps API key not configured"}), 500
    return jsonify({"apiKey": key})


# TODO debug (remove)
@bp.route("/api/config/google-maps-id")
def get_google_maps_id():
    """Return the Google Maps Map ID.

    Returns:
        JSON response containing the Google Maps Map ID or an error message
    """
    key = current_app.config.get("GOOGLE_MAPS_MAP_ID")
    if not key:
        return jsonify({"error": "Google Maps Map ID not configured"}), 500
    return jsonify({"mapId": key})


@bp.route("/test/google-places")
@login_required
def google_places_test():
    """Test page for Google Places API integration.

    This page provides a testing interface for the Google Places API functionality.
    It allows users to search for places and view the results on a map.

    Returns:
        str: Rendered template for the Google Places test page.
    """
    return render_template("test/google_places_test.html", title="Google Places Test")


@bp.route("/sticky-tables-demo")
@login_required
def sticky_tables_demo():
    """Demo page for sticky table headers and frozen columns."""
    return render_template("components/sticky_table_examples.html")


@bp.route("/error-handling-demo")
@login_required
def error_handling_demo():
    """Demo page for enhanced restaurant error handling."""
    return render_template("test/error-handling-demo.html")


@bp.route("/css/user-tags.css")
@login_required
def user_tag_css():
    """Generate dynamic CSS with user's tag colors.

    This route generates CSS that applies the user's custom tag colors
    to tag elements. The CSS is cached by the browser but includes
    cache-busting parameters to ensure updates when tags are modified.

    Returns:
        Response: CSS content with user's tag colors
    """
    # Get all tags for the current user with their last modified timestamps
    user_tags = db.session.execute(select(Tag).where(Tag.user_id == current_user.id)).scalars().all()

    # Generate CSS rules for each tag
    css_rules = []
    max_updated_at = None

    for tag in user_tags:
        # Create a CSS class for each tag using its ID
        css_rule = f"""
.tag-{tag.id} {{
    background-color: {tag.color} !important;
    color: white !important;
}}"""
        css_rules.append(css_rule)

        # Track the most recent update time for cache busting
        if tag.updated_at and (max_updated_at is None or tag.updated_at > max_updated_at):
            max_updated_at = tag.updated_at

    # Combine all CSS rules
    css_content = "\n".join(css_rules)

    # Add a comment with timestamp for cache busting
    css_content = f"""/* User tag colors - Generated at {datetime.utcnow().isoformat()} */
{css_content}"""

    # Create ETag based on user ID, tag count, and last update time
    etag_parts = [str(current_user.id), str(len(user_tags))]
    if max_updated_at:
        etag_parts.append(str(int(max_updated_at.timestamp())))
    etag = f'"{hash("-".join(etag_parts))}"'

    # Return CSS response with appropriate headers
    response = Response(
        css_content,
        mimetype="text/css",
        headers={
            "Cache-Control": "public, max-age=300",  # Cache for 5 minutes
            "ETag": etag,  # ETag for cache validation
            "Last-Modified": max_updated_at.strftime("%a, %d %b %Y %H:%M:%S GMT") if max_updated_at else None,
        },
    )

    return response
