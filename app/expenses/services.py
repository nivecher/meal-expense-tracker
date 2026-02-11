"""Service functions for the expenses blueprint."""

import csv
from dataclasses import dataclass
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
from app.utils.timezone_utils import get_timezone

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

    # Extract tags - can be multiple values (e.g., ?tags=tag1&tags=tag2) or comma-separated
    tags_param = request.args.getlist("tags")  # Gets all values for 'tags' parameter
    tags_list: list[str] = []
    if tags_param:
        # Handle both comma-separated strings and multiple parameters
        for tag_value in tags_param:
            if isinstance(tag_value, str) and tag_value.strip():
                # Split by comma if comma-separated, otherwise use the whole value
                if "," in tag_value:
                    tags_list.extend([t.strip() for t in tag_value.split(",") if t.strip()])
                else:
                    tags_list.append(tag_value.strip())

    return {
        "search": search_term,
        "meal_type": request.args.get("meal_type", "").strip(),
        "order_type": request.args.get("order_type", "").strip(),
        "category": request.args.get("category", "").strip(),
        "tags": tags_list,  # List of tag names to filter by
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


def _parse_filter_date_value(date_value: str | None) -> date | None:
    """Parse a date string from filter inputs."""
    if not date_value or date_value == "None":
        return None
    try:
        return datetime.strptime(date_value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _get_date_filter_bounds(filters: dict[str, Any]) -> tuple[datetime | None, datetime | None]:
    """Get UTC datetime bounds for date filters in browser timezone."""
    start_date = _parse_filter_date_value(filters.get("start_date"))
    end_date = _parse_filter_date_value(filters.get("end_date"))

    if not start_date and not end_date:
        return None, None

    browser_timezone = get_timezone()
    start_dt_utc = (
        datetime.combine(start_date, time.min, tzinfo=browser_timezone).astimezone(UTC) if start_date else None
    )
    end_dt_utc = datetime.combine(end_date, time.max, tzinfo=browser_timezone).astimezone(UTC) if end_date else None
    return start_dt_utc, end_dt_utc


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
                func.coalesce(Expense.order_type, "").ilike(search_term),
                # Category fields (handle NULL values from outer join)
                func.coalesce(Category.name, "").ilike(search_term),
            )
        )

    # Apply meal type filter
    if filters["meal_type"]:
        stmt = stmt.where(Expense.meal_type == filters["meal_type"])

    # Apply order type filter
    if filters.get("order_type"):
        stmt = stmt.where(Expense.order_type == filters["order_type"])

    # Apply category filter
    if filters["category"]:
        stmt = stmt.where(Category.name == filters["category"])

    # Apply tags filter - expenses must have ALL specified tags
    if filters.get("tags"):
        tags_list: list[str] = filters["tags"]
        if tags_list:
            # For each tag, ensure the expense has that tag using EXISTS subqueries
            # This ensures expenses have ALL tags (AND condition, not OR)
            for tag_name in tags_list:
                tag_subquery = (
                    select(ExpenseTag.expense_id)
                    .join(Tag, Tag.id == ExpenseTag.tag_id)
                    .where(Tag.name == tag_name)
                    .where(ExpenseTag.expense_id == Expense.id)
                )
                stmt = stmt.where(tag_subquery.exists())

    # Apply date range filters in browser timezone
    start_dt_utc, end_dt_utc = _get_date_filter_bounds(filters)
    if start_dt_utc:
        stmt = stmt.where(Expense.date >= start_dt_utc)
    if end_dt_utc:
        stmt = stmt.where(Expense.date <= end_dt_utc)

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
        tags_list: List of tags to validate (can be strings or dicts with "value" key)

    Returns:
        A tuple of (cleaned_tags, error_message)
    """
    if not isinstance(tags_list, list):
        return None, "Tags must be a list"

    processed_tags = []
    for tag in tags_list:
        # Handle dict format: {"value": "tag_name"} (for backward compatibility)
        if isinstance(tag, dict) and "value" in tag:
            tag_name = tag["value"]
        elif isinstance(tag, dict) and "name" in tag:
            tag_name = tag["name"]
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


def export_expenses_for_user(user_id: int, expense_ids: list[int] | None = None) -> list[dict[str, Any]]:
    """Get all expenses for a user in a format suitable for export.

    Args:
        user_id: The ID of the user whose expenses to export
        expense_ids: Optional list of expense IDs to export

    Returns:
        A list of dictionaries containing expense data
    """
    if expense_ids is not None and not expense_ids:
        return []

    query = (
        select(Expense)
        .options(
            joinedload(Expense.restaurant),
            joinedload(Expense.category),
            joinedload(Expense.expense_tags).joinedload(ExpenseTag.tag),
        )
        .where(Expense.user_id == user_id)
        .order_by(Expense.date.desc())
    )

    if expense_ids:
        query = query.where(Expense.id.in_(expense_ids))

    expenses = db.session.execute(query).unique().scalars().all()

    def safe_float(value: Any) -> float | None:
        """Safely convert value to float."""
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    def format_tag_names(expense: Expense) -> str:
        """Format tag names as a comma-separated string."""
        tag_names = [tag.name for tag in expense.tags if tag and tag.name]
        return ", ".join(sorted(tag_names)) if tag_names else ""

    def to_utc_datetime_string(expense: Expense) -> tuple[str, str, str]:
        """Return (date, time_utc, datetime_utc) strings for export."""
        expense_dt = expense.date
        if not expense_dt:
            return "", "", ""

        # Expense.date is expected to be a datetime; keep a single code path for type-checkers.
        dt_val = expense_dt

        if dt_val.tzinfo is None:
            dt_val = dt_val.replace(tzinfo=UTC)

        dt_utc = dt_val.astimezone(UTC).replace(microsecond=0)
        date_str = dt_utc.date().isoformat()
        time_str = dt_utc.time().isoformat()
        datetime_str = dt_utc.isoformat().replace("+00:00", "Z")
        return date_str, time_str, datetime_str

    export_rows: list[dict[str, Any]] = []
    for expense in expenses:
        date_str, time_str, datetime_str = to_utc_datetime_string(expense)
        export_rows.append(
            {
                # Backup-friendly: include both a human-friendly date and full UTC timestamp.
                "date": date_str,
                "time_utc": time_str,
                "datetime_utc": datetime_str,
                "amount": safe_float(expense.amount) if expense.amount is not None else "",
                "meal_type": expense.meal_type or "",
                "order_type": expense.order_type or "",
                "party_size": expense.party_size if expense.party_size is not None else "",
                "notes": expense.notes or "",
                "category_name": expense.category.name if expense.category else "",
                "restaurant_name": expense.restaurant.name if expense.restaurant else "",
                "restaurant_address": expense.restaurant.address if expense.restaurant else "",
                "restaurant_city": expense.restaurant.city if expense.restaurant else "",
                "restaurant_state": expense.restaurant.state if expense.restaurant else "",
                "restaurant_postal_code": expense.restaurant.postal_code if expense.restaurant else "",
                "restaurant_country": expense.restaurant.country if expense.restaurant else "",
                "restaurant_google_place_id": expense.restaurant.google_place_id if expense.restaurant else "",
                "tags": format_tag_names(expense),
                "created_at": expense.created_at.isoformat() if expense.created_at else "",
                "updated_at": expense.updated_at.isoformat() if expense.updated_at else "",
            }
        )

    return export_rows


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
        "datetime": "datetime_utc",
        "date_time": "datetime_utc",
        "datetime_utc": "datetime_utc",
        "timestamp": "datetime_utc",
        # Time field mappings
        "time": "time_utc",
        "time_utc": "time_utc",
        "transaction_time": "time_utc",
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
        "restaurant_city": "restaurant_city",
        "city": "restaurant_city",
        "restaurant_state": "restaurant_state",
        "state": "restaurant_state",
        "restaurant_postal_code": "restaurant_postal_code",
        "postal_code": "restaurant_postal_code",
        "zip": "restaurant_postal_code",
        "zip_code": "restaurant_postal_code",
        "restaurant_country": "restaurant_country",
        "country": "restaurant_country",
        "restaurant_google_place_id": "restaurant_google_place_id",
        "google_place_id": "restaurant_google_place_id",
        # Meal type mappings
        "meal": "meal_type",
        "meal_category": "meal_type",
        # Order / party mappings
        "order_type": "order_type",
        "order": "order_type",
        "service_type": "order_type",
        "party_size": "party_size",
        "party": "party_size",
        "people": "party_size",
        "guests": "party_size",
        # Notes mappings
        "description": "notes",
        "memo": "notes",
        "note": "notes",
        "comment": "notes",
        "remarks": "notes",
        # Tag mappings
        "tag": "tags",
        "tags": "tags",
        "label": "tags",
        "labels": "tags",
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


def _parse_import_file(file: FileStorage) -> tuple[list[dict[str, Any]] | None, str | None]:
    """Parse the uploaded file and return normalized data.

    Args:
        file: The uploaded file

    Returns:
        Tuple of (normalized_data, error_message)
    """
    try:
        max_rows = int(current_app.config.get("IMPORT_MAX_ROWS", 2000))

        if file.filename and file.filename.lower().endswith(".json"):
            # Reset file pointer to beginning
            file.seek(0)
            data = json.load(file)
            if not isinstance(data, list):
                current_app.logger.error("Invalid JSON format. Expected an array of expenses.")
                return None, "Invalid JSON format. Expected an array of expenses."
        else:
            # Parse CSV file
            file.seek(0)
            csv_data = file.read().decode("utf-8")
            reader = csv.DictReader(io.StringIO(csv_data))
            data = list(reader)

        if len(data) > max_rows:
            return (
                None,
                f"File contains {len(data)} rows, which exceeds the maximum supported ({max_rows}). "
                "Please split the file into smaller imports and try again.",
            )

        # Normalize field names for all rows
        normalized_data = []
        for row in data:
            normalized_row = _normalize_field_names(row)
            normalized_data.append(normalized_row)

        return normalized_data, None
    except UnicodeDecodeError:
        current_app.logger.error("Error decoding the file. Please ensure it's a valid CSV or JSON file.")
        return None, "Error decoding the file. Please ensure it's a valid CSV or JSON file."
    except Exception as e:
        current_app.logger.error(f"Error parsing import file: {str(e)}")
        return None, f"Error parsing import file: {str(e)}"


def _parse_import_tags(tags_value: Any) -> tuple[list[str] | None, str | None]:
    """Parse tags from import data (CSV/JSON).

    Accepts comma-separated strings, JSON arrays, or list values.
    """
    if tags_value is None:
        return [], None

    if isinstance(tags_value, str):
        tags_str = tags_value.strip()
        if not tags_str:
            return [], None

        if tags_str.startswith("[") or tags_str.startswith("{"):
            parsed_tags, error = _parse_tags_json(tags_str)
            if error:
                return None, error
            return _validate_tags_list(parsed_tags)

        parsed = [tag.strip() for tag in tags_str.split(",") if tag.strip()]
        return parsed, None

    if isinstance(tags_value, list):
        return _validate_tags_list(tags_value)

    return None, "Tags must be a list or comma-separated string"


def _normalize_tag_name(tag_name: str) -> str:
    """Normalize tag name to match existing creation rules."""
    normalized_name = tag_name.strip().replace(" ", "-")
    normalized_name = "".join(c for c in normalized_name if c.isalnum() or c == "-")
    return normalized_name


def _build_tag_summary(tag_counts: dict[str, int], created_tags: set[str]) -> list[dict[str, Any]]:
    """Build tag summary list for import results."""
    summary = [{"name": name, "count": count, "is_new": name in created_tags} for name, count in tag_counts.items()]
    return sorted(summary, key=lambda item: (-item["count"], item["name"].lower()))


def _normalize_import_tag_names(tag_names: list[str]) -> list[str]:
    """Normalize and deduplicate tag names for imports."""
    normalized_names: list[str] = []
    seen: set[str] = set()
    for tag_name in tag_names:
        normalized_name = _normalize_tag_name(tag_name)
        if not normalized_name or normalized_name in seen:
            continue
        seen.add(normalized_name)
        normalized_names.append(normalized_name)
    return normalized_names


def _apply_import_tags_to_expense(
    expense: Expense,
    user_id: int,
    normalized_tags: list[str],
    existing_tags: dict[str, Tag],
    created_tags: set[str],
    tag_counts: dict[str, int],
) -> None:
    """Attach tags to an imported expense without committing."""
    if not normalized_tags:
        return

    for tag_name in normalized_tags:
        tag = existing_tags.get(tag_name)
        if not tag:
            tag = Tag(name=tag_name, color="#6c757d", user_id=user_id)
            db.session.add(tag)
            existing_tags[tag_name] = tag
            created_tags.add(tag_name)

        expense_tag = ExpenseTag(expense=expense, tag=tag, added_by=user_id)
        db.session.add(expense_tag)
        tag_counts[tag_name] = tag_counts.get(tag_name, 0) + 1


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


def _parse_expense_time(time_value: Any) -> tuple[time | None, str | None]:
    """Parse an optional time value for imports (UTC)."""
    if time_value is None:
        return None, None

    time_str = str(time_value).strip()
    if not time_str:
        return None, None

    time_formats = [
        "%H:%M:%S",
        "%H:%M",
    ]

    for time_format in time_formats:
        try:
            parsed = datetime.strptime(time_str, time_format).time()
            return parsed.replace(microsecond=0), None
        except ValueError:
            continue

    return None, f"Invalid time format: {time_str}. Supported formats: HH:MM or HH:MM:SS (UTC)"


def _parse_expense_datetime_utc(data: dict[str, Any]) -> tuple[datetime | None, date | None, str | None]:
    """Parse expense datetime for imports, prioritizing full UTC timestamp.

    Supported inputs (in priority order):
    - datetime_utc: ISO datetime string (with Z or offset)
    - date + time_utc: date + optional time (assumed UTC)
    - date only: interpreted as noon UTC (preserves intended date across timezones)
    """
    raw_datetime = data.get("datetime_utc")
    if raw_datetime is not None:
        dt_str = str(raw_datetime).strip()
        if dt_str:
            normalized = dt_str.replace("Z", "+00:00")
            try:
                parsed_dt = datetime.fromisoformat(normalized)
                if parsed_dt.tzinfo is None:
                    parsed_dt = parsed_dt.replace(tzinfo=UTC)
                dt_utc = parsed_dt.astimezone(UTC).replace(microsecond=0)
                return dt_utc, dt_utc.date(), None
            except ValueError:
                # Fall through to date/time parsing
                pass

    # Date is still required for imports
    raw_date = data.get("date")
    if isinstance(raw_date, str):
        raw_date = raw_date.strip()
    parsed_date, date_error = _parse_expense_date(raw_date)
    if date_error:
        return None, None, date_error

    raw_time = data.get("time_utc")
    parsed_time, time_error = _parse_expense_time(raw_time)
    if time_error:
        return None, None, time_error

    if parsed_date is None:
        return None, None, "Date is required"

    # If no time is provided, use noon UTC (matches model validation intent).
    final_time = parsed_time if parsed_time is not None else time.min.replace(hour=12)
    dt_utc = datetime.combine(parsed_date, final_time, tzinfo=UTC).replace(microsecond=0)
    return dt_utc, parsed_date, None


def _parse_import_party_size(party_size_value: Any) -> tuple[int | None, str | None]:
    """Parse optional party size for imports."""
    if party_size_value is None:
        return None, None

    raw = str(party_size_value).strip()
    if not raw:
        return None, None

    if not raw.isdigit():
        return None, f"Invalid party size: {raw}. Must be an integer."

    value = int(raw)
    if value < 1 or value > 50:
        return None, f"Invalid party size: {value}. Must be between 1 and 50."

    return value, None


def _parse_import_order_type(order_type_value: Any) -> str | None:
    """Parse optional order type for imports."""
    if order_type_value is None:
        return None
    value = str(order_type_value).strip()
    return value.lower() if value else None


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


@dataclass
class ExpenseImportContext:
    user_id: int
    categories_by_name: dict[str, Category]
    categories_by_lower_name: dict[str, Category]
    categories_all: list[Category]
    restaurants_by_name: dict[str, list[Restaurant]]
    restaurants_by_name_address: dict[tuple[str, str], Restaurant]
    existing_duplicate_keys: set[tuple[int | None, Decimal, date, str | None]]
    seen_import_keys: set[tuple[int | tuple[str, str] | None, Decimal, date, str | None]]


def _build_category_cache_for_import(user_id: int) -> tuple[dict[str, Category], dict[str, Category], list[Category]]:
    """Build category caches for import processing (avoid per-row queries)."""
    categories = Category.query.filter_by(user_id=user_id).all()
    categories_by_name: dict[str, Category] = {}
    categories_by_lower_name: dict[str, Category] = {}

    for category in categories:
        name = category.name.strip() if category.name else ""
        if not name:
            continue
        categories_by_name[name] = category
        categories_by_lower_name[name.lower()] = category

    return categories_by_name, categories_by_lower_name, categories


def _find_category_for_import(category_name: str, ctx: ExpenseImportContext) -> Category | None:
    """Find category by name using in-memory caches (supports hierarchical + fuzzy match)."""
    if not category_name:
        return None

    raw_name = category_name.strip()
    if not raw_name:
        return None

    # Exact match (fast path)
    category = ctx.categories_by_name.get(raw_name)
    if category:
        return category

    # Case-insensitive exact match
    category = ctx.categories_by_lower_name.get(raw_name.lower())
    if category:
        return category

    # Hierarchical category format (e.g., "Parent:Child")
    if ":" in raw_name:
        parent, child = raw_name.split(":", 1)
        child_name = child.strip()
        parent_name = parent.strip()

        if child_name:
            category = ctx.categories_by_name.get(child_name) or ctx.categories_by_lower_name.get(child_name.lower())
            if category:
                return category

        if parent_name:
            category = ctx.categories_by_name.get(parent_name) or ctx.categories_by_lower_name.get(parent_name.lower())
            if category:
                return category

    # Fuzzy "contains" match to mirror the previous DB ilike fallback
    needle = raw_name.lower()
    for cat in ctx.categories_all:
        name = cat.name.strip() if cat.name else ""
        if name and needle in name.lower():
            return cat

    # Restore-friendly: create missing categories on import.
    new_category = Category(
        user_id=ctx.user_id,
        name=raw_name,
        description=None,
        color="#6c757d",
        icon=None,
        is_default=False,
    )
    db.session.add(new_category)
    ctx.categories_by_name[raw_name] = new_category
    ctx.categories_by_lower_name[raw_name.lower()] = new_category
    ctx.categories_all.append(new_category)
    return new_category


def _build_restaurant_cache_for_import(
    user_id: int,
) -> tuple[dict[str, list[Restaurant]], dict[tuple[str, str], Restaurant]]:
    """Build restaurant caches for import processing (avoid per-row queries)."""
    restaurants = Restaurant.query.filter_by(user_id=user_id).all()
    restaurants_by_name: dict[str, list[Restaurant]] = {}
    restaurants_by_name_address: dict[tuple[str, str], Restaurant] = {}

    for restaurant in restaurants:
        name = restaurant.name.strip() if restaurant.name else ""
        if not name:
            continue
        restaurants_by_name.setdefault(name, []).append(restaurant)

        address = restaurant.address_line_1.strip() if restaurant.address_line_1 else ""
        if address:
            restaurants_by_name_address[(name, address)] = restaurant

    return restaurants_by_name, restaurants_by_name_address


def _find_existing_restaurant_for_import(
    restaurant_name: str,
    restaurant_address: str,
    ctx: ExpenseImportContext,
    restaurant_city: str | None = None,
) -> Restaurant | None:
    """Find an existing restaurant for import duplicate prefetch (no creation, no warnings)."""
    name = restaurant_name.strip()
    if not name:
        return None

    address = restaurant_address.strip() if restaurant_address else ""
    if address:
        return ctx.restaurants_by_name_address.get((name, address))

    matches = ctx.restaurants_by_name.get(name, [])
    if len(matches) == 1:
        return matches[0]

    if restaurant_city:
        city_norm = restaurant_city.strip().lower()
        if city_norm:
            city_matches = [r for r in matches if (r.city or "").strip().lower() == city_norm]
            if len(city_matches) == 1:
                return city_matches[0]

    return None


def _find_or_create_restaurant_for_import(
    restaurant_name: str,
    restaurant_address: str,
    ctx: ExpenseImportContext,
    restaurant_details: dict[str, Any] | None = None,
) -> tuple[Restaurant | None, str | None]:
    """Import-specific restaurant resolution using caches (creates without per-row DB lookups)."""

    def merge_details(restaurant: Restaurant) -> None:
        if not restaurant_details:
            return

        def set_if_empty(attr: str, value: Any) -> None:
            if value is None:
                return
            value_str = str(value).strip()
            if not value_str:
                return
            current = getattr(restaurant, attr, None)
            if current is None:
                setattr(restaurant, attr, value_str)
                return
            if isinstance(current, str) and not current.strip():
                setattr(restaurant, attr, value_str)

        set_if_empty("city", restaurant_details.get("restaurant_city"))
        set_if_empty("state", restaurant_details.get("restaurant_state"))
        set_if_empty("postal_code", restaurant_details.get("restaurant_postal_code"))
        set_if_empty("country", restaurant_details.get("restaurant_country"))
        set_if_empty("google_place_id", restaurant_details.get("restaurant_google_place_id"))

    if not restaurant_name:
        return None, None

    name = restaurant_name.strip()
    if not name:
        return None, None

    address = restaurant_address.strip() if restaurant_address else ""
    if address:
        existing = ctx.restaurants_by_name_address.get((name, address))
        if existing:
            merge_details(existing)
            return existing, None

        new_restaurant = Restaurant(
            user_id=ctx.user_id,
            name=name,
            address_line_1=address,
            city=str((restaurant_details or {}).get("restaurant_city") or "").strip() or None,
            state=str((restaurant_details or {}).get("restaurant_state") or "").strip() or None,
            postal_code=str((restaurant_details or {}).get("restaurant_postal_code") or "").strip() or None,
            country=str((restaurant_details or {}).get("restaurant_country") or "").strip() or None,
            google_place_id=str((restaurant_details or {}).get("restaurant_google_place_id") or "").strip() or None,
        )
        db.session.add(new_restaurant)

        ctx.restaurants_by_name.setdefault(name, []).append(new_restaurant)
        ctx.restaurants_by_name_address[(name, address)] = new_restaurant
        return new_restaurant, None

    name_matches = ctx.restaurants_by_name.get(name, [])
    if len(name_matches) == 1:
        merge_details(name_matches[0])
        return name_matches[0], None
    if len(name_matches) > 1:
        # If city is provided, try to disambiguate by city
        city_norm = str((restaurant_details or {}).get("restaurant_city") or "").strip().lower()
        if city_norm:
            city_matches = [r for r in name_matches if (r.city or "").strip().lower() == city_norm]
            if len(city_matches) == 1:
                merge_details(city_matches[0])
                return city_matches[0], None

        return (
            None,
            f"Restaurant '{name}' matches multiple existing restaurants. Please provide an address to disambiguate.",
        )

    # No matches and no address: create a restaurant so CSV backups can be restored.
    new_restaurant = Restaurant(
        user_id=ctx.user_id,
        name=name,
        address_line_1=None,
        city=str((restaurant_details or {}).get("restaurant_city") or "").strip() or None,
        state=str((restaurant_details or {}).get("restaurant_state") or "").strip() or None,
        postal_code=str((restaurant_details or {}).get("restaurant_postal_code") or "").strip() or None,
        country=str((restaurant_details or {}).get("restaurant_country") or "").strip() or None,
        google_place_id=str((restaurant_details or {}).get("restaurant_google_place_id") or "").strip() or None,
    )
    db.session.add(new_restaurant)
    ctx.restaurants_by_name.setdefault(name, []).append(new_restaurant)
    return new_restaurant, None


def _compute_import_duplicate_prefetch_scope(
    data: list[dict[str, Any]],
    ctx: ExpenseImportContext,
) -> tuple[date | None, date | None, set[int], bool]:
    """Compute date range + restaurant scope to prefetch duplicates efficiently."""
    min_date: date | None = None
    max_date: date | None = None
    restaurant_ids: set[int] = set()
    includes_null_restaurant = False

    for row in data:
        _dt_utc, parsed_date, _dt_error = _parse_expense_datetime_utc(row)
        if parsed_date:
            min_date = parsed_date if min_date is None else min(min_date, parsed_date)
            max_date = parsed_date if max_date is None else max(max_date, parsed_date)

        restaurant_name = str(row.get("restaurant_name", "") or "").strip()
        restaurant_address = str(row.get("restaurant_address", "") or "").strip()
        restaurant_city = str(row.get("restaurant_city", "") or "").strip()
        if not restaurant_name:
            includes_null_restaurant = True
            continue

        existing_restaurant = _find_existing_restaurant_for_import(
            restaurant_name,
            restaurant_address,
            ctx,
            restaurant_city=restaurant_city,
        )
        if existing_restaurant and existing_restaurant.id is not None:
            restaurant_ids.add(int(existing_restaurant.id))

    return min_date, max_date, restaurant_ids, includes_null_restaurant


def _prefetch_existing_duplicate_keys_for_import(
    user_id: int,
    min_date: date | None,
    max_date: date | None,
    restaurant_ids: set[int],
    includes_null_restaurant: bool,
) -> set[tuple[int | None, Decimal, date, str | None]]:
    """Prefetch existing expenses for duplicate checks (massively reduces per-row queries)."""
    if min_date is None or max_date is None:
        return set()

    if not restaurant_ids and not includes_null_restaurant:
        return set()

    start_dt = datetime.combine(min_date, time.min, tzinfo=UTC)
    end_dt_exclusive = datetime.combine(max_date + timedelta(days=1), time.min, tzinfo=UTC)

    query = (
        db.session.query(Expense.restaurant_id, Expense.amount, Expense.meal_type, Expense.date)
        .filter(Expense.user_id == user_id)
        .filter(Expense.date >= start_dt)
        .filter(Expense.date < end_dt_exclusive)
    )

    if restaurant_ids and includes_null_restaurant:
        query = query.filter(or_(Expense.restaurant_id.in_(restaurant_ids), Expense.restaurant_id.is_(None)))
    elif restaurant_ids:
        query = query.filter(Expense.restaurant_id.in_(restaurant_ids))
    else:
        query = query.filter(Expense.restaurant_id.is_(None))

    existing_keys: set[tuple[int | None, Decimal, date, str | None]] = set()
    for restaurant_id, amount, meal_type, expense_dt in query.all():
        expense_date = expense_dt.date() if isinstance(expense_dt, datetime) else expense_dt
        existing_keys.add((restaurant_id, amount, expense_date, meal_type))

    return existing_keys


def _build_expense_import_context(user_id: int, data: list[dict[str, Any]]) -> ExpenseImportContext:
    """Build a full import context with in-memory caches and prefetched duplicates."""
    categories_by_name, categories_by_lower_name, categories_all = _build_category_cache_for_import(user_id)
    restaurants_by_name, restaurants_by_name_address = _build_restaurant_cache_for_import(user_id)

    ctx = ExpenseImportContext(
        user_id=user_id,
        categories_by_name=categories_by_name,
        categories_by_lower_name=categories_by_lower_name,
        categories_all=categories_all,
        restaurants_by_name=restaurants_by_name,
        restaurants_by_name_address=restaurants_by_name_address,
        existing_duplicate_keys=set(),
        seen_import_keys=set(),
    )

    scope_min_date, scope_max_date, restaurant_ids, includes_null_restaurant = _compute_import_duplicate_prefetch_scope(
        data,
        ctx,
    )
    ctx.existing_duplicate_keys = _prefetch_existing_duplicate_keys_for_import(
        user_id=user_id,
        min_date=scope_min_date,
        max_date=scope_max_date,
        restaurant_ids=restaurant_ids,
        includes_null_restaurant=includes_null_restaurant,
    )

    return ctx


def _create_expense_from_data(data: dict[str, Any], ctx: ExpenseImportContext) -> tuple[Expense | None, str | None]:
    """Create an expense from import data with smart restaurant handling and duplicate detection.

    Args:
        data: The expense data dictionary
        ctx: Import context (caches + duplicate tracking)

    Returns:
        Tuple of (expense, error_message)
    """
    try:
        # Parse datetime (UTC) with restore-friendly support for full timestamps
        expense_dt_utc, expense_date, datetime_error = _parse_expense_datetime_utc(data)
        if datetime_error:
            return None, datetime_error
        if expense_dt_utc is None or expense_date is None:
            return None, "Date is required"

        # Parse amount
        amount, amount_error = _parse_expense_amount(str(data.get("amount", "")).strip())
        if amount_error:
            return None, amount_error
        if amount is None:
            return None, "Amount is required"

        # Parse optional order details
        order_type = _parse_import_order_type(data.get("order_type"))
        party_size, party_size_error = _parse_import_party_size(data.get("party_size"))
        if party_size_error:
            return None, party_size_error

        # Find category
        category = _find_category_for_import(str(data.get("category_name", "") or ""), ctx)

        # Find or create restaurant with smart logic
        restaurant_name = str(data.get("restaurant_name") or "").strip()
        restaurant_address = str(data.get("restaurant_address") or "").strip()
        restaurant_details = {
            "restaurant_city": str(data.get("restaurant_city") or "").strip(),
            "restaurant_state": str(data.get("restaurant_state") or "").strip(),
            "restaurant_postal_code": str(data.get("restaurant_postal_code") or "").strip(),
            "restaurant_country": str(data.get("restaurant_country") or "").strip(),
            "restaurant_google_place_id": str(data.get("restaurant_google_place_id") or "").strip(),
        }
        restaurant, restaurant_warning = _find_or_create_restaurant_for_import(
            restaurant_name,
            restaurant_address,
            ctx,
            restaurant_details=restaurant_details,
        )

        # If restaurant matching failed due to ambiguity, return warning
        if restaurant_warning:
            return None, restaurant_warning

        # Extract meal type
        meal_type = str(data.get("meal_type") or "").strip() or None

        # Check for duplicate expense (prefetched DB keys + duplicates within this import)
        restaurant_id = restaurant.id if restaurant else None
        db_key = (restaurant_id, amount, expense_date, meal_type)
        if restaurant_id is not None and db_key in ctx.existing_duplicate_keys:
            restaurant_name_display = restaurant.name if restaurant else "Unknown"
            return (
                None,
                f"Duplicate expense: ${amount} at {restaurant_name_display} on {expense_date} for {meal_type or 'unspecified meal'}",
            )

        import_restaurant_identity: int | tuple[str, str] | None
        if restaurant_id is not None:
            import_restaurant_identity = int(restaurant_id)
        elif restaurant and restaurant.name:
            import_restaurant_identity = (restaurant.name, restaurant.address_line_1 or "")
        else:
            import_restaurant_identity = None

        import_key = (import_restaurant_identity, amount, expense_date, meal_type)
        if import_key in ctx.seen_import_keys:
            restaurant_name_display = restaurant.name if restaurant else "Unknown"
            return (
                None,
                f"Duplicate expense: ${amount} at {restaurant_name_display} on {expense_date} for {meal_type or 'unspecified meal'}",
            )
        ctx.seen_import_keys.add(import_key)

        # Create expense
        expense = Expense(
            user_id=ctx.user_id,
            date=expense_dt_utc,
            amount=amount,
            meal_type=meal_type,
            order_type=order_type,
            party_size=party_size,
            notes=str(data.get("notes") or "").strip() or None,
            category=category if category else None,
            restaurant=restaurant if restaurant else None,
        )

        return expense, None

    except Exception as e:
        return None, f"Error creating expense: {str(e)}"


def _import_expenses_from_reader(
    data: list[dict[str, Any]], user_id: int
) -> tuple[int, list[str], list[str], dict[str, Any]]:
    """Import expenses from parsed data.

    Args:
        data: List of expense data dictionaries
        user_id: The ID of the user importing the expenses

    Returns:
        Tuple of (success_count, errors, info_messages, import_summary)
    """
    success_count = 0
    errors: list[str] = []
    info_messages: list[str] = []
    batch_size = int(current_app.config.get("IMPORT_BATCH_SIZE", 200))
    batch_size = max(10, min(batch_size, 1000))  # Safety bounds
    max_summary_items = 10

    import_ctx = _build_expense_import_context(user_id, data)

    existing_tags = {tag.name: tag for tag in Tag.query.filter_by(user_id=user_id).all()}
    created_tags: set[str] = set()
    tag_counts: dict[str, int] = {}
    restaurant_names: set[str] = set()
    expense_summaries: list[dict[str, Any]] = []

    for i, row in enumerate(data, 1):
        tag_names, tag_error = _parse_import_tags(row.get("tags"))
        if tag_error:
            _handle_import_error(f"Tags error: {tag_error}", i, errors, info_messages)
            continue

        normalized_tags = _normalize_import_tag_names(tag_names or [])

        expense, error = _process_expense_row(row, import_ctx, i)
        if error:
            _handle_import_error(error, i, errors, info_messages)
            continue

        if expense:
            db.session.add(expense)
            success_count += 1

            if normalized_tags:
                _apply_import_tags_to_expense(
                    expense,
                    user_id,
                    normalized_tags,
                    existing_tags,
                    created_tags,
                    tag_counts,
                )

            if expense.restaurant and expense.restaurant.name:
                restaurant_names.add(expense.restaurant.name)

            if len(expense_summaries) < max_summary_items:
                expense_summaries.append(
                    {
                        "date": expense.date.isoformat() if expense.date else "",
                        "amount": float(expense.amount) if expense.amount is not None else None,
                        "restaurant_name": expense.restaurant.name if expense.restaurant else "",
                        "meal_type": expense.meal_type or "",
                        "tags": ", ".join(normalized_tags) if normalized_tags else "",
                    }
                )

            # Commit every batch_size records to avoid memory issues
            if success_count % batch_size == 0:
                commit_success = _commit_batch(success_count, batch_size, errors)
                if not commit_success:
                    import_summary = {
                        "tag_summary": _build_tag_summary(tag_counts, created_tags),
                        "restaurant_summary": sorted(restaurant_names),
                        "expense_summary": expense_summaries,
                        "expense_summary_total": success_count,
                    }
                    return success_count, errors, info_messages, import_summary

    # Don't limit messages - let the frontend handle display properly
    import_summary = {
        "tag_summary": _build_tag_summary(tag_counts, created_tags),
        "restaurant_summary": sorted(restaurant_names),
        "expense_summary": expense_summaries,
        "expense_summary_total": success_count,
    }
    return success_count, errors, info_messages, import_summary


def _process_expense_row(
    row: dict[str, Any],
    ctx: ExpenseImportContext,
    row_number: int,
) -> tuple[Expense | None, str | None]:
    """Process a single expense row and return expense or error.

    Args:
        row: The expense data dictionary
        ctx: Import context (caches + duplicate tracking)
        row_number: The row number for error reporting

    Returns:
        Tuple of (expense, error_message)
    """
    try:
        return _create_expense_from_data(row, ctx)
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
    success_count: int,
    errors: list[str],
    info_messages: list[str],
    import_summary: dict[str, Any],
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
        "tag_summary": import_summary.get("tag_summary", []),
        "restaurant_summary": import_summary.get("restaurant_summary", []),
        "expense_summary": import_summary.get("expense_summary", []),
        "expense_summary_total": import_summary.get("expense_summary_total", 0),
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
        data, parse_error = _parse_import_file(file)
        if data is None:
            error_msg = parse_error or "Error parsing file. Please check the file format."
            return False, {"message": error_msg, "has_errors": True, "error_details": [error_msg]}

        # Import expenses from the data
        success_count, errors, info_messages, import_summary = _import_expenses_from_reader(data, user_id)

        # Generate the result data
        return _generate_import_result(success_count, errors, info_messages, import_summary)

    except Exception as e:
        db.session.rollback()
        error_msg = f"Error processing file: {str(e)}"
        return False, {"message": error_msg, "has_errors": True, "error_details": [error_msg]}


# Tag Services
def create_tag(user_id: int, name: str, color: str = "#6c757d", description: str | None = None) -> Tag:
    """Create a new tag for a user.

    Args:
        user_id: ID of the user creating the tag
        name: Name of the tag (spaces will be replaced with hyphens, case preserved)
        color: Hex color code for the tag
        description: Optional description of the tag

    Returns:
        The created Tag object

    Raises:
        ValueError: If tag name is invalid or already exists
    """
    if not name or not name.strip():
        raise ValueError("Tag name is required")

    # Normalize tag name (preserve case, replace spaces with hyphens)
    normalized_name = name.strip().replace(" ", "-")
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
        name: New name of the tag (spaces will be replaced with hyphens, case preserved)
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

    # Normalize tag name (preserve case, replace spaces with hyphens)
    normalized_name = name.strip().replace(" ", "-")
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

    # Expire any cached Tag queries to ensure fresh data
    # This is important after deletions to avoid stale data
    db.session.expire_all()

    # Explicitly filter by user_id to ensure security
    # Use fresh query to avoid session cache issues
    tags = db.session.query(Tag).filter_by(user_id=user_id).order_by(Tag.name).all()

    # Defensive check: Verify all tags belong to the user (security measure)
    invalid_tags = [tag for tag in tags if tag.user_id != user_id]
    if invalid_tags:
        current_app.logger.error(
            f"SECURITY ISSUE: Found {len(invalid_tags)} tags that don't belong to user {user_id}. "
            f"Tag IDs: {[tag.id for tag in invalid_tags]}"
        )
        # Filter out any tags that don't belong to the user
        tags = [tag for tag in tags if tag.user_id == user_id]

    # Optimize: Get all expense statistics in a single query instead of N+1 queries
    if tags:
        tag_ids = [tag.id for tag in tags]

        # Get comprehensive statistics per tag: count, total amount, last visit date
        # Joining with Expense to ensure expenses exist and filter by user_id
        stats = (
            db.session.query(
                ExpenseTag.tag_id,
                func.count(ExpenseTag.id).label("count"),
                func.coalesce(func.sum(Expense.amount), 0).label("total_amount"),
                func.max(Expense.date).label("last_visit"),
            )
            .join(Expense, ExpenseTag.expense_id == Expense.id)
            .filter(ExpenseTag.tag_id.in_(tag_ids))
            .filter(Expense.user_id == user_id)  # Ensure we only count user's expenses
            .group_by(ExpenseTag.tag_id)
            .all()
        )

        # Create dictionaries mapping tag_id to statistics
        count_dict = {}
        total_amount_dict = {}
        last_visit_dict = {}

        for tag_id, count, total_amount, last_visit in stats:
            count_dict[tag_id] = count
            total_amount_dict[tag_id] = float(total_amount) if total_amount else 0.0
            last_visit_dict[tag_id] = last_visit

        # Set statistics on each tag object
        for tag in tags:
            tag._expense_count = count_dict.get(tag.id, 0)
            tag._total_amount = total_amount_dict.get(tag.id, 0.0)
            tag._last_visit = last_visit_dict.get(tag.id, None)

    return cast(list[Tag], tags)


def search_tags(user_id: int, query: str, limit: int = 10) -> list[Tag]:
    """Search tags by name for a user (case-insensitive for autocomplete).

    Args:
        user_id: ID of the user
        query: Search query string
        limit: Maximum number of results to return

    Returns:
        List of matching Tag objects (with original case preserved)

    Note:
        Search is case-insensitive to match Jira-style UX, but tags are
        stored case-sensitively. Typing "morgan" will match "Morgan".
    """
    if not query or not query.strip():
        return []

    search_term = f"%{query.strip()}%"
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
    # Normalize tag name (preserve case, replace spaces with hyphens)
    normalized_name = name.strip().replace(" ", "-")
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

        # Normalize tag name (preserve case, replace spaces with hyphens)
        normalized_name = tag_name.strip().replace(" ", "-")
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

    Raises:
        Exception: If database operation fails
    """
    from flask import current_app

    try:
        # Get tag and verify it exists
        tag = db.session.get(Tag, tag_id)
        if not tag:
            current_app.logger.warning(f"Tag {tag_id} not found for deletion by user {user_id}")
            return False

        # Verify ownership
        if tag.user_id != user_id:
            current_app.logger.warning(
                f"Tag {tag_id} belongs to user {tag.user_id}, but user {user_id} attempted deletion"
            )
            return False

        # Remove tag from all expenses (bulk delete for performance)
        # Use synchronize_session=False to avoid session state issues
        expense_tag_count = ExpenseTag.query.filter_by(tag_id=tag_id).count()
        if expense_tag_count > 0:
            ExpenseTag.query.filter_by(tag_id=tag_id).delete(synchronize_session=False)
            current_app.logger.debug(f"Removed tag {tag_id} from {expense_tag_count} expense(s)")

        # Delete the tag itself
        db.session.delete(tag)

        # Flush to ensure the delete is in the session before commit
        db.session.flush()

        # Commit the transaction - this actually deletes from database
        db.session.commit()

        # Force a new session query context to ensure fresh data
        # This prevents any cached queries from returning the deleted tag
        db.session.expire_all()

        # Verify deletion by attempting to reload (should return None after commit)
        # Use a fresh query to bypass any session cache
        deleted_tag = db.session.query(Tag).filter_by(id=tag_id).first()
        if deleted_tag is not None:
            current_app.logger.error(
                f"Tag {tag_id} still exists after deletion! This indicates a database transaction issue."
            )
            # Don't rollback here - the commit already happened
            # Just log the error and return False
            return False

        current_app.logger.info(f"Tag {tag_id} deleted successfully by user {user_id}")
        return True
    except Exception as e:
        current_app.logger.error(f"Error deleting tag {tag_id} for user {user_id}: {e}", exc_info=True)
        db.session.rollback()
        raise


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
