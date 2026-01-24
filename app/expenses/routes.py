"""Expense-related routes for the application."""

# Standard library imports
import csv
import io
import json
from math import ceil

# Type annotations for responses
from typing import Any, Optional, Tuple, Union

from flask import (
    Response,
    abort,
    current_app,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

# Third-party imports
from flask_wtf import FlaskForm

ResponseReturnValue = Union[str, Response, tuple]

from app.constants.categories import get_default_categories

# Local application imports
from app.expenses import bp, models as expense_models, services as expense_services
from app.expenses.forms import ExpenseForm, ExpenseImportForm
from app.expenses.models import Category, Expense
from app.extensions import db
from app.restaurants.models import Restaurant
from app.utils.decorators import db_transaction
from app.utils.messages import FlashMessages
from app.utils.timezone_utils import (
    get_browser_timezone_info,
    get_timezone_abbreviation,
)

# Constants
PER_PAGE = 10  # Number of expenses per page
SHOW_ALL = -1  # Special value to show all expenses


def _get_page_size_from_cookie(cookie_name: str = "expense_page_size", default_size: int = PER_PAGE) -> int:
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


def _sort_categories_by_default_order(categories: list[Category]) -> list[Category]:
    """Sort categories according to the default definition order."""
    default_categories = get_default_categories()
    default_names = [cat["name"] for cat in default_categories]

    # Create a mapping of category name to order index
    name_to_order: dict[str, int] = {name: i for i, name in enumerate(default_names)}

    # Sort categories: default categories first (in original order), then others
    def sort_key(cat: Category) -> tuple[int, int]:
        cat_name = cat.name
        if cat_name in name_to_order:
            order_idx = name_to_order[cat_name]
            return (0, order_idx)  # Default categories first
        # For custom categories, use hash of name for consistent ordering
        return (1, hash(cat_name) % 10000)  # Custom categories after, alphabetically

    return sorted(categories, key=sort_key)


def _get_form_choices(
    user_id: int,
) -> tuple[list[tuple[int, str, str, str | None]], list[tuple[int, str]]]:
    """Get category and restaurant choices for the expense form.

    Args:
        user_id: ID of the current user

    Returns:
        Tuple of (category_choices, restaurant_choices)
    """
    # Ensure the user has baseline categories to choose from
    _ensure_default_categories_for_user(user_id)
    # Get categories and sort them by default order
    categories_query = Category.query.filter_by(user_id=user_id).all()
    sorted_categories = _sort_categories_by_default_order(categories_query)
    categories: list[tuple[int, str, str, str | None]] = []
    for c in sorted_categories:
        cat_id: int = c.id
        cat_name: str = c.name
        # Note: cat_id and cat_name are non-nullable, so no None check needed
        color_val: str = c.color if c.color else "#6c757d"
        icon_val: str | None = c.icon
        categories.append((cat_id, cat_name, color_val, icon_val))
    restaurants: list[tuple[int, str]] = [
        (r.id, r.name) for r in Restaurant.query.filter_by(user_id=user_id).order_by(Restaurant.name).all()
    ]
    return categories, restaurants


def _ensure_default_categories_for_user(user_id: int) -> None:
    """Create baseline categories for a user if they have none."""
    from app.constants.categories import get_default_categories

    existing_names = {c.name for c in Category.query.filter_by(user_id=user_id).all()}
    default_categories = get_default_categories()

    created_any = False
    for cat in default_categories:
        if cat["name"] not in existing_names:
            db.session.add(
                Category(
                    user_id=user_id,
                    name=cat["name"],
                    description=cat.get("description"),
                    color=cat.get("color"),
                    icon=cat.get("icon"),
                    is_default=True,
                )
            )
            created_any = True

    if created_any:
        db.session.commit()


def _initialize_expense_form() -> tuple[ExpenseForm, bool]:
    """Initialize the expense form with choices and handle AJAX detection.

    Returns:
        Tuple of (form, is_ajax)
    """
    current_app.logger.info("Initializing expense form")
    categories, restaurants = _get_form_choices(current_user.id)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    restaurant_id = request.args.get("restaurant_id")

    # Normalize restaurant_id to int/None to match SelectField coerce
    try:
        normalized_restaurant_id = int(restaurant_id) if restaurant_id and str(restaurant_id).isdigit() else None
    except (ValueError, TypeError):
        normalized_restaurant_id = None

    # Set default date to current date in browser's timezone
    from app.utils.timezone_utils import get_current_time_in_browser_timezone

    browser_timezone, _ = get_browser_timezone_info()
    current_datetime_browser_tz = get_current_time_in_browser_timezone(browser_timezone)
    current_date_browser_tz = current_datetime_browser_tz.date()
    current_time_browser_tz = current_datetime_browser_tz.time()

    form = ExpenseForm(
        category_choices=[(None, "Select a category (optional)")] + [(c[0], c[1]) for c in categories],
        restaurant_choices=[(None, "Select a restaurant")] + restaurants,
        restaurant_id=normalized_restaurant_id,
        date=current_date_browser_tz,
        time=current_time_browser_tz,
    )
    return form, is_ajax


def _handle_expense_creation(form: ExpenseForm, is_ajax: bool) -> ResponseReturnValue:
    """Handle the expense creation process.

    Args:
        form: The validated form
        is_ajax: Whether the request is an AJAX request

    Returns:
        Response with appropriate success/error message
    """
    try:
        # Get receipt file if uploaded
        receipt_file = request.files.get("receipt_image")
        expense, error = expense_services.create_expense(current_user.id, form, receipt_file)

        if error:
            return _handle_creation_error(error, form, is_ajax)

        if expense is None:
            return _handle_creation_error("Failed to create expense", form, is_ajax, status_code=500)

        return _handle_creation_success(expense, is_ajax)

    except Exception as e:
        current_app.logger.error(f"Unexpected error in _handle_expense_creation: {str(e)}", exc_info=True)
        extra_data: dict[str, Any] = {"error": str(e)}
        return _handle_creation_error("An unexpected error occurred", form, is_ajax, status_code=500, **extra_data)


def _handle_creation_error(
    error: str, form: ExpenseForm, is_ajax: bool, status_code: int = 400, **extra: dict
) -> ResponseReturnValue:
    """Handle expense creation errors.

    Args:
        error: Error message
        form: The form with validation errors
        is_ajax: Whether the request is an AJAX request
        status_code: HTTP status code to return
        extra: Additional error details

    Returns:
        Error response in appropriate format
    """
    current_app.logger.error(f"Error creating expense: {error}")
    if is_ajax:
        response = {"success": False, "message": str(error), "errors": {"_error": [str(error)]}}
        response.update(extra)
        return jsonify(response), status_code

    flash(str(error), "error")
    # Get browser timezone for display
    browser_timezone, timezone_display = get_browser_timezone_info()

    return (
        render_template(
            "expenses/form.html",
            form=form,
            is_edit=False,
            browser_timezone=browser_timezone,
            timezone_display=timezone_display,
        ),
        status_code,
    )


def _handle_creation_success(expense: Expense, is_ajax: bool) -> ResponseReturnValue:
    """Handle successful expense creation.

    Args:
        expense: The created expense
        is_ajax: Whether the request is an AJAX request

    Returns:
        Success response in appropriate format
    """
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
    return redirect(url_for("expenses.list_expenses"))  # type: ignore[return-value]  # type: ignore[return-value]


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add_expense() -> ResponseReturnValue:
    """Add a new expense.

    Returns:
        Rendered template or JSON response for AJAX requests
    """
    current_app.logger.info("=== Starting add_expense route ===")
    current_app.logger.info("Method: %s", request.method)

    # Initialize form and check if it's an AJAX request
    form, is_ajax = _initialize_expense_form()

    if request.method == "POST":
        current_app.logger.info("Processing POST request")
        current_app.logger.info("Form data: %s", request.form.to_dict())
        current_app.logger.info("Tags data: %s", request.form.get("tags"))

        # Create form with submitted data
        form = ExpenseForm(
            data=request.form.to_dict(),
            category_choices=form.category_id.choices,
            restaurant_choices=form.restaurant_id.choices,
            restaurant_id=form.restaurant_id.data,
        )

        # Validate form
        if not form.validate():
            current_app.logger.warning(f"Form validation failed. Errors: {form.errors}")
            if is_ajax:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "Form validation failed",
                            "errors": form.errors,
                        }
                    ),
                    400,
                )
            # Get browser timezone for display
            browser_timezone, timezone_display = get_browser_timezone_info()

            return render_template(
                "expenses/form.html",
                form=form,
                is_edit=False,
                browser_timezone=browser_timezone,
                timezone_display=timezone_display,
            )

        # Process valid form submission
        return _handle_expense_creation(form, is_ajax)

    # Handle GET request
    current_app.logger.info("Rendering expense form")

    # Get restaurant context if provided
    restaurant = None
    if form.restaurant_id.data:
        restaurant = Restaurant.query.filter_by(id=form.restaurant_id.data, user_id=current_user.id).first()

    # Get browser timezone for display
    browser_timezone, timezone_display = get_browser_timezone_info()

    return render_template(
        "expenses/form.html",
        title="Add Expense",
        form=form,
        is_edit=False,
        restaurant=restaurant,
        browser_timezone=browser_timezone,
        timezone_display=timezone_display,
    )


