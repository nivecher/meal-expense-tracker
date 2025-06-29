"""Expense-related routes for the application."""

# Standard library imports
import os
from datetime import date, datetime

# Third-party imports
from flask import (
    abort,
    current_app,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func, or_
from sqlalchemy.exc import SQLAlchemyError
from werkzeug import Response

# Local application imports
from app import db
from app.expenses import bp  # noqa: F401 - Used for route registration
from app.expenses.forms import ExpenseForm
from app.expenses.models import Category  # Import Category model
from app.expenses.models import Expense
from app.expenses.services import get_expense_filters, get_filter_options
from app.expenses.utils import save_receipt  # Import save_receipt utility
from app.restaurants.models import Restaurant  # Import Restaurant model


@bp.route("/")
@login_required
def list_expenses():
    """List all expenses for the current user.

    Returns:
        Rendered template with the list of expenses
    """
    try:
        # Get filter parameters from request
        filters = get_expense_filters(request)
        # Get page number from request args, default to 1
        page = request.args.get("page", 1, type=int)
        per_page = 10  # Number of items per page
        # Get expenses and total amount with pagination
        expenses_query = Expense.query.filter_by(user_id=current_user.id)
        # Apply filters
        if filters.get("start_date"):
            expenses_query = expenses_query.filter(Expense.date >= filters["start_date"])
        if filters.get("end_date"):
            expenses_query = expenses_query.filter(Expense.date <= filters["end_date"])
        if filters.get("search"):
            search = f"%{filters['search']}%"
            expenses_query = expenses_query.filter(or_(Expense.description.ilike(search), Expense.notes.ilike(search)))
        # Order by date descending
        expenses_query = expenses_query.order_by(Expense.date.desc())
        # Paginate the query
        expenses = expenses_query.paginate(page=page, per_page=per_page, error_out=False)
        # Calculate total amount for the filtered results
        total_amount = (
            db.session.query(func.sum(Expense.amount)).filter(Expense.user_id == current_user.id).scalar() or 0.0
        )

        # Get filter options
        filter_options = get_filter_options(current_user.id)

        # Generate dynamic CSS for category colors
        dynamic_css = []
        seen_categories = set()
        for expense in expenses.items:
            if expense.category and expense.category.id not in seen_categories:
                seen_categories.add(expense.category.id)
                color = expense.category.color
                dynamic_css.append(
                    f".category-badge-{expense.category.id} {{\n" f"    background-color: {color} !important;\n" "}"
                )
        # Join all CSS rules and add newlines
        dynamic_css_str = "\n".join(dynamic_css) + "\n" if dynamic_css else ""
        # Write dynamic CSS to file
        dynamic_css_path = os.path.join(current_app.static_folder, "css", "dynamic.css")
        # Ensure directory exists
        os.makedirs(os.path.dirname(dynamic_css_path), exist_ok=True)
        with open(dynamic_css_path, "w", encoding="utf-8") as f:
            f.write(dynamic_css_str)
        response = make_response(
            render_template(
                "expenses/list.html",
                expenses=expenses,
                total_amount=float(total_amount),
                **filters,
                **filter_options,
            )
        )
        # Add cache control headers to prevent caching of the dynamic CSS
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    except Exception as e:
        current_app.logger.error(f"Error loading expenses: {str(e)}", exc_info=True)
        flash("An error occurred while loading expenses. Please try again.", "danger")
        return render_template("expenses/list.html", expenses=[], total_amount=0)


def _setup_expense_form(restaurant_id: int = None) -> tuple[ExpenseForm, list, list]:
    """Set up the expense form with choices and defaults.

    Args:
        restaurant_id: Optional ID of the restaurant to pre-select

    Returns:
        Tuple of (form, categories, restaurants)
    """
    form = ExpenseForm()
    filter_options = get_filter_options(current_user.id)
    categories = filter_options["categories"]

    # Set up category choices
    form.category_id.choices = [(str(c.id), c.name) for c in categories]

    # Set default category
    if not form.category_id.data and categories:
        last_category_id = session.get(f"user_{current_user.id}_last_category")
        if last_category_id and any(str(c.id) == last_category_id for c in categories):
            form.category_id.data = last_category_id
        else:
            default_category = next((c for c in categories if c.name.lower() == "dining"), categories[0])
            form.category_id.data = str(default_category.id)

    # Set up restaurant choices
    restaurants = Restaurant.query.filter_by(user_id=current_user.id).order_by(Restaurant.name).all()
    form.restaurant_id.choices = [("", "Select a restaurant...")] + [(str(r.id), r.name) for r in restaurants]

    # Handle restaurant pre-selection
    if restaurant_id:
        restaurant_id = str(restaurant_id)
        form.restaurant_id.data = restaurant_id
        session[f"user_{current_user.id}_last_restaurant"] = restaurant_id
    else:
        last_restaurant_id = session.get(f"user_{current_user.id}_last_restaurant")
        if last_restaurant_id and any(str(r.id) == last_restaurant_id for r in restaurants):
            form.restaurant_id.data = last_restaurant_id

    # Set default date
    if not form.date.data:
        form.date.data = datetime.utcnow().date()

    return form, categories, restaurants


def _validate_category_id(category_id_str: str, categories: list) -> tuple[bool, int | None, str | None]:
    """Validate the category ID and return (is_valid, category_id, error_msg)"""
    if not category_id_str:
        return True, None, None

    try:
        category_id = int(category_id_str)
        if not any(c.id == category_id for c in categories):
            return False, None, "Invalid category selected"
        return True, category_id, None
    except (ValueError, TypeError):
        return False, None, "Please select a valid category"


def _create_expense_from_form(form, categories: list, user_id: int) -> tuple[Expense | None, str]:
    """Create an expense object from form data.

    Args:
        form: WTForms form object
        categories: List of valid categories
        user_id: ID of the current user

    Returns:
        Tuple of (expense_object, error_message)
    """
    # Validate category
    is_valid, category_id, error_msg = _validate_category_id(form.category_id.data, categories)
    if not is_valid:
        current_app.logger.warning(f"Invalid category_id: {form.category_id.data}")
        return None, error_msg or "Please select a valid category"

    # Process date
    date_obj, date_error = _process_expense_date(form.date.data)
    if date_error:
        return None, date_error

    # Create expense object
    restaurant_id = int(form.restaurant_id.data) if form.restaurant_id.data else None
    meal_type = form.meal_type.data if form.meal_type.data else None
    notes = form.notes.data.strip() if form.notes.data else None

    expense = Expense(
        user_id=user_id,
        amount=float(form.amount.data),
        date=date_obj,
        notes=notes,
        category_id=category_id,
        restaurant_id=restaurant_id,
        meal_type=meal_type,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    return expense, ""


def _process_expense_date(date_str: str) -> tuple[date | None, str | None]:
    """Process and validate the expense date.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Tuple of (date_object, error_message)
    """
    if not date_str:
        return None, None

    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date(), None
    except (ValueError, TypeError):
        current_app.logger.error("Invalid date format: %s", date_str)
        return None, "Invalid date format. Please use YYYY-MM-DD format."


def _process_receipt_upload(receipt_file) -> tuple[str | None, str | None]:
    """Process receipt file upload.

    Args:
        receipt_file: File object from request.files

    Returns:
        Tuple of (file_path, error_message)
    """
    if not receipt_file or not receipt_file.filename:
        return None, None

    try:
        receipt_path = save_receipt(receipt_file, current_app.config["UPLOAD_FOLDER"])
        return receipt_path, None
    except Exception as e:
        current_app.logger.error("Error saving receipt: %s", str(e), exc_info=True)
        return None, "Error processing receipt. Please try again."


def _handle_database_error(error: SQLAlchemyError) -> str:
    """Handle database errors and return appropriate error messages.

    Args:
        error: SQLAlchemy error object

    Returns:
        Error message string
    """
    if hasattr(error, "orig") and hasattr(error.orig, "pgcode"):
        if error.orig.pgcode == "23503":  # Foreign key violation
            return "A database constraint was violated. Please check your input data."
        if error.orig.pgcode == "23505":  # Unique violation
            return "This record already exists. Please check your input."
    return f"An unexpected error occurred: {str(error)}"


def _update_expense_fields(expense: Expense, form_data: dict, category_id: int, date_obj: date) -> None:
    """Update expense fields from form data."""
    expense.amount = float(form_data.get("amount", 0))
    expense.date = date_obj
    expense.notes = form_data.get("notes", "").strip() or None
    expense.category_id = category_id
    expense.restaurant_id = int(form_data["restaurant_id"]) if form_data.get("restaurant_id") else None
    expense.meal_type = form_data.get("meal_type") or None
    expense.updated_at = datetime.utcnow()


def _update_expense_from_form(expense: Expense, form_data: dict, categories: list) -> tuple[bool, str]:
    """Update expense object with form data.

    Args:
        expense: Expense object to update
        form_data: Form data dictionary
        categories: List of valid categories

    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Process category
        is_valid, category_id, error_msg = _validate_category_id(form_data.get("category_id"), categories)
        if not is_valid:
            return False, error_msg or "Please select a valid category"

        # Process date
        date_str = form_data.get("date")
        if not date_str:
            return False, "Date is required"

        date_obj, date_error = _process_expense_date(date_str)
        if date_error:
            return False, date_error

        # Process receipt if present
        receipt_path = None
        if "receipt" in request.files:
            receipt_file = request.files["receipt"]
            receipt_path, receipt_error = _process_receipt_upload(receipt_file)
            if receipt_error:
                return False, receipt_error

        # Update expense fields
        _update_expense_fields(expense, form_data, category_id, date_obj)

        if receipt_path:
            expense.receipt_path = receipt_path

        db.session.add(expense)
        db.session.commit()
        return True, ""

    except SQLAlchemyError as e:
        db.session.rollback()
        error_msg = _handle_database_error(e)
        current_app.logger.error("Database error updating expense: %s", str(e), exc_info=True)
        return False, error_msg
    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Error updating expense: %s", str(e), exc_info=True)
        return False, f"An error occurred while updating the expense: {str(e)}"


def _prepare_expense_form(categories: list, restaurants: list) -> tuple[ExpenseForm, list, list]:
    """Prepare expense form with choices and return form with context."""
    form = ExpenseForm()
    form.category_id.choices = [(str(c.id), c.name) for c in categories]
    form.restaurant_id.choices = [("", "Select a restaurant...")] + [(str(r.id), r.name) for r in restaurants]
    return form, categories, restaurants


def _handle_expense_creation(form: ExpenseForm, categories: list, user_id: int) -> tuple[Expense | None, str]:
    """Handle expense creation logic."""
    expense, error_msg = _create_expense_from_form(form, categories, user_id)
    if not expense:
        return None, error_msg

    try:
        db.session.add(expense)
        db.session.commit()
        return expense, ""
    except SQLAlchemyError as e:
        db.session.rollback()
        error_msg = _handle_database_error(e)
        current_app.logger.error("Database error adding expense: %s", str(e), exc_info=True)
        return None, error_msg


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add_expense() -> Response | str:
    """Add a new expense."""
    categories = Category.query.filter_by(user_id=current_user.id).all()
    restaurants = Restaurant.query.filter_by(user_id=current_user.id).all()
    form, categories, restaurants = _prepare_expense_form(categories, restaurants)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "POST" and form.validate_on_submit():
        expense, error_msg = _handle_expense_creation(form, categories, current_user.id)

        if not expense:
            if is_ajax:
                return jsonify({"status": "error", "message": error_msg}), 400
            flash(error_msg, "danger")
            return render_template("expenses/add.html", form=form, categories=categories, restaurants=restaurants)

        if is_ajax:
            return jsonify(
                {
                    "status": "success",
                    "message": "Expense added successfully!",
                    "redirect": url_for("expenses.list_expenses", _external=True),
                }
            )

        flash("Expense added successfully!", "success")
        return redirect(url_for("expenses.list_expenses"))

    return render_template("expenses/add.html", form=form, categories=categories, restaurants=restaurants)


def _populate_expense_form(form: ExpenseForm, expense: Expense) -> None:
    """Populate form fields with expense data."""
    form.amount.data = expense.amount
    form.date.data = expense.date.strftime("%Y-%m-%d") if expense.date else None
    form.notes.data = expense.notes
    form.category_id.data = str(expense.category_id) if expense.category_id else None
    form.restaurant_id.data = str(expense.restaurant_id) if expense.restaurant_id else None
    form.meal_type.data = expense.meal_type


def _handle_expense_update(
    expense: Expense, form: ExpenseForm, categories: list, is_ajax: bool
) -> tuple[bool, str | Response]:
    """Handle expense update logic."""
    if not form.validate():
        current_app.logger.error("Form validation failed: %s", form.errors)
        if is_ajax:
            return (
                False,
                jsonify(
                    {
                        "status": "error",
                        "message": "Form validation failed",
                        "errors": form.errors,
                    }
                ),
                400,
            )
        return False, "Form validation failed"

    success, error_msg = _update_expense_from_form(expense, request.form, categories)
    if not success:
        return False, error_msg

    if is_ajax:
        return True, jsonify(
            {
                "status": "success",
                "message": "Expense updated successfully!",
                "redirect": url_for("expenses.list_expenses", _external=True),
            }
        )
    return True, "Expense updated successfully!"


@bp.route("/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def edit_expense(expense_id: int) -> Response | str:
    """Edit an existing expense."""
    expense = Expense.query.get_or_404(expense_id)
    if expense.user_id != current_user.id:
        abort(403)

    categories = Category.query.filter_by(user_id=current_user.id).all()
    restaurants = Restaurant.query.filter_by(user_id=current_user.id).all()
    form, categories, restaurants = _prepare_expense_form(categories, restaurants)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "GET":
        _populate_expense_form(form, expense)

    if request.method == "POST":
        result = _handle_expense_update(expense, form, categories, is_ajax)
        if isinstance(result, tuple):
            success, response = result
            if not success:
                if is_ajax:
                    return jsonify({"status": "error", "message": response}), 400
                flash(response, "danger")
            else:
                if is_ajax:
                    return response
                flash("Expense updated successfully!", "success")
                return redirect(url_for("expenses.list_expenses"))

    # Prepare form for GET request or failed POST
    form, categories, restaurants = _prepare_expense_form(categories, restaurants)
    _populate_expense_form(form, expense)

    # Get minimum date for date picker
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    min_date = min((r.date for r in expenses if r.date), default=datetime.utcnow().date())

    return render_template(
        "expenses/edit.html",
        form=form,
        expense=expense,
        categories=categories,
        restaurants=restaurants,
        today=datetime.utcnow().date(),
        min_date=min_date,
    )


@bp.route("/<int:expense_id>")
@login_required
def expense_details(expense_id: int) -> str:
    """View details of a specific expense.

    Args:
        expense_id: ID of the expense to view

    Returns:
        Rendered template with expense details
    """
    expense = Expense.query.get_or_404(expense_id)
    if expense.user_id != current_user.id:
        abort(403)
    return render_template("expenses/detail.html", expense=expense)


@bp.route("/<int:expense_id>/delete", methods=["POST"])
@login_required
def delete_expense(expense_id: int) -> Response:
    """Delete an expense.

    Args:
        expense_id: ID of the expense to delete

    Returns:
        JSON response (AJAX) or redirect to expenses list
    """
    expense = Expense.query.get_or_404(expense_id)
    if expense.user_id != current_user.id:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Permission denied",
                        "errors": {"_error": ["You don't have permission to delete this expense."]},
                    }
                ),
                403,
            )
        abort(403)
    try:
        db.session.delete(expense)
        db.session.commit()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(
                {
                    "status": "success",
                    "message": "Expense deleted successfully!",
                    "redirect": url_for("expenses.list_expenses"),
                }
            )
        flash("Expense deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        error_msg = "An error occurred while deleting the expense. Please try again."
        current_app.logger.error(f"Error deleting expense: {str(e)}", exc_info=True)

        # Handle AJAX error response
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"status": "error", "message": error_msg, "errors": {"_error": [error_msg]}}), 500

        flash(error_msg, "danger")

    return redirect(url_for("expenses.list_expenses"))
