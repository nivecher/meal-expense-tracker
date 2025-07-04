"""Expense-related routes for the application."""

# Standard library imports
from datetime import datetime
from math import ceil

# Third-party imports
from flask import (
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug import Response

# Local application imports
from app import db
from app.expenses import bp  # noqa: F401 - Used for route registration
from app.expenses.forms import ExpenseForm
from app.expenses.models import Category, Expense
from app.expenses.services import (
    get_expense_filters,
    get_filter_options,
    get_user_expenses,
)
from app.restaurants.models import Restaurant
from app.utils.decorators import db_transaction
from app.utils.messages import FlashMessages

# Constants
PER_PAGE = 10  # Number of expenses per page


@bp.route("/add", methods=["GET", "POST"])
@login_required
@db_transaction(success_message=FlashMessages.EXPENSE_ADDED, error_message=FlashMessages.EXPENSE_ADD_ERROR)
def add_expense() -> Response | str:
    """Add a new expense."""
    # Get all categories (not user-specific) and order by name
    categories = Category.query.order_by(Category.name).all()
    # Filter restaurants by user and order by name
    restaurants = Restaurant.query.filter_by(user_id=current_user.id).order_by(Restaurant.name).all()
    form, categories, restaurants = _prepare_expense_form(categories, restaurants)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "POST":
        if form.validate_on_submit():
            expense, error_msg = _create_expense_from_form(form, categories, current_user.id)
            if not expense:
                if is_ajax:
                    return jsonify({"status": "error", "message": error_msg}), 400
                flash(error_msg, "danger")
                return render_template(
                    "expenses/add.html",
                    form=form,
                    categories=categories,
                    restaurants=restaurants,
                    today=datetime.utcnow().date(),
                )
            db.session.add(expense)
            if is_ajax:
                return jsonify(
                    {
                        "status": "success",
                        "message": FlashMessages.EXPENSE_ADDED,
                        "redirect": url_for("expenses.list_expenses"),
                    }
                )
            return redirect(url_for("expenses.list_expenses"))
        else:
            if is_ajax:
                errors = {field.name: field.errors for field in form if field.errors}
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": FlashMessages.EXPENSE_FORM_INVALID,
                            "errors": errors,
                            "form_data": {k: v for k, v in request.form.items()},
                        }
                    ),
                    400,
                )

    # For GET requests or failed POSTs
    return render_template(
        "expenses/add.html", form=form, categories=categories, restaurants=restaurants, today=datetime.utcnow().date()
    )


@bp.route("/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
@db_transaction(success_message=FlashMessages.EXPENSE_UPDATED, error_message=FlashMessages.EXPENSE_UPDATE_ERROR)
def edit_expense(expense_id: int) -> Response | str:
    """Edit an existing expense."""
    expense = Expense.query.get_or_404(expense_id)
    if expense.user_id != current_user.id:
        abort(403)

    # Get all categories (not user-specific) and order by name
    categories = Category.query.order_by(Category.name).all()
    # Filter restaurants by user and order by name
    restaurants = Restaurant.query.filter_by(user_id=current_user.id).order_by(Restaurant.name).all()

    # Initialize the form with the correct choices
    form = ExpenseForm()

    # Set up the form choices
    form.category_id.choices = [("", "Select a category (optional)")] + [(str(c.id), c.name) for c in categories]
    form.restaurant_id.choices = [("", "Select a restaurant")] + [(str(r.id), r.name) for r in restaurants]

    # Always populate the form with expense data for both GET and failed POST requests
    if request.method == "GET" or not form.validate_on_submit():
        # Process the form to initialize it with the choices
        form.process()

        # Populate the form data
        form.amount.data = expense.amount
        form.date.data = expense.date
        form.meal_type.data = expense.meal_type
        form.notes.data = expense.notes

        # Set category and restaurant data
        if expense.category_id:
            form.category_id.data = str(expense.category_id)
        if expense.restaurant_id:
            form.restaurant_id.data = str(expense.restaurant_id)

        # Debug output
        print(f"Form category_id.choices: {form.category_id.choices}")
        print(f"Form category_id.data: {form.category_id.data}")
        print(f"Expense category_id: {expense.category_id}")

    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    if request.method == "POST":
        # For POST requests, process the form
        if form.validate_on_submit():
            is_valid, category_id, error_msg = _validate_expense_form_data(form, categories)
            if not is_valid:
                if is_ajax:
                    return jsonify({"status": "error", "message": error_msg}), 400
                flash(error_msg, "danger")
                return render_template(
                    "expenses/edit.html",
                    form=form,
                    expense=expense,
                    categories=categories,
                    restaurants=restaurants,
                    today=datetime.utcnow().date(),
                    min_date=datetime.utcnow().date(),
                )
            _update_expense_from_form(expense, form, category_id)
            if is_ajax:
                return jsonify(
                    {
                        "status": "success",
                        "message": FlashMessages.EXPENSE_UPDATED,
                        "redirect": url_for("expenses.list_expenses"),
                    }
                )
            return redirect(url_for("expenses.list_expenses"))

    # For GET requests or failed POSTs, render the edit template with the form
    # The form has already been populated above
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
        debug=True,  # Enable debug mode to show debug information
    )