def _get_expense_for_editing(
    expense_id: int,
) -> tuple[Expense | None, ResponseReturnValue | None]:
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


def _setup_expense_form() -> tuple[FlaskForm, list[tuple[int, str, str, str | None]], list[tuple[int, str]]]:
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
    if expense is None:
        return _handle_expense_not_found()

    return _process_edit_request(expense)


def _initialize_expense_edit(
    expense_id: int,
) -> tuple[Expense | None, ResponseReturnValue | None]:
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
    # CRITICAL: Don't initialize form with default date when editing
    # The default date from _init_expense_form might interfere with our browser timezone date
    form = ExpenseForm(
        category_choices=[(None, "Select a category (optional)")] + [(c[0], c[1]) for c in categories],
        restaurant_choices=[(None, "Select a restaurant")] + restaurants,
    )
    _populate_expense_form(form, expense)
    categories_for_render: list[tuple[int, str, str, str | None]] = categories
    return _render_expense_form(form, expense, categories_for_render, is_edit=True)


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
    categories_for_update: list[tuple[int, str, str, str | None]] = categories
    restaurants_for_update: list[tuple[int, str]] = restaurants
    return _handle_expense_update(expense, form, categories_for_update, restaurants_for_update, is_ajax)


def _handle_unsupported_method() -> ResponseReturnValue:
    """Handle unsupported HTTP methods.

    Returns:
        A 405 Method Not Allowed response
    """
    return ("Method Not Allowed", 405, {"Allow": "GET, POST"})


