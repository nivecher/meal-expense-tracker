"""
Main blueprint routes.

This module contains the route handlers for the main blueprint.
"""

import os
from datetime import datetime, timezone

from flask import (
    Response,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func, select

from app.expenses.models import Expense, Tag
from app.extensions import db
from app.restaurants.models import Restaurant

from . import bp

# Constants for pagination
PER_PAGE = 10  # Number of expenses per page
SHOW_ALL = -1  # Special value to show all expenses


def _get_page_size_from_cookie(cookie_name="expense_page_size", default_size=PER_PAGE):
    """Get page size from cookie with validation and fallback."""
    try:
        cookie_value = request.cookies.get(cookie_name)
        if cookie_value:
            page_size = int(cookie_value)
            # Validate page size is in allowed values
            if page_size in [10, 25, 50, 100, SHOW_ALL]:
                return page_size
    except (ValueError, TypeError):
        pass
    return default_size


@bp.app_template_global()
def get_receipt_url(storage_path):
    """Generate URL for accessing a receipt file."""
    from app.expenses.utils import get_receipt_url

    return get_receipt_url(storage_path)


@bp.route("/uploads/<filename>")
@login_required
def serve_uploaded_file(filename):
    """Serve uploaded receipt files.

    Args:
        filename: The name of the file to serve

    Returns:
        The requested file or 404 if not found
    """
    # Verify the user owns an expense with this receipt
    from app.expenses.models import Expense

    # Check both old format (uploads/filename) and new format (filename)
    expense = Expense.query.filter(
        (Expense.receipt_image == f"uploads/{filename}") | (Expense.receipt_image == filename),
        Expense.user_id == current_user.id,
    ).first()

    if not expense:
        abort(404)

    upload_folder = current_app.config.get("UPLOAD_FOLDER")

    # Determine MIME type based on file extension
    mimetype = None
    if filename.lower().endswith(".pdf"):
        mimetype = "application/pdf"

    return send_from_directory(upload_folder, filename, mimetype=mimetype)


@bp.route("/expense-statistics")
@login_required
def expense_statistics():
    """Redirect to expense statistics page."""
    return redirect(url_for("reports.expense_statistics"))


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
    from app._version import __build_timestamp__, __version__

    return render_template(
        "main/about.html",
        app_version=__version__,
        build_timestamp=__build_timestamp__,
    )


@bp.route("/help")
def help_page():
    """Render the comprehensive help page.

    Returns:
        Rendered help page template with all feature information
    """
    # Import all the constants for displaying options
    from app.constants import MEAL_TYPES
    from app.constants.categories import get_default_categories
    from app.constants.cuisines import get_cuisine_color, get_cuisine_constants

    # Get cuisine constants but override colors with centralized Bootstrap colors
    cuisines = get_cuisine_constants()
    for cuisine in cuisines:
        cuisine["color"] = get_cuisine_color(cuisine["name"])

    return render_template(
        "main/help.html",
        meal_types=list(MEAL_TYPES.values()),
        cuisines=cuisines,
        categories=get_default_categories(),
    )


@bp.route("/terms")
def terms():
    """Render the terms of service page.

    Returns:
        Rendered terms of service template with current datetime
    """
    return render_template("main/terms.html", now=datetime.now(timezone.utc))


@bp.route("/privacy")
def privacy():
    """Render the privacy policy page.

    Returns:
        Rendered privacy policy template with current datetime
    """
    return render_template("main/privacy.html", now=datetime.now(timezone.utc))


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


@bp.route("/test")
def test():
    return "Test route works"


@bp.route("/")
@login_required
def index():
    """Display the main dashboard with welcome message, stats, and recent activity."""
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

    # Get recent expenses (top 5 most recent)
    recent_expenses = db.session.execute(
        select(
            Expense,
            Restaurant.name.label("restaurant_name"),
            Restaurant.website.label("restaurant_website"),
        )
        .join(Restaurant, Expense.restaurant_id == Restaurant.id, isouter=True)
        .where(Expense.user_id == user_id)
        .order_by(Expense.date.desc(), Expense.created_at.desc())
        .limit(5)
    ).all()

    # Get top restaurants by expense count (top 5)
    top_restaurants = db.session.execute(
        select(
            Restaurant.id,
            Restaurant.name,
            Restaurant.website,
            Restaurant.cuisine,
            func.count(Expense.id).label("visit_count"),
            func.coalesce(func.sum(Expense.amount), 0).label("total_spent"),
        )
        .join(Expense, Restaurant.id == Expense.restaurant_id)
        .where(Restaurant.user_id == user_id)
        .group_by(Restaurant.id, Restaurant.name, Restaurant.website, Restaurant.cuisine)
        .order_by(func.count(Expense.id).desc())
        .limit(5)
    ).all()

    return render_template(
        "main/dashboard.html",
        expense_stats=expense_stats,
        restaurant_stats=restaurant_stats,
        recent_expenses=recent_expenses,
        top_restaurants=top_restaurants,
    )


@bp.route("/index.html")
@login_required
def index_html():
    """Serve the main dashboard for index.html requests (browser default)."""
    return index()


@bp.route("/index")
def index_redirect():
    """Redirect to the main index page."""
    return redirect(url_for("main.index"))


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
        # Create a CSS class for each tag using its ID with higher specificity
        css_rule = f"""
.tag-badge.tag-{tag.id} {{
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
    css_content = f"""/* User tag colors - Generated at {datetime.now(timezone.utc).isoformat()} */
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
            "Last-Modified": (max_updated_at.strftime("%a, %d %b %Y %H:%M:%S GMT") if max_updated_at else None),
        },
    )

    return response
