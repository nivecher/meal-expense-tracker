"""Expense-related routes for the application."""

# Standard library imports
from math import ceil
from typing import Optional, Tuple

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
from flask.typing import ResponseReturnValue
from flask.wrappers import Response as FlaskResponse
from flask_login import current_user, login_required

# Third-party imports
from flask_wtf import FlaskForm
from sqlalchemy import desc, extract
from werkzeug.wrappers import Response as WerkzeugResponse

# Local application imports
from app.expenses import bp
from app.expenses import services as expense_services
from app.expenses.forms import ExpenseForm
from app.expenses.models import Category, Expense
from app.restaurants.models import Restaurant
from app.utils.decorators import db_transaction
from app.utils.messages import FlashMessages

# Constants
PER_PAGE = 10  # Number of expenses per page


def _get_form_choices(
    user_id: int,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Get category and restaurant choices for the expense form.

    Args:
        user_id: ID of the current user

    Returns:
        Tuple of (category_choices, restaurant_choices)
    """
    categories = [(str(c.id), c.name) for c in Category.query.filter_by(user_id=user_id).all()]
    restaurants = [(str(r.id), r.name) for r in Restaurant.query.filter_by(user_id=user_id).all()]
    return categories, restaurants


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add_expense() -> ResponseReturnValue:
    """Add a new expense.

    Returns:
        Rendered template or JSON response for AJAX requests
    """
    current_app.logger.info("=== Starting add_expense route ===")
    current_app.logger.info("Method: %s", request.method)
    current_app.logger.info("Headers: %s", dict(request.headers))
    current_app.logger.info("Form data: %s", request.form.to_dict())

    # Get form choices
    categories, restaurants = _get_form_choices(current_user.id)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    current_app.logger.info(f"Is AJAX request: {is_ajax}")

    # Get restaurant_id from query parameters if present
    restaurant_id = request.args.get("restaurant_id")
    current_app.logger.info(f"Restaurant ID from query params: {restaurant_id}")

    # Initialize form with choices and restaurant_id if provided
    form = ExpenseForm(
        category_choices=[("", "Select a category (optional)")] + categories,
        restaurant_choices=[("", "Select a restaurant (optional)")] + restaurants,
        restaurant_id=restaurant_id,
        meta={"csrf": False},  # We'll handle CSRF in the form
    )

    current_app.logger.info("Form initialized with choices")

    if request.method == "POST":
        current_app.logger.info("=== Processing POST request ===")
        current_app.logger.info(f"Request form data: {request.form.to_dict()}")
        current_app.logger.info(f"Request JSON: {request.get_json(silent=True) or 'No JSON data'}")

        # Convert form data to dict for validation
        form_data = request.form.to_dict()
        current_app.logger.info(f"Form data after conversion: {form_data}")

        # Log CSRF token if present
        csrf_token = request.headers.get("X-CSRFToken") or request.form.get("csrf_token")
        current_app.logger.info(f"CSRF Token: {'Present' if csrf_token else 'Missing'}")

        # Create form instance with the submitted data and restaurant_id
        form = ExpenseForm(
            data=form_data,
            category_choices=[("", "Select a category (optional)")] + categories,
            restaurant_choices=[("", "Select a restaurant (optional)")] + restaurants,
            restaurant_id=restaurant_id,  # Pass the restaurant_id from query params
            meta={"csrf": False},
        )

        current_app.logger.info(f"Form initialized. Is valid: {form.validate()}")
        current_app.logger.info(f"Form errors: {form.errors}")
        current_app.logger.info(f"Form data after validation: {form.data}")

        # Validate form
        if not form.validate():
            current_app.logger.warning(f"Form validation failed. Errors: {form.errors}")
            if is_ajax:
                return jsonify({"success": False, "message": "Form validation failed", "errors": form.errors}), 400
            return render_template("expenses/form.html", form=form, is_edit=False)

        # If form is valid, try to create the expense
        try:
            current_app.logger.info("Form validation successful, creating expense...")
            expense, error = expense_services.create_expense(current_user.id, form)

            if error:
                current_app.logger.error(f"Error creating expense: {error}")
                if is_ajax:
                    return jsonify({"success": False, "message": str(error), "errors": {"_error": [str(error)]}}), 400
                flash(str(error), "error")
                return render_template("expenses/form.html", form=form, is_edit=False)

            # Success case
            current_app.logger.info(f"Successfully created expense with ID: {expense.id}")
            if is_ajax:
                return (
                    jsonify(
                        {
                            "success": True,
                            "message": "Expense added successfully!",
                            "redirect": url_for("expenses.list_expenses"),
                        }
                    ),
                    200,
                )

            flash("Expense added successfully!", "success")
            return redirect(url_for("expenses.list_expenses"))

        except Exception as e:
            current_app.logger.error(f"Unexpected error in add_expense: {str(e)}", exc_info=True)
            error_msg = "An unexpected error occurred. Please try again."
            if is_ajax:
                return jsonify({"success": False, "message": error_msg, "error": str(e)}), 500
            flash(error_msg, "error")
            return render_template("expenses/form.html", form=form, is_edit=False)

    # Handle GET request or form with validation errors
    current_app.logger.info("Rendering expense form")
    return render_template(
        "expenses/form.html",
        title="Add Expense",
        form=form,
        is_edit=False,
    )


def _get_expense_for_editing(expense_id: int) -> Tuple[Optional[Expense], Optional[ResponseReturnValue]]:
    """Retrieve an expense for editing or return an error response.

    Args:
        expense_id: ID of the expense to edit

    Returns:
        A tuple of (expense, error_response) where only one will be non-None
    """
    expense = _get_expense_or_404(expense_id)
    if not expense:
        return None, _handle_expense_not_found()
    return expense, None


def _setup_expense_form() -> Tuple[FlaskForm, list, list]:
    """Set up the expense form with choices.

    Returns:
        A tuple of (form, categories, restaurants)
    """
    categories, restaurants = _get_form_choices(current_user.id)
    form = _init_expense_form(categories, restaurants)
    return form, categories, restaurants


def _process_edit_request(expense: Expense) -> ResponseReturnValue:
    """Process an edit request based on the HTTP method.

    Args:
        expense: The expense being edited

    Returns:
        The appropriate response for the request
    """
    if request.method == "GET":
        return _handle_get_request(expense)
    if request.method == "POST":
        return _handle_post_request(expense)
    return _handle_unsupported_method()


@bp.route("/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def edit_expense(expense_id: int) -> ResponseReturnValue:
    """Edit an existing expense.

    This endpoint handles both displaying the edit form (GET) and processing form
    submissions (POST) for editing an existing expense.

    Args:
        expense_id: ID of the expense to edit

    Returns:
        Rendered template or JSON response for AJAX requests
    """
    expense, error_response = _get_expense_for_editing(expense_id)
    if error_response:
        return error_response

    return _process_edit_request(expense)


def _initialize_expense_edit(expense_id: int) -> Tuple[Optional[Expense], Optional[ResponseReturnValue]]:
    """Initialize the expense edit process.

    Args:
        expense_id: ID of the expense to edit

    Returns:
        A tuple containing:
        - The expense object if found, None otherwise
        - A response to return if there was an error, None otherwise
    """
    expense = _get_expense_or_404(expense_id)
    if not expense:
        return None, _handle_expense_not_found()
    return expense, None


def _handle_get_request(expense: Expense) -> ResponseReturnValue:
    """Handle GET request for editing an expense.

    Args:
        expense: The expense to edit

    Returns:
        Rendered template with the edit form
    """
    categories, restaurants = _get_form_choices(current_user.id)
    form = _init_expense_form(categories, restaurants)
    _populate_expense_form(form, expense)
    return _render_expense_form(form, expense, categories, is_edit=True)


def _handle_post_request(expense: Expense) -> ResponseReturnValue:
    """Handle POST request for updating an expense.

    Args:
        expense: The expense to update

    Returns:
        Redirect or JSON response based on the request type
    """
    categories, restaurants = _get_form_choices(current_user.id)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    form = _init_expense_form(categories, restaurants)
    return _handle_expense_update(expense, form, categories, restaurants, is_ajax)


def _handle_unsupported_method() -> ResponseReturnValue:
    """Handle unsupported HTTP methods.

    Returns:
        A 405 Method Not Allowed response
    """
    return ("Method Not Allowed", 405, {"Allow": "GET, POST"})


def _get_expense_or_404(expense_id: int) -> Expense:
    """Retrieve an expense by ID or return None if not found."""
    return expense_services.get_expense_by_id(expense_id, current_user.id)


def _handle_expense_not_found() -> ResponseReturnValue:
    """Handle case when expense is not found."""
    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return {"success": False, "message": "Expense not found"}, 404
    flash("Expense not found.", "error")
    return redirect(url_for("expenses.list_expenses"))


def _init_expense_form(categories: list[tuple[str, str]], restaurants: list[tuple[str, str]]) -> ExpenseForm:
    """Initialize an expense form with the given choices."""
    return ExpenseForm(
        category_choices=[("", "Select a category (optional)")] + categories,
        restaurant_choices=[("", "Select a restaurant")] + restaurants,
        meta={"csrf": False},
    )


def _populate_expense_form(form: ExpenseForm, expense: Expense) -> None:
    """Populate the expense form with existing expense data."""
    form.process(obj=expense)
    if expense.category_id:
        form.category_id.data = str(expense.category_id)
    if expense.restaurant_id:
        form.restaurant_id.data = str(expense.restaurant_id)
    if expense.meal_type:
        form.meal_type.data = expense.meal_type


def _handle_expense_update(
    expense: Expense,
    form: ExpenseForm,
    categories: list[tuple[str, str]],
    restaurants: list[tuple[str, str]],
    is_ajax: bool,
) -> ResponseReturnValue:
    """Handle the expense update form submission."""
    form = _reinitialize_form_with_data(form, categories, restaurants)

    if form.validate():
        updated_expense, error = expense_services.update_expense(expense, form)
        if error:
            return _handle_update_error(error, is_ajax)
        return _handle_update_success(expense.id, is_ajax)

    return _handle_validation_errors(form, is_ajax)


def _reinitialize_form_with_data(
    form: ExpenseForm, categories: list[tuple[str, str]], restaurants: list[tuple[str, str]]
) -> ExpenseForm:
    """Reinitialize form with submitted data and choices."""
    form_data = request.form.to_dict()
    return ExpenseForm(
        data=form_data,
        category_choices=[("", "Select a category (optional)")] + categories,
        restaurant_choices=[("", "Select a restaurant")] + restaurants,
        meta={"csrf": False},
    )


def _handle_update_error(error: str, is_ajax: bool) -> ResponseReturnValue:
    """Handle update error response."""
    if is_ajax:
        return {"success": False, "message": error, "errors": {"_error": [error]}}, 400
    flash(error, "error")
    return None


def _handle_update_success(expense_id: int, is_ajax: bool) -> ResponseReturnValue:
    """Handle successful update response."""
    if is_ajax:
        return {
            "success": True,
            "message": "Expense updated successfully!",
            "redirect": url_for("expenses.expense_details", expense_id=expense_id),
        }
    flash("Expense updated successfully!", "success")
    return redirect(url_for("expenses.expense_details", expense_id=expense_id))


def _handle_validation_errors(form: ExpenseForm, is_ajax: bool) -> ResponseReturnValue:
    """Handle form validation errors."""
    if is_ajax and form.errors:
        return {"success": False, "errors": form.errors}, 400
    return None


def _render_expense_form(
    form: ExpenseForm, expense: Expense, categories: list[tuple[str, str]], is_edit: bool = False
) -> str:
    """Render the expense form template."""
    if request.method == "GET":
        form.amount.data = str(expense.amount) if expense.amount else ""
        form.date.data = expense.date
        form.notes.data = expense.notes or ""
        form.category_id.data = str(expense.category_id) if expense.category_id else ""
        form.restaurant_id.data = str(expense.restaurant_id) if expense.restaurant_id else ""
        form.meal_type.data = expense.meal_type or ""

    return render_template(
        "expenses/form.html",
        form=form,
        expense=expense if is_edit else None,
        is_edit=is_edit,
        categories=categories,
        debug=current_app.debug,
    )


@bp.route("/")
@login_required
def list_expenses() -> str:
    """List all expenses for the current user with optional filtering.

    Returns:
        Rendered template with paginated expenses and filter options
    """
    # Get pagination parameters with type hints
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", PER_PAGE, type=int)

    # Get expenses for the current user with optional filtering
    query = Expense.query.filter_by(user_id=current_user.id)

    # Apply filters from query parameters with type safety
    if "category" in request.args and request.args["category"]:
        try:
            query = query.filter_by(category_id=int(request.args["category"]))
        except (ValueError, TypeError):
            pass  # Ignore invalid category IDs

    if "month" in request.args and request.args["month"]:
        try:
            month, year = request.args["month"].split("/")
            query = query.filter(
                extract("month", Expense.date) == int(month),
                extract("year", Expense.date) == int(year),
            )
        except (ValueError, AttributeError):
            pass  # Ignore invalid month/year format

    if "year" in request.args and request.args["year"]:
        try:
            query = query.filter(extract("year", Expense.date) == int(request.args["year"]))
        except (ValueError, TypeError):
            pass  # Ignore invalid year

    # Order by date descending (newest first)
    expenses = query.order_by(desc(Expense.date)).all()
    total_amount = sum(e.amount for e in expenses)  # type: ignore

    # Calculate pagination with bounds checking
    total_pages = max(1, ceil(len(expenses) / per_page)) if expenses else 1
    page = max(1, min(page, total_pages))  # Ensure page is within bounds
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_expenses = expenses[start_idx:end_idx]

    # Get filter options for the filter form
    filter_options = expense_services.get_filter_options(current_user.id)

    # Prepare filter values for the template with type safety
    search = str(request.args.get("q", ""))
    start_date = str(request.args.get("start_date", ""))
    end_date = str(request.args.get("end_date", ""))

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


@bp.route("/<int:expense_id>")
@login_required
def expense_details(expense_id: int) -> ResponseReturnValue:
    """View details of a specific expense.

    Args:
        expense_id: The ID of the expense to view

    Returns:
        Rendered template with expense details or redirect
    """
    expense = expense_services.get_expense_by_id(expense_id, current_user.id)
    if not expense:
        flash("Expense not found.", "error")
        return redirect(url_for("expenses.list_expenses"))

    return render_template("expenses/details.html", expense=expense)


@bp.route("/<int:expense_id>/delete", methods=["POST"])
@login_required
@db_transaction(
    success_message=FlashMessages.EXPENSE_DELETED,
    error_message=FlashMessages.EXPENSE_DELETE_ERROR,
)
def delete_expense(expense_id: int) -> FlaskResponse | WerkzeugResponse:
    """Delete an expense.

    Args:
        expense_id: The ID of the expense to delete

    Returns:
        Redirect to expenses list

    Raises:
        404: If expense is not found
        403: If user doesn't have permission to delete the expense
    """
    expense = Expense.query.get_or_404(expense_id)
    if expense.user_id != current_user.id:
        abort(403)
    expense_services.delete_expense(expense)
    return redirect(url_for("expenses.list_expenses"))
