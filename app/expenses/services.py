"""Service functions for the expenses blueprint."""

import csv
from datetime import UTC, date, datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
import io
import json
import re
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from flask import Request, current_app
from flask_wtf import FlaskForm
from sqlalchemy import extract, func, or_, select
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import Select
from werkzeug.datastructures import FileStorage

from app.constants.categories import get_default_categories
from app.expenses.forms import ExpenseForm
from app.expenses.models import Category, Expense, ExpenseTag, Tag
from app.extensions import db
from app.restaurants.models import Restaurant

# =============================================================================
# EXPENSE FILTERING AND SEARCH FUNCTIONALITY
# =============================================================================


def get_expense_filters(request: Request) -> dict[str, Any]:
    """Extract and validate filter parameters from the request.

    Args:
        request: The Flask request object

    Returns:
        Dict containing filter parameters
    """
    # Support both 'search' and 'q' parameters for search functionality
    search_term = request.args.get("search", "").strip() or request.args.get("q", "").strip()
    return {
        "search": search_term,
        "meal_type": request.args.get("meal_type", "").strip(),
        "category": request.args.get("category", "").strip(),
        "start_date": request.args.get("start_date", "").strip(),
        "end_date": request.args.get("end_date", "").strip(),
        "sort_by": request.args.get("sort", "date"),
        "sort_order": request.args.get("order", "desc"),
    }


def get_user_expenses(user_id: int, filters: dict[str, Any]) -> tuple[list[Expense], float, float | None]:
    """Get expenses for a user with the given filters.

    Args:
        user_id: The ID of the user
        filters: Dictionary of filter parameters

    Returns:
        Tuple of (expenses, total_amount, avg_price_per_person)
    """
    # Base query with eager loading of tags
    stmt = (
        select(Expense)
        .options(joinedload(Expense.expense_tags).joinedload(ExpenseTag.tag))
        .where(Expense.user_id == user_id)
    )

    # Apply filters
    stmt = apply_filters(stmt, filters)

    # Apply sorting
    stmt = apply_sorting(stmt, filters["sort_by"], filters["sort_order"])

    # Execute query
    result = db.session.execute(stmt)
    expenses_list = list(result.scalars().unique().all())

    # Calculate total
    total_amount = float(sum(expense.amount for expense in expenses_list)) if expenses_list else 0.0

    # Calculate average price per person
    # Include all expenses where party_size is set (including single person)
    # This matches what's displayed in the table
    price_per_person_values: list[float] = []
    for expense in expenses_list:
        if expense.party_size is not None and expense.party_size > 0:
            # Include all expenses with party size set (single or multi-person)
            price_per_person = expense.price_per_person
            if price_per_person is not None:
                price_per_person_values.append(float(price_per_person))

    avg_price_per_person = (
        sum(price_per_person_values) / len(price_per_person_values) if price_per_person_values else None
    )

    return expenses_list, total_amount, avg_price_per_person


def apply_filters(stmt: Select, filters: dict[str, Any]) -> Select:
    """Apply filters to the query with comprehensive search across text fields.

    Args:
        stmt: The SQLAlchemy select statement
        filters: Dictionary of filter parameters

    Returns:
        The modified select statement with filters applied
    """
    # Always join restaurant and category tables for search (using outer joins to include expenses without these)
    stmt = stmt.join(Expense.restaurant, isouter=True)
    stmt = stmt.join(Expense.category, isouter=True)
    # Apply search filter across all text-based fields
    if filters["search"]:
        search_term = f"%{filters['search']}%"
        stmt = stmt.where(
            or_(
                # Restaurant fields (handle NULL values from outer join)
                func.coalesce(Restaurant.name, "").ilike(search_term),
                func.coalesce(Restaurant.address_line_1, "").ilike(search_term),
                func.coalesce(Restaurant.address_line_2, "").ilike(search_term),
                # Expense fields
                func.coalesce(Expense.notes, "").ilike(search_term),
                func.coalesce(Expense.meal_type, "").ilike(search_term),
                # Category fields (handle NULL values from outer join)
                func.coalesce(Category.name, "").ilike(search_term),
            )
        )

    # Apply meal type filter
    if filters["meal_type"]:
        stmt = stmt.where(Expense.meal_type == filters["meal_type"])

    # Apply category filter
    if filters["category"]:
        stmt = stmt.where(Category.name == filters["category"])

    # Apply date range filters with proper error handling
    if filters["start_date"]:
        try:
            start_date: date = datetime.strptime(filters["start_date"], "%Y-%m-%d").date()
            stmt = stmt.where(Expense.date >= start_date)
        except (ValueError, TypeError):
            # Log the error but don't fail the query
            pass

    if filters["end_date"]:
        try:
            end_date: date = datetime.strptime(filters["end_date"], "%Y-%m-%d").date()
            stmt = stmt.where(Expense.date <= end_date)
        except (ValueError, TypeError):
            # Log the error but don't fail the query
            pass

    return stmt


def apply_sorting(stmt: Select, sort_by: str, sort_order: str) -> Select:
    """Apply sorting to the query.

    Args:
        stmt: The SQLAlchemy select statement
        sort_by: Field to sort by
        sort_order: Sort order ('asc' or 'desc')

    Returns:
        The modified select statement with sorting applied
    """
    is_desc = sort_order.lower() == "desc"
    sort_fields: list[Any] = []

    if sort_by == "date":
        # Primary sort by date, secondary sort by created_at for recently entered expenses
        date_col = Expense.date
        created_at_col = Expense.created_at
        primary_field = date_col.desc() if is_desc else date_col.asc()
        secondary_field = created_at_col.desc() if is_desc else created_at_col.asc()
        sort_fields = [primary_field, secondary_field]
    elif sort_by == "amount":
        sort_field: Any = Expense.amount.desc() if is_desc else Expense.amount.asc()
        sort_fields = [sort_field]
    elif sort_by == "meal_type":
        sort_field = Expense.meal_type.desc() if is_desc else Expense.meal_type.asc()
        sort_fields = [sort_field]
    elif sort_by == "category":
        # Sort by category name through the relationship
        stmt = stmt.join(Expense.category)
        sort_field = Category.name.desc() if is_desc else Category.name.asc()
        sort_fields = [sort_field]
    elif sort_by == "restaurant":
        sort_field = Restaurant.name.desc() if is_desc else Restaurant.name.asc()
        sort_fields = [sort_field]
    elif sort_by == "created_at":
        # Sort by created_at only
        sort_field = Expense.created_at.desc() if is_desc else Expense.created_at.asc()
        sort_fields = [sort_field]

    if sort_fields:
        return stmt.order_by(*sort_fields)

    return stmt


def get_main_filter_options(user_id: int) -> dict[str, list[str]]:
    """Get filter options (meal types and categories) for the current user.

    This provides simple filter options for main dashboard filtering.

    Args:
        user_id: The ID of the user

    Returns:
        Dictionary containing filter options
    """
    # Get unique meal types and categories for filter dropdowns
    meal_types = (
        db.session.query(Expense.meal_type).filter(Expense.user_id == user_id, Expense.meal_type != "").distinct().all()
    )

    # Get unique categories through the relationship
    categories = (
        db.session.query(Category.name)
        .join(Expense, Expense.category_id == Category.id)
        .filter(Expense.user_id == user_id)
        .distinct()
        .all()
    )

    return {
        "meal_types": [m[0] for m in meal_types if m[0]],  # Filter out None values
        "categories": [c[0] for c in categories if c[0]],  # Filter out None values
    }


# =============================================================================
# EXISTING FUNCTIONALITY
# =============================================================================


def _sort_categories_by_default_order(categories: list[Category]) -> list[Category]:
    """Sort categories according to the default definition order."""
    default_categories = get_default_categories()
    default_names = [cat["name"] for cat in default_categories]

    # Create a mapping of category name to order index
    name_to_order = {name: i for i, name in enumerate(default_names)}

    # Sort categories: default categories first (in original order), then others
    def sort_key(cat: Category) -> tuple[int, int | str]:
        if cat.name in name_to_order:
            return (0, name_to_order[cat.name])  # Default categories first
        else:
            return (1, cat.name)  # Custom categories after, alphabetically

    return sorted(categories, key=sort_key)


def prepare_expense_form(
    user_id: int, form: FlaskForm | None = None
) -> tuple[ExpenseForm, list[Category], list["Restaurant"]]:
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

    categories: list[Category] = Category.query.order_by(Category.name).all()
    restaurants: list[Restaurant] = Restaurant.query.filter_by(user_id=user_id).order_by(Restaurant.name).all()

    form.category_id.choices = [(None, "Select a category (optional)")] + [(c.id, c.name) for c in categories]
    form.restaurant_id.choices = [(None, "Select a restaurant")] + [(r.id, r.name) for r in restaurants]

    if not form.date.data:
        form.date.data = datetime.now(UTC).date()

    return form, categories, restaurants


def _process_category_id(form: ExpenseForm) -> tuple[int | None, str | None]:
    """Process and validate category_id from form data."""
    category_id = form.category_id.data if form.category_id.data else None
    if isinstance(category_id, str):
        try:
            return (int(category_id) if category_id.strip() else None), None
        except (ValueError, TypeError) as e:
            current_app.logger.error("Invalid category_id: %s. Error: %s", form.category_id.data, e)
            return None, f"Invalid category ID: {form.category_id.data}"
    return category_id, None


