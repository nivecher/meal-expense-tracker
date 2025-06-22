from __future__ import annotations

# Standard library imports
import csv
import io
import logging
from sqlalchemy import desc, distinct
from datetime import datetime, timedelta
from typing import Optional

# Third-party imports
from flask import (
    flash,
    redirect,
    render_template,
    request,
    url_for,
    abort,
    current_app,
    send_file,
)
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, or_, func

from sqlalchemy.orm import joinedload

# Local application imports
from app import db
from app.expenses import bp
from app.expenses.models import Expense
from app.expenses.category import Category
from app.restaurants.models import Restaurant

logger = logging.getLogger(__name__)


def _apply_search_filter(stmt, search: str):
    """Apply search filter to the query."""
    if not search:
        return stmt
    return stmt.where(
        or_(
            Expense.description.ilike(f"%{search}%"),
            Expense.notes.ilike(f"%{search}%"),
        )
    )


def _apply_date_filter(stmt, date_field: str, date_value: str, operator: str):
    """Apply a date filter to the query."""
    if not date_value:
        return stmt

    try:
        date = datetime.strptime(date_value, "%Y-%m-%d")
        if operator == ">=":
            return stmt.where(Expense.date >= date)
        elif operator == "<=":
            # Add one day to include the entire end date
            date = date + timedelta(days=1)
            return stmt.where(Expense.date <= date)
    except ValueError:
        logger.warning(f"Invalid date format: {date_value}")

    return stmt


def _apply_simple_filter(stmt, field_name: str, value: str):
    """Apply a simple equality filter to the query."""
    if not value:
        return stmt
    return stmt.where(getattr(Expense, field_name) == value)


