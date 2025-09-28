"""Service functions for the expenses blueprint."""

import csv
import io
import json
from datetime import date, datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from flask import Request, current_app
from flask_wtf import FlaskForm
from sqlalchemy import extract, func, or_, select
from sqlalchemy.orm import joinedload
from werkzeug.datastructures import FileStorage

from app.constants.categories import get_default_categories
from app.expenses.forms import ExpenseForm
from app.expenses.models import Category, Expense, ExpenseTag, Tag
from app.extensions import db
from app.restaurants.models import Restaurant

# =============================================================================
# EXPENSE FILTERING AND SEARCH FUNCTIONALITY
# =============================================================================


def get_expense_filters(request: Request) -> Dict[str, Any]:
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


def get_user_expenses(user_id: int, filters: Dict[str, Any]) -> Tuple[List[Expense], float]:
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
    expenses = result.scalars().unique().all()

    # Calculate total
    total_amount = sum(expense.amount for expense in expenses) if expenses else 0.0

    # Calculate average price per person
    # Include all expenses where party_size is set (including single person)
    # This matches what's displayed in the table
    price_per_person_values = []
    for expense in expenses:
        if expense.party_size is not None and expense.party_size > 0:
            # Include all expenses with party size set (single or multi-person)
            price_per_person_values.append(float(expense.price_per_person))

    avg_price_per_person = (
        sum(price_per_person_values) / len(price_per_person_values) if price_per_person_values else None
    )

    return expenses, total_amount, avg_price_per_person


def apply_filters(stmt, filters: Dict[str, Any]):
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
                # Restaurant fields
                Restaurant.name.ilike(search_term),
                Restaurant.address_line_1.ilike(search_term),
                Restaurant.address_line_2.ilike(search_term),
                # Expense fields
                Expense.notes.ilike(search_term),
                Expense.meal_type.ilike(search_term),
                # Category fields
                Category.name.ilike(search_term),
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
            start_date = datetime.strptime(filters["start_date"], "%Y-%m-%d").date()
            stmt = stmt.where(Expense.date >= start_date)
        except (ValueError, TypeError):
            # Log the error but don't fail the query
            pass

    if filters["end_date"]:
        try:
            end_date = datetime.strptime(filters["end_date"], "%Y-%m-%d").date()
            stmt = stmt.where(Expense.date <= end_date)
        except (ValueError, TypeError):
            # Log the error but don't fail the query
            pass

    return stmt


def apply_sorting(stmt, sort_by: str, sort_order: str):
    """Apply sorting to the query.

    Args:
        stmt: The SQLAlchemy select statement
        sort_by: Field to sort by
        sort_order: Sort order ('asc' or 'desc')

    Returns:
        The modified select statement with sorting applied
    """
    is_desc = sort_order.lower() == "desc"
    sort_fields = []

    if sort_by == "date":
        # Primary sort by date, secondary sort by created_at for recently entered expenses
        primary_field = Expense.date.desc() if is_desc else Expense.date.asc()
        secondary_field = Expense.created_at.desc() if is_desc else Expense.created_at.asc()
        sort_fields = [primary_field, secondary_field]
    elif sort_by == "amount":
        sort_field = Expense.amount.desc() if is_desc else Expense.amount.asc()
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


def get_main_filter_options(user_id: int) -> Dict[str, List[str]]:
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


def _process_time(time_value: Any) -> Tuple[Optional[time], Optional[str]]:
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


def _process_amount(amount_value: Any) -> Tuple[Optional[Decimal], Optional[str]]:
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


def _parse_tags_json(tags_data: str) -> Tuple[Optional[list], Optional[str]]:
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


def _validate_tags_list(tags_list: Any) -> Tuple[Optional[list[str]], Optional[str]]:
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