def _process_restaurant_id(form: ExpenseForm) -> tuple[int | None, str | None]:
    """Process and validate restaurant_id from form data."""
    restaurant_id = form.restaurant_id.data if form.restaurant_id.data else None
    if isinstance(restaurant_id, str):
        try:
            return (int(restaurant_id) if restaurant_id.strip() else None), None
        except (ValueError, TypeError) as e:
            current_app.logger.error("Invalid restaurant_id: %s. Error: %s", form.restaurant_id.data, e)
            return None, f"Invalid restaurant ID: {form.restaurant_id.data}"
    return restaurant_id, None


def _process_date(date_value: Any) -> tuple[date | None, str | None]:
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


def _process_time(time_value: Any) -> tuple[time | None, str | None]:
    """Process and validate time from form data."""
    if not time_value:
        return None, None  # Time is optional

    try:
        if isinstance(time_value, str):
            return datetime.strptime(time_value, "%H:%M").time(), None
        # Accept native time objects
        if hasattr(time_value, "time"):
            return time_value.time(), None
        if hasattr(time_value, "hour") and hasattr(time_value, "minute"):
            return time_value, None
        return None, "Invalid time format"
    except (ValueError, TypeError, AttributeError) as e:
        current_app.logger.error("Invalid time: %s. Error: %s", time_value, e)
        return None, "Invalid time format. Please use HH:MM format."


def _process_amount(amount_value: Any) -> tuple[Decimal | None, str | None]:
    """Process and validate amount from form data with smart amount support."""
    try:
        amount_str = str(amount_value).strip()

        # Remove any non-numeric characters except decimal point
        clean_value = "".join(c for c in amount_str if c.isdigit() or c == ".")

        # Handle smart amount conversion if no decimal point is present (like Quicken)
        if "." not in clean_value and clean_value.isdigit() and len(clean_value) > 0:
            # Simple rule: assume last 2 digits are cents
            if len(clean_value) == 1:
                # Single digit: 5 → 0.05
                clean_value = f"0.0{clean_value}"
            elif len(clean_value) == 2:
                # Two digits: 50 → 0.50
                clean_value = f"0.{clean_value}"
            else:
                # Three or more digits: 789 → 7.89, 1234 → 12.34
                integer_part = clean_value[:-2]
                cents_part = clean_value[-2:]
                clean_value = f"{integer_part}.{cents_part}"

        amount_decimal = Decimal(clean_value)
        return amount_decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), None
    except (ValueError, TypeError, InvalidOperation) as e:
        current_app.logger.error("Invalid amount: %s. Error: %s", amount_value, e)
        return None, f"Invalid amount: {amount_value}"


def _parse_tags_json(tags_data: str) -> tuple[list | None, str | None]:
    """Parse JSON tags data.

    Args:
        tags_data: JSON string containing tags

    Returns:
        A tuple of (parsed_tags, error_message)
    """
    try:
        current_app.logger.info(f"Attempting to parse JSON: {tags_data}")
        parsed = json.loads(tags_data)
        current_app.logger.info(f"Successfully parsed JSON: {parsed}")
        return parsed, None
    except json.JSONDecodeError as e:
        current_app.logger.error(f"JSON decode error: {e}, data: {tags_data}")
        return None, "Invalid tags format"


def _validate_tags_list(tags_list: Any) -> tuple[list[str] | None, str | None]:
    """Validate and clean tags list.

    Args:
        tags_list: List of tags to validate (can be strings or Tagify objects)

    Returns:
        A tuple of (cleaned_tags, error_message)
    """
    if not isinstance(tags_list, list):
        return None, "Tags must be a list"

    processed_tags = []
    for tag in tags_list:
        # Handle Tagify format: {"value": "tag_name"}
        if isinstance(tag, dict) and "value" in tag:
            tag_name = tag["value"]
        elif isinstance(tag, str):
            tag_name = tag
        else:
            return None, f"Invalid tag format: {tag}"

        tag_clean = tag_name.strip()
        if tag_clean:  # Only add non-empty tags
            processed_tags.append(tag_clean)

    return processed_tags, None


def _process_tags(form: ExpenseForm) -> tuple[list[str] | None, str | None]:
    """Process and validate tags from form data.

    Args:
        form: The expense form containing tags data

    Returns:
        A tuple of (processed_tags, error_message)
    """
    try:
        # Get tags from form data (sent as JSON string from JavaScript)
        tags_data = form.tags.data if hasattr(form, "tags") and form.tags.data else None
        current_app.logger.info(f"Processing tags - raw data: {tags_data}, type: {type(tags_data)}")

        if not tags_data:
            current_app.logger.info("No tags data found")
            return [], None  # No tags is valid

        # Parse JSON if it's a string
        if isinstance(tags_data, str):
            # Try to parse as JSON first
            tags_list, error = _parse_tags_json(tags_data)
            if error:
                # If JSON parsing fails, treat as a single tag name (fallback for plain text)
                current_app.logger.info(f"Tags data is not JSON, treating as single tag: {tags_data}")
                tags_list = [tags_data.strip()] if tags_data.strip() else []
        else:
            tags_list = tags_data  # type: ignore[unreachable]

        # Validate and clean tags
        result = _validate_tags_list(tags_list)
        current_app.logger.info(f"Tags processing result: {result}")
        return result

    except Exception as e:
        current_app.logger.error(f"Error processing tags: {str(e)}")
        return None, f"Error processing tags: {str(e)}"


def _add_tags_to_expense(expense_id: int, user_id: int, tags: list[str]) -> None:
    """Add tags to an expense safely.

    Args:
        expense_id: ID of the expense
        user_id: ID of the user
        tags: List of tag names to add
    """
    try:
        update_expense_tags(expense_id, user_id, tags)
    except Exception as e:
        current_app.logger.warning(f"Failed to add tags to expense {expense_id}: {str(e)}")


def create_expense(
    user_id: int, form: ExpenseForm, receipt_file: FileStorage | None = None
) -> tuple[Expense | None, str | None]:
    """Create a new expense from form data.

    Args:
        user_id: The ID of the current user
        form: The validated expense form
        receipt_file: Optional uploaded receipt file

    Returns:
        A tuple containing:
        - The created expense on success, None on failure
        - Error message on failure, None on success
    """
    try:
        # Get browser timezone for proper time handling
        from app.utils.timezone_utils import get_browser_timezone, normalize_timezone

        browser_timezone_raw = get_browser_timezone() or "UTC"
        browser_timezone = normalize_timezone(browser_timezone_raw) or "UTC"
        # Process form data
        expense_data = _process_expense_form_data(form, browser_timezone)
        if isinstance(expense_data, str):  # Error message
            return None, expense_data

        category_id, restaurant_id, datetime_value, amount, tags = expense_data

        # Handle receipt upload if provided
        receipt_image_path = None
        if receipt_file and receipt_file.filename:
            try:
                from flask import current_app

                from app.expenses.utils import save_receipt_to_storage

                upload_folder = current_app.config.get("UPLOAD_FOLDER")
                if not isinstance(upload_folder, str):
                    return None, "UPLOAD_FOLDER configuration is not set"
                storage_path, error = save_receipt_to_storage(receipt_file, upload_folder)

                if error:
                    return None, error

                receipt_image_path = storage_path
                current_app.logger.info(f"Receipt saved: {receipt_image_path}")
            except Exception as e:
                current_app.logger.error(f"Failed to save receipt: {str(e)}")
                return None, f"Failed to save receipt: {str(e)}"

        # Create and save the expense
        # Use current datetime in browser's timezone if no datetime provided
        if not datetime_value:
            from app.utils.timezone_utils import (
                get_browser_timezone,
                get_current_time_in_browser_timezone,
                normalize_timezone,
            )

            browser_timezone_raw = get_browser_timezone() or "UTC"
            browser_timezone = normalize_timezone(browser_timezone_raw) or "UTC"
            datetime_value = get_current_time_in_browser_timezone(browser_timezone)

        expense = Expense(
            user_id=user_id,
            amount=amount,
            date=datetime_value,
            notes=form.notes.data.strip() if form.notes.data else None,
            category_id=category_id,
            restaurant_id=restaurant_id,
            meal_type=form.meal_type.data or None,
            order_type=form.order_type.data or None,
            party_size=form.party_size.data,
            receipt_image=receipt_image_path,
        )

        db.session.add(expense)
        db.session.commit()

        # Add tags to the expense after it's created
        if tags:
            _add_tags_to_expense(expense.id, user_id, tags)

        # Recalculate restaurant statistics since we added a new expense
        from app.restaurants.services import recalculate_restaurant_statistics

        recalculate_restaurant_statistics(user_id)

        return expense, None

    except Exception as e:
        db.session.rollback()
        current_app.logger.error("Error creating expense: %s", str(e), exc_info=True)
        return None, f"An error occurred while creating the expense: {str(e)}"


