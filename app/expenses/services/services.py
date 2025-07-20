"""Service functions for the expenses blueprint."""

from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple, cast

from flask import current_app
from flask_wtf import FlaskForm
from sqlalchemy import extract, func

from app.expenses.forms import ExpenseForm
from app.expenses.models import Category, Expense
from app.extensions import db
from app.restaurants.models import Restaurant


def prepare_expense_form(
    user_id: int, form: Optional[FlaskForm] = None
) -> Tuple[ExpenseForm, List[Category], List[Restaurant]]:
    """Prepare the expense form with categories and restaurants.

    Args:
        user_id: The ID of the current user
        form: Optional form instance to populate

    Returns:
        A tuple containing:
        - The prepared form
        - List of categories
        - List of restaurants
    """
    if form is None:
        form = ExpenseForm()
    else:
        form = cast(ExpenseForm, form)

    categories: List[Category] = Category.query.order_by(Category.name).all()
    restaurants: List[Restaurant] = Restaurant.query.filter_by(user_id=user_id).order_by(Restaurant.name).all()

    form.category_id.choices = [("", "Select a category (optional)")] + [(str(c.id), c.name) for c in categories]
    form.restaurant_id.choices = [("", "Select a restaurant")] + [(str(r.id), r.name) for r in restaurants]

    if not form.date.data:
        form.date.data = datetime.now(timezone.utc).date()

    return form, categories, restaurants


def _process_category_id(form: ExpenseForm) -> Tuple[Optional[int], Optional[str]]:
    """Process and validate category_id from form data."""
    category_id = form.category_id.data if form.category_id.data else None
    if isinstance(category_id, str):
        try:
            return (int(category_id) if category_id.strip() else None), None
        except (ValueError, TypeError) as e:
            current_app.logger.error("Invalid category_id: %s. Error: %s", form.category_id.data, e)
            return None, f"Invalid category ID: {form.category_id.data}"
    return category_id, None


def _process_restaurant_id(form: ExpenseForm) -> Tuple[Optional[int], Optional[str]]:
    """Process and validate restaurant_id from form data."""
    restaurant_id = form.restaurant_id.data if form.restaurant_id.data else None
    if isinstance(restaurant_id, str):
        try:
            return (int(restaurant_id) if restaurant_id.strip() else None), None
        except (ValueError, TypeError) as e:
            current_app.logger.error("Invalid restaurant_id: %s. Error: %s", form.restaurant_id.data, e)
            return None, f"Invalid restaurant ID: {form.restaurant_id.data}"
    return restaurant_id, None


def _process_date(date_value: Any) -> Tuple[Optional[date], Optional[str]]:
    """Process and validate date from form data."""
    if not date_value:
        return None, "Date is required"

    try:
        if isinstance(date_value, str):
            return datetime.strptime(date_value, "%Y-%m-%d").date(), None
        if hasattr(date_value, "date"):
            return date_value.date(), None
        return None, "Invalid date format"
    except (ValueError, TypeError, AttributeError) as e:
        current_app.logger.error("Invalid date: %s. Error: %s", date_value, e)
        return None, "Invalid date format. Please use YYYY-MM-DD format."


def _process_amount(amount_value: Any) -> Tuple[Optional[Decimal], Optional[str]]:
    """Process and validate amount from form data."""
    try:
        amount_str = str(amount_value)
        return Decimal(amount_str).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), None
    except (ValueError, TypeError, InvalidOperation) as e:
        current_app.logger.error("Invalid amount: %s. Error: %s", amount_value, e)
        return None, f"Invalid amount: {amount_value}"


def create_expense(user_id: int, form: ExpenseForm) -> Tuple[Optional[Expense], Optional[str]]:
    """Create a new expense from form data.

    Args:
        user_id: The ID of the current user
        form: The validated expense form

    Returns:
        A tuple containing:
        - The created expense on success, None on failure
        - Error message on failure, None on success
    """
    try:
        # Process form data
        category_id, error = _process_category_id(form)
        if error:
            return None, error

        restaurant_id, error = _process_restaurant_id(form)
        if error:
            return None, error

        date_value, error = _process_date(form.date.data)
        if error:
            return None, error

        amount, error = _process_amount(form.amount.data)
        if error:
            return None, error

        # Create and save the expense
        expense = Expense(
            user_id=user_id,
            amount=amount,
            date=date_value or datetime.now(timezone.utc).date(),
            notes=form.notes.data.strip() if form.notes.data else None,
            category_id=category_id,
            restaurant_id=restaurant_id,
            meal_type=form.meal_type.data or None,
        )

        db.session.add(expense)
        db.session.commit()
        return expense, None

    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Error creating expense: %s", str(e), exc_info=True)
        return None, f"An error occurred while creating the expense: {str(e)}"


