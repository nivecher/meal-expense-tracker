"""Service functions for the expenses blueprint."""

import csv
import io
import json
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple, cast

from flask import current_app
from flask_wtf import FlaskForm
from sqlalchemy import extract, func, select
from werkzeug.datastructures import FileStorage

from app.constants.categories import get_default_categories
from app.expenses.forms import ExpenseForm
from app.expenses.models import Category, Expense
from app.extensions import db
from app.restaurants.models import Restaurant


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


def prepare_expense_form(
    user_id: int, form: Optional[FlaskForm] = None
) -> Tuple[ExpenseForm, List[Category], List["Restaurant"]]:
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

    form.category_id.choices = [(None, "Select a category (optional)")] + [(c.id, c.name) for c in categories]
    form.restaurant_id.choices = [(None, "Select a restaurant")] + [(r.id, r.name) for r in restaurants]

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
        # Accept native date objects
        if isinstance(date_value, date):
            return date_value, None
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


def get_expenses_for_user(user_id: int) -> List[Expense]:
    """
    Get all expenses for a specific user.

    Args:
        user_id: ID of the current user

    Returns:
        List of expenses belonging to the user
    """
    return Expense.query.filter_by(user_id=user_id).order_by(Expense.date.desc()).all()


def create_expense_for_user(user_id: int, data: Dict[str, Any]) -> Expense:
    """
    Create a new expense for a user from API data.

    Args:
        user_id: ID of the current user
        data: Dictionary containing expense data

    Returns:
        The created expense
    """
    # Create a new expense object
    expense = Expense(
        user_id=user_id,
        amount=data.get("amount"),
        date=data.get("date"),
        description=data.get("description"),
        category_id=data.get("category_id"),
        restaurant_id=data.get("restaurant_id"),
        notes=data.get("notes"),
    )

    db.session.add(expense)
    db.session.commit()

    return expense


def update_expense_for_user(expense: Expense, data: Dict[str, Any]) -> Expense:
    """
    Update an existing expense for a user from API data.

    Args:
        expense: The expense to update
        data: Dictionary containing updated expense data

    Returns:
        The updated expense
    """
    # Update expense fields
    if "amount" in data:
        expense.amount = data["amount"]
    if "date" in data:
        expense.date = data["date"]
    if "description" in data:
        expense.description = data["description"]
    if "category_id" in data:
        expense.category_id = data["category_id"]
    if "restaurant_id" in data:
        expense.restaurant_id = data["restaurant_id"]
    if "notes" in data:
        expense.notes = data["notes"]

    db.session.commit()

    return expense


def delete_expense_for_user(expense: Expense) -> None:
    """
    Delete an expense for a user.

    Args:
        expense: The expense to delete
    """
    db.session.delete(expense)
    db.session.commit()


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
    # Get unique categories with counts, colors, and icons
    categories_with_counts = (
        db.session.query(Category.name, Category.color, Category.icon, func.count(Expense.id).label("count"))
        .join(Expense, Expense.category_id == Category.id)
        .filter(Expense.user_id == user_id)
        .group_by(Category.name, Category.color, Category.icon)
        .all()
    )

    # Sort categories by default order
    default_categories = get_default_categories()
    default_names = [cat["name"] for cat in default_categories]
    name_to_order = {name: i for i, name in enumerate(default_names)}

    def sort_key(cat_tuple):
        cat_name = cat_tuple[0]  # name is still the first element
        if cat_name in name_to_order:
            return (0, name_to_order[cat_name])  # Default categories first
        else:
            return (1, cat_name)  # Custom categories after, alphabetically

    categories = sorted(categories_with_counts, key=sort_key)

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
    unique_month_options = []
    for m in month_options:
        if m[0] not in seen:
            seen.add(m[0])
            unique_month_options.append(m)
    month_options = unique_month_options

    return {
        "categories": [
            {"name": str(cat[0]), "color": str(cat[1]), "icon": str(cat[2]) if cat[2] else None, "count": int(cat[3])}
            for cat in categories
        ],
        "years": year_options,
        "months": [{"value": m[0], "display": m[1]} for m in month_options],
    }