def _combine_date_time_with_timezone(date_value: date, time_value: time | None, browser_timezone: str) -> datetime:
    """Combine date and time into a datetime object, handling timezone conversion.

    WYSIWYG (What You See Is What You Get): The user enters date/time in their browser timezone,
    and that's exactly what gets stored (converted to UTC). When displayed back, it will show
    the same date/time in the browser timezone.

    Args:
        date_value: The date value (required) - interpreted as date in browser timezone
        time_value: The time value (optional) - interpreted as time in browser timezone
        browser_timezone: Browser timezone string (already normalized)

    Returns:
        Datetime object in UTC (timezone-aware for proper database storage)
        Note: The UTC date may differ from date_value if time_value causes a date shift.
        This is expected and correct - when converted back to browser timezone, it will
        display as the original date_value and time_value.
    """
    from datetime import UTC

    from flask import current_app

    from app.utils.timezone_utils import get_timezone

    browser_tz = get_timezone(browser_timezone)

    if time_value:
        # Use the provided time - interpret as browser's local time
        # This is WYSIWYG: what user enters is what gets stored (in UTC)
        browser_datetime = datetime.combine(date_value, time_value)
        # Localize to browser's timezone, then convert to UTC for storage
        browser_datetime_tz = browser_datetime.replace(tzinfo=browser_tz)
        result = browser_datetime_tz.astimezone(UTC)
        current_app.logger.debug(
            f"_combine_date_time_with_timezone: date={date_value}, time={time_value}, "
            f"browser_tz={browser_timezone}, browser_datetime={browser_datetime_tz}, "
            f"result_utc={result} (UTC date may differ if time crosses midnight)"
        )
        return result

    # Use noon in browser timezone to avoid date shifts when no time is provided
    # This ensures the date_value is preserved when displayed back
    browser_datetime = datetime.combine(date_value, time(12, 0))
    browser_datetime_tz = browser_datetime.replace(tzinfo=browser_tz)
    # Convert to UTC and return timezone-aware datetime
    # Database expects timezone-aware for timezone=True columns
    result = browser_datetime_tz.astimezone(UTC)
    current_app.logger.debug(
        f"_combine_date_time_with_timezone: date={date_value}, time=None (using noon), "
        f"browser_tz={browser_timezone}, browser_datetime={browser_datetime_tz}, "
        f"result_utc={result}"
    )
    return result


def _process_expense_form_data(
    form: ExpenseForm, browser_timezone: str = "UTC"
) -> tuple[int | None, int | None, datetime, Decimal, list[str]] | str:
    """Process all form data for expense creation/update.

    Args:
        form: The expense form
        browser_timezone: Browser timezone string (will be normalized if deprecated)

    Returns:
        Either a tuple of processed data or an error message string
    """
    from app.utils.timezone_utils import normalize_timezone

    # Normalize deprecated timezone names (e.g., US/Central -> America/Chicago)
    browser_timezone = normalize_timezone(browser_timezone) or "UTC"
    category_id, error = _process_category_id(form)
    if error:
        return error

    restaurant_id, error = _process_restaurant_id(form)
    if error:
        return error

    date_value, error = _process_date(form.date.data)
    if error:
        return error
    if date_value is None:
        return "Date is required"

    time_value, error = _process_time(form.time.data)
    if error:
        return error

    amount, error = _process_amount(form.amount.data)
    if error:
        return error
    if amount is None:
        return "Amount is required"

    tags, error = _process_tags(form)
    if error:
        return error
    if tags is None:
        return "Tags processing error"

    # Combine date and time into a datetime object
    datetime_value = _combine_date_time_with_timezone(date_value, time_value, browser_timezone)
    current_app.logger.debug(
        f"Date processing: form_date={form.date.data}, processed_date={date_value}, "
        f"form_time={form.time.data}, processed_time={time_value}, "
        f"browser_tz={browser_timezone}, result_datetime={datetime_value}"
    )

    return category_id, restaurant_id, datetime_value, amount, tags


def _handle_receipt_update(expense: Expense, receipt_file: FileStorage | None, delete_receipt: bool) -> str | None:
    """Handle receipt upload or deletion for an expense.

    Args:
        expense: The expense being updated
        receipt_file: Optional uploaded receipt file
        delete_receipt: Whether to delete the existing receipt

    Returns:
        Error message if failed, None if successful
    """
    if receipt_file and receipt_file.filename:
        return _upload_new_receipt(expense, receipt_file)
    elif delete_receipt and expense.receipt_image:
        return _delete_existing_receipt(expense)
    return None


def _upload_new_receipt(expense: Expense, receipt_file: FileStorage) -> str | None:
    """Upload a new receipt for an expense."""
    try:
        from flask import current_app

        from app.expenses.utils import save_receipt_to_storage

        upload_folder = current_app.config.get("UPLOAD_FOLDER")
        if not isinstance(upload_folder, str):
            return "UPLOAD_FOLDER configuration is not set"
        storage_path, error = save_receipt_to_storage(receipt_file, upload_folder)

        if error:
            return error

        # Store the storage path directly (S3 key or local filename)
        expense.receipt_image = storage_path
        current_app.logger.info(f"Receipt updated: {storage_path}")
        return None
    except Exception as e:
        current_app.logger.error(f"Failed to save receipt: {str(e)}")
        return f"Failed to save receipt: {str(e)}"


def _delete_existing_receipt(expense: Expense) -> str | None:
    """Delete an existing receipt from an expense."""
    try:
        from flask import current_app

        from app.expenses.utils import delete_receipt_from_storage

        # Check if there's actually a receipt to delete
        if not expense.receipt_image:
            current_app.logger.info("No receipt to delete")
            return None

        upload_folder = current_app.config.get("UPLOAD_FOLDER")
        if not isinstance(upload_folder, str):
            return "UPLOAD_FOLDER configuration is not set"
        error = delete_receipt_from_storage(expense.receipt_image, upload_folder)

        if error:
            return error

        expense.receipt_image = None
        current_app.logger.info("Receipt deleted from expense")
        return None

    except Exception as e:
        current_app.logger.error(f"Failed to delete receipt: {str(e)}")
        return f"Failed to delete receipt: {str(e)}"


def update_expense(
    expense: Expense, form: ExpenseForm, receipt_file: FileStorage | None = None, delete_receipt: bool = False
) -> tuple[Expense | None, str | None]:
    """Update an existing expense from form data.

    Args:
        expense: The expense to update
        form: The validated expense form
        receipt_file: Optional uploaded receipt file
        delete_receipt: Whether to delete the existing receipt

    Returns:
        A tuple containing:
        - The updated expense on success, None on failure
        - Error message on failure, None on success
    """
    try:
        current_app.logger.info("Updating expense with form data: %s", form.data)

        # Get user timezone for proper time handling
        from app.extensions import db

        # Get browser timezone for proper time handling
        from app.utils.timezone_utils import get_browser_timezone, normalize_timezone

        browser_timezone_raw = get_browser_timezone() or "UTC"
        browser_timezone = normalize_timezone(browser_timezone_raw) or "UTC"
        # Process form data
        expense_data = _process_expense_form_data(form, browser_timezone)
        if isinstance(expense_data, str):  # Error message
            return None, expense_data

        category_id, restaurant_id, date_value, amount, tags = expense_data

        # Handle receipt upload/deletion
        receipt_error = _handle_receipt_update(expense, receipt_file, delete_receipt)
        if receipt_error:
            return None, receipt_error

        # Update expense fields
        expense.amount = Decimal(str(amount))
        # date_value from _combine_date_time_with_timezone is already timezone-aware (UTC)
        old_date = expense.date
        expense.date = date_value
        current_app.logger.info(
            f"Updating expense {expense.id} date: "
            f"OLD: {old_date} (tz-aware: {old_date.tzinfo is not None if old_date else 'N/A'}), "
            f"NEW: {date_value} (tz-aware: {date_value.tzinfo is not None}), "
            f"Browser TZ={browser_timezone}, "
            f"Form date={form.date.data}, Form time={form.time.data}"
        )
        expense.notes = form.notes.data.strip() if form.notes.data else None
        expense.category_id = category_id
        expense.restaurant_id = restaurant_id
        expense.meal_type = form.meal_type.data or None
        expense.order_type = form.order_type.data or None
        expense.party_size = form.party_size.data

        current_app.logger.info("Updated expense data: %s", expense)
        db.session.commit()

        # Update tags for the expense
        if tags is not None:  # Allow empty list to clear tags
            _add_tags_to_expense(expense.id, expense.user_id, tags)

        # Recalculate restaurant statistics since we updated an expense
        from app.restaurants.services import recalculate_restaurant_statistics

        recalculate_restaurant_statistics(expense.user_id)

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
    user_id = expense.user_id
    db.session.delete(expense)
    db.session.commit()

    # Recalculate restaurant statistics since we deleted an expense
    from app.restaurants.services import recalculate_restaurant_statistics

    recalculate_restaurant_statistics(user_id)


def get_expense_by_id(expense_id: int, user_id: int) -> Expense | None:
    """Get an expense by ID, ensuring it belongs to the user.

    Args:
        expense_id: The ID of the expense to retrieve
        user_id: The ID of the user who owns the expense

    Returns:
        The expense if found and belongs to the user, None otherwise
    """
    result = (
        Expense.query.options(joinedload(Expense.expense_tags).joinedload(ExpenseTag.tag))
        .filter_by(id=expense_id, user_id=user_id)
        .first()
    )
    return cast(Expense | None, result)