def _get_expense_or_404(expense_id: int) -> Expense | None:
    """Retrieve an expense by ID or return None if not found."""
    return expense_services.get_expense_by_id(expense_id, current_user.id)


def _handle_expense_not_found() -> ResponseReturnValue:
    """Handle case when expense is not found."""
    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return {"success": False, "message": "Expense not found"}, 404
    flash("Expense not found.", "error")
    return redirect(url_for("expenses.list_expenses"))  # type: ignore[return-value]


def _init_expense_form(
    categories: list[tuple[int, str, str, str | None]], restaurants: list[tuple[int, str]]
) -> ExpenseForm:
    """Initialize an expense form with the given choices."""
    # Set default date to current date in browser's timezone
    from app.utils.timezone_utils import get_current_time_in_browser_timezone

    browser_timezone, _ = get_browser_timezone_info()
    current_datetime_browser_tz = get_current_time_in_browser_timezone(browser_timezone)
    current_date_browser_tz = current_datetime_browser_tz.date()
    current_time_browser_tz = current_datetime_browser_tz.time()
    return ExpenseForm(
        category_choices=[(None, "Select a category (optional)")] + [(c[0], c[1]) for c in categories],
        restaurant_choices=[(None, "Select a restaurant")] + restaurants,
        date=current_date_browser_tz,
        time=current_time_browser_tz,
    )


def _populate_expense_form(form: ExpenseForm, expense: Expense) -> None:
    """Populate the expense form with existing expense data.

    CRITICAL: Date and time must be converted to browser timezone BEFORE extracting
    the date component. This ensures WYSIWYG - what the user sees is what they get.
    """
    from datetime import UTC

    from app.utils.timezone_utils import convert_to_browser_timezone

    browser_timezone, _ = get_browser_timezone_info()
    expense_date = expense.date

    # Ensure expense_date is timezone-aware (assume UTC if naive)
    if expense_date.tzinfo is None:
        expense_date = expense_date.replace(tzinfo=UTC)

    # CRITICAL: Convert to browser timezone FIRST, then extract date and time
    # This ensures the date shown in the form matches what the user sees in list/details
    # DO NOT extract date from UTC datetime - always convert to browser TZ first!
    expense_datetime_browser_tz = convert_to_browser_timezone(expense_date, browser_timezone)

    # Extract date and time from the browser timezone datetime (NOT from UTC!)
    browser_date = expense_datetime_browser_tz.date()
    browser_time = expense_datetime_browser_tz.time()

    # CRITICAL: Do NOT use form.process(obj=expense) because it extracts expense.date.date()
    # which is the UTC date, overwriting our browser timezone date!
    # Instead, manually populate all form fields to ensure browser timezone date is preserved

    # Set date FIRST before anything else to ensure it's not overwritten
    form.date.data = browser_date  # Browser timezone date, NOT UTC!
    form.time.data = browser_time  # Browser timezone time

    # Now set all other fields
    form.amount.data = expense.amount
    form.notes.data = expense.notes
    form.restaurant_id.data = expense.restaurant_id
    form.category_id.data = expense.category_id
    form.meal_type.data = expense.meal_type
    form.order_type.data = expense.order_type
    form.party_size.data = expense.party_size

    # Don't set form.tags.data for editing - let the template handle the display
    # The template sets value="" and data-existing-tags="..." attributes
    # Tom Select will initialize with the data-existing-tags and handle the JSON conversion