def export_expenses_for_user(user_id: int) -> List[Dict[str, Any]]:
    """Get all expenses for a user in a format suitable for export.

    Args:
        user_id: The ID of the user whose expenses to export

    Returns:
        A list of dictionaries containing expense data
    """
    expenses = db.session.scalars(select(Expense).where(Expense.user_id == user_id).order_by(Expense.date.desc())).all()

    def safe_float(value):
        """Safely convert value to float."""
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    return [
        {
            "date": expense.date.isoformat() if expense.date else "",
            "amount": safe_float(expense.amount) if expense.amount is not None else "",
            "meal_type": expense.meal_type or "",
            "notes": expense.notes or "",
            "category_name": expense.category.name if expense.category else "",
            "restaurant_name": expense.restaurant.name if expense.restaurant else "",
            "restaurant_address": expense.restaurant.address if expense.restaurant else "",
            "created_at": expense.created_at.isoformat() if expense.created_at else "",
            "updated_at": expense.updated_at.isoformat() if expense.updated_at else "",
        }
        for expense in expenses
    ]


def _validate_import_file(file: FileStorage) -> bool:
    """Validate the uploaded file for expense import.

    Args:
        file: The uploaded file

    Returns:
        True if valid, False otherwise
    """
    if not file or not file.filename:
        current_app.logger.warning("No file provided for import")
        return False

    if not file.filename.lower().endswith((".csv", ".json")):
        current_app.logger.warning(f"Invalid file type: {file.filename}")
        return False

    return True


def _parse_import_file(file: FileStorage) -> Optional[List[Dict[str, Any]]]:
    """Parse the uploaded file and return the data.

    Args:
        file: The uploaded file

    Returns:
        List of expense data dictionaries or None if error
    """
    try:
        if file.filename.lower().endswith(".json"):
            # Reset file pointer to beginning
            file.seek(0)
            data = json.load(file)
            if not isinstance(data, list):
                current_app.logger.error("Invalid JSON format. Expected an array of expenses.")
                return None
            return data

        # Parse CSV file
        file.seek(0)
        csv_data = file.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(csv_data))
        return list(reader)
    except UnicodeDecodeError:
        current_app.logger.error("Error decoding the file. Please ensure it's a valid CSV or JSON file.")
        return None
    except Exception as e:
        current_app.logger.error(f"Error parsing import file: {str(e)}")
        return None


def _process_csv_file(file: FileStorage) -> Tuple[bool, Optional[str], Optional[csv.DictReader]]:
    """Process the CSV file and return a reader.

    Args:
        file: The uploaded CSV file

    Returns:
        Tuple of (success, error_message, csv_reader)
    """
    try:
        file.seek(0)
        csv_data = file.read().decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(csv_data))
        return True, None, csv_reader
    except Exception as e:
        return False, f"Error processing CSV file: {str(e)}", None


def _parse_expense_date(date_str: str) -> Tuple[Optional[date], Optional[str]]:
    """Parse expense date from string.

    Args:
        date_str: The date string to parse

    Returns:
        Tuple of (parsed_date, error_message)
    """
    if not date_str:
        return None, "Date is required"

    try:
        return datetime.fromisoformat(date_str).date(), None
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date(), None
        except ValueError:
            return None, f"Invalid date format: {date_str}"


def _parse_expense_amount(amount_str: str) -> Tuple[Optional[Decimal], Optional[str]]:
    """Parse expense amount from string.

    Args:
        amount_str: The amount string to parse

    Returns:
        Tuple of (parsed_amount, error_message)
    """
    if not amount_str:
        return None, "Amount is required"

    try:
        amount = Decimal(str(amount_str).replace("$", "").replace(",", ""))
        return amount, None
    except (ValueError, InvalidOperation):
        return None, f"Invalid amount: {amount_str}"


def _find_category_by_name(category_name: str, user_id: int) -> Optional[Category]:
    """Find category by name for a user.

    Args:
        category_name: The category name to search for
        user_id: The user ID

    Returns:
        The category if found, None otherwise
    """
    if not category_name:
        return None
    return Category.query.filter_by(user_id=user_id, name=category_name).first()