def get_expense_by_id_for_user(expense_id: int, user_id: int) -> Expense | None:
    """Get an expense by ID for a specific user.

    Args:
        expense_id: The ID of the expense to retrieve
        user_id: The ID of the user who owns the expense

    Returns:
        The expense if found and belongs to the user, None otherwise
    """
    return get_expense_by_id(expense_id, user_id)


def get_expenses_for_user(
    user_id: int, start_date: datetime | None = None, end_date: datetime | None = None
) -> list[Expense]:
    """
    Get all expenses for a specific user, optionally filtered by date range.

    Args:
        user_id: ID of the current user
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering

    Returns:
        List of expenses belonging to the user
    """
    query = Expense.query.options(joinedload(Expense.expense_tags).joinedload(ExpenseTag.tag)).filter_by(
        user_id=user_id
    )

    if start_date:
        query = query.filter(Expense.date >= start_date.date())
    if end_date:
        query = query.filter(Expense.date <= end_date.date())

    result = query.order_by(Expense.date.desc()).all()
    return cast(list[Expense], result)


def create_expense_for_user(user_id: int, data: dict[str, Any]) -> Expense:
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
        category_id=data.get("category_id"),
        restaurant_id=data.get("restaurant_id"),
        notes=data.get("notes"),
    )

    db.session.add(expense)
    db.session.commit()

    return expense


def update_expense_for_user(expense: Expense, data: dict[str, Any]) -> Expense:
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
    if "category_id" in data:
        expense.category_id = data["category_id"]
    if "restaurant_id" in data:
        expense.restaurant_id = data["restaurant_id"]
    if "notes" in data:
        expense.notes = data["notes"]
    if "meal_type" in data:
        expense.meal_type = data["meal_type"]

    db.session.commit()

    # Recalculate restaurant statistics since we updated an expense
    from app.restaurants.services import recalculate_restaurant_statistics

    recalculate_restaurant_statistics(expense.user_id)

    return expense


def delete_expense_for_user(expense: Expense) -> None:
    """
    Delete an expense for a user.

    Args:
        expense: The expense to delete
    """
    user_id = expense.user_id
    db.session.delete(expense)
    db.session.commit()

    # Recalculate restaurant statistics since we deleted an expense
    from app.restaurants.services import recalculate_restaurant_statistics

    recalculate_restaurant_statistics(user_id)


def get_filter_options(user_id: int) -> dict[str, Any]:
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

    def sort_key(cat_row: Any) -> tuple[int, Any]:
        cat_name = cat_row[0]  # name is still the first element
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
    month_options: list[tuple[str, str]] = []
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
            {
                "name": str(cat[0]),
                "color": str(cat[1]),
                "icon": str(cat[2]) if cat[2] else None,
                "count": int(cat[3]),
            }
            for cat in categories
        ],
        "years": year_options,
        "months": [{"value": m[0], "display": m[1]} for m in month_options],
    }


def export_expenses_for_user(user_id: int) -> list[dict[str, Any]]:
    """Get all expenses for a user in a format suitable for export.

    Args:
        user_id: The ID of the user whose expenses to export

    Returns:
        A list of dictionaries containing expense data
    """
    expenses = db.session.scalars(select(Expense).where(Expense.user_id == user_id).order_by(Expense.date.desc())).all()

    def safe_float(value: Any) -> float | None:
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


def _normalize_field_names(data_row: dict[str, Any]) -> dict[str, Any]:
    """Normalize field names to match expected format.

    Maps various common field names to the standard field names used by the system.

    Args:
        data_row: Raw data row from import file

    Returns:
        Normalized data row with standard field names
    """
    # Define field mappings (case-insensitive)
    field_mappings = {
        # Date field mappings
        "postedon": "date",
        "posted_on": "date",
        "transaction_date": "date",
        "expense_date": "date",
        "when": "date",
        # Amount field mappings
        "cost": "amount",
        "price": "amount",
        "total": "amount",
        "expense_amount": "amount",
        "value": "amount",
        # Restaurant/vendor mappings
        "payee": "restaurant_name",
        "vendor": "restaurant_name",
        "merchant": "restaurant_name",
        "restaurant": "restaurant_name",
        "place": "restaurant_name",
        "location": "restaurant_name",
        # Category mappings
        "usage_category": "category_name",
        "expense_category": "category_name",
        "type": "category_name",
        "category": "category_name",
        # Address mappings
        "address": "restaurant_address",
        "location_address": "restaurant_address",
        "vendor_address": "restaurant_address",
        # Meal type mappings
        "meal": "meal_type",
        "meal_category": "meal_type",
        # Notes mappings
        "description": "notes",
        "memo": "notes",
        "note": "notes",
        "comment": "notes",
        "remarks": "notes",
    }

    # Create normalized row
    normalized_row = {}

    # First, copy all original fields (preserve case)
    for key, value in data_row.items():
        normalized_row[key] = value

    # Then add normalized field mappings
    for original_key, value in data_row.items():
        normalized_key = field_mappings.get(original_key.lower().strip())
        if normalized_key:
            normalized_row[normalized_key] = value

    return normalized_row


def _parse_import_file(file: FileStorage) -> list[dict[str, Any]] | None:
    """Parse the uploaded file and return normalized data.

    Args:
        file: The uploaded file

    Returns:
        List of normalized expense data dictionaries or None if error
    """
    try:
        if file.filename and file.filename.lower().endswith(".json"):
            # Reset file pointer to beginning
            file.seek(0)
            data = json.load(file)
            if not isinstance(data, list):
                current_app.logger.error("Invalid JSON format. Expected an array of expenses.")
                return None
        else:
            # Parse CSV file
            file.seek(0)
            csv_data = file.read().decode("utf-8")
            reader = csv.DictReader(io.StringIO(csv_data))
            data = list(reader)

        # Normalize field names for all rows
        normalized_data = []
        for row in data:
            normalized_row = _normalize_field_names(row)
            normalized_data.append(normalized_row)

        return normalized_data
    except UnicodeDecodeError:
        current_app.logger.error("Error decoding the file. Please ensure it's a valid CSV or JSON file.")
        return None
    except Exception as e:
        current_app.logger.error(f"Error parsing import file: {str(e)}")
        return None


def _process_csv_file(file: FileStorage) -> tuple[bool, str | None, csv.DictReader | None]:
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


def _parse_excel_serial_date(date_value: str | int | float | None) -> tuple[date | None, bool]:
    """Parse Excel serial date format.

    Excel stores dates as sequential serial numbers starting from January 1, 1900 (day 1).
    Example: 45985 = 2025-11-24

    Args:
        date_value: The date value to parse (string, int, or float)

    Returns:
        Tuple of (parsed_date, is_excel_date)
    """
    if date_value is None:
        return None, False

    try:
        # Handle both string and numeric types
        if isinstance(date_value, (int, float)):
            serial_number = float(date_value)
        else:
            # Convert string to float, handling empty strings
            date_str = str(date_value).strip()
            if not date_str:
                return None, False
            serial_number = float(date_str)

        # Excel date range: 1 to 2958465 (represents dates from 1900-01-01 to 9999-12-31)
        # Only accept integers or floats that represent integers (e.g., 45985.0)
        if 1 <= serial_number <= 2958465 and serial_number.is_integer():
            # Excel uses 1900-01-01 as day 1, but incorrectly treats 1900 as a leap year
            # We use 1899-12-30 as epoch (day 0) to account for this
            excel_epoch = datetime(1899, 12, 30)
            try:
                parsed_date = excel_epoch + timedelta(days=int(serial_number))
                return parsed_date.date(), True
            except (ValueError, OverflowError) as e:
                current_app.logger.warning(f"Error converting Excel date {serial_number}: {e}")
                pass
    except (ValueError, TypeError, AttributeError):
        # Not a numeric value, so not an Excel serial date
        pass

    return None, False


def _parse_standard_date_formats(date_str: str) -> tuple[date | None, str | None]:
    """Parse standard date formats (ISO, US, European).

    Args:
        date_str: The date string to parse

    Returns:
        Tuple of (parsed_date, error_message)
    """
    # First try fromisoformat for strict ISO
    try:
        return datetime.fromisoformat(date_str).date(), None
    except ValueError:
        pass

    # Try multiple date formats in order of preference
    date_formats = [
        "%Y-%m-%d",  # ISO format: 2025-08-30
        "%m/%d/%Y",  # US format: 8/30/2025, 08/30/2025
        "%m-%d-%Y",  # Alternative: 8-30-2025, 08-30-2025
        "%d/%m/%Y",  # European: 30/8/2025, 30/08/2025
        "%Y/%m/%d",  # Alternative ISO: 2025/08/30
    ]

    # Try each format
    for date_format in date_formats:
        try:
            return datetime.strptime(date_str, date_format).date(), None
        except ValueError:
            continue

    return (
        None,
        f"Invalid date format: {date_str}. Supported formats: YYYY-MM-DD, M/D/YYYY, MM/DD/YYYY, Excel serial dates",
    )