def _handle_expense_update(
    expense: Expense,
    form: ExpenseForm,
    categories: list[tuple[int, str, str, str | None]],
    restaurants: list[tuple[int, str]],
    is_ajax: bool,
) -> ResponseReturnValue:
    """Handle the expense update form submission."""
    form = _reinitialize_form_with_data(form, categories, restaurants)

    if form.validate():
        # Get receipt file if uploaded
        receipt_file = request.files.get("receipt_image")
        delete_receipt = request.form.get("delete_receipt", "false").lower() == "true"
        updated_expense, error = expense_services.update_expense(expense, form, receipt_file, delete_receipt)
        if error:
            return _handle_update_error(error, is_ajax)
        # Note: expense is non-nullable parameter, so expense.id is always available
        expense_id: int = expense.id
        return _handle_update_success(expense_id, is_ajax, receipt_deleted=delete_receipt)

    return _handle_validation_errors(form, expense, is_ajax)


def _reinitialize_form_with_data(
    form: ExpenseForm,
    categories: list[tuple[int, str, str, str | None]],
    restaurants: list[tuple[int, str]],
) -> ExpenseForm:
    """Reinitialize form with submitted data and choices."""
    form_data = request.form.to_dict()
    current_app.logger.info("Edit form data: %s", form_data)
    current_app.logger.info("Edit tags data: %s", request.form.get("tags"))
    return ExpenseForm(
        data=form_data,
        category_choices=[(None, "Select a category (optional)")] + [(c[0], c[1]) for c in categories],
        restaurant_choices=[(None, "Select a restaurant")] + restaurants,
    )


def _handle_update_error(error: str, is_ajax: bool) -> ResponseReturnValue:
    """Handle update error response."""
    if is_ajax:
        return {"success": False, "message": error, "errors": {"_error": [error]}}, 400
    flash(error, "error")
    # Get browser timezone for display
    browser_timezone, timezone_display = get_browser_timezone_info()

    return (
        render_template(
            "expenses/form.html",
            form=ExpenseForm(),
            is_edit=True,
            browser_timezone=browser_timezone,
            timezone_display=timezone_display,
        ),
        400,
    )


def _handle_update_success(expense_id: int, is_ajax: bool, receipt_deleted: bool = False) -> ResponseReturnValue:
    """Handle successful update response."""
    if is_ajax:
        message = "Receipt deleted successfully!" if receipt_deleted else "Expense updated successfully!"
        return (
            jsonify(
                {
                    "success": True,
                    "message": message,
                    "redirect": url_for("expenses.expense_details", expense_id=expense_id),
                }
            ),
            200,
        )

    # Set appropriate flash message
    if receipt_deleted:
        flash("Receipt deleted successfully!", "success")
    else:
        flash("Expense updated successfully!", "success")

    return redirect(url_for("expenses.expense_details", expense_id=expense_id))  # type: ignore[return-value]


def _handle_validation_errors(form: ExpenseForm, expense: Expense, is_ajax: bool) -> ResponseReturnValue:
    """Handle form validation errors."""
    if is_ajax and form.errors:
        return {"success": False, "errors": form.errors}, 400
    # Get browser timezone for display
    browser_timezone, timezone_display = get_browser_timezone_info()

    return (
        render_template(
            "expenses/form.html",
            form=form,
            expense=expense,
            is_edit=True,
            browser_timezone=browser_timezone,
            timezone_display=timezone_display,
        ),
        400,
    )