def _process_tags(form: ExpenseForm) -> Tuple[Optional[list[str]], Optional[str]]:
    """Process and validate tags from form data.

    Args:
        form: The expense form containing tags data

    Returns:
        A tuple of (processed_tags, error_message)
    """
    try:
        # Get tags from form data (sent as JSON string from JavaScript)
        tags_data = form.tags.data if hasattr(form, "tags") and form.tags.data else None
        current_app.logger.info(f"Processing tags - raw data: {tags_data}")

        if not tags_data:
            current_app.logger.info("No tags data found")
            return [], None  # No tags is valid

        # Parse JSON if it's a string
        if isinstance(tags_data, str):
            tags_list, error = _parse_tags_json(tags_data)
            if error:
                return None, error
        else:
            tags_list = tags_data

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
        # Get user timezone for proper time handling
        from app.auth.models import User
        from app.extensions import db

        user = db.session.get(User, user_id)
        user_timezone = user.timezone if user and user.timezone else "UTC"
        # Process form data
        expense_data = _process_expense_form_data(form, user_timezone)
        if isinstance(expense_data, str):  # Error message
            return None, expense_data

        category_id, restaurant_id, datetime_value, amount, tags = expense_data

        # Create and save the expense
        # Use current datetime in user's timezone if no datetime provided
        if not datetime_value:
            from app.auth.models import User
            from app.utils.timezone_utils import get_current_time_in_user_timezone

            user = User.query.get(user_id)
            user_timezone = user.timezone if user and user.timezone else "UTC"
            datetime_value = get_current_time_in_user_timezone(user_timezone)

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


def _process_expense_form_data(
    form: ExpenseForm, user_timezone: str = "UTC"
) -> Union[Tuple[int, Optional[int], datetime, Decimal, list[str]], str]:
    """Process all form data for expense creation/update.

    Args:
        form: The expense form

    Returns:
        Either a tuple of processed data or an error message string
    """
    category_id, error = _process_category_id(form)
    if error:
        return error

    restaurant_id, error = _process_restaurant_id(form)
    if error:
        return error

    date_value, error = _process_date(form.date.data)
    if error:
        return error

    time_value, error = _process_time(form.time.data)
    if error:
        return error

    amount, error = _process_amount(form.amount.data)
    if error:
        return error

    tags, error = _process_tags(form)
    if error:
        return error

    # Combine date and time into a datetime object
    if time_value:
        # Use the provided time - interpret as user's local time
        import pytz

        from app.utils.timezone_utils import get_user_timezone

        user_tz = get_user_timezone(user_timezone)
        user_datetime = datetime.combine(date_value, time_value)
        # Localize to user's timezone, then convert to UTC for storage
        user_datetime_tz = user_tz.localize(user_datetime)
        datetime_value = user_datetime_tz.astimezone(pytz.UTC).replace(tzinfo=None)  # Remove tzinfo for storage
    else:
        # Use noon to avoid timezone issues (as we did before)
        datetime_value = datetime.combine(date_value, time(12, 0))

    return category_id, restaurant_id, datetime_value, amount, tags


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
        expense_data = _process_expense_form_data(form)
        if isinstance(expense_data, str):  # Error message
            return None, expense_data

        category_id, restaurant_id, date_value, amount, tags = expense_data

        # Update expense fields
        expense.amount = float(amount)
        expense.date = date_value
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


def get_expense_by_id(expense_id: int, user_id: int) -> Optional[Expense]:
    """Get an expense by ID, ensuring it belongs to the user.

    Args:
        expense_id: The ID of the expense to retrieve
        user_id: The ID of the user who owns the expense

    Returns:
        The expense if found and belongs to the user, None otherwise
    """
    return (
        Expense.query.options(joinedload(Expense.expense_tags).joinedload(ExpenseTag.tag))
        .filter_by(id=expense_id, user_id=user_id)
        .first()
    )


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
    return (
        Expense.query.options(joinedload(Expense.expense_tags).joinedload(ExpenseTag.tag))
        .filter_by(user_id=user_id)
        .order_by(Expense.date.desc())
        .all()
    )


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