def _parse_expense_date(date_value: str | int | float | None) -> tuple[date | None, str | None]:
    """Parse expense date from string or numeric value with support for multiple formats.

    Supported formats:
    - ISO format: YYYY-MM-DD
    - US format: M/D/YYYY, MM/DD/YYYY
    - Alternative US: M-D-YYYY, MM-DD-YYYY
    - Excel serial dates: numeric values (e.g., 45985 = 2025-11-24)

    Args:
        date_value: The date value to parse (string, int, float, or None)

    Returns:
        Tuple of (parsed_date, error_message)
    """
    if date_value is None:
        return None, "Date is required"

    # Handle numeric types directly for Excel dates
    if isinstance(date_value, (int, float)):
        excel_date, is_excel = _parse_excel_serial_date(date_value)
        if is_excel:
            return excel_date, None
        # If numeric but not a valid Excel date, convert to string for standard parsing
        date_str = str(date_value).strip()
    else:
        # Handle string types
        date_str = str(date_value).strip()
        if not date_str:
            return None, "Date is required"

        # Try Excel serial date first (in case it's a string like "45985")
        excel_date, is_excel = _parse_excel_serial_date(date_str)
        if is_excel:
            return excel_date, None

    # Try standard date formats
    return _parse_standard_date_formats(date_str)


def _parse_expense_amount(amount_str: str) -> tuple[Decimal | None, str | None]:
    """Parse expense amount from string with support for multiple formats.

    Supported formats:
    - Basic numeric: 24.77, -24.77
    - Currency symbols: $24.77, -$24.77
    - Parentheses for negative: (24.77), ($24.77)
    - Thousands separators: 1,234.56, $1,234.56

    Args:
        amount_str: The amount string to parse

    Returns:
        Tuple of (parsed_amount, error_message)
    """
    if not amount_str:
        return None, "Amount is required"

    try:
        # Clean the amount string
        cleaned_amount = str(amount_str).strip()

        # Handle parentheses for negative amounts
        is_negative = False
        if cleaned_amount.startswith("(") and cleaned_amount.endswith(")"):
            is_negative = True
            cleaned_amount = cleaned_amount[1:-1]  # Remove parentheses

        # Remove currency symbols and thousands separators
        cleaned_amount = cleaned_amount.replace("$", "").replace(",", "").strip()

        # Convert to Decimal
        amount = Decimal(cleaned_amount)

        # Handle amount sign logic for expenses vs reimbursements
        # Parentheses amounts like ($24.77) → store as positive (regular expenses)
        # Plus sign amounts like +$76.89 → store as negative (reimbursements)
        # Plain amounts without sign → store as positive (regular expenses)

        # Check if original amount string had explicit plus sign (reimbursement)
        has_plus_sign = str(amount_str).strip().startswith("+")

        if is_negative:
            # Parentheses indicate a regular expense, store as positive
            amount = abs(amount)
        elif has_plus_sign:
            # Plus sign indicates a reimbursement, store as negative
            amount = -abs(amount)
        else:
            # Plain amounts are regular expenses, store as positive
            amount = abs(amount)

        return amount, None
    except (ValueError, InvalidOperation):
        return (
            None,
            f"Invalid amount: {amount_str}. Supported formats: 24.77, $24.77, (24.77), ($24.77)",
        )


def _find_category_by_name(category_name: str, user_id: int) -> Category | None:
    """Find category by name for a user with support for hierarchical categories.

    Args:
        category_name: The category name to search for (supports hierarchical format like "Parent:Child")
        user_id: The user ID

    Returns:
        The category if found, None otherwise
    """
    if not category_name:
        return None

    # First try exact match
    category = Category.query.filter_by(user_id=user_id, name=category_name).first()
    if category:
        return cast(Category | None, category)

    # Handle hierarchical category format (e.g., "Dining & Drinks:Fast Food")
    if ":" in category_name:
        # Try the part after the colon (subcategory)
        subcategory_name = category_name.split(":", 1)[1].strip()
        category = Category.query.filter_by(user_id=user_id, name=subcategory_name).first()
        if category:
            return cast(Category | None, category)

        # Try the part before the colon (parent category)
        parent_category_name = category_name.split(":", 1)[0].strip()
        category = Category.query.filter_by(user_id=user_id, name=parent_category_name).first()
        if category:
            return cast(Category | None, category)

    # Try case-insensitive search as fallback
    category = Category.query.filter(Category.user_id == user_id, Category.name.ilike(f"%{category_name}%")).first()

    return cast(Category | None, category)


def _find_or_create_restaurant(
    restaurant_name: str, restaurant_address: str, user_id: int
) -> tuple[Restaurant | None, str | None]:
    """Find existing restaurant or create new one if not found, with ambiguity checking.

    Prevents duplicate creation by:
    1. Exact name + address match (if address provided)
    2. Unique name match (only if exactly one restaurant with that name exists)
    3. Skips creation if name is ambiguous without address

    Args:
        restaurant_name: The restaurant name
        restaurant_address: The restaurant address (optional)
        user_id: The user ID

    Returns:
        Tuple of (restaurant, warning_message):
        - restaurant: The found restaurant if unique match, None if ambiguous/not found
        - warning_message: None if success, warning text if skipped due to ambiguity
    """
    if not restaurant_name:
        return None, None

    # Clean inputs
    restaurant_name = restaurant_name.strip()
    restaurant_address_cleaned: str | None = restaurant_address.strip() if restaurant_address else None

    # Strategy 1: Exact name + address match (if address provided)
    if restaurant_address_cleaned:
        existing = Restaurant.query.filter_by(
            user_id=user_id, name=restaurant_name, address_line_1=restaurant_address_cleaned
        ).first()
        if existing:
            return existing, None

        # If address provided but no match, create new restaurant
        try:
            new_restaurant = Restaurant(
                user_id=user_id,
                name=restaurant_name,
                address_line_1=restaurant_address_cleaned,
                city=None,  # Will be filled by user later if needed
            )
            db.session.add(new_restaurant)
            db.session.flush()  # Get the ID without committing
            return new_restaurant, None
        except Exception:
            # If creation fails, try to find again
            existing = Restaurant.query.filter_by(user_id=user_id, name=restaurant_name).first()
            return existing, None

    # Strategy 2: Check for name matches when no address provided
    name_matches = Restaurant.query.filter_by(user_id=user_id, name=restaurant_name).all()
    if len(name_matches) == 1:
        # Exactly one match - safe to use
        return name_matches[0], None
    elif len(name_matches) > 1:
        # Multiple matches - ambiguous, skip with warning
        return (
            None,
            f"Restaurant '{restaurant_name}' matches multiple existing restaurants. Please provide an address to disambiguate.",
        )
    else:
        # No matches - skip creation without address to prevent duplicates
        return (
            None,
            f"Restaurant '{restaurant_name}' not found. Please provide an address to create a new restaurant entry.",
        )


def _check_expense_duplicate(
    user_id: int,
    restaurant_id: int | None,
    amount: Decimal,
    expense_date: date,
    meal_type: str | None,
) -> bool:
    """Check if an expense with the same details already exists.

    Args:
        user_id: User ID
        restaurant_id: Restaurant ID (can be None)
        amount: Expense amount
        expense_date: Date of expense
        meal_type: Type of meal (can be None)

    Returns:
        True if duplicate exists, False otherwise
    """
    existing = (
        Expense.query.filter_by(user_id=user_id, restaurant_id=restaurant_id, amount=amount, meal_type=meal_type)
        .filter(db.func.date(Expense.date) == expense_date)
        .first()
    )

    return existing is not None


def _find_restaurant_by_name(restaurant_name: str, user_id: int) -> Restaurant | None:
    """Find restaurant by name for a user.

    Args:
        restaurant_name: The restaurant name to search for
        user_id: The user ID

    Returns:
        The restaurant if found, None otherwise
    """
    if not restaurant_name:
        return None
    result = Restaurant.query.filter_by(user_id=user_id, name=restaurant_name).first()
    return cast(Restaurant | None, result)


def _create_expense_from_data(data: dict[str, Any], user_id: int) -> tuple[Expense | None, str | None]:
    """Create an expense from import data with smart restaurant handling and duplicate detection.

    Args:
        data: The expense data dictionary
        user_id: The ID of the user creating the expense

    Returns:
        Tuple of (expense, error_message)
    """
    try:
        # Parse date - handle both string and numeric values (Excel dates)
        date_value = data.get("date")
        if date_value is not None and isinstance(date_value, str):
            date_value = date_value.strip()
        expense_date, date_error = _parse_expense_date(date_value)
        if date_error:
            return None, date_error

        # Parse amount
        amount, amount_error = _parse_expense_amount(str(data.get("amount", "")).strip())
        if amount_error:
            return None, amount_error

        # Find category
        category = _find_category_by_name(data.get("category_name", "").strip(), user_id)

        # Find or create restaurant with smart logic
        restaurant_name = data.get("restaurant_name", "").strip()
        restaurant_address = data.get("restaurant_address", "").strip()
        restaurant, restaurant_warning = _find_or_create_restaurant(restaurant_name, restaurant_address, user_id)

        # If restaurant matching failed due to ambiguity, return warning
        if restaurant_warning:
            return None, restaurant_warning

        # Extract meal type
        meal_type = data.get("meal_type", "").strip() or None

        # Check for duplicate expense
        if amount is not None and expense_date is not None:
            if _check_expense_duplicate(
                user_id, restaurant.id if restaurant else None, amount, expense_date, meal_type
            ):
                restaurant_name_display = restaurant.name if restaurant else "Unknown"
                return (
                    None,
                    f"Duplicate expense: ${amount} at {restaurant_name_display} on {expense_date} for {meal_type or 'unspecified meal'}",
                )

        # Create expense
        expense = Expense(
            user_id=user_id,
            date=expense_date,
            amount=amount,
            meal_type=meal_type,
            notes=data.get("notes", "").strip() or None,
            category_id=category.id if category else None,
            restaurant_id=restaurant.id if restaurant else None,
        )

        return expense, None

    except Exception as e:
        return None, f"Error creating expense: {str(e)}"