def _render_expense_form(
    form: ExpenseForm,
    expense: Expense,
    categories: list[tuple[int, str, str, str | None]],
    is_edit: bool = False,
) -> str:
    """Render the expense form template.

    CRITICAL: Do NOT overwrite form data here!
    The form has already been populated by _populate_expense_form() with the correct
    browser timezone date. Overwriting it here would replace the browser TZ date with
    the UTC date from expense.date, causing the date to display incorrectly.

    The form data is already set correctly by _populate_expense_form() which:
    1. Converts expense.date (UTC) to browser timezone
    2. Extracts the date component from the browser timezone datetime
    3. Sets form.date.data to the browser timezone date

    The old code that was overwriting form.date.data with expense.date (UTC) has been removed.
    """

    # Transform categories for template (include color and icon info)
    categories_for_template = [{"id": c[0], "name": c[1], "color": c[2], "icon": c[3]} for c in categories]

    # Get browser timezone for display
    browser_timezone, timezone_display = get_browser_timezone_info()

    return render_template(
        "expenses/form.html",
        form=form,
        expense=expense if is_edit else None,
        is_edit=is_edit,
        categories=categories_for_template,
        browser_timezone=browser_timezone,
        timezone_display=timezone_display,
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
    # Check for per_page in URL params first, then cookie, then default
    per_page = request.args.get("per_page", type=int)
    if per_page is None:
        per_page = _get_page_size_from_cookie("expense_page_size", PER_PAGE)

    # Extract filters from request using the service layer
    filters = expense_services.get_expense_filters(request)

    # Get filtered expenses using the service layer
    expenses: list[Expense] = []
    total_amount: float = 0.0
    avg_price_per_person: float | None = None
    try:
        expenses, total_amount, avg_price_per_person = expense_services.get_user_expenses(current_user.id, filters)
        current_app.logger.info(f"Found {len(expenses)} expenses for user {current_user.id}")
    except Exception as e:
        current_app.logger.error(f"Error filtering expenses: {str(e)}")

    # Handle pagination or show all
    total_expenses = len(expenses)
    if per_page == SHOW_ALL:
        # Show all expenses without pagination
        paginated_expenses = expenses
        total_pages = 1
        page = 1
    else:
        # Calculate pagination with bounds checking
        total_pages = max(1, ceil(total_expenses / per_page)) if total_expenses else 1
        page = max(1, min(page, total_pages))  # Ensure page is within bounds
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_expenses = expenses[start_idx:end_idx]

    # Get filter options for the filter form
    filter_options = expense_services.get_filter_options(current_user.id)
    # Also get main service filter options for dropdowns
    try:
        main_filter_options = expense_services.get_main_filter_options(current_user.id)
        filter_options.update(main_filter_options)
    except Exception as e:
        current_app.logger.error(f"Error getting filter options: {str(e)}")

    # Get browser timezone for display
    _, timezone_display = get_browser_timezone_info()

    return render_template(
        "expenses/list.html",
        expenses=paginated_expenses,
        total_amount=total_amount,
        avg_price_per_person=avg_price_per_person,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_expenses=total_expenses,
        search=filters["search"],
        meal_type=filters["meal_type"],
        category=filters["category"],
        tags=filters.get("tags", []),  # List of selected tag names
        start_date=filters["start_date"],
        end_date=filters["end_date"],
        timezone_display=timezone_display,
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
        return redirect(url_for("expenses.list_expenses"))  # type: ignore[return-value]  # type: ignore[return-value]  # type: ignore[return-value]

    # Get browser timezone for display
    browser_timezone, timezone_display = get_browser_timezone_info()
    timezone_abbr = get_timezone_abbreviation(browser_timezone)

    return render_template(
        "expenses/details.html",
        expense=expense,
        browser_timezone=browser_timezone,
        timezone_display=timezone_display,
        timezone_abbr=timezone_abbr,
    )


@bp.route("/<int:expense_id>/delete", methods=["POST"])
@login_required
@db_transaction(
    success_message=FlashMessages.EXPENSE_DELETED,
    error_message=FlashMessages.EXPENSE_DELETE_ERROR,
)
def delete_expense(expense_id: int) -> Response:
    """Delete an expense.

    Args:
        expense_id: The ID of the expense to delete

    Returns:
        Redirect to expenses list

    Raises:
        404: If expense is not found
        403: If user doesn't have permission to delete the expense
    """
    # Use SQLAlchemy 2.0 style to avoid LegacyAPIWarning for Query.get()
    expense = db.session.get(Expense, expense_id)
    if expense is None:
        abort(404)
    if expense.user_id != current_user.id:
        abort(403)
    expense_services.delete_expense(expense)
    return redirect(url_for("expenses.list_expenses"))  # type: ignore[return-value]


@bp.route("/export")
@login_required
def export_expenses() -> ResponseReturnValue:
    """Export expenses as CSV or JSON."""
    format_type = request.args.get("format", "csv").lower()
    is_sample = request.args.get("sample", "false").lower() == "true"

    # If sample is requested, generate sample CSV with required fields
    if is_sample:
        sample_data = [
            {
                "date": "2025-01-15",
                "amount": 24.77,
                "restaurant_name": "Sample Restaurant",
                "restaurant_address": "123 Main St, City, ST 12345",
                "category_name": "Dining",
                "meal_type": "lunch",
                "notes": "Sample expense entry",
            },
            {
                "date": "2025-01-16",
                "amount": 15.50,
                "restaurant_name": "Another Restaurant",
                "restaurant_address": "",
                "category_name": "Fast Food",
                "meal_type": "dinner",
                "notes": "",
            },
        ]

        if format_type == "json":
            response = make_response(json.dumps(sample_data, indent=2))
            response.headers["Content-Type"] = "application/json"
            response.headers["Content-Disposition"] = "attachment; filename=sample_expenses.json"
            return response

        # Default to CSV format
        output = io.StringIO()
        fieldnames = ["date", "amount", "restaurant_name", "restaurant_address", "category_name", "meal_type", "notes"]
        writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_NONNUMERIC)
        writer.writeheader()
        writer.writerows(sample_data)

        response = make_response(output.getvalue())
        response.headers["Content-Type"] = "text/csv"
        response.headers["Content-Disposition"] = "attachment; filename=sample_expenses.csv"
        return response

    # Get the data from the service
    expenses = expense_services.export_expenses_for_user(current_user.id)

    if not expenses:
        flash("No expenses found to export", "warning")
        return redirect(url_for("expenses.list_expenses"))  # type: ignore[return-value]  # type: ignore[return-value]

    if format_type == "json":
        response = make_response(json.dumps(expenses, indent=2))
        response.headers["Content-Type"] = "application/json"
        response.headers["Content-Disposition"] = "attachment; filename=expenses.json"
        return response

    # Default to CSV format
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=expenses[0].keys() if expenses else [], quoting=csv.QUOTE_NONNUMERIC)
    writer.writeheader()
    writer.writerows(expenses)

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = "attachment; filename=expenses.csv"
    return response