def _find_restaurant_by_name(restaurant_name: str, user_id: int) -> Optional[Restaurant]:
    """Find restaurant by name for a user.

    Args:
        restaurant_name: The restaurant name to search for
        user_id: The user ID

    Returns:
        The restaurant if found, None otherwise
    """
    if not restaurant_name:
        return None
    return Restaurant.query.filter_by(user_id=user_id, name=restaurant_name).first()


def _create_expense_from_data(data: Dict[str, Any], user_id: int) -> Tuple[Optional[Expense], Optional[str]]:
    """Create an expense from import data.

    Args:
        data: The expense data dictionary
        user_id: The ID of the user creating the expense

    Returns:
        Tuple of (expense, error_message)
    """
    try:
        # Parse date
        expense_date, date_error = _parse_expense_date(data.get("date", "").strip())
        if date_error:
            return None, date_error

        # Parse amount
        amount, amount_error = _parse_expense_amount(str(data.get("amount", "")).strip())
        if amount_error:
            return None, amount_error

        # Find category and restaurant
        category = _find_category_by_name(data.get("category_name", "").strip(), user_id)
        restaurant = _find_restaurant_by_name(data.get("restaurant_name", "").strip(), user_id)

        # Create expense
        expense = Expense(
            user_id=user_id,
            date=expense_date,
            amount=amount,
            meal_type=data.get("meal_type", "").strip() or None,
            notes=data.get("notes", "").strip() or None,
            category_id=category.id if category else None,
            restaurant_id=restaurant.id if restaurant else None,
        )

        return expense, None

    except Exception as e:
        return None, f"Error creating expense: {str(e)}"


def _import_expenses_from_reader(data: List[Dict[str, Any]], user_id: int) -> Tuple[int, List[str]]:
    """Import expenses from parsed data.

    Args:
        data: List of expense data dictionaries
        user_id: The ID of the user importing the expenses

    Returns:
        Tuple of (success_count, errors)
    """
    success_count = 0
    errors = []

    for i, row in enumerate(data, 1):
        try:
            expense, error = _create_expense_from_data(row, user_id)
            if error:
                errors.append(f"Row {i}: {error}")
                continue

            if expense:
                db.session.add(expense)
                success_count += 1

        except Exception as e:
            errors.append(f"Row {i}: Unexpected error - {str(e)}")

    # Limit errors reported to avoid overwhelming output
    if len(errors) > 10:
        errors = errors[:10] + [f"... and {len(errors) - 10} more errors"]

    return success_count, errors


def _generate_import_result(success_count: int, errors: List[str]) -> Tuple[bool, str]:
    """Generate the result of the import operation.

    Args:
        success_count: Number of successfully imported expenses
        errors: List of error messages

    Returns:
        Tuple of (success, message)
    """
    if success_count > 0:
        db.session.commit()

    if errors:
        error_msg = (
            f"{success_count} expenses imported successfully, but {len(errors)} "
            f"rows had errors. Errors: {', '.join(errors)}"
        )
        return success_count > 0, error_msg

    return True, f"{success_count} expenses imported successfully"


def import_expenses_from_csv(file: FileStorage, user_id: int) -> Tuple[bool, str]:
    """Import expenses from a CSV file.

    Args:
        file: The uploaded CSV file
        user_id: ID of the user importing the expenses

    Returns:
        A tuple containing (success: bool, message: str)
    """
    try:
        # Validate file
        if not _validate_import_file(file):
            return False, "Invalid file type. Please upload a CSV or JSON file."

        # Parse file
        data = _parse_import_file(file)
        if data is None:
            return False, "Error parsing file. Please check the file format."

        # Import expenses from the data
        success_count, errors = _import_expenses_from_reader(data, user_id)

        # Generate the result message
        return _generate_import_result(success_count, errors)

    except Exception as e:
        db.session.rollback()
        return False, f"Error processing file: {str(e)}"