def _import_expenses_from_reader(data: list[dict[str, Any]], user_id: int) -> tuple[int, list[str], list[str]]:
    """Import expenses from parsed data.

    Args:
        data: List of expense data dictionaries
        user_id: The ID of the user importing the expenses

    Returns:
        Tuple of (success_count, errors, info_messages)
    """
    success_count = 0
    errors: list[str] = []
    info_messages: list[str] = []
    batch_size = 50  # Process in batches to avoid memory issues

    for i, row in enumerate(data, 1):
        expense, error = _process_expense_row(row, user_id, i)
        if error:
            _handle_import_error(error, i, errors, info_messages)
            continue

        if expense:
            db.session.add(expense)
            success_count += 1

            # Commit every batch_size records to avoid memory issues
            if success_count % batch_size == 0:
                commit_success = _commit_batch(success_count, batch_size, errors)
                if not commit_success:
                    return success_count, errors, info_messages

    # Don't limit messages - let the frontend handle display properly
    return success_count, errors, info_messages


def _process_expense_row(row: dict[str, Any], user_id: int, row_number: int) -> tuple[Expense | None, str | None]:
    """Process a single expense row and return expense or error.

    Args:
        row: The expense data dictionary
        user_id: The ID of the user importing the expenses
        row_number: The row number for error reporting

    Returns:
        Tuple of (expense, error_message)
    """
    try:
        return _create_expense_from_data(row, user_id)
    except Exception as e:
        return None, f"Row {row_number}: Unexpected error - {str(e)}"


def _handle_import_error(error: str, row_number: int, errors: list[str], info_messages: list[str]) -> None:
    """Handle different types of import errors.

    Args:
        error: The error message
        row_number: The row number where the error occurred
        errors: List to append actual errors to
        info_messages: List to append informational messages to
    """
    if error.startswith("Duplicate expense:"):
        info_messages.append(f"Row {row_number}: {error}")
    elif _is_restaurant_warning(error):
        # Restaurant ambiguity warnings should be treated as info messages
        info_messages.append(f"Row {row_number}: {error}")
    else:
        errors.append(f"Row {row_number}: {error}")


def _is_restaurant_warning(error: str) -> bool:
    """Check if error is a restaurant-related warning that should be treated as info.

    Args:
        error: The error message to check

    Returns:
        True if this is a restaurant warning, False otherwise
    """
    return "matches multiple existing restaurants" in error or "not found. Please provide an address" in error


def _commit_batch(success_count: int, batch_size: int, errors: list[str]) -> bool:
    """Commit a batch of expenses and handle errors.

    Args:
        success_count: Current count of successful imports
        batch_size: Size of the batch being committed
        errors: List to append errors to

    Returns:
        True if commit was successful, False otherwise
    """
    try:
        db.session.commit()
        current_app.logger.info(f"Committed batch of {batch_size} expenses")
        return True
    except Exception as e:
        current_app.logger.error(f"Error committing batch: {str(e)}")
        db.session.rollback()
        errors.append(f"Batch {success_count // batch_size}: Database error - {str(e)}")
        return False


def _count_warning_types(info_messages: list[str]) -> tuple[int, int]:
    """Count different types of warning messages.

    Args:
        info_messages: List of informational messages

    Returns:
        Tuple of (duplicate_count, restaurant_warning_count)
    """
    duplicate_count = sum(1 for msg in info_messages if "Duplicate expense:" in msg)
    restaurant_warning_count = len(info_messages) - duplicate_count
    return duplicate_count, restaurant_warning_count


def _build_warning_message(info_messages: list[str]) -> str:
    """Build warning message text from info messages.

    Args:
        info_messages: List of informational messages

    Returns:
        Warning message text or empty string if no warnings
    """
    if not info_messages:
        return ""

    duplicate_count, restaurant_warning_count = _count_warning_types(info_messages)

    if duplicate_count > 0 and restaurant_warning_count > 0:
        return f"{duplicate_count} duplicates and {restaurant_warning_count} restaurant warnings"
    elif duplicate_count > 0:
        return f"{duplicate_count} duplicates skipped"
    elif restaurant_warning_count > 0:
        return f"{restaurant_warning_count} restaurant warnings"

    return ""


def _build_import_message(success_count: int, info_messages: list[str], errors: list[str]) -> str:
    """Build the main import result message.

    Args:
        success_count: Number of successfully imported expenses
        info_messages: List of informational messages
        errors: List of error messages

    Returns:
        Complete import result message
    """
    parts = []

    if success_count > 0:
        parts.append(f"{success_count} expenses imported successfully")

    warning_message = _build_warning_message(info_messages)
    if warning_message:
        parts.append(warning_message)

    if errors:
        parts.append(f"{len(errors)} errors occurred")

    if parts:
        return ". ".join(parts) + "."
    else:
        return "No expenses processed."


def _prepare_error_details(errors: list[str]) -> list[str]:
    """Prepare error details with appropriate limits.

    Args:
        errors: List of error messages

    Returns:
        Limited list of error details for display
    """
    if not errors:
        return []

    error_limit = 5
    if len(errors) > error_limit:
        return errors[:error_limit] + [f"... and {len(errors) - error_limit} more errors"]
    else:
        return errors


def _generate_import_result(
    success_count: int, errors: list[str], info_messages: list[str]
) -> tuple[bool, dict[str, Any]]:
    """Generate the result of the import operation.

    Args:
        success_count: Number of successfully imported expenses
        errors: List of error messages (actual problems)
        info_messages: List of informational messages (like duplicates)

    Returns:
        Tuple of (success, result_data)
    """
    # Only commit if we have successful imports and no errors during processing
    # (Note: Individual batches may have already been committed during import)
    if success_count > 0 and len(errors) == 0:
        try:
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Error committing final batch: {str(e)}")
            db.session.rollback()
            errors.append(f"Final commit failed: {str(e)}")

    # Build result data structure
    result_data = {
        "success_count": success_count,
        "skipped_count": len(info_messages),
        "error_count": len(errors),
        "errors": errors,
        "info_messages": info_messages,
        "has_warnings": len(info_messages) > 0,
        "has_errors": len(errors) > 0,
        "message": _build_import_message(success_count, info_messages, errors),
    }

    # Add error details if needed
    if errors:
        result_data["error_details"] = _prepare_error_details(errors)

    # Determine success - it's successful if there are no actual errors
    is_success = len(errors) == 0
    return is_success, result_data


def import_expenses_from_csv(file: FileStorage, user_id: int) -> tuple[bool, dict[str, Any]]:
    """Import expenses from a CSV file.

    Args:
        file: The uploaded CSV file
        user_id: ID of the user importing the expenses

    Returns:
        A tuple containing (success: bool, result_data: Dict[str, Any])
    """
    try:
        # Validate file
        if not _validate_import_file(file):
            error_msg = "Invalid file type. Please upload a CSV or JSON file."
            return False, {"message": error_msg, "has_errors": True, "error_details": [error_msg]}

        # Parse file
        data = _parse_import_file(file)
        if data is None:
            error_msg = "Error parsing file. Please check the file format."
            return False, {"message": error_msg, "has_errors": True, "error_details": [error_msg]}

        # Import expenses from the data
        success_count, errors, info_messages = _import_expenses_from_reader(data, user_id)

        # Generate the result data
        return _generate_import_result(success_count, errors, info_messages)

    except Exception as e:
        db.session.rollback()
        error_msg = f"Error processing file: {str(e)}"
        return False, {"message": error_msg, "has_errors": True, "error_details": [error_msg]}


# Tag Services
def create_tag(user_id: int, name: str, color: str = "#6c757d", description: str | None = None) -> Tag:
    """Create a new tag for a user.

    Args:
        user_id: ID of the user creating the tag
        name: Name of the tag (will be normalized to Jira-style)
        color: Hex color code for the tag
        description: Optional description of the tag

    Returns:
        The created Tag object

    Raises:
        ValueError: If tag name is invalid or already exists
    """
    if not name or not name.strip():
        raise ValueError("Tag name is required")

    # Normalize tag name to Jira-style
    normalized_name = name.strip().lower().replace(" ", "-")
    normalized_name = "".join(c for c in normalized_name if c.isalnum() or c == "-")

    if not normalized_name:
        raise ValueError("Tag name must contain at least one alphanumeric character")

    # Check if tag already exists for this user
    existing_tag = Tag.query.filter_by(name=normalized_name, user_id=user_id).first()
    if existing_tag:
        raise ValueError(f"Tag '{name}' already exists")

    # Create new tag
    tag = Tag(name=normalized_name, color=color, description=description, user_id=user_id)

    db.session.add(tag)
    db.session.commit()

    return tag