@bp.route("/import", methods=["GET", "POST"])
@login_required
def import_expenses() -> ResponseReturnValue:
    """Handle expense import from file upload."""
    form = ExpenseImportForm()

    if request.method == "POST" and form.validate_on_submit():
        file = form.file.data
        current_app.logger.info(f"Import request received for file: {file.filename if file else 'None'}")

        if file and file.filename:
            try:
                current_app.logger.info("Processing expense import...")
                success, result_data = expense_services.import_expenses_from_csv(file, current_user.id)
                current_app.logger.info(f"Import result: success={success}, data={result_data}")

                # Handle the structured result data to show appropriate toasts
                if success:
                    # Show success message for imported expenses
                    if result_data.get("success_count", 0) > 0:
                        flash(
                            f"Successfully imported {result_data['success_count']} expenses.",
                            "success",
                        )

                    # Show warning toast for skipped items (duplicates and restaurant warnings)
                    if result_data.get("has_warnings", False):
                        warning_count = result_data.get("skipped_count", 0)
                        flash(
                            f"{warning_count} items were skipped (duplicates or restaurant warnings).",
                            "warning",
                        )

                    # If there are warnings but success, show import summary before redirecting
                    if result_data.get("has_warnings", False) and result_data.get("info_messages"):
                        return render_template(
                            "expenses/import.html",
                            form=form,
                            import_summary=result_data,
                            warnings=result_data.get("info_messages", []),
                        )

                    return redirect(url_for("expenses.list_expenses"))  # type: ignore[return-value]  # type: ignore[return-value]  # type: ignore[return-value]
                else:
                    # Show error toast with summary
                    error_message = result_data.get("message", "Import failed")
                    flash(error_message, "danger")

                    # Pass detailed errors to template for display
                    detailed_errors = result_data.get("error_details", [])
                    current_app.logger.error(f"Import errors: {detailed_errors}")

                    # Render template with error details
                    return render_template(
                        "expenses/import.html",
                        form=form,
                        errors=detailed_errors,
                        import_summary=result_data,
                    )

            except ValueError as e:
                current_app.logger.error("ValueError during import: %s", str(e))
                flash(str(e), "danger")
                return render_template("expenses/import.html", form=form, errors=[str(e)])
            except Exception as e:
                current_app.logger.error("Unexpected error during import: %s", str(e))
                flash("An unexpected error occurred during import", "danger")
                return render_template(
                    "expenses/import.html",
                    form=form,
                    errors=["An unexpected error occurred during import"],
                )
        else:
            flash("Please select a file to upload", "danger")

    return render_template("expenses/import.html", form=form)