def _normalize_field_names(data_row: Dict[str, Any]) -> Dict[str, Any]:
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


def _parse_import_file(file: FileStorage) -> Optional[List[Dict[str, Any]]]:
    """Parse the uploaded file and return normalized data.

    Args:
        file: The uploaded file

    Returns:
        List of normalized expense data dictionaries or None if error
    """
    try:
        if file.filename.lower().endswith(".json"):
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


def _parse_excel_serial_date(date_str: str) -> Tuple[Optional[date], bool]:
    """Parse Excel serial date format.

    Args:
        date_str: The date string to parse

    Returns:
        Tuple of (parsed_date, is_excel_date)
    """
    try:
        serial_number = float(date_str)
        if serial_number.is_integer() and 1 <= serial_number <= 2958465:  # Valid Excel date range
            # Excel uses 1900-01-01 as day 1, but incorrectly treats 1900 as a leap year
            excel_epoch = datetime(1899, 12, 30)  # Day 0 in Excel
            try:
                parsed_date = excel_epoch + timedelta(days=int(serial_number))
                return parsed_date.date(), True
            except (ValueError, OverflowError):
                pass
    except (ValueError, TypeError):
        pass

    return None, False


def _parse_standard_date_formats(date_str: str) -> Tuple[Optional[date], Optional[str]]:
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


def _parse_expense_date(date_str: str) -> Tuple[Optional[date], Optional[str]]:
    """Parse expense date from string with support for multiple formats.

    Supported formats:
    - ISO format: YYYY-MM-DD
    - US format: M/D/YYYY, MM/DD/YYYY
    - Alternative US: M-D-YYYY, MM-DD-YYYY
    - Excel serial dates: numeric values (1-based from 1900-01-01)

    Args:
        date_str: The date string to parse

    Returns:
        Tuple of (parsed_date, error_message)
    """
    if not date_str:
        return None, "Date is required"

    # Strip whitespace
    date_str = str(date_str).strip()

    # Try Excel serial date first
    excel_date, is_excel = _parse_excel_serial_date(date_str)
    if is_excel:
        return excel_date, None

    # Try standard date formats
    return _parse_standard_date_formats(date_str)


def _parse_expense_amount(amount_str: str) -> Tuple[Optional[Decimal], Optional[str]]:
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
        return None, f"Invalid amount: {amount_str}. Supported formats: 24.77, $24.77, (24.77), ($24.77)"


def _find_category_by_name(category_name: str, user_id: int) -> Optional[Category]:
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
        return category

    # Handle hierarchical category format (e.g., "Dining & Drinks:Fast Food")
    if ":" in category_name:
        # Try the part after the colon (subcategory)
        subcategory_name = category_name.split(":", 1)[1].strip()
        category = Category.query.filter_by(user_id=user_id, name=subcategory_name).first()
        if category:
            return category

        # Try the part before the colon (parent category)
        parent_category_name = category_name.split(":", 1)[0].strip()
        category = Category.query.filter_by(user_id=user_id, name=parent_category_name).first()
        if category:
            return category

    # Try case-insensitive search as fallback
    category = Category.query.filter(Category.user_id == user_id, Category.name.ilike(f"%{category_name}%")).first()

    return category


