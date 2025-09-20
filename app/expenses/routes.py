"""Expense-related routes for the application."""

# Standard library imports
import csv
import io
import json
from math import ceil

# Type annotations for responses
from typing import Optional, Tuple, Union

from flask import (
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
from flask.wrappers import Response as FlaskResponse

ResponseReturnValue = Union[str, FlaskResponse, tuple]
from flask_login import current_user, login_required

# Third-party imports
from flask_wtf import FlaskForm
from werkzeug.wrappers import Response as WerkzeugResponse

from app.constants.categories import get_default_categories

# Local application imports
from app.expenses import bp
from app.expenses import services as expense_services
from app.expenses.forms import ExpenseForm, ExpenseImportForm
from app.expenses.models import Category, Expense
from app.extensions import db
from app.restaurants.models import Restaurant
from app.utils.decorators import db_transaction
from app.utils.messages import FlashMessages

# Constants
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


def _sort_categories_by_default_order(categories: list[Category]) -> list[Category]:
    """Sort categories according to the default definition order."""
    default_categories = get_default_categories()
    default_names = [cat["name"] for cat in default_categories]

    # Create a mapping of category name to order index
    name_to_order = {name: i for i, name in enumerate(default_names)}

    # Sort categories: default categories first (in original order), then others
    def sort_key(cat):
        if cat.name in name_to_order:
            return (0, name_to_order[cat.name])  # Default categories first
        else:
            return (1, cat.name)  # Custom categories after, alphabetically

    return sorted(categories, key=sort_key)


def _get_form_choices(
    user_id: int,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
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
    categories = [(c.id, c.name, c.color, c.icon) for c in sorted_categories]
    restaurants = [(r.id, r.name) for r in Restaurant.query.filter_by(user_id=user_id).order_by(Restaurant.name).all()]
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

    form = ExpenseForm(
        category_choices=[(None, "Select a category (optional)")] + [(c[0], c[1]) for c in categories],
        restaurant_choices=[(None, "Select a restaurant")] + restaurants,
        restaurant_id=normalized_restaurant_id,
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
        expense, error = expense_services.create_expense(current_user.id, form)

        if error:
            return _handle_creation_error(error, form, is_ajax)

        if expense is None:
            return _handle_creation_error("Failed to create expense", form, is_ajax, status_code=500)

        return _handle_creation_success(expense, is_ajax)

    except Exception as e:
        current_app.logger.error(f"Unexpected error in _handle_expense_creation: {str(e)}", exc_info=True)
        return _handle_creation_error("An unexpected error occurred", form, is_ajax, status_code=500, error=str(e))


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
    return render_template("expenses/form.html", form=form, is_edit=False), status_code


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
    return redirect(url_for("expenses.list_expenses"))


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
                return jsonify({"success": False, "message": "Form validation failed", "errors": form.errors}), 400
            return render_template("expenses/form.html", form=form, is_edit=False)

        # Process valid form submission
        return _handle_expense_creation(form, is_ajax)

    # Handle GET request
    current_app.logger.info("Rendering expense form")

    # Get restaurant context if provided
    restaurant = None
    if form.restaurant_id.data:
        restaurant = Restaurant.query.filter_by(id=form.restaurant_id.data, user_id=current_user.id).first()

    return render_template(
        "expenses/form.html",
        title="Add Expense",
        form=form,
        is_edit=False,
        restaurant=restaurant,
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


def _init_expense_form(categories: list[tuple[int, str, str, str]], restaurants: list[tuple[str, str]]) -> ExpenseForm:
    """Initialize an expense form with the given choices."""
    return ExpenseForm(
        category_choices=[(None, "Select a category (optional)")] + [(c[0], c[1]) for c in categories],
        restaurant_choices=[(None, "Select a restaurant")] + restaurants,
    )


def _populate_expense_form(form: ExpenseForm, expense: Expense) -> None:
    """Populate the expense form with existing expense data."""
    form.process(obj=expense)
    if expense.category_id:
        form.category_id.data = expense.category_id
    if expense.restaurant_id:
        form.restaurant_id.data = expense.restaurant_id
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

    return _handle_validation_errors(form, expense, is_ajax)


def _reinitialize_form_with_data(
    form: ExpenseForm, categories: list[tuple[int, str, str, str]], restaurants: list[tuple[str, str]]
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
    return render_template("expenses/form.html", form=ExpenseForm(), is_edit=True), 400


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


def _handle_validation_errors(form: ExpenseForm, expense: Expense, is_ajax: bool) -> ResponseReturnValue:
    """Handle form validation errors."""
    if is_ajax and form.errors:
        return {"success": False, "errors": form.errors}, 400
    return render_template("expenses/form.html", form=form, expense=expense, is_edit=True), 400


def _render_expense_form(
    form: ExpenseForm, expense: Expense, categories: list[tuple[int, str, str, str]], is_edit: bool = False
) -> str:
    """Render the expense form template."""
    if request.method == "GET":
        form.amount.data = str(expense.amount) if expense.amount else ""
        form.date.data = expense.date
        form.notes.data = expense.notes or ""
        form.category_id.data = expense.category_id if expense.category_id else None
        form.restaurant_id.data = expense.restaurant_id if expense.restaurant_id else None
        form.meal_type.data = expense.meal_type or ""

    # Transform categories for template (include color and icon info)
    categories_for_template = [{"id": c[0], "name": c[1], "color": c[2], "icon": c[3]} for c in categories]

    return render_template(
        "expenses/form.html",
        form=form,
        expense=expense if is_edit else None,
        is_edit=is_edit,
        categories=categories_for_template,
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
    try:
        expenses, total_amount, avg_price_per_person = expense_services.get_user_expenses(current_user.id, filters)
        current_app.logger.info(f"Found {len(expenses)} expenses for user {current_user.id}")
    except Exception as e:
        current_app.logger.error(f"Error filtering expenses: {str(e)}")
        expenses, total_amount, avg_price_per_person = [], 0.0, None

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
        start_date=filters["start_date"],
        end_date=filters["end_date"],
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


@bp.route("/export")
@login_required
def export_expenses():
    """Export expenses as CSV or JSON."""
    format_type = request.args.get("format", "csv").lower()

    # Get the data from the service
    expenses = expense_services.export_expenses_for_user(current_user.id)

    if not expenses:
        flash("No expenses found to export", "warning")
        return redirect(url_for("expenses.list_expenses"))

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
def import_expenses():
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
                        flash(f"Successfully imported {result_data['success_count']} expenses.", "success")

                    # Show warning toast for skipped items (duplicates and restaurant warnings)
                    if result_data.get("has_warnings", False):
                        warning_count = result_data.get("skipped_count", 0)
                        flash(f"{warning_count} items were skipped (duplicates or restaurant warnings).", "warning")

                    # If there are warnings but success, show import summary before redirecting
                    if result_data.get("has_warnings", False) and result_data.get("info_messages"):
                        return render_template(
                            "expenses/import.html",
                            form=form,
                            import_summary=result_data,
                            warnings=result_data.get("info_messages", []),
                        )

                    return redirect(url_for("expenses.list_expenses"))
                else:
                    # Show error toast with summary
                    error_message = result_data.get("message", "Import failed")
                    flash(error_message, "danger")

                    # Pass detailed errors to template for display
                    detailed_errors = result_data.get("error_details", [])
                    current_app.logger.error(f"Import errors: {detailed_errors}")

                    # Render template with error details
                    return render_template(
                        "expenses/import.html", form=form, errors=detailed_errors, import_summary=result_data
                    )

            except ValueError as e:
                current_app.logger.error("ValueError during import: %s", str(e))
                flash(str(e), "danger")
                return render_template("expenses/import.html", form=form, errors=[str(e)])
            except Exception as e:
                current_app.logger.error("Unexpected error during import: %s", str(e))
                flash("An unexpected error occurred during import", "danger")
                return render_template(
                    "expenses/import.html", form=form, errors=["An unexpected error occurred during import"]
                )
        else:
            flash("Please select a file to upload", "danger")

    return render_template("expenses/import.html", form=form)


# Tag Management Routes
@bp.route("/tags", methods=["GET"])
@login_required
def list_tags():
    """Get all tags for the current user."""
    try:
        tags = expense_services.get_user_tags(current_user.id)
        return jsonify({"success": True, "tags": [tag.to_dict() for tag in tags]})
    except Exception as e:
        current_app.logger.error(f"Error fetching tags: {e}")
        return jsonify({"success": False, "message": "Failed to fetch tags"}), 500


@bp.route("/tags/search", methods=["GET"])
@login_required
def search_tags():
    """Search tags by name."""
    query = request.args.get("q", "").strip()
    limit = request.args.get("limit", 10, type=int)

    try:
        tags = expense_services.search_tags(current_user.id, query, limit)
        return jsonify({"success": True, "tags": [tag.to_dict() for tag in tags]})
    except Exception as e:
        current_app.logger.error(f"Error searching tags: {e}")
        return jsonify({"success": False, "message": "Failed to search tags"}), 500


@bp.route("/tags", methods=["POST"])
@login_required
def create_tag():
    """Create a new tag."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400

    # Debug: Log the received data
    current_app.logger.info(f"Creating tag with data: {data}")
    print(f"DEBUG: Creating tag with data: {data}")

    name = data.get("name", "").strip()
    color = data.get("color", "#6c757d")
    description = data.get("description", "").strip()

    # Debug: Log extracted values
    current_app.logger.info(f"Extracted values - name: '{name}', color: '{color}', description: '{description}'")
    print(f"DEBUG: Extracted values - name: '{name}', color: '{color}', description: '{description}'")

    if not name:
        return jsonify({"success": False, "message": "Tag name is required"}), 400

    try:
        tag = expense_services.create_tag(current_user.id, name, color, description)
        return jsonify({"success": True, "tag": tag.to_dict(), "message": f"Tag '{name}' created successfully"}), 201
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error creating tag: {e}")
        return jsonify({"success": False, "message": "Failed to create tag"}), 500


@bp.route("/tags/<int:tag_id>", methods=["PUT"])
@login_required
def update_tag(tag_id):
    """Update an existing tag."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400

    # Debug: Log the received data
    current_app.logger.info(f"Updating tag {tag_id} with data: {data}")
    print(f"DEBUG: Updating tag {tag_id} with data: {data}")

    name = data.get("name", "").strip()
    color = data.get("color", "#6c757d")
    description = data.get("description", "").strip()

    # Debug: Log extracted values
    current_app.logger.info(f"Extracted values - name: '{name}', color: '{color}', description: '{description}'")
    print(f"DEBUG: Extracted values - name: '{name}', color: '{color}', description: '{description}'")

    if not name:
        return jsonify({"success": False, "message": "Tag name is required"}), 400

    try:
        tag = expense_services.update_tag(current_user.id, tag_id, name, color, description)
        if tag:
            return (
                jsonify({"success": True, "tag": tag.to_dict(), "message": f"Tag '{name}' updated successfully"}),
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
def delete_tag(tag_id):
    """Delete a tag."""
    try:
        success = expense_services.delete_tag(current_user.id, tag_id)
        if success:
            return jsonify({"success": True, "message": "Tag deleted successfully"})
        else:
            return jsonify({"success": False, "message": "Tag not found or unauthorized"}), 404
    except Exception as e:
        current_app.logger.error(f"Error deleting tag: {e}")
        return jsonify({"success": False, "message": "Failed to delete tag"}), 500


@bp.route("/<int:expense_id>/tags", methods=["GET"])
@login_required
def get_expense_tags(expense_id):
    """Get all tags for an expense."""
    try:
        tags = expense_services.get_expense_tags(expense_id, current_user.id)
        return jsonify({"success": True, "tags": [tag.to_dict() for tag in tags]})
    except Exception as e:
        current_app.logger.error(f"Error fetching expense tags: {e}")
        return jsonify({"success": False, "message": "Failed to fetch expense tags"}), 500


@bp.route("/<int:expense_id>/tags", methods=["POST"])
@login_required
def add_expense_tags(expense_id):
    """Add tags to an expense."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400

    tag_names = data.get("tags", [])
    if not tag_names:
        return jsonify({"success": False, "message": "No tags provided"}), 400

    try:
        added_tags = expense_services.add_tags_to_expense(expense_id, current_user.id, tag_names)
        return jsonify(
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
def update_expense_tags(expense_id):
    """Update tags for an expense (replace all existing tags)."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400

    tag_names = data.get("tags", [])

    try:
        final_tags = expense_services.update_expense_tags(expense_id, current_user.id, tag_names)
        return jsonify(
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
def remove_expense_tags(expense_id):
    """Remove tags from an expense."""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400

    tag_names = data.get("tags", [])
    if not tag_names:
        return jsonify({"success": False, "message": "No tags provided"}), 400

    try:
        removed_tags = expense_services.remove_tags_from_expense(expense_id, current_user.id, tag_names)
        return jsonify(
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
def get_popular_tags():
    """Get the most popular tags for the current user."""
    limit = request.args.get("limit", 10, type=int)

    try:
        popular_tags = expense_services.get_popular_tags(current_user.id, limit)
        return jsonify({"success": True, "tags": popular_tags})
    except Exception as e:
        current_app.logger.error(f"Error fetching popular tags: {e}")
        return jsonify({"success": False, "message": "Failed to fetch popular tags"}), 500