# Tag Management Routes
@bp.route("/tags", methods=["GET"])
@login_required
def list_tags() -> ResponseReturnValue:
    """Get all tags for the current user."""
    try:
        user_id = current_user.id
        current_app.logger.debug(f"Fetching tags for user {user_id}")

        # Expire session to ensure fresh data (important after deletions)
        from app.extensions import db

        db.session.expire_all()

        tags = expense_services.get_user_tags(user_id)

        # Defensive check: Verify all tags belong to the current user
        invalid_tags = [tag for tag in tags if tag.user_id != user_id]
        if invalid_tags:
            current_app.logger.error(
                f"SECURITY ISSUE: User {user_id} received {len(invalid_tags)} tags that don't belong to them. "
                f"Tag IDs: {[tag.id for tag in invalid_tags]}"
            )
            # Filter out any tags that don't belong to the user
            tags = [tag for tag in tags if tag.user_id == user_id]

        current_app.logger.debug(f"Returning {len(tags)} tags for user {user_id}")
        return jsonify({"success": True, "tags": [tag.to_dict() for tag in tags]})  # type: ignore[no-any-return]
    except Exception as e:
        current_app.logger.error(f"Error fetching tags for user {current_user.id}: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Failed to fetch tags"}), 500


@bp.route("/tags/search", methods=["GET"])
@login_required
def search_tags() -> ResponseReturnValue:
    """Search tags by name."""
    query = request.args.get("q", "").strip()
    limit = request.args.get("limit", 10, type=int)

    try:
        tags = expense_services.search_tags(current_user.id, query, limit)
        return jsonify({"success": True, "tags": [tag.to_dict() for tag in tags]})  # type: ignore[no-any-return]
    except Exception as e:
        current_app.logger.error(f"Error searching tags: {e}")
        return jsonify({"success": False, "message": "Failed to search tags"}), 500


@bp.route("/tags", methods=["POST"])
@login_required
def create_tag() -> ResponseReturnValue:
    """Create a new tag."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400

    name = data.get("name", "").strip()
    color = data.get("color", "#6c757d")
    description = data.get("description", "").strip()

    if not name:
        return jsonify({"success": False, "message": "Tag name is required"}), 400

    try:
        tag = expense_services.create_tag(current_user.id, name, color, description)
        return (
            jsonify(
                {
                    "success": True,
                    "tag": tag.to_dict(),
                    "message": f"Tag '{name}' created successfully",
                }
            ),
            201,
        )
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error creating tag: {e}")
        return jsonify({"success": False, "message": "Failed to create tag"}), 500


@bp.route("/tags/<int:tag_id>", methods=["PUT"])
@login_required
def update_tag(tag_id: int) -> ResponseReturnValue:
    """Update an existing tag."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400

    name = data.get("name", "").strip()
    color = data.get("color", "#6c757d")
    description = data.get("description", "").strip()

    if not name:
        return jsonify({"success": False, "message": "Tag name is required"}), 400

    try:
        tag = expense_services.update_tag(current_user.id, tag_id, name, color, description)
        if tag:
            return (
                jsonify(
                    {
                        "success": True,
                        "tag": tag.to_dict(),
                        "message": f"Tag '{name}' updated successfully",
                    }
                ),
                200,
            )
        else:
            return jsonify({"success": False, "message": "Tag not found"}), 404
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error updating tag: {e}")
        return jsonify({"success": False, "message": "Failed to update tag"}), 500