def update_tag(
    user_id: int, tag_id: int, name: str, color: str = "#6c757d", description: str | None = None
) -> Tag | None:
    """Update an existing tag for a user.

    Args:
        user_id: ID of the user updating the tag
        tag_id: ID of the tag to update
        name: New name of the tag (will be normalized to Jira-style)
        color: New hex color code for the tag
        description: New optional description of the tag

    Returns:
        The updated Tag object, or None if not found

    Raises:
        ValueError: If tag name is invalid or already exists
    """
    if not name or not name.strip():
        raise ValueError("Tag name is required")

    # Find the tag
    tag = Tag.query.filter_by(id=tag_id, user_id=user_id).first()
    if not tag:
        return None

    # Normalize tag name to Jira-style
    normalized_name = name.strip().lower().replace(" ", "-")
    normalized_name = "".join(c for c in normalized_name if c.isalnum() or c == "-")

    if not normalized_name:
        raise ValueError("Tag name must contain at least one alphanumeric character")

    # Check if another tag with this name already exists for this user
    existing_tag = Tag.query.filter(Tag.name == normalized_name, Tag.user_id == user_id, Tag.id != tag_id).first()
    if existing_tag:
        raise ValueError(f"Tag '{name}' already exists")

    # Update the tag
    tag.name = normalized_name
    tag.color = color
    tag.description = description
    tag.updated_at = datetime.now(UTC)

    db.session.commit()

    return cast(Tag, tag)


def get_user_tags(user_id: int) -> list[Tag]:
    """Get all tags for a user with accurate expense counts.

    Args:
        user_id: ID of the user

    Returns:
        List of Tag objects for the user with expense_count populated
    """
    from flask import current_app

    # Explicitly filter by user_id to ensure security
    tags = Tag.query.filter_by(user_id=user_id).order_by(Tag.name).all()

    # Defensive check: Verify all tags belong to the user (security measure)
    invalid_tags = [tag for tag in tags if tag.user_id != user_id]
    if invalid_tags:
        current_app.logger.error(
            f"SECURITY ISSUE: Found {len(invalid_tags)} tags that don't belong to user {user_id}. "
            f"Tag IDs: {[tag.id for tag in invalid_tags]}"
        )
        # Filter out any tags that don't belong to the user
        tags = [tag for tag in tags if tag.user_id == user_id]

    # Optimize: Get all expense counts in a single query instead of N+1 queries
    if tags:
        tag_ids = [tag.id for tag in tags]

        # Count expenses per tag, joining with Expense to ensure expenses exist
        # Also filter by user_id to ensure we only count the user's expenses
        counts = (
            db.session.query(ExpenseTag.tag_id, func.count(ExpenseTag.id).label("count"))
            .join(Expense, ExpenseTag.expense_id == Expense.id)
            .filter(ExpenseTag.tag_id.in_(tag_ids))
            .filter(Expense.user_id == user_id)  # Ensure we only count user's expenses
            .group_by(ExpenseTag.tag_id)
            .all()
        )

        # Create a dictionary mapping tag_id to count
        count_dict = {tag_id: count for tag_id, count in counts}

        # Set expense_count on each tag object
        for tag in tags:
            tag._expense_count = count_dict.get(tag.id, 0)

    return cast(list[Tag], tags)


def search_tags(user_id: int, query: str, limit: int = 10) -> list[Tag]:
    """Search tags by name for a user.

    Args:
        user_id: ID of the user
        query: Search query string
        limit: Maximum number of results to return

    Returns:
        List of matching Tag objects
    """
    if not query or not query.strip():
        return []

    search_term = f"%{query.strip().lower()}%"
    result = Tag.query.filter(Tag.user_id == user_id, Tag.name.ilike(search_term)).limit(limit).all()
    return cast(list[Tag], result)


def get_or_create_tag(user_id: int, name: str, color: str = "#6c757d") -> Tag:
    """Get an existing tag or create a new one if it doesn't exist.

    Args:
        user_id: ID of the user
        name: Name of the tag
        color: Hex color code for new tags (legacy, now uses CSS classes)

    Returns:
        The Tag object (existing or newly created)
    """
    # Normalize tag name
    normalized_name = name.strip().lower().replace(" ", "-")
    normalized_name = "".join(c for c in normalized_name if c.isalnum() or c == "-")

    if not normalized_name:
        raise ValueError("Tag name must contain at least one alphanumeric character")

    # Try to find existing tag
    tag = Tag.query.filter_by(name=normalized_name, user_id=user_id).first()

    if not tag:
        # Create new tag with default color (CSS classes handle the actual colors)
        tag = Tag(name=normalized_name, color=color, user_id=user_id)
        db.session.add(tag)
        db.session.commit()

    return cast(Tag, tag)


def add_tags_to_expense(expense_id: int, user_id: int, tag_names: list[str]) -> list[Tag]:
    """Add tags to an expense.

    Args:
        expense_id: ID of the expense
        user_id: ID of the user adding the tags
        tag_names: List of tag names to add

    Returns:
        List of Tag objects that were added
    """
    # Use SQLAlchemy 2.0 style to avoid LegacyAPIWarning for Query.get()
    expense = db.session.get(Expense, expense_id)
    if not expense:
        raise ValueError("Expense not found")

    if expense.user_id != user_id:
        raise ValueError("User can only add tags to their own expenses")

    added_tags = []

    for tag_name in tag_names:
        if not tag_name or not tag_name.strip():
            continue

        try:
            # Get or create tag
            tag = get_or_create_tag(user_id, tag_name.strip())

            # Check if tag is already added to this expense
            existing_expense_tag = ExpenseTag.query.filter_by(expense_id=expense_id, tag_id=tag.id).first()

            if not existing_expense_tag:
                # Add tag to expense
                expense_tag = ExpenseTag(expense_id=expense_id, tag_id=tag.id, added_by=user_id)
                db.session.add(expense_tag)
                added_tags.append(tag)

        except ValueError as e:
            current_app.logger.warning(f"Failed to add tag '{tag_name}': {e}")
            continue

    if added_tags:
        db.session.commit()

    return added_tags


def remove_tags_from_expense(expense_id: int, user_id: int, tag_names: list[str]) -> list[Tag]:
    """Remove tags from an expense.

    Args:
        expense_id: ID of the expense
        user_id: ID of the user removing the tags
        tag_names: List of tag names to remove

    Returns:
        List of Tag objects that were removed
    """
    expense = db.session.get(Expense, expense_id)
    if not expense:
        raise ValueError("Expense not found")

    if expense.user_id != user_id:
        raise ValueError("User can only remove tags from their own expenses")

    removed_tags = []

    for tag_name in tag_names:
        if not tag_name or not tag_name.strip():
            continue

        # Normalize tag name
        normalized_name = tag_name.strip().lower().replace(" ", "-")
        normalized_name = "".join(c for c in normalized_name if c.isalnum() or c == "-")

        # Find tag
        tag = Tag.query.filter_by(name=normalized_name, user_id=user_id).first()
        if not tag:
            continue

        # Find and remove expense tag
        expense_tag = ExpenseTag.query.filter_by(expense_id=expense_id, tag_id=tag.id).first()

        if expense_tag:
            db.session.delete(expense_tag)
            removed_tags.append(tag)

    if removed_tags:
        db.session.commit()

    return removed_tags


def get_expense_tags(expense_id: int, user_id: int) -> list[Tag]:
    """Get all tags for an expense.

    Args:
        expense_id: ID of the expense
        user_id: ID of the user (for authorization)

    Returns:
        List of Tag objects for the expense
    """
    expense = db.session.get(Expense, expense_id)
    if not expense:
        return []

    if expense.user_id != user_id:
        return []

    # Type checker limitation: doesn't recognize SQLAlchemy relationship return type
    return list(expense.tags)


def update_expense_tags(expense_id: int, user_id: int, tag_names: list[str]) -> list[Tag]:
    """Update tags for an expense (replace all existing tags).

    Args:
        expense_id: ID of the expense
        user_id: ID of the user updating the tags
        tag_names: List of tag names to set

    Returns:
        List of Tag objects that are now associated with the expense
    """
    expense = db.session.get(Expense, expense_id)
    if not expense:
        raise ValueError("Expense not found")

    if expense.user_id != user_id:
        raise ValueError("User can only update tags on their own expenses")

    # Remove all existing tags
    ExpenseTag.query.filter_by(expense_id=expense_id).delete()

    # Add new tags
    final_tags = []
    for tag_name in tag_names:
        if not tag_name or not tag_name.strip():
            continue

        try:
            tag = get_or_create_tag(user_id, tag_name.strip())
            expense_tag = ExpenseTag(expense_id=expense_id, tag_id=tag.id, added_by=user_id)
            db.session.add(expense_tag)
            final_tags.append(tag)
        except ValueError as e:
            current_app.logger.warning(f"Failed to add tag '{tag_name}': {e}")
            continue

    db.session.commit()
    return final_tags