def _prepare_expense_form(categories: list, restaurants: list) -> tuple[ExpenseForm, list, list]:
    """Prepare the expense form with the given categories and restaurants.

    Args:
        categories: List of categories to include in the form
        restaurants: List of restaurants to include in the form

    Returns:
        Tuple of (form, categories, restaurants)
    """
    form = ExpenseForm()

    # Prepend an empty option to categories
    form.category_id.choices = [("", "Select a category (optional)")] + [(str(c.id), c.name) for c in categories]
    # Add empty option for restaurant selection
    form.restaurant_id.choices = [("", "Select a restaurant")] + [(str(r.id), r.name) for r in restaurants]
    # Set default date to today for new expenses
    if not form.date.data:
        form.date.data = datetime.utcnow().date()
    return form, categories, restaurants


def _create_expense_from_form(form, categories: list, user_id: int) -> tuple[Expense | None, str]:
    """Create an expense from form data.

    Args:
        form: The form containing the expense data
        categories: List of valid categories
        user_id: ID of the current user

    Returns:
        Tuple of (expense, error_message)
    """
    try:
        # Get category
        category_id = int(form.category_id.data) if form.category_id.data else None
        if category_id and not any(c.id == category_id for c in categories):
            return None, "Invalid category selected"

        # Get restaurant
        restaurant_id = int(form.restaurant_id.data) if form.restaurant_id.data else None

        # Handle date - it might already be a date object or a string
        date_value = form.date.data
        if isinstance(date_value, str):
            date_value = datetime.strptime(date_value, "%Y-%m-%d").date()
        elif hasattr(date_value, "date"):  # Already a datetime/date object
            date_value = date_value.date() if hasattr(date_value, "date") else date_value

        # Create expense
        expense = Expense(
            user_id=user_id,
            amount=float(form.amount.data),
            date=date_value,
            notes=form.notes.data.strip() if form.notes.data else None,
            category_id=category_id,
            restaurant_id=restaurant_id,
            meal_type=form.meal_type.data or None,
        )

        return expense, ""

    except ValueError:
        return None, "Invalid form data. Please check your input."
    except Exception as e:
        current_app.logger.error(f"Error creating expense from form: {str(e)}")
        return None, "An error occurred while processing your request."


def _validate_expense_form_data(form, categories: list) -> tuple[bool, int | None, str | None]:
    """Validate expense form data and extract category ID.

    Args:
        form: The form containing the expense data
        categories: List of valid categories

    Returns:
        Tuple of (is_valid, category_id, error_message)
    """
    category_id = None
    category_data = form.category_id.data

    # Handle empty/None category
    if not category_data or str(category_data).strip() == "":
        return True, None, None

    try:
        category_id = int(category_data)
        if not any(c.id == category_id for c in categories):
            current_app.logger.warning(
                "Invalid category ID %s. Available categories: %s", category_id, [c.id for c in categories]
            )
            return False, None, "Invalid category selected"
        return True, category_id, None
    except (ValueError, TypeError) as e:
        current_app.logger.error(
            "Error parsing category ID: %s (type: %s, value: %s)", str(e), type(category_data), category_data
        )
        return False, None, "Invalid category ID format"