@bp.route("/tags/<int:tag_id>", methods=["DELETE"])
@login_required
def delete_tag(tag_id: int) -> ResponseReturnValue:
    """Delete a tag.

    The service layer handles all validation (existence, ownership, deletion).
    This route just calls the service and returns appropriate responses.
    """
    from flask import make_response

    try:
        # Call service to delete tag (service handles all validation and ExpenseTag cleanup)
        success = expense_services.delete_tag(current_user.id, tag_id)

        if success:
            current_app.logger.info(f"Tag {tag_id} deleted successfully by user {current_user.id}")
            response = make_response(jsonify({"success": True, "message": "Tag deleted successfully"}), 200)
            response.headers["Content-Type"] = "application/json"
            return response
        else:
            # Service returned False - tag not found or unauthorized
            # Check if tag exists to determine if it's 404 or 403
            tag = db.session.get(expense_models.Tag, tag_id)
            if not tag:
                # Tag doesn't exist
                current_app.logger.warning(
                    f"User {current_user.id} attempted to delete non-existent tag {tag_id}. "
                    f"This may indicate a race condition or stale UI state."
                )
                response = make_response(
                    jsonify(
                        {
                            "success": False,
                            "message": f"Tag {tag_id} not found. It may have been deleted already. Please refresh the page.",
                            "code": 404,
                        }
                    ),
                    404,
                )
            else:
                # Tag exists but doesn't belong to user (unauthorized)
                current_app.logger.warning(
                    f"User {current_user.id} attempted to delete tag {tag_id} owned by user {tag.user_id}. "
                    f"This indicates a security issue - tag should not have been visible to this user."
                )
                response = make_response(
                    jsonify(
                        {
                            "success": False,
                            "message": "You don't have permission to delete this tag. It may belong to another user.",
                            "code": 403,
                        }
                    ),
                    403,
                )
            response.headers["Content-Type"] = "application/json"
            return response
    except Exception as e:
        current_app.logger.error(f"Error deleting tag {tag_id} for user {current_user.id}: {e}", exc_info=True)
        response = make_response(
            jsonify({"success": False, "message": f"An error occurred while deleting the tag: {str(e)}", "code": 500}),
            500,
        )
        response.headers["Content-Type"] = "application/json"
        return response


@bp.route("/<int:expense_id>/tags", methods=["GET"])
@login_required
def get_expense_tags(expense_id: int) -> ResponseReturnValue:
    """Get all tags for an expense."""
    try:
        tags = expense_services.get_expense_tags(expense_id, current_user.id)
        return jsonify({"success": True, "tags": [tag.to_dict() for tag in tags]})  # type: ignore[no-any-return]
    except Exception as e:
        current_app.logger.error(f"Error fetching expense tags: {e}")
        return jsonify({"success": False, "message": "Failed to fetch expense tags"}), 500


@bp.route("/<int:expense_id>/tags", methods=["POST"])
@login_required
def add_expense_tags(expense_id: int) -> ResponseReturnValue:
    """Add tags to an expense."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400

    tag_names = data.get("tags", [])
    if not tag_names:
        return jsonify({"success": False, "message": "No tags provided"}), 400

    try:
        added_tags = expense_services.add_tags_to_expense(expense_id, current_user.id, tag_names)
        return jsonify(  # type: ignore[no-any-return]
            {
                "success": True,
                "tags": [tag.to_dict() for tag in added_tags],
                "message": f"Added {len(added_tags)} tag(s) to expense",
            }
        )
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error adding tags to expense: {e}")
        return jsonify({"success": False, "message": "Failed to add tags to expense"}), 500


@bp.route("/<int:expense_id>/tags", methods=["PUT"])
@login_required
def update_expense_tags(expense_id: int) -> ResponseReturnValue:
    """Update tags for an expense (replace all existing tags)."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400

    tag_names = data.get("tags", [])

    try:
        final_tags = expense_services.update_expense_tags(expense_id, current_user.id, tag_names)
        return jsonify(  # type: ignore[no-any-return]
            {
                "success": True,
                "tags": [tag.to_dict() for tag in final_tags],
                "message": f"Updated expense with {len(final_tags)} tag(s)",
            }
        )
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error updating expense tags: {e}")
        return jsonify({"success": False, "message": "Failed to update expense tags"}), 500


@bp.route("/<int:expense_id>/tags", methods=["DELETE"])
@login_required
def remove_expense_tags(expense_id: int) -> ResponseReturnValue:
    """Remove tags from an expense."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400

    tag_names = data.get("tags", [])
    if not tag_names:
        return jsonify({"success": False, "message": "No tags provided"}), 400

    try:
        removed_tags = expense_services.remove_tags_from_expense(expense_id, current_user.id, tag_names)
        return jsonify(  # type: ignore[no-any-return]
            {
                "success": True,
                "tags": [tag.to_dict() for tag in removed_tags],
                "message": f"Removed {len(removed_tags)} tag(s) from expense",
            }
        )
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error removing tags from expense: {e}")
        return jsonify({"success": False, "message": "Failed to remove tags from expense"}), 500


@bp.route("/tags/popular", methods=["GET"])
@login_required
def get_popular_tags() -> ResponseReturnValue:
    """Get the most popular tags for the current user."""
    limit = request.args.get("limit", 10, type=int)

    try:
        popular_tags = expense_services.get_popular_tags(current_user.id, limit)
        return jsonify({"success": True, "tags": popular_tags})  # type: ignore[no-any-return]
    except Exception as e:
        current_app.logger.error(f"Error fetching popular tags: {e}")
        return jsonify({"success": False, "message": "Failed to fetch popular tags"}), 500