def delete_tag(user_id: int, tag_id: int) -> bool:
    """Delete a tag and remove it from all expenses.

    Args:
        user_id: ID of the user deleting the tag
        tag_id: ID of the tag to delete

    Returns:
        True if tag was deleted, False if not found or unauthorized
    """
    from flask import current_app

    tag = db.session.get(Tag, tag_id)
    if not tag:
        current_app.logger.warning(f"Tag {tag_id} not found for deletion by user {user_id}")
        return False

    if tag.user_id != user_id:
        current_app.logger.warning(f"Tag {tag_id} belongs to user {tag.user_id}, but user {user_id} attempted deletion")
        return False

    # Remove tag from all expenses
    ExpenseTag.query.filter_by(tag_id=tag_id).delete()

    # Delete the tag
    db.session.delete(tag)
    db.session.commit()

    current_app.logger.info(f"Tag {tag_id} deleted successfully by user {user_id}")
    return True


def get_popular_tags(user_id: int, limit: int = 10) -> list[dict]:
    """Get the most popular tags for a user.

    Args:
        user_id: ID of the user
        limit: Maximum number of tags to return

    Returns:
        List of dicts with tag info and usage count
    """
    from sqlalchemy import func

    result = (
        db.session.query(Tag, func.count(ExpenseTag.id).label("usage_count"))
        .outerjoin(ExpenseTag)
        .filter(Tag.user_id == user_id)
        .group_by(Tag.id)
        .order_by(func.count(ExpenseTag.id).desc(), Tag.name)
        .limit(limit)
        .all()
    )

    return [{"tag": tag.to_dict(), "usage_count": usage_count} for tag, usage_count in result]


# =============================================================================
# RECEIPT OCR RECONCILIATION FUNCTIONALITY
# =============================================================================


def _parse_time_string(time_str: str) -> tuple[int, int, str]:
    """Parse time string in HH:MM AM/PM format.

    Args:
        time_str: Time string like "12:55 PM" or "9:30 AM"

    Returns:
        Tuple of (hour, minute, am_pm) where hour is 1-12, minute is 0-59, am_pm is "AM" or "PM"
    """
    time_str = time_str.strip().upper()
    # Match pattern like "12:55 PM" or "9:30 AM"
    match = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM)?", time_str)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        am_pm = match.group(3) if match.group(3) else "AM"
        return hour, minute, am_pm
    raise ValueError(f"Invalid time format: {time_str}")


def reconcile_receipt_with_expense(expense: Expense, receipt_data: dict[str, Any]) -> dict[str, Any]:
    """Reconcile OCR-extracted receipt data with expense form data.

    Args:
        expense: The expense object to reconcile
        receipt_data: Dictionary containing OCR-extracted data from receipt

    Returns:
        Dictionary containing:
        - matches: dict mapping field names to boolean match status
        - suggestions: dict mapping field names to suggested values
        - warnings: list of mismatch warning messages
        - confidence: overall confidence score (0.0-1.0)
    """
    matches: dict[str, bool] = {}
    suggestions: dict[str, Any] = {}
    warnings: list[str] = []

    # Extract OCR data
    ocr_amount = Decimal(receipt_data.get("amount") or receipt_data.get("total") or "0")
    ocr_date_str = receipt_data.get("date")
    ocr_time_str = receipt_data.get("time", "").strip()
    ocr_restaurant = receipt_data.get("restaurant_name", "").strip()
    ocr_address = receipt_data.get("restaurant_address", "").strip()
    ocr_confidence = receipt_data.get("confidence_scores", {})

    # Compare amount
    if ocr_amount > 0:
        expense_amount = expense.amount
        amount_diff = abs(expense_amount - ocr_amount)
        amount_tolerance = Decimal("0.01")  # Allow 1 cent difference

        if amount_diff <= amount_tolerance:
            matches["amount"] = True
        else:
            matches["amount"] = False
            suggestions["amount"] = str(ocr_amount)
            warnings.append(f"Amount mismatch: Form has ${expense_amount}, receipt shows ${ocr_amount}")

    # Compare date
    if ocr_date_str:
        try:
            from datetime import datetime

            ocr_date = datetime.fromisoformat(ocr_date_str.replace("Z", "+00:00"))
            expense_date = expense.date.replace(tzinfo=None) if expense.date.tzinfo else expense.date
            ocr_date_only = ocr_date.date()
            expense_date_only = expense_date.date()

            # Allow ±1 day difference (timezone/rounding issues)
            date_diff = abs((ocr_date_only - expense_date_only).days)

            if date_diff <= 1:
                matches["date"] = True
            else:
                matches["date"] = False
                suggestions["date"] = ocr_date_only.isoformat()
                warnings.append(f"Date mismatch: Form has {expense_date_only}, receipt shows {ocr_date_only}")
        except Exception as e:
            current_app.logger.warning(f"Failed to compare dates: {e}")
            matches["date"] = False

    # Compare restaurant name (fuzzy matching)
    if ocr_restaurant and expense.restaurant:
        import jellyfish

        expense_restaurant_name = expense.restaurant.name.strip().lower()
        ocr_restaurant_lower = ocr_restaurant.lower()

        # Exact match
        if expense_restaurant_name == ocr_restaurant_lower:
            matches["restaurant"] = True
            # Include similarity score for exact matches (100%)
            suggestions["restaurant"] = ocr_restaurant
            suggestions["restaurant_similarity"] = 1.0
        else:
            # Check if one name contains the other (substring match)
            # This handles cases like "Cotton Patch Cafe" vs "Cotton Patch Cafe - Wylie"
            one_contains_other = (
                expense_restaurant_name in ocr_restaurant_lower or ocr_restaurant_lower in expense_restaurant_name
            )

            # Fuzzy match using Jaro-Winkler similarity
            similarity = jellyfish.jaro_winkler_similarity(expense_restaurant_name, ocr_restaurant_lower)

            # Always include suggestion and similarity score, even for partial matches
            suggestions["restaurant"] = ocr_restaurant
            suggestions["restaurant_similarity"] = round(similarity, 2)

            # Stricter matching: require exact match or very high similarity (>= 0.98)
            # AND not a substring match (which indicates location suffix differences)
            if similarity >= 0.98 and not one_contains_other:
                matches["restaurant"] = True
            else:
                # Partial match - show as mismatch but still allow applying
                matches["restaurant"] = False
                if one_contains_other:
                    warnings.append(
                        f"Restaurant name partial match (substring): Form has '{expense.restaurant.name}', receipt shows '{ocr_restaurant}'"
                    )
                else:
                    warnings.append(
                        f"Restaurant name partial match ({similarity*100:.0f}%): Form has '{expense.restaurant.name}', receipt shows '{ocr_restaurant}'"
                    )

    # Compare restaurant address (if both are available)
    if ocr_address and expense.restaurant:
        expense_address = expense.restaurant.full_address or ""

        if expense_address and ocr_address:
            # Use semantic address comparison with USPS normalization
            from app.utils.address_utils import compare_addresses_semantic

            is_match, format_differs = compare_addresses_semantic(expense_address, ocr_address)

            if is_match:
                matches["restaurant_address"] = True
                if format_differs:
                    warnings.append(
                        f"Restaurant address formats differ but match semantically: "
                        f"Form has '{expense_address}', receipt shows '{ocr_address}'"
                    )
            else:
                # Fallback to fuzzy match using Jaro-Winkler similarity
                expense_normalized = re.sub(r"[^\w\s]", "", expense_address.lower())
                expense_normalized = re.sub(r"\s+", " ", expense_normalized).strip()
                ocr_normalized = re.sub(r"[^\w\s]", "", ocr_address.lower())
                ocr_normalized = re.sub(r"\s+", " ", ocr_normalized).strip()

                similarity = jellyfish.jaro_winkler_similarity(expense_normalized, ocr_normalized)

                if similarity >= 0.80:  # 80% similarity threshold for addresses
                    matches["restaurant_address"] = True
                else:
                    matches["restaurant_address"] = False
                    suggestions["restaurant_address"] = ocr_address
                    warnings.append(
                        f"Restaurant address mismatch: Form has '{expense_address}', receipt shows '{ocr_address}'"
                    )
        elif ocr_address:
            # OCR found address but expense doesn't have one - suggest it
            matches["restaurant_address"] = False
            suggestions["restaurant_address"] = ocr_address

    # Calculate overall confidence
    if matches:
        match_count = sum(1 for v in matches.values() if v)
        total_fields = len(matches)
        confidence = match_count / total_fields if total_fields > 0 else 0.0

        # Adjust confidence based on OCR confidence scores
        if ocr_confidence:
            avg_ocr_confidence = sum(ocr_confidence.values()) / len(ocr_confidence) if ocr_confidence else 0.0
            confidence = (confidence + avg_ocr_confidence) / 2.0
    else:
        confidence = 0.0

    # Include restaurant address in response for UI comparison
    restaurant_address_data = None
    if expense.restaurant:
        restaurant_address_data = {
            "full_address": expense.restaurant.full_address,
            "address_line_1": expense.restaurant.address_line_1,
            "address_line_2": expense.restaurant.address_line_2,
            "city": expense.restaurant.city,
            "state": expense.restaurant.state,
            "postal_code": expense.restaurant.postal_code,
        }

    return {
        "matches": matches,
        "suggestions": suggestions,
        "warnings": warnings,
        "confidence": round(confidence, 2),
        "restaurant_address": restaurant_address_data,
        "ocr_restaurant_address": ocr_address,
        "ocr_time": ocr_time_str,
    }