def update_expense(expense: Expense, form: ExpenseForm) -> Tuple[Optional[Expense], Optional[str]]:
    """Update an existing expense from form data.

    Args:
        expense: The expense to update
        form: The validated expense form

    Returns:
        A tuple containing:
        - The updated expense on success, None on failure
        - Error message on failure, None on success
    """
    try:
        current_app.logger.info("Updating expense with form data: %s", form.data)

        # Process form data
        category_id, error = _process_category_id(form)
        if error:
            return None, error

        restaurant_id, error = _process_restaurant_id(form)
        if error:
            return None, error

        date_value, error = _process_date(form.date.data)
        if error:
            return None, error

        amount, error = _process_amount(form.amount.data)
        if error:
            return None, error

        # Update expense fields
        expense.amount = float(amount)
        expense.date = date_value
        expense.notes = form.notes.data.strip() if form.notes.data else None
        expense.category_id = category_id
        expense.restaurant_id = restaurant_id
        expense.meal_type = form.meal_type.data or None

        current_app.logger.info("Updated expense data: %s", expense)
        db.session.commit()
        return expense, None

    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Error updating expense: %s", str(e), exc_info=True)
        return None, f"An error occurred while updating the expense: {str(e)}"


def delete_expense(expense: Expense) -> None:
    """Delete an expense.

    Args:
        expense: The expense to delete
    """
    db.session.delete(expense)


def get_expense_by_id(expense_id: int, user_id: int) -> Optional[Expense]:
    """Get an expense by ID, ensuring it belongs to the user.

    Args:
        expense_id: The ID of the expense to retrieve
        user_id: The ID of the user who owns the expense

    Returns:
        The expense if found and belongs to the user, None otherwise
    """
    return Expense.query.filter_by(id=expense_id, user_id=user_id).first()


def get_expense_by_id_for_user(expense_id: int, user_id: int) -> Optional[Expense]:
    """Get an expense by ID for a specific user.

    Args:
        expense_id: The ID of the expense to retrieve
        user_id: The ID of the user who owns the expense

    Returns:
        The expense if found and belongs to the user, None otherwise
    """
    return get_expense_by_id(expense_id, user_id)


def get_filter_options(user_id: int) -> Dict[str, Any]:
    """
    Get filter options for the expenses list.

    Args:
        user_id: ID of the current user

    Returns:
        Dictionary containing filter options:
        - categories: List of category names and counts
        - years: List of years with expenses
        - months: List of months with expenses (formatted as MM/YYYY)
    """
    # Get unique categories with counts
    categories = (
        db.session.query(Category.name, func.count(Expense.id).label("count"))
        .join(Expense, Expense.category_id == Category.id)
        .filter(Expense.user_id == user_id)
        .group_by(Category.name)
        .order_by(Category.name)
        .all()
    )

    # Get unique years and months with expenses
    date_parts = (
        db.session.query(
            extract("year", Expense.date).label("year"),
            extract("month", Expense.date).label("month"),
        )
        .filter(Expense.user_id == user_id)
        .distinct()
        .order_by("year", "month")
        .all()
    )

    # Format the results
    year_options = sorted({int(part.year) for part in date_parts if part is not None and part.year is not None})

    # Create month options with formatted display
    month_options: List[Tuple[str, str]] = []
    for part in date_parts:
        if part is not None and part.year is not None and part.month is not None:
            month_str = f"{int(part.month):02d}/{int(part.year)}"
            display_str = f"{datetime(1900, int(part.month), 1).strftime('%B')} {int(part.year)}"
            month_options.append((month_str, display_str))

    # Remove duplicates while preserving order
    seen: set[str] = set()
    month_options = [m for m in month_options if not (m[0] in seen or seen.add(m[0]))]

    return {
        "categories": [{"name": str(cat[0]), "count": int(cat[1])} for cat in categories],
        "years": year_options,
        "months": [{"value": m[0], "display": m[1]} for m in month_options],
    }
