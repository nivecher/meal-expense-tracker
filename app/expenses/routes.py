"""Expense-related routes for the application."""

# Standard library imports
from datetime import datetime

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
from app.expenses.models import Category  # Import Category model
from app.expenses.models import Expense
from app.restaurants.models import Restaurant  # Import Restaurant model


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add_expense() -> Response | str:
    """Add a new expense."""
    # Get all categories (not user-specific) and order by name
    categories = Category.query.order_by(Category.name).all()
    # Filter restaurants by user and order by name
    restaurants = Restaurant.query.filter_by(user_id=current_user.id).order_by(Restaurant.name).all()
    form, categories, restaurants = _prepare_expense_form(categories, restaurants)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "POST" and form.validate_on_submit():
        expense, error_msg = _create_expense_from_form(form, categories, current_user.id)

        if not expense:
            if is_ajax:
                return jsonify({"status": "error", "message": error_msg}), 400
            flash(error_msg, "danger")
            return render_template("expenses/add.html", form=form, categories=categories, restaurants=restaurants)

        try:
            db.session.add(expense)
            db.session.commit()

            if is_ajax:
                return jsonify(
                    {
                        "status": "success",
                        "message": "Expense added successfully!",
                        "redirect": url_for("expenses.list_expenses"),
                    }
                )

            flash("Expense added successfully!", "success")
            return redirect(url_for("expenses.list_expenses"))

        except Exception as e:
            db.session.rollback()
            error_msg = "An error occurred while saving the expense. Please try again."
            current_app.logger.error(f"Error adding expense: {str(e)}")
            if is_ajax:
                return jsonify({"status": "error", "message": error_msg}), 500
            flash(error_msg, "danger")

    # For GET requests or failed POSTs
    return render_template(
        "expenses/add.html", form=form, categories=categories, restaurants=restaurants, today=datetime.utcnow().date()
    )


@bp.route("/<int:expense_id>/edit", methods=["GET", "POST"])
@login_required
def edit_expense(expense_id: int) -> Response | str:
    """Edit an existing expense."""
    expense = Expense.query.get_or_404(expense_id)
    if expense.user_id != current_user.id:
        abort(403)

    # Get all categories (not user-specific) and order by name
    categories = Category.query.order_by(Category.name).all()
    # Filter restaurants by user and order by name
    restaurants = Restaurant.query.filter_by(user_id=current_user.id).order_by(Restaurant.name).all()
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


def _prepare_expense_form(categories: list, restaurants: list) -> tuple[ExpenseForm, list, list]:
    """Prepare the expense form with the given categories and restaurants.

    Args:
        categories: List of categories to include in the form
        restaurants: List of restaurants to include in the form

    Returns:
        Tuple of (form, categories, restaurants)
    """
    form = ExpenseForm()

    # Set up category choices
    form.category_id.choices = [(str(c.id), c.name) for c in categories]

    # Set up restaurant choices
    form.restaurant_id.choices = [("", "Select a restaurant...")] + [(str(r.id), r.name) for r in restaurants]

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

        # Create expense
        expense = Expense(
            user_id=user_id,
            amount=float(form.amount.data),
            date=datetime.strptime(form.date.data, "%Y-%m-%d"),
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
    if form.category_id.data:
        try:
            category_id = int(form.category_id.data)
            if not any(c.id == category_id for c in categories):
                return False, None, "Invalid category selected"
        except ValueError:
            return False, None, "Invalid category ID format"
    return True, category_id, None


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
    expense.amount = float(form.amount.data)
    expense.date = datetime.strptime(form.date.data, "%Y-%m-%d")
    expense.notes = form.notes.data.strip() if form.notes.data else None
    expense.category_id = category_id
    expense.restaurant_id = int(form.restaurant_id.data) if form.restaurant_id.data else None
    expense.meal_type = form.meal_type.data or None


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


def _populate_expense_form(form: ExpenseForm, expense: Expense) -> None:
    """Populate the form fields with expense data.

    Args:
        form: The form to populate
        expense: The expense containing the data
    """
    form.amount.data = expense.amount
    form.date.data = expense.date.strftime("%Y-%m-%d") if expense.date else ""
    form.notes.data = expense.notes or ""
    form.category_id.data = str(expense.category_id) if expense.category_id else ""
    form.restaurant_id.data = str(expense.restaurant_id) if expense.restaurant_id else ""
    form.meal_type.data = expense.meal_type or ""