def apply_filters(
    stmt,
    search: Optional[str] = None,
    meal_type: Optional[str] = None,
    category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Apply filters to the expense query.

    Args:
        stmt: The base select statement to apply filters to
        search: Search term to filter by
        meal_type: Filter by meal type
        category: Filter by category
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        Select: The filtered select statement
    """
    try:
        stmt = _apply_search_filter(stmt, search)
        stmt = _apply_simple_filter(stmt, "meal_type", meal_type)
        stmt = _apply_simple_filter(stmt, "category", category)
        stmt = _apply_date_filter(stmt, "date", start_date, ">=")
        stmt = _apply_date_filter(stmt, "date", end_date, "<=")
        return stmt
    except Exception as e:
        logger.error(f"Error applying filters: {str(e)}")
        raise


def _get_sort_column(sort_by: str):
    """Get the appropriate column for sorting.

    Args:
        sort_by: The field name to sort by

    Returns:
        The column to sort by, defaults to Expense.date
    """
    sort_mapping = {
        "date": Expense.date,
        "amount": Expense.amount,
        "description": Expense.description,
    }
    return sort_mapping.get(sort_by, Expense.date)


def _get_sort_order(sort_order: str):
    """Validate and return the sort order.

    Args:
        sort_order: The sort order ('asc' or 'desc')

    Returns:
        The validated sort order, defaults to 'desc'
    """
    return sort_order if sort_order in ["asc", "desc"] else "desc"


def apply_sorting(stmt, sort_by: str, sort_order: str):
    """Apply sorting to the expense query.

    Args:
        stmt: The select statement to sort
        sort_by: Field to sort by (date, amount, or description)
        sort_order: Sort order ('asc' or 'desc')

    Returns:
        Select: The sorted select statement
    """
    sort_column = _get_sort_column(sort_by)
    sort_order = _get_sort_order(sort_order)

    if sort_order == "desc":
        return stmt.order_by(desc(sort_column))
    return stmt.order_by(sort_column)


def _get_filter_parameters():
    """Extract and return filter parameters from the request."""
    return {
        "search": request.args.get("search"),
        "meal_type": request.args.get("meal_type"),
        "category": request.args.get("category"),
        "start_date": request.args.get("start_date"),
        "end_date": request.args.get("end_date"),
        "sort_by": request.args.get("sort_by", "date"),
        "sort_order": request.args.get("sort_order", "desc"),
        "page": request.args.get("page", 1, type=int),
        "per_page": request.args.get("per_page", 10, type=int),
    }


def _get_dropdown_values(user_id: int) -> tuple[list, list]:
    """Get unique values for filter dropdowns."""
    # Get unique meal types
    meal_types_query = (
        select(distinct(Expense.meal_type))
        .where(Expense.user_id == user_id, Expense.meal_type.isnot(None))
        .order_by(Expense.meal_type)
    )
    meal_types = [mt[0] for mt in db.session.execute(meal_types_query).all()]

    # Get unique categories
    categories_query = (
        select(distinct(Expense.category))
        .where(Expense.user_id == user_id, Expense.category.isnot(None))
        .order_by(Expense.category)
    )
    categories = [c[0] for c in db.session.execute(categories_query).all()]

    return meal_types, categories


def _get_restaurant_expense_counts(user_id: int, expenses: list) -> dict:
    """Calculate expense counts per restaurant."""
    restaurant_ids = [e.restaurant_id for e in expenses if e.restaurant_id]
    if not restaurant_ids:
        return {}

    # Using SQLAlchemy 2.0 style query
    stmt = (
        select(Expense.restaurant_id, func.count(Expense.id).label("count"))
        .where(Expense.user_id == user_id, Expense.restaurant_id.in_(restaurant_ids))
        .group_by(Expense.restaurant_id)
    )

    results = db.session.execute(stmt).all()
    return {row.restaurant_id: row.count for row in results}


def _get_empty_context() -> dict:
    """Return an empty context dictionary for error cases."""
    return {
        "expenses": [],
        "pagination": None,
        "search": "",
        "meal_type": "",
        "category": "",
        "start_date": "",
        "end_date": "",
        "sort_by": "date",
        "sort_order": "desc",
        "meal_types": [],
        "categories": [],
        "total_amount": 0.0,
        "restaurant_expense_counts": {},
    }


def get_main_index_context():
    """Get the context for the main index page."""
    try:
        # Get filter parameters
        params = _get_filter_parameters()

        # Build and execute the query
        stmt = select(Expense).where(Expense.user_id == current_user.id)
        stmt = apply_filters(
            stmt, params["search"], params["meal_type"], params["category"], params["start_date"], params["end_date"]
        )
        stmt = apply_sorting(stmt, params["sort_by"], params["sort_order"])

        # Get paginated results
        pagination = db.paginate(stmt, page=params["page"], per_page=params["per_page"], error_out=False)
        expenses = pagination.items

        # Get additional data
        meal_types, categories = _get_dropdown_values(current_user.id)
        total_amount = sum(expense.amount for expense in expenses) if expenses else 0.0
        restaurant_expense_counts = _get_restaurant_expense_counts(current_user.id, expenses)

        return {
            "expenses": expenses,
            "pagination": pagination,
            "search": params["search"] or "",
            "meal_type": params["meal_type"] or "",
            "category": params["category"] or "",
            "start_date": params["start_date"] or "",
            "end_date": params["end_date"] or "",
            "sort_by": params["sort_by"],
            "sort_order": params["sort_order"],
            "meal_types": meal_types,
            "categories": categories,
            "total_amount": total_amount,
            "restaurant_expense_counts": restaurant_expense_counts,
        }

    except Exception as e:
        logger.error(f"Error in get_main_index_context: {str(e)}")
        flash("An error occurred while loading expenses.", "danger")
        return _get_empty_context()


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add_expense():
    restaurant_id = request.args.get("restaurant_id")
    restaurant = None
    if restaurant_id:
        restaurant = db.session.get(Restaurant, restaurant_id)
        if not restaurant:
            flash("Restaurant not found.", "error")
            return redirect(url_for("main.index"))

    if request.method == "POST":
        date = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
        restaurant_id = request.form.get("restaurant_id")
        restaurant_type = None
        if restaurant_id:
            restaurant = db.session.get(Restaurant, restaurant_id)
            if restaurant:
                restaurant_type = restaurant.type
        type_to_category = {
            "restaurant": "Dining",
            "cafe": "Coffee",
            "bar": "Drinks",
            "fast_food": "Fast Food",
            "food_truck": "Street Food",
            "bakery": "Bakery",
            "grocery": "Groceries",
        }
        from app.expenses.category import Category

        # Get category name from restaurant type or form
        category_name = type_to_category.get(restaurant_type, request.form.get("category", ""))

        # Get or create the category
        category = None
        if category_name:
            category = db.session.scalars(select(Category).where(Category.name == category_name)).first()

            if not category and category_name:  # Create the category if it doesn't exist
                category = Category(name=category_name)
                db.session.add(category)
                db.session.flush()  # Get the ID for the new category

        expense = Expense(
            date=date,
            amount=float(request.form["amount"]),
            category=category,  # Pass the Category object, not the name
            meal_type=request.form["meal_type"],
            notes=request.form["notes"],
            user_id=current_user.id,
            restaurant_id=restaurant_id,
        )
        db.session.add(expense)
        db.session.commit()
        flash("Expense added successfully!", "success")
        if restaurant_id:
            return redirect(url_for("restaurants.restaurant_details", restaurant_id=restaurant_id))
        return redirect(url_for("main.index"))

    # Get all restaurants for the dropdown
    stmt = select(Restaurant).order_by(Restaurant.name)
    restaurants = db.session.scalars(stmt).all()

    today = datetime.now().date()
    min_date = today - timedelta(days=365)  # Allow expenses up to 1 year in the past

    return render_template(
        "expenses/add_expense.html",
        restaurant=restaurant,
        restaurants=restaurants,
        today=today.strftime("%Y-%m-%d"),
        min_date=min_date.strftime("%Y-%m-%d"),
    )


def _get_restaurant_type_mapping():
    """Return mapping of restaurant types to display names."""
    return {
        "restaurant": "Restaurant",
        "cafe": "Café",
        "bar": "Bar/Pub",
        "fast_food": "Fast Food",
        "food_truck": "Food Truck",
        "bakery": "Bakery",
        "grocery": "Grocery Store",
        "other": "Other",
    }


def _get_type_to_category_mapping():
    """Return mapping of restaurant types to category names."""
    return {
        "restaurant": "Dining",
        "cafe": "Coffee",
        "bar": "Drinks",
        "fast_food": "Fast Food",
        "food_truck": "Street Food",
        "bakery": "Bakery",
        "grocery": "Groceries",
    }


def _update_expense_from_form(expense, form_data):
    """Update expense attributes from form data.

    Args:
        expense: Expense instance to update
        form_data: Dictionary containing form data

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        expense.amount = float(form_data.get("amount", 0))
        expense.date = datetime.strptime(form_data.get("date", ""), "%Y-%m-%d").date()
        expense.description = form_data.get("description", "").strip()
        expense.meal_type = form_data.get("meal_type")
        expense.notes = form_data.get("notes", "")
        return True, ""
    except ValueError as e:
        logger.error(f"Invalid form data: {e}", exc_info=True)
        return False, "Invalid input. Please check your entries."
    except Exception as e:
        logger.error(f"Error updating expense: {e}", exc_info=True)
        return False, "An error occurred while updating the expense."


def _get_or_create_category(category_name):
    """Get or create a category by name.

    Args:
        category_name: Name of the category

    Returns:
        Category: The category instance or None if name is empty
    """
    if not category_name:
        return None

    category = db.session.scalar(select(Category).where(Category.name == category_name))

    if not category:
        category = Category(name=category_name)
        db.session.add(category)
        db.session.flush()

    return category


def _get_edit_expense_context(expense, restaurant):
    """Generate context for the edit expense template."""
    # Get all categories and restaurants for the dropdowns
    categories = db.session.scalars(select(Category).order_by(Category.name)).all()
    restaurants = db.session.scalars(select(Restaurant).order_by(Restaurant.name)).all()

    return {
        "expense": expense,
        "restaurant": restaurant,
        "restaurants": restaurants,  # Add restaurants to the context
        "categories": categories,
        "meal_types": ["Breakfast", "Lunch", "Dinner", "Snack", "Other"],
        "restaurant_types": _get_restaurant_type_mapping(),
        "today": datetime.now().date().strftime("%Y-%m-%d"),
        "min_date": (datetime.now().date() - timedelta(days=365)).strftime("%Y-%m-%d"),
    }


def _render_edit_form(expense, restaurant):
    """Render the edit expense form with the provided context."""
    return render_template("expenses/edit_expense.html", **_get_edit_expense_context(expense, restaurant))


def _get_expense_and_restaurant(expense_id: int):
    """Get and validate expense and associated restaurant.

    Args:
        expense_id: The ID of the expense to fetch

    Returns:
        tuple: (expense, restaurant) if valid, (None, None) if not found
    """
    expense = db.session.get(Expense, expense_id)
    if not expense or expense.user_id != current_user.id:
        return None, None

    # Get the restaurant without user check since restaurants are shared
    restaurant = db.session.get(Restaurant, expense.restaurant_id)
    if not restaurant:
        return None, None

    return expense, restaurant


def _update_restaurant_info(restaurant, form_data):
    """Update restaurant information from form data.

    Args:
        restaurant: Restaurant instance to update
        form_data: Dictionary containing form data

    Returns:
        str: The restaurant type
    """
    restaurant_type = form_data.get("restaurant_type")
    if restaurant_type and restaurant_type != "other":
        restaurant.type = restaurant_type
    elif "restaurant_name" in form_data:
        restaurant.name = form_data["restaurant_name"].strip()
        restaurant_type = "restaurant"
    return restaurant_type


def _update_expense_category(expense, restaurant_type, form_data):
    """Update the category for an expense based on restaurant type and form data.

    Args:
        expense: The expense to update
        restaurant_type: Type of the restaurant
        form_data: Form data containing category information

    Returns:
        tuple: (success: bool, message: str) or (True, None) if successful
    """
    type_mapping = _get_type_to_category_mapping()
    category_name = type_mapping.get(restaurant_type, form_data.get("category", ""))

    if not category_name:
        expense.category = None
        return True, None

    category = _get_or_create_category(category_name)
    if not category:
        logger.warning(f"Failed to get or create category: {category_name}")
        return False, f"Failed to process category: {category_name}"

    expense.category = category
    return True, None


def _process_expense_updates(expense, restaurant, form_data):
    """Process the actual expense updates.

    Args:
        expense: Expense instance to update
        restaurant: Associated restaurant
        form_data: Form data dictionary

    Returns:
        tuple: (success: bool, message: str)
    """
    success, message = _update_expense_from_form(expense, form_data)
    if not success:
        return False, message

    restaurant_type = _update_restaurant_info(restaurant, form_data)
    success, message = _update_expense_category(expense, restaurant_type, form_data)
    if not success:
        return False, message

    return True, "Expense updated successfully!"


def _process_expense_update(expense, restaurant, form_data):
    """Process the expense update from form data.

    Args:
        expense: Expense instance to update
        restaurant: Associated restaurant
        form_data: Form data dictionary

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        success, message = _process_expense_updates(expense, restaurant, form_data)
        if success:
            db.session.commit()
        else:
            db.session.rollback()
        return success, message

    except ValueError as e:
        db.session.rollback()
        logger.error("Invalid data in form: %s", e, exc_info=True)
        return False, "Invalid data provided. Please check your inputs."

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error("Database error updating expense: %s", e, exc_info=True)
        return False, "A database error occurred. Please try again."

    except Exception as e:
        db.session.rollback()
        logger.error("Unexpected error updating expense: %s", e, exc_info=True)
        return False, "An unexpected error occurred. Please try again."


@bp.route("/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def edit_expense(expense_id: int):
    """Edit an existing expense.

    Args:
        expense_id: The ID of the expense to edit

    Returns:
        Rendered template or redirect
    """
    # Get and validate expense and restaurant
    expense, restaurant = _get_expense_and_restaurant(expense_id)
    if not all([expense, restaurant]):
        abort(404)

    if request.method == "GET":
        return _render_edit_form(expense, restaurant)

    # Process form submission
    success, message = _process_expense_update(expense, restaurant, request.form)
    flash(message, "success" if success else "danger")

    if success:
        return redirect(url_for("main.index"))
    return _render_edit_form(expense, restaurant)


@bp.route("/stats")
@login_required
def expense_stats():
    # Get date range from request or default to last 30 days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)

    # Use SQLAlchemy 2.0 style query
    stmt = select(Expense).where(
        Expense.user_id == current_user.id,
        Expense.date >= start_date,
        Expense.date <= end_date,
    )
    expenses = db.session.scalars(stmt).all()

    total_amount = sum(expense.amount for expense in expenses)
    category_totals = {}
    meal_type_totals = {}
    for expense in expenses:
        category_totals[expense.category] = category_totals.get(expense.category, 0) + expense.amount
        meal_type_totals[expense.meal_type] = meal_type_totals.get(expense.meal_type, 0) + expense.amount

    return render_template(
        "expenses/stats.html",
        total_amount=total_amount,
        category_totals=category_totals,
        meal_type_totals=meal_type_totals,
        start_date=start_date,
        end_date=end_date,
    )


@bp.route("/<int:expense_id>")
@login_required
def expense_details(expense_id: int):
    """Display details of a specific expense.

    Args:
        expense_id: The ID of the expense to display

    Returns:
        Rendered template with expense details or redirect
    """
    try:
        # Use SQLAlchemy 2.0 style query with join for eager loading
        stmt = select(Expense).options(joinedload(Expense.restaurant)).where(Expense.id == expense_id)
        expense = db.session.scalar(stmt)

        if expense is None:
            logger.warning(f"Expense {expense_id} not found")
            abort(404)

        if expense.user_id != current_user.id:
            logger.warning(
                f"User {current_user.id} attempted to view expense {expense_id} " f"owned by user {expense.user_id}"
            )
            flash("You do not have permission to view this expense.", "error")
            return redirect(url_for("main.index"))

        # Ensure restaurant is loaded
        if not hasattr(expense, "restaurant") and expense.restaurant_id:
            expense.restaurant = db.session.get(Restaurant, expense.restaurant_id)
        return render_template("expenses/expense_detail.html", expense=expense)

    except SQLAlchemyError as e:
        logger.error(f"Database error fetching expense {expense_id}: {str(e)}", exc_info=True)
        flash("An error occurred while fetching the expense details.", "error")
        return redirect(url_for("main.index"))
    except Exception as e:
        logger.error(f"Unexpected error in expense_details: {str(e)}", exc_info=True)
        flash("An unexpected error occurred.", "error")
        return redirect(url_for("main.index"))


@bp.route("/<int:expense_id>/delete", methods=["POST"])
@login_required
def delete_expense(expense_id):
    """Delete an expense.

    Args:
        expense_id: The ID of the expense to delete

    Returns:
        Redirects to the previous page or index with a status message
    """
    try:
        # Get the expense using SQLAlchemy 2.0 style
        stmt = select(Expense).where(Expense.id == expense_id)
        expense = db.session.scalar(stmt)

        if not expense:
            flash("Expense not found.", "error")
            return redirect(url_for("main.index"))

        if expense.user_id != current_user.id:
            flash("You don't have permission to delete this expense.", "error")
            return redirect(url_for("main.index"))

        # Delete the expense
        db.session.delete(expense)
        db.session.commit()

        flash("Expense deleted successfully.", "success")

        # Redirect back to the previous page or index
        if request.referrer:
            return redirect(request.referrer)
        return redirect(url_for("main.index"))

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error deleting expense {expense_id}: {str(e)}", exc_info=True)
        flash("An error occurred while deleting the expense.", "error")
        return redirect(url_for("main.index"))
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error deleting expense {expense_id}: {str(e)}", exc_info=True)
        flash("An unexpected error occurred while deleting the expense.", "error")
        return redirect(url_for("main.index"))


@bp.route("/export")
@login_required
def export_expenses():
    """Export expenses to CSV."""
    try:
        # Get all expenses for the current user with join to restaurant
        stmt = (
            select(Expense)
            .options(joinedload(Expense.restaurant))
            .where(Expense.user_id == current_user.id)
            .order_by(Expense.date.desc())
        )
        expenses = db.session.scalars(stmt).all()

        # Create a CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "Date",
                "Amount",
                "Description",
                "Meal Type",
                "Category",
                "Restaurant",
                "Notes",
            ]
        )

        # Write data
        for expense in expenses:
            writer.writerow(
                [
                    expense.date.strftime("%Y-%m-%d") if expense.date else "",
                    str(expense.amount) if expense.amount is not None else "0.00",
                    expense.description or "",
                    expense.meal_type or "",
                    expense.category or "",
                    expense.restaurant.name if expense.restaurant else "",
                    expense.notes or "",
                ]
            )

        # Prepare the response
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode("utf-8")),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"expenses-{datetime.now().strftime('%Y%m%d')}.csv",
        )
    except Exception as e:
        logger.error(f"Error exporting expenses: {str(e)}", exc_info=True)
        flash("An error occurred while exporting expenses. Please try again.", "error")
        return redirect(url_for("expenses.index"))