def _find_or_create_restaurant(
    restaurant_name: str, restaurant_address: str, user_id: int
) -> Tuple[Optional[Restaurant], Optional[str]]:
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
    restaurant_address = restaurant_address.strip() if restaurant_address else None

    # Strategy 1: Exact name + address match (if address provided)
    if restaurant_address:
        existing = Restaurant.query.filter_by(user_id=user_id, name=restaurant_name, address=restaurant_address).first()
        if existing:
            return existing, None

        # If address provided but no match, create new restaurant
        try:
            new_restaurant = Restaurant(
                user_id=user_id,
                name=restaurant_name,
                address=restaurant_address,
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
    user_id: int, restaurant_id: Optional[int], amount: Decimal, expense_date: date, meal_type: Optional[str]
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
    """Create an expense from import data with smart restaurant handling and duplicate detection.

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
        if _check_expense_duplicate(user_id, restaurant.id if restaurant else None, amount, expense_date, meal_type):
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


def _import_expenses_from_reader(data: List[Dict[str, Any]], user_id: int) -> Tuple[int, List[str], List[str]]:
    """Import expenses from parsed data.

    Args:
        data: List of expense data dictionaries
        user_id: The ID of the user importing the expenses

    Returns:
        Tuple of (success_count, errors, info_messages)
    """
    success_count = 0
    errors = []
    info_messages = []

    for i, row in enumerate(data, 1):
        try:
            expense, error = _create_expense_from_data(row, user_id)
            if error:
                if error.startswith("Duplicate expense:"):
                    info_messages.append(f"Row {i}: {error}")
                elif (
                    "matches multiple existing restaurants" in error or "not found. Please provide an address" in error
                ):
                    # Restaurant ambiguity warnings should be treated as info messages
                    info_messages.append(f"Row {i}: {error}")
                else:
                    errors.append(f"Row {i}: {error}")
                continue

            if expense:
                db.session.add(expense)
                success_count += 1

        except Exception as e:
            errors.append(f"Row {i}: Unexpected error - {str(e)}")

    # Limit messages reported to avoid overwhelming output
    if len(errors) > 10:
        errors = errors[:10] + [f"... and {len(errors) - 10} more errors"]
    if len(info_messages) > 10:
        info_messages = info_messages[:10] + [f"... and {len(info_messages) - 10} more duplicates"]

    return success_count, errors, info_messages


def _count_warning_types(info_messages: List[str]) -> Tuple[int, int]:
    """Count different types of warning messages.

    Args:
        info_messages: List of informational messages

    Returns:
        Tuple of (duplicate_count, restaurant_warning_count)
    """
    duplicate_count = sum(1 for msg in info_messages if "Duplicate expense:" in msg)
    restaurant_warning_count = len(info_messages) - duplicate_count
    return duplicate_count, restaurant_warning_count


def _build_warning_message(info_messages: List[str]) -> str:
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


def _build_import_message(success_count: int, info_messages: List[str], errors: List[str]) -> str:
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


def _prepare_error_details(errors: List[str]) -> List[str]:
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
    success_count: int, errors: List[str], info_messages: List[str]
) -> Tuple[bool, Dict[str, Any]]:
    """Generate the result of the import operation.

    Args:
        success_count: Number of successfully imported expenses
        errors: List of error messages (actual problems)
        info_messages: List of informational messages (like duplicates)

    Returns:
        Tuple of (success, result_data)
    """
    if success_count > 0:
        db.session.commit()

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


def import_expenses_from_csv(file: FileStorage, user_id: int) -> Tuple[bool, Dict[str, Any]]:
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
def create_tag(user_id: int, name: str, color: str = "#6c757d", description: str = None) -> Tag:
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


def update_tag(user_id: int, tag_id: int, name: str, color: str = "#6c757d", description: str = None) -> Optional[Tag]:
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
    tag.updated_at = datetime.now(timezone.utc)

    db.session.commit()

    return tag


def get_user_tags(user_id: int) -> list[Tag]:
    """Get all tags for a user.

    Args:
        user_id: ID of the user

    Returns:
        List of Tag objects for the user
    """
    return Tag.query.filter_by(user_id=user_id).order_by(Tag.name).all()


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
    return Tag.query.filter(Tag.user_id == user_id, Tag.name.ilike(search_term)).limit(limit).all()


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

    return tag


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

    return expense.tags


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
    tag = db.session.get(Tag, tag_id)
    if not tag or tag.user_id != user_id:
        return False

    # Remove tag from all expenses
    ExpenseTag.query.filter_by(tag_id=tag_id).delete()

    # Delete the tag
    db.session.delete(tag)
    db.session.commit()

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