def _handle_expense_update(
    expense: Expense, form: ExpenseForm, categories: list, is_ajax: bool
) -> tuple[bool, str | Response]:
    """Handle updating an existing expense.

    Args:
        expense: The expense to update
        form: The form containing the updated data
        categories: List of valid categories
        is_ajax: Whether the request is an AJAX request

    Returns:
        Tuple of (success, response) where response is either an error message
        or a response object
    """
    if not form.validate_on_submit():
        error_msg = "Form validation failed. Please check your input."
        return _handle_error_response(error_msg, is_ajax)

    # Validate form data and get category ID
    is_valid, category_id, error_msg = _validate_expense_form_data(form, categories)
    if not is_valid:
        return _handle_error_response(error_msg, is_ajax)

    try:
        _update_expense_from_form(expense, form, category_id)
        db.session.commit()
        return _handle_success_response(is_ajax)

    except ValueError:
        return _handle_error_response("Invalid form data. Please check your input.", is_ajax)
    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Error updating expense: %s", str(e))
        return _handle_error_response("An error occurred while updating the expense.", is_ajax)


def _update_expense_from_form(expense: Expense, form: ExpenseForm, category_id: int | None) -> None:
    """Update expense fields from form data."""
    try:
        expense.amount = float(form.amount.data)

        # Handle date - it might already be a date object or a string
        date_value = form.date.data
        if isinstance(date_value, str):
            date_value = datetime.strptime(date_value, "%Y-%m-%d").date()
        elif hasattr(date_value, "date"):  # Already a datetime/date object
            date_value = date_value.date() if hasattr(date_value, "date") else date_value

        expense.date = date_value
        expense.notes = form.notes.data.strip() if form.notes.data else None
        expense.category_id = category_id
        expense.restaurant_id = int(form.restaurant_id.data) if form.restaurant_id.data else None
        expense.meal_type = form.meal_type.data or None
    except Exception as e:
        current_app.logger.error(f"Error updating expense from form: {str(e)}")
        raise ValueError("Invalid form data")


@bp.route("/")
@login_required
def list_expenses() -> str:
    """List all expenses for the current user with optional filtering."""
    # Get filter parameters from request
    filters = get_expense_filters(request)

    # Get pagination parameters
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", PER_PAGE, type=int)
    # Get expenses for the current user with filters
    expenses, total_amount = get_user_expenses(current_user.id, filters)
    # Calculate pagination
    total_pages = ceil(len(expenses) / per_page) if expenses else 1
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_expenses = expenses[start_idx:end_idx]

    # Get filter options for the filter form
    filter_options = get_filter_options(current_user.id)
    # Prepare filter values for the template
    search = request.args.get("search", "")
    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")
    return render_template(
        "expenses/list.html",
        expenses=paginated_expenses,
        total_amount=total_amount,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        search=search,
        start_date=start_date,
        end_date=end_date,
        **filter_options,
    )


def _handle_error_response(error_msg: str, is_ajax: bool) -> tuple[bool, str]:
    """Handle error responses consistently."""
    if is_ajax:
        return False, error_msg
    return False, error_msg


def _handle_success_response(is_ajax: bool) -> tuple[bool, Response] | tuple[bool, str]:
    """Handle success responses consistently."""
    if is_ajax:
        return True, jsonify(
            {
                "status": "success",
                "message": "Expense updated successfully!",
                "redirect": url_for("expenses.list_expenses"),
            }
        )
    return True, "Expense updated successfully!"


@bp.route("/<int:expense_id>", methods=["GET"])
@login_required
def expense_details(expense_id: int) -> str:
    """View details of a specific expense.

    Args:
        expense_id: The ID of the expense to view

    Returns:
        Rendered template with expense details
    """
    expense = Expense.query.get_or_404(expense_id)
    if expense.user_id != current_user.id:
        abort(403)
    return render_template("expenses/details.html", expense=expense)


@bp.route("/<int:expense_id>/delete", methods=["POST"])
@login_required
@db_transaction(success_message=FlashMessages.EXPENSE_DELETED, error_message=FlashMessages.EXPENSE_DELETE_ERROR)
def delete_expense(expense_id: int) -> Response:
    """Delete an expense.

    Args:
        expense_id: The ID of the expense to delete

    Returns:
        Redirect to expenses list or JSON response for AJAX
    """
    expense = Expense.query.get_or_404(expense_id)
    if expense.user_id != current_user.id:
        abort(403)
    db.session.delete(expense)
    return redirect(url_for("expenses.list_expenses"))
