"""Service functions for the expenses blueprint."""

from collections import defaultdict
import csv
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
import io
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from flask import Request, current_app, url_for
from flask_wtf import FlaskForm
from sqlalchemy import extract, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import Select
from werkzeug.datastructures import FileStorage

from app.constants.categories import get_default_categories
from app.expenses.forms import ExpenseForm
from app.expenses.models import Category, Expense, ExpenseTag, Tag
from app.extensions import db
from app.receipts.models import Receipt
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
        .options(
            joinedload(Expense.expense_tags).joinedload(ExpenseTag.tag),
            joinedload(Expense.receipt),
        )
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


def _get_expense_aggregates(user_id: int, filters: dict[str, Any]) -> tuple[float, float | None]:
    """Get total amount and average price per person over the filtered expense set.

    Args:
        user_id: The ID of the user
        filters: Dictionary of filter parameters (same as apply_filters)

    Returns:
        Tuple of (total_amount, avg_price_per_person)
    """
    stmt = select(Expense).where(Expense.user_id == user_id)
    stmt = apply_filters(stmt, filters)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_count = db.session.execute(count_stmt).scalar_one() or 0
    if total_count == 0:
        return 0.0, None

    sum_stmt = select(func.coalesce(func.sum(Expense.amount), 0)).where(Expense.user_id == user_id)
    sum_stmt = apply_filters(sum_stmt, filters)
    total_amount = float(db.session.execute(sum_stmt).scalar_one() or 0)

    # Avg price per person: average of (amount/party_size) for expenses with party_size > 0
    avg_stmt = (
        select(func.avg(Expense.amount / func.nullif(Expense.party_size, 0)))
        .where(Expense.user_id == user_id)
        .where(Expense.party_size.isnot(None))
        .where(Expense.party_size > 0)
    )
    avg_stmt = apply_filters(avg_stmt, filters)
    avg_result = db.session.execute(avg_stmt).scalar_one()
    avg_price_per_person = float(avg_result) if avg_result is not None else None
    return total_amount, avg_price_per_person


def get_user_expenses_paginated(
    user_id: int,
    filters: dict[str, Any],
    offset: int = 0,
    limit: int = 25,
) -> tuple[list[Expense], int, float, float | None]:
    """Get a page of expenses for a user with the given filters (SQL-level pagination).

    Args:
        user_id: The ID of the user
        filters: Dictionary of filter parameters
        offset: Number of rows to skip
        limit: Maximum number of rows to return

    Returns:
        Tuple of (expenses_page, total_count, total_amount, avg_price_per_person)
    """
    stmt = (
        select(Expense)
        .options(
            joinedload(Expense.expense_tags).joinedload(ExpenseTag.tag),
            joinedload(Expense.receipt),
        )
        .where(Expense.user_id == user_id)
    )
    stmt = apply_filters(stmt, filters)
    stmt = apply_sorting(stmt, filters["sort_by"], filters["sort_order"])

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_count = db.session.execute(count_stmt).scalar_one() or 0

    total_amount, avg_price_per_person = _get_expense_aggregates(user_id, filters)

    stmt = stmt.limit(limit).offset(offset)
    result = db.session.execute(stmt)
    expenses_page = list(result.scalars().unique().all())

    return expenses_page, total_count, total_amount, avg_price_per_person


# Maximum number of expenses to load for calendar JSON (avoids huge payloads)
CALENDAR_EXPENSES_LIMIT = 500


def get_calendar_expenses(
    user_id: int,
    filters: dict[str, Any],
    limit: int = CALENDAR_EXPENSES_LIMIT,
) -> list[Expense]:
    """Get a limited set of expenses for calendar view JSON (same filters, no full scan).

    Args:
        user_id: The ID of the user
        filters: Dictionary of filter parameters
        limit: Maximum number of expenses to return (default 500)

    Returns:
        List of Expense objects (most recent first by date)
    """
    stmt = select(Expense).options(joinedload(Expense.restaurant)).where(Expense.user_id == user_id)
    stmt = apply_filters(stmt, filters)
    # Calendar: sort by date desc so we get most recent
    stmt = apply_sorting(stmt, "date", "desc")
    stmt = stmt.limit(limit)
    result = db.session.execute(stmt)
    return list(result.scalars().unique().all())


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


def _normalize_receipt_storage_path(storage_path: str | None) -> str | None:
    """Normalize receipt storage references for reconciliation."""
    if not storage_path:
        return None
    normalized = storage_path.strip()
    return normalized or None


def _detect_receipt_storage_backend(storage_path: str) -> str:
    """Infer the storage backend for a receipt reference."""
    s3_prefix = current_app.config.get("S3_RECEIPTS_PREFIX", "receipts/")
    normalized_path = storage_path.lower()
    if normalized_path.startswith("s3://"):
        return "s3"
    if s3_prefix and storage_path.startswith(s3_prefix):
        return "s3"
    if normalized_path.startswith(("http://", "https://")):
        return "remote"
    return "local"


def _resolve_local_receipt_path(storage_path: str) -> Path | None:
    """Resolve a local receipt reference to a filesystem path."""
    upload_folder = current_app.config.get("UPLOAD_FOLDER")
    if not upload_folder:
        return None
    filename = Path(storage_path).name
    if not filename:
        return None
    return Path(upload_folder) / filename


def get_receipt_reconciliation(user_id: int) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Build a reconciliation view across receipt storage, receipt rows, and expenses."""
    expense_stmt = (
        select(Expense)
        .options(joinedload(Expense.restaurant))
        .where(Expense.user_id == user_id)
        .where(Expense.receipt_image.is_not(None))
        .order_by(Expense.date.desc(), Expense.id.desc())
    )
    receipt_stmt = (
        select(Receipt)
        .options(joinedload(Receipt.expense).joinedload(Expense.restaurant))
        .where(Receipt.user_id == user_id)
        .order_by(Receipt.created_at.desc(), Receipt.id.desc())
    )

    expense_refs = list(db.session.execute(expense_stmt).scalars().all())
    receipt_rows = list(db.session.execute(receipt_stmt).scalars().unique().all())

    grouped_refs: dict[str, dict[str, Any]] = defaultdict(lambda: {"expenses": [], "receipts": []})

    for expense in expense_refs:
        storage_path = _normalize_receipt_storage_path(expense.receipt_image)
        if storage_path:
            grouped_refs[storage_path]["expenses"].append(expense)

    for receipt in receipt_rows:
        storage_path = _normalize_receipt_storage_path(receipt.file_uri)
        if storage_path:
            grouped_refs[storage_path]["receipts"].append(receipt)

    summary = {
        "total_receipts": 0,
        "reconciled": 0,
        "missing_receipt_row": 0,
        "missing_expense": 0,
        "review_required": 0,
        "local_missing": 0,
        "s3_backed": 0,
        "local_backed": 0,
    }
    rows: list[dict[str, Any]] = []

    for storage_path, grouped in grouped_refs.items():
        storage_backend = _detect_receipt_storage_backend(storage_path)
        local_file_path = _resolve_local_receipt_path(storage_path) if storage_backend == "local" else None
        storage_exists = local_file_path.exists() if local_file_path else None

        expense_ids_from_image = {expense.id for expense in grouped["expenses"]}
        linked_expenses_by_id: dict[int, Expense] = {expense.id: expense for expense in grouped["expenses"]}
        receipt_rows_for_storage: list[Receipt] = grouped["receipts"]
        receipt_expense_ids: set[int] = set()
        linkage_mismatches: list[str] = []

        for receipt in receipt_rows_for_storage:
            linked_expense = receipt.expense
            if linked_expense is None:
                continue
            linked_expenses_by_id[linked_expense.id] = linked_expense
            receipt_expense_ids.add(linked_expense.id)

            linked_expense_path = _normalize_receipt_storage_path(linked_expense.receipt_image)
            if linked_expense_path and linked_expense_path != storage_path:
                linkage_mismatches.append(
                    f"Expense #{linked_expense.id} points to {linked_expense_path} instead of {storage_path}."
                )

        linked_expenses = sorted(
            linked_expenses_by_id.values(),
            key=lambda expense: (
                expense.date if expense.date is not None else datetime.min.replace(tzinfo=UTC),
                expense.id,
            ),
            reverse=True,
        )

        issues: list[str] = []
        if not receipt_rows_for_storage:
            issues.append("Missing receipt DB row")
        if not linked_expenses:
            issues.append("Missing linked expense")
        if any(receipt.expense_id is None for receipt in receipt_rows_for_storage):
            issues.append("Receipt row is not linked directly to an expense")
        if len(receipt_rows_for_storage) > 1:
            issues.append("Multiple receipt rows reference the same image")
        if len(linked_expenses) > 1:
            issues.append("Multiple expenses reference the same receipt image")
        if expense_ids_from_image and receipt_expense_ids and expense_ids_from_image != receipt_expense_ids:
            issues.append("Receipt row and expense image links do not match")
        issues.extend(linkage_mismatches)
        if storage_backend == "local" and storage_exists is False:
            issues.append("Local receipt file is missing from storage")

        if not receipt_rows_for_storage:
            status = "missing_receipt_row"
        elif not linked_expenses:
            status = "missing_expense"
        elif issues:
            status = "review_required"
        else:
            status = "reconciled"

        summary["total_receipts"] += 1
        summary[status] += 1
        if storage_backend == "local":
            summary["local_backed"] += 1
            if storage_exists is False:
                summary["local_missing"] += 1
        elif storage_backend == "s3":
            summary["s3_backed"] += 1

        last_updated_candidates = [
            timestamp
            for timestamp in [
                *[expense.updated_at or expense.created_at for expense in linked_expenses],
                *[receipt.updated_at or receipt.created_at for receipt in receipt_rows_for_storage],
            ]
            if timestamp is not None
        ]

        rows.append(
            {
                "storage_path": storage_path,
                "storage_backend": storage_backend,
                "storage_exists": storage_exists,
                "local_file_path": str(local_file_path) if local_file_path else None,
                "receipt_rows": receipt_rows_for_storage,
                "receipt_row_ids": [receipt.id for receipt in receipt_rows_for_storage],
                "linked_expenses": linked_expenses,
                "linked_expense_ids": [expense.id for expense in linked_expenses],
                "status": status,
                "issues": issues,
                "has_ocr_data": any(receipt.has_ocr_data for receipt in receipt_rows_for_storage),
                "last_updated_at": max(last_updated_candidates) if last_updated_candidates else None,
            }
        )

    status_rank = {
        "review_required": 0,
        "missing_receipt_row": 1,
        "missing_expense": 2,
        "reconciled": 3,
    }
    rows.sort(
        key=lambda row: (
            status_rank.get(row["status"], 99),
            row["last_updated_at"] if row["last_updated_at"] is not None else datetime.min.replace(tzinfo=UTC),
        )
    )

    return rows, summary


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
    form.restaurant_id.choices = [(None, "Select a restaurant")] + [(r.id, r.display_name) for r in restaurants]

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


def _process_optional_date(date_value: Any) -> tuple[date | None, str | None]:
    """Process an optional date from form data."""
    if not date_value:
        return None, None
    return _process_date(date_value)


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


def _infer_receipt_type(storage_path: str) -> str:
    """Infer receipt type from the storage path extension."""
    suffix = Path(storage_path).suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        return "paper"
    return "unknown"


def _get_receipt_record_for_expense(expense: Expense) -> Receipt | None:
    """Return the canonical receipt row for an expense if one exists."""
    receipt_obj = expense.receipt
    if receipt_obj is not None:
        return receipt_obj

    stmt = (
        select(Receipt)
        .where(Receipt.expense_id == expense.id)
        .where(Receipt.user_id == expense.user_id)
        .order_by(Receipt.id.asc())
    )
    return db.session.scalars(stmt).first()


def _upsert_receipt_record_for_expense(expense: Expense, storage_path: str) -> Receipt:
    """Create or update the structured receipt row for an expense."""
    receipt = _get_receipt_record_for_expense(expense)
    if receipt is None:
        receipt = Receipt(
            expense_id=expense.id,
            restaurant_id=expense.restaurant_id,
            visit_id=expense.visit_id,
            user_id=expense.user_id,
            file_uri=storage_path,
            receipt_type=_infer_receipt_type(storage_path),
        )
        db.session.add(receipt)
        db.session.flush()
    else:
        receipt.expense_id = expense.id
        receipt.restaurant_id = expense.restaurant_id
        receipt.visit_id = expense.visit_id
        receipt.user_id = expense.user_id
        receipt.file_uri = storage_path
        receipt.receipt_type = _infer_receipt_type(storage_path)

    # Transitional mirror until the legacy field is removed everywhere.
    expense.receipt = receipt
    expense.receipt_image = storage_path
    return receipt


def _delete_receipt_records_for_expense(expense: Expense) -> None:
    """Delete all structured receipt rows for an expense."""
    stmt = select(Receipt).where(Receipt.expense_id == expense.id).where(Receipt.user_id == expense.user_id)
    for receipt in db.session.execute(stmt).scalars().all():
        db.session.delete(receipt)


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

        category_id, restaurant_id, datetime_value, cleared_date, amount, tags = expense_data

        # Handle receipt upload if provided
        receipt_image_path: str | None = None
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
            cleared_date=cleared_date,
            notes=form.notes.data.strip() if form.notes.data else None,
            category_id=category_id,
            restaurant_id=restaurant_id,
            meal_type=form.meal_type.data or None,
            order_type=form.order_type.data or None,
            party_size=form.party_size.data,
            receipt_image=receipt_image_path,
        )

        db.session.add(expense)
        db.session.flush()

        if receipt_image_path:
            _upsert_receipt_record_for_expense(expense, receipt_image_path)

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
) -> tuple[int | None, int | None, datetime, date | None, Decimal, list[str]] | str:
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

    cleared_date, error = _process_optional_date(form.cleared_date.data)
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

    return category_id, restaurant_id, datetime_value, cleared_date, amount, tags


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
    elif delete_receipt and expense.receipt_storage_path:
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

        if storage_path is None:
            return "Receipt storage path is not set"
        _upsert_receipt_record_for_expense(expense, storage_path)
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

        storage_path = expense.receipt_storage_path
        if not storage_path:
            current_app.logger.info("No receipt to delete")
            return None

        upload_folder = current_app.config.get("UPLOAD_FOLDER")
        if not isinstance(upload_folder, str):
            return "UPLOAD_FOLDER configuration is not set"
        error = delete_receipt_from_storage(storage_path, upload_folder)

        if error:
            return error

        _delete_receipt_records_for_expense(expense)
        expense.receipt = None
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

        # Get browser timezone for proper time handling
        from app.utils.timezone_utils import get_browser_timezone, normalize_timezone

        browser_timezone_raw = get_browser_timezone() or "UTC"
        browser_timezone = normalize_timezone(browser_timezone_raw) or "UTC"
        # Process form data
        expense_data = _process_expense_form_data(form, browser_timezone)
        if isinstance(expense_data, str):  # Error message
            return None, expense_data

        category_id, restaurant_id, date_value, cleared_date, amount, tags = expense_data

        # Handle receipt upload/deletion
        receipt_error = _handle_receipt_update(expense, receipt_file, delete_receipt)
        if receipt_error:
            return None, receipt_error

        # Update expense fields
        expense.amount = Decimal(str(amount))
        # date_value from _combine_date_time_with_timezone is already timezone-aware (UTC)
        old_date = expense.date
        expense.date = date_value
        expense.cleared_date = cleared_date
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

        receipt_record = _get_receipt_record_for_expense(expense)
        if receipt_record is None and expense.receipt_image:
            receipt_record = _upsert_receipt_record_for_expense(expense, expense.receipt_image)
        if receipt_record is not None:
            receipt_record.restaurant_id = expense.restaurant_id
            receipt_record.visit_id = expense.visit_id

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
    _delete_receipt_records_for_expense(expense)
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
        Expense.query.options(
            joinedload(Expense.expense_tags).joinedload(ExpenseTag.tag),
            joinedload(Expense.receipt),
        )
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
    query = Expense.query.options(
        joinedload(Expense.expense_tags).joinedload(ExpenseTag.tag),
        joinedload(Expense.receipt),
    ).filter_by(user_id=user_id)

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
        cleared_date=data.get("cleared_date"),
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
    if "cleared_date" in data:
        expense.cleared_date = data["cleared_date"]
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
        return ", ".join(tag_names) if tag_names else ""

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
                "cleared_date": expense.cleared_date.isoformat() if isinstance(expense.cleared_date, date) else "",
                "time_utc": time_str,
                "datetime_utc": datetime_str,
                "amount": safe_float(expense.amount) if expense.amount is not None else "",
                "meal_type": expense.meal_type or "",
                "order_type": expense.order_type or "",
                "party_size": expense.party_size if expense.party_size is not None else "",
                "notes": expense.notes or "",
                "category_name": expense.category.name if expense.category else "",
                "restaurant_name": expense.restaurant.display_name if expense.restaurant else "",
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
        # Canonical field names (case-insensitive pass-through)
        "date": "date",
        "visit_date": "visit_date",
        "cleared_date": "cleared_date",
        "amount": "amount",
        "restaurant_name": "restaurant_name",
        "restaurant_address": "restaurant_address",
        "category_name": "category_name",
        "meal_type": "meal_type",
        "order_type": "order_type",
        "party_size": "party_size",
        "notes": "notes",
        "tags": "tags",
        "datetime_utc": "datetime_utc",
        "time_utc": "time_utc",
        "restaurant_city": "restaurant_city",
        "restaurant_state": "restaurant_state",
        "restaurant_postal_code": "restaurant_postal_code",
        "restaurant_country": "restaurant_country",
        "restaurant_google_place_id": "restaurant_google_place_id",
        # Date field mappings
        "postedon": "date",
        "posted_on": "date",
        "transaction_date": "date",
        "expense_date": "date",
        "visit date": "visit_date",
        "cleared date": "cleared_date",
        "when": "date",
        "datetime": "datetime_utc",
        "date_time": "datetime_utc",
        "timestamp": "datetime_utc",
        # Time field mappings
        "time": "time_utc",
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
        "city": "restaurant_city",
        "state": "restaurant_state",
        "postal_code": "restaurant_postal_code",
        "zip": "restaurant_postal_code",
        "zip_code": "restaurant_postal_code",
        "country": "restaurant_country",
        "google_place_id": "restaurant_google_place_id",
        # Meal type mappings
        "meal": "meal_type",
        "meal_category": "meal_type",
        # Order / party mappings
        "order": "order_type",
        "service_type": "order_type",
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

        parsed = [tag.strip() for tag in re.split(r"[;,]", tags_str) if tag.strip()]
        return parsed, None

    if isinstance(tags_value, list):
        return _validate_tags_list(tags_value)

    return None, "Tags must be a list or comma-separated string"


def _normalize_tag_name(tag_name: str) -> str:
    """Normalize tag name to match existing creation rules."""
    normalized_name = tag_name.strip().replace(" ", "-")
    normalized_name = "".join(c for c in normalized_name if c.isalnum() or c == "-")
    return normalized_name


def _detect_import_source_type(row: dict[str, Any]) -> str:
    """Infer the import source type from row headers."""
    normalized_keys = {str(key).strip().lower() for key in row.keys() if str(key).strip()}
    if "payee" in normalized_keys or "exclusion" in normalized_keys:
        return "simplifi"
    if (
        "visit_date" in normalized_keys
        or "cleared_date" in normalized_keys
        or "datetime_utc" in normalized_keys
        or "time_utc" in normalized_keys
    ):
        return "standard"
    return "standard"


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

    existing_linked_tag_ids = {
        expense_tag.tag_id
        for expense_tag in getattr(expense, "expense_tags", [])
        if getattr(expense_tag, "tag_id", None)
    }
    existing_linked_tag_names = {
        expense_tag.tag.name
        for expense_tag in getattr(expense, "expense_tags", [])
        if getattr(expense_tag, "tag", None) is not None and getattr(expense_tag.tag, "name", None)
    }

    for tag_name in normalized_tags:
        tag = existing_tags.get(tag_name)
        if not tag:
            tag = Tag(name=tag_name, color="#6c757d", user_id=user_id)
            db.session.add(tag)
            existing_tags[tag_name] = tag
            created_tags.add(tag_name)

        if (tag.id is not None and tag.id in existing_linked_tag_ids) or tag.name in existing_linked_tag_names:
            continue

        expense_tag = ExpenseTag(expense=expense, tag=tag, added_by=user_id)
        db.session.add(expense_tag)
        if tag.id is not None:
            existing_linked_tag_ids.add(tag.id)
        existing_linked_tag_names.add(tag.name)
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
        "%d-%b-%y",  # Simplifi style: 7-Mar-26
        "%d-%b-%Y",  # Simplifi style with 4-digit year
        "%b %d, %Y",  # Simplifi default: Jan 1, 2025
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
    - date only: interpreted as midnight UTC for storage; review UI can still show that no explicit time was provided
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

    # If no time is provided, store the date at midnight UTC.
    final_time = parsed_time if parsed_time is not None else time.min
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


def _normalize_import_category_name(category_name: str | None) -> str:
    """Normalize import category names for Simplifi-style hierarchical categories."""
    raw_name = str(category_name or "").strip()
    if not raw_name:
        return ""

    if ":" in raw_name:
        _left, right = raw_name.split(":", 1)
        normalized_right = right.strip()
        if normalized_right:
            return normalized_right

    return raw_name


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
    restaurants_by_google_place_id: dict[str, Restaurant]
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
) -> tuple[dict[str, list[Restaurant]], dict[tuple[str, str], Restaurant], dict[str, Restaurant]]:
    """Build restaurant caches for import processing (avoid per-row queries)."""
    restaurants = Restaurant.query.filter_by(user_id=user_id).all()
    restaurants_by_name: dict[str, list[Restaurant]] = {}
    restaurants_by_name_address: dict[tuple[str, str], Restaurant] = {}
    restaurants_by_google_place_id: dict[str, Restaurant] = {}

    for restaurant in restaurants:
        name = restaurant.name.strip() if restaurant.name else ""
        if not name:
            continue
        restaurants_by_name.setdefault(name, []).append(restaurant)

        address = restaurant.address_line_1.strip() if restaurant.address_line_1 else ""
        if address:
            restaurants_by_name_address[(name, address)] = restaurant

        place_id = (restaurant.google_place_id or "").strip()
        if place_id:
            restaurants_by_google_place_id[place_id] = restaurant

    return restaurants_by_name, restaurants_by_name_address, restaurants_by_google_place_id


def _find_existing_restaurant_for_import(
    restaurant_name: str,
    restaurant_address: str,
    ctx: ExpenseImportContext,
    restaurant_city: str | None = None,
    restaurant_google_place_id: str | None = None,
) -> Restaurant | None:
    """Find an existing restaurant for import duplicate prefetch (no creation, no warnings)."""
    name = restaurant_name.strip()
    if not name:
        return None

    place_id = (restaurant_google_place_id or "").strip()
    if place_id:
        existing = ctx.restaurants_by_google_place_id.get(place_id)
        if existing:
            return existing

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
    from app.merchants.services import find_merchant_for_restaurant_name

    def assign_merchant_if_missing(restaurant: Restaurant) -> None:
        if restaurant.merchant_id is not None:
            return
        matched_merchant = find_merchant_for_restaurant_name(restaurant.name or "")
        if matched_merchant:
            restaurant.merchant_id = matched_merchant.id

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

    place_id = str((restaurant_details or {}).get("restaurant_google_place_id") or "").strip() or None
    if place_id:
        existing_by_place_id = ctx.restaurants_by_google_place_id.get(place_id)
        if existing_by_place_id:
            merge_details(existing_by_place_id)
            assign_merchant_if_missing(existing_by_place_id)
            return existing_by_place_id, None

    address = restaurant_address.strip() if restaurant_address else ""
    if address:
        existing = ctx.restaurants_by_name_address.get((name, address))
        if existing:
            merge_details(existing)
            assign_merchant_if_missing(existing)
            return existing, None

        if place_id and place_id in ctx.restaurants_by_google_place_id:
            existing_by_place_id = ctx.restaurants_by_google_place_id[place_id]
            merge_details(existing_by_place_id)
            assign_merchant_if_missing(existing_by_place_id)
            ctx.restaurants_by_name.setdefault(name, []).append(existing_by_place_id)
            ctx.restaurants_by_name_address[(name, address)] = existing_by_place_id
            return existing_by_place_id, None

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
        assign_merchant_if_missing(new_restaurant)
        db.session.add(new_restaurant)
        ctx.restaurants_by_name.setdefault(name, []).append(new_restaurant)
        ctx.restaurants_by_name_address[(name, address)] = new_restaurant
        if place_id:
            ctx.restaurants_by_google_place_id[place_id] = new_restaurant
        return new_restaurant, None

    name_matches = ctx.restaurants_by_name.get(name, [])
    if len(name_matches) == 1:
        merge_details(name_matches[0])
        assign_merchant_if_missing(name_matches[0])
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

    if place_id and place_id in ctx.restaurants_by_google_place_id:
        existing_by_place_id = ctx.restaurants_by_google_place_id[place_id]
        merge_details(existing_by_place_id)
        assign_merchant_if_missing(existing_by_place_id)
        ctx.restaurants_by_name.setdefault(name, []).append(existing_by_place_id)
        return existing_by_place_id, None

    # No matches and no address: create a restaurant so CSV backups can be restored.
    new_restaurant = Restaurant(
        user_id=ctx.user_id,
        name=name,
        address_line_1=None,
        city=str((restaurant_details or {}).get("restaurant_city") or "").strip() or None,
        state=str((restaurant_details or {}).get("restaurant_state") or "").strip() or None,
        postal_code=str((restaurant_details or {}).get("restaurant_postal_code") or "").strip() or None,
        country=str((restaurant_details or {}).get("restaurant_country") or "").strip() or None,
        google_place_id=place_id,
    )
    assign_merchant_if_missing(new_restaurant)
    db.session.add(new_restaurant)
    ctx.restaurants_by_name.setdefault(name, []).append(new_restaurant)
    if place_id:
        ctx.restaurants_by_google_place_id[place_id] = new_restaurant
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
        restaurant_google_place_id = str(row.get("restaurant_google_place_id", "") or "").strip() or None
        if not restaurant_name:
            includes_null_restaurant = True
            continue

        existing_restaurant = _find_existing_restaurant_for_import(
            restaurant_name,
            restaurant_address,
            ctx,
            restaurant_city=restaurant_city,
            restaurant_google_place_id=restaurant_google_place_id,
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
    restaurants_by_name, restaurants_by_name_address, restaurants_by_google_place_id = (
        _build_restaurant_cache_for_import(user_id)
    )

    ctx = ExpenseImportContext(
        user_id=user_id,
        categories_by_name=categories_by_name,
        categories_by_lower_name=categories_by_lower_name,
        categories_all=categories_all,
        restaurants_by_name=restaurants_by_name,
        restaurants_by_name_address=restaurants_by_name_address,
        restaurants_by_google_place_id=restaurants_by_google_place_id,
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

    except IntegrityError as e:
        db.session.rollback()
        error_str = str(e.orig) if getattr(e, "orig", None) else str(e)
        if "restaurant" in error_str.lower() and "unique" in error_str.lower():
            error_msg = (
                "Import failed: a restaurant in the file already exists (same Google Place ID). "
                "The import now reuses existing restaurants by Place ID; if you still see this, "
                "please report the file format."
            )
        else:
            error_msg = f"Import failed due to a data conflict: {error_str}"
        return False, {"message": error_msg, "has_errors": True, "error_details": [error_msg]}
    except Exception as e:
        db.session.rollback()
        error_msg = f"Error processing file: {str(e)}"
        return False, {"message": error_msg, "has_errors": True, "error_details": [error_msg]}


def _normalize_import_match_text(value: str | None) -> str:
    """Normalize payee/restaurant text for import matching."""
    if value is None:
        return ""

    normalized = value.lower()
    normalized = normalized.replace("&", " and ")
    normalized = re.sub(r"\b(app|online|order|mobile)\b", " ", normalized)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _is_blank_import_row(row: dict[str, Any]) -> bool:
    """Return True when an import row has no meaningful values."""
    for value in row.values():
        if value is None:
            continue
        if str(value).strip():
            return False
    return True


def _build_import_name_variants(value: str | None) -> set[str]:
    """Build normalized name variants for payee/restaurant comparison."""
    raw_value = str(value or "").strip()
    if not raw_value:
        return set()

    variants: set[str] = set()
    normalized = _normalize_import_match_text(raw_value)
    if normalized:
        variants.add(normalized)

    for separator in [" - ", " – ", " — ", ":"]:
        if separator in raw_value:
            head = raw_value.split(separator, 1)[0].strip()
            head_normalized = _normalize_import_match_text(head)
            if head_normalized:
                variants.add(head_normalized)

    tokens = normalized.split()
    if tokens:
        variants.add(" ".join(token for token in tokens if token not in {"the"}).strip())

    return {variant for variant in variants if variant}


def _shared_prefix_word_count(left: str, right: str) -> int:
    """Return the count of shared leading words between two normalized strings."""
    left_parts = left.split()
    right_parts = right.split()
    count = 0
    for left_part, right_part in zip(left_parts, right_parts):
        if left_part != right_part:
            break
        count += 1
    return count


def _score_import_restaurant_match(payee_name: str, restaurant: Restaurant) -> int:
    """Score a restaurant candidate for an imported payee name."""
    payee_variants = _build_import_name_variants(payee_name)
    if not payee_variants:
        return 0

    restaurant_variants: set[str] = set()
    restaurant_variants.update(_build_import_name_variants(restaurant.name))
    restaurant_variants.update(_build_import_name_variants(restaurant.display_name))

    best_score = 0
    for payee_variant in payee_variants:
        for restaurant_variant in restaurant_variants:
            if payee_variant == restaurant_variant:
                best_score = max(best_score, 100)
            elif (
                payee_variant
                and restaurant_variant
                and (payee_variant in restaurant_variant or restaurant_variant in payee_variant)
            ):
                best_score = max(best_score, 80)
            else:
                shared_prefix = _shared_prefix_word_count(payee_variant, restaurant_variant)
                if shared_prefix >= 3:
                    best_score = max(best_score, 88)
                elif shared_prefix >= 2:
                    best_score = max(best_score, 84)
    return best_score


def _is_exact_import_display_name_match(payee_name: str, restaurant: Restaurant) -> bool:
    """Return True when the imported payee exactly matches the restaurant display name."""
    normalized_payee = _normalize_import_match_text(payee_name)
    normalized_display_name = _normalize_import_match_text(restaurant.display_name or "")
    return bool(normalized_payee and normalized_payee == normalized_display_name)


def _is_exact_import_address_match(imported_address: str, restaurant: Restaurant) -> bool:
    """Return True when the imported address exactly matches the restaurant address."""
    normalized_imported_address = _normalize_import_match_text(imported_address)
    restaurant_address_variants = {
        _normalize_import_match_text(restaurant.address or ""),
        _normalize_import_match_text(restaurant.full_address or ""),
    }
    return bool(
        normalized_imported_address
        and normalized_imported_address in {variant for variant in restaurant_address_variants if variant}
    )


def _serialize_restaurant_for_import_review(
    restaurant: Restaurant,
    score: int,
    match_basis: str,
    *,
    exact_display_name_match: bool = False,
    exact_address_match: bool = False,
) -> dict[str, Any]:
    """Serialize restaurant summary for import review UI."""
    return {
        "id": restaurant.id,
        "name": restaurant.name,
        "display_name": restaurant.display_name,
        "city": restaurant.city or "",
        "state": restaurant.state or "",
        "postal_code": restaurant.postal_code or "",
        "address": restaurant.address or "",
        "detail_url": url_for("restaurants.restaurant_details", restaurant_id=restaurant.id, _external=True),
        "match_score": score,
        "match_basis": match_basis,
        "exact_display_name_match": exact_display_name_match,
        "exact_address_match": exact_address_match,
    }


def _sort_restaurants_for_import_review(restaurants: list[Restaurant]) -> list[Restaurant]:
    """Return restaurants sorted alphabetically by display name for review UIs."""
    return sorted(
        restaurants,
        key=lambda restaurant: ((restaurant.display_name or restaurant.name or "").lower(), restaurant.id),
    )


def _serialize_duplicate_expense_for_import_review(expense: Expense) -> dict[str, Any]:
    """Serialize duplicate-candidate summary for import review UI."""
    return {
        "id": expense.id,
        "label": f"Expense #{expense.id}",
        "date": expense.date.date().isoformat() if expense.date else "",
        "visit_date": expense.date.date().isoformat() if expense.date else "",
        "cleared_date": expense.cleared_date.isoformat() if isinstance(expense.cleared_date, date) else "",
        "time_display": expense.date.strftime("%H:%M UTC") if expense.date else "",
        "datetime_display": expense.date.strftime("%Y-%m-%d %H:%M UTC") if expense.date else "",
        "amount": f"{expense.amount:.2f}" if expense.amount is not None else "",
        "restaurant_name": expense.restaurant.display_name if expense.restaurant else "",
        "restaurant_address": expense.restaurant.address if expense.restaurant else "",
        "category_name": expense.category.name if expense.category else "",
        "meal_type": expense.meal_type or "",
        "order_type": expense.order_type or "",
        "party_size": expense.party_size,
        "notes": expense.notes or "",
        "tags": [tag.name for tag in expense.tags],
        "detail_url": url_for("expenses.expense_details", expense_id=expense.id, _external=True),
    }


def _import_row_has_explicit_time(row: dict[str, Any]) -> bool:
    """Return True when the raw import row includes an explicit time component."""
    raw_datetime = str(row.get("datetime_utc") or "").strip()
    if raw_datetime:
        return "T" in raw_datetime or " " in raw_datetime

    raw_time = str(row.get("time_utc") or "").strip()
    return bool(raw_time)


def _format_import_review_value(value: Any, empty_label: str = "Not provided") -> str:
    """Format a comparison value for the import review UI."""
    if value is None:
        return empty_label

    if isinstance(value, Decimal):
        return f"${value:.2f}"

    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else empty_label

    text = str(value).strip()
    return text if text else empty_label


def _is_import_review_empty_value(value: Any) -> bool:
    """Return True when a comparison value should be treated as missing."""
    if value is None:
        return True
    if isinstance(value, list):
        return len(value) == 0
    if isinstance(value, str):
        return not value.strip() or value.strip() == "Not provided"
    return False


def _ensure_utc_datetime(value: datetime | None) -> datetime | None:
    """Return a timezone-aware UTC datetime."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _build_import_expense_datetime(
    parsed_date: date,
    parsed_datetime_utc: str,
    has_explicit_time: bool,
    existing_expense: Expense | None = None,
) -> datetime:
    """Build the stored expense datetime for an import review row."""
    if parsed_datetime_utc:
        parsed_datetime = datetime.fromisoformat(parsed_datetime_utc)
        if parsed_datetime.tzinfo is None:
            parsed_datetime = parsed_datetime.replace(tzinfo=UTC)
        if has_explicit_time:
            return parsed_datetime.astimezone(UTC).replace(microsecond=0)

    existing_expense_datetime = _ensure_utc_datetime(existing_expense.date if existing_expense else None)
    if existing_expense_datetime:
        return datetime.combine(parsed_date, existing_expense_datetime.time(), tzinfo=UTC).replace(microsecond=0)

    return datetime.combine(parsed_date, time.min, tzinfo=UTC).replace(microsecond=0)


def _parse_import_review_dates(
    row: dict[str, Any],
    import_source_type: str,
) -> tuple[datetime | None, date | None, date | None, str | None]:
    """Parse visit and cleared dates for an import review row."""
    parsed_visit_datetime_utc: datetime | None = None
    parsed_visit_date: date | None = None
    parsed_cleared_date: date | None = None

    visit_row = dict(row)
    explicit_visit_date = row.get("visit_date")
    if explicit_visit_date not in (None, ""):
        visit_row["date"] = explicit_visit_date

    if import_source_type == "standard":
        parsed_visit_datetime_utc, parsed_visit_date, date_error = _parse_expense_datetime_utc(visit_row)
        if date_error:
            return None, None, None, date_error
        raw_cleared_date = row.get("cleared_date")
        if raw_cleared_date not in (None, ""):
            parsed_cleared_date, cleared_error = _parse_expense_date(raw_cleared_date)
            if cleared_error:
                return None, None, None, cleared_error
        return parsed_visit_datetime_utc, parsed_visit_date, parsed_cleared_date, None

    raw_cleared_date = row.get("cleared_date", row.get("date"))
    parsed_cleared_date, cleared_error = _parse_expense_date(raw_cleared_date)
    if cleared_error:
        return None, None, None, cleared_error

    if explicit_visit_date not in (None, ""):
        parsed_visit_datetime_utc, parsed_visit_date, visit_error = _parse_expense_datetime_utc(visit_row)
        if visit_error:
            return None, None, None, visit_error

    return parsed_visit_datetime_utc, parsed_visit_date, parsed_cleared_date, None


def _build_cleared_date_warning(
    visit_date: date | None,
    cleared_date: date | None,
    label: str | None = None,
) -> str | None:
    """Return a warning when cleared date is more than three days after visit date."""
    if visit_date is None or cleared_date is None:
        return None
    delta_days = (cleared_date - visit_date).days
    if delta_days <= 3:
        return None

    prefix = f"{label}: " if label else ""
    return (
        f"{prefix}Cleared date {cleared_date.isoformat()} is {delta_days} days after "
        f"visit date {visit_date.isoformat()}."
    )


def _build_duplicate_expense_comparison(
    duplicate_expense: Expense,
    review_row: dict[str, Any],
    normalized_tags: list[str],
    matched_restaurant_name: str,
) -> dict[str, Any]:
    """Build a field-by-field comparison between an existing expense and the imported row."""
    import_source_type = str(review_row.get("import_source_type") or "standard")
    parsed_visit_date_raw = str(review_row.get("parsed_visit_date") or "").strip()
    parsed_cleared_date_raw = str(review_row.get("parsed_cleared_date") or "").strip()
    parsed_datetime_raw = str(review_row.get("parsed_visit_datetime_utc") or "").strip()
    has_explicit_time = bool(review_row.get("has_explicit_time"))
    imported_visit_date = date.fromisoformat(parsed_visit_date_raw) if parsed_visit_date_raw else None
    imported_cleared_date = date.fromisoformat(parsed_cleared_date_raw) if parsed_cleared_date_raw else None
    imported_datetime = (
        _build_import_expense_datetime(imported_visit_date, parsed_datetime_raw, has_explicit_time, duplicate_expense)
        if imported_visit_date
        else None
    )
    imported_amount = Decimal(str(review_row.get("amount") or "0"))
    imported_category_name = str(review_row.get("category_name") or "").strip()
    imported_meal_type = str(review_row.get("meal_type") or "").strip()
    imported_order_type = str(review_row.get("order_type") or "").strip()
    imported_party_size_raw = str(review_row.get("party_size") or "").strip()
    imported_party_size = int(imported_party_size_raw) if imported_party_size_raw.isdigit() else None
    imported_notes = str(review_row.get("notes") or "").strip()
    existing_tags = [tag.name for tag in duplicate_expense.tags]

    duplicate_datetime = _ensure_utc_datetime(duplicate_expense.date)
    current_restaurant_name = duplicate_expense.restaurant.display_name if duplicate_expense.restaurant else ""
    current_category_name = duplicate_expense.category.name if duplicate_expense.category else ""
    current_time_display = duplicate_datetime.strftime("%H:%M UTC") if duplicate_datetime else ""
    imported_time_display = (
        imported_datetime.astimezone(UTC).strftime("%H:%M UTC")
        if has_explicit_time and imported_datetime is not None
        else ""
    )
    field_specs = [
        (
            "Visit Date",
            duplicate_datetime.date().isoformat() if duplicate_datetime else "",
            imported_visit_date.isoformat() if imported_visit_date else "",
        ),
        ("Time", current_time_display, imported_time_display),
        (
            "Cleared Date",
            duplicate_expense.cleared_date.isoformat() if isinstance(duplicate_expense.cleared_date, date) else "",
            imported_cleared_date.isoformat() if imported_cleared_date else "",
        ),
        ("Amount", _format_import_review_value(duplicate_expense.amount), _format_import_review_value(imported_amount)),
        (
            "Restaurant",
            _format_import_review_value(current_restaurant_name),
            _format_import_review_value(matched_restaurant_name),
        ),
        (
            "Expense category",
            _format_import_review_value(current_category_name),
            _format_import_review_value(imported_category_name),
        ),
        (
            "Meal type",
            _format_import_review_value(duplicate_expense.meal_type),
            _format_import_review_value(imported_meal_type),
        ),
        (
            "Order type",
            _format_import_review_value(duplicate_expense.order_type),
            _format_import_review_value(imported_order_type),
        ),
        (
            "Party size",
            _format_import_review_value(duplicate_expense.party_size),
            _format_import_review_value(imported_party_size),
        ),
        ("Notes", _format_import_review_value(duplicate_expense.notes), _format_import_review_value(imported_notes)),
        ("Tags", _format_import_review_value(existing_tags), _format_import_review_value(normalized_tags)),
    ]

    changes: list[dict[str, str]] = []
    field_comparisons: list[dict[str, str]] = []
    for field_label, current_value, new_value in field_specs:
        if field_label == "Time" and not has_explicit_time:
            status = "unchanged"
        elif field_label == "Visit Date" and import_source_type == "simplifi" and not imported_visit_date:
            status = "unchanged"
        elif current_value == new_value:
            status = "match"
        elif _is_import_review_empty_value(current_value) and not _is_import_review_empty_value(new_value):
            status = "add"
        elif _is_import_review_empty_value(new_value):
            status = "unchanged"
        else:
            status = "update"

        field_comparisons.append(
            {
                "field": field_label,
                "current": current_value,
                "new": new_value,
                "status": status,
            }
        )
        if status in {"add", "update"}:
            changes.append({"field": field_label, "current": current_value, "new": new_value})

    return {
        "change_count": len(changes),
        "changes": changes,
        "fields": field_comparisons,
        "summary": (
            "No fields would change."
            if not changes
            else "Update this expense with " + ", ".join(change["field"].lower() for change in changes) + "."
        ),
    }


def _replace_import_tags_on_expense(
    expense: Expense,
    user_id: int,
    normalized_tags: list[str],
    existing_tags: dict[str, Tag],
    created_tags: set[str],
    tag_counts: dict[str, int],
) -> None:
    """Replace an expense's tags during import review without committing."""
    expense.expense_tags.clear()
    db.session.flush()
    _apply_import_tags_to_expense(expense, user_id, normalized_tags, existing_tags, created_tags, tag_counts)


def _find_restaurant_candidates_for_import_review(
    payee_name: str,
    restaurant_address: str,
    restaurants: list[Restaurant],
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Find likely restaurant matches for a payee name."""
    normalized_address = _normalize_import_match_text(restaurant_address)

    if not normalized_address:
        matches_without_address: list[tuple[int, str, Restaurant]] = []
        for restaurant in restaurants:
            exact_display_name_match = _is_exact_import_display_name_match(payee_name, restaurant)
            if exact_display_name_match:
                matches_without_address.append((130, "exact display name", restaurant))
                continue

            score = _score_import_restaurant_match(payee_name, restaurant)
            if score <= 0:
                continue

            match_basis = "partial name"
            if score >= 100:
                match_basis = "exact name"
            elif score >= 84:
                match_basis = "shared prefix"
            matches_without_address.append((score, match_basis, restaurant))

        matches_without_address.sort(key=lambda item: (-item[0], item[2].display_name.lower(), item[2].id))
        return [
            _serialize_restaurant_for_import_review(
                restaurant,
                score,
                match_basis,
                exact_display_name_match=match_basis == "exact display name",
            )
            for score, match_basis, restaurant in matches_without_address[:limit]
        ]

    scored_matches: list[tuple[int, str, Restaurant]] = []
    for restaurant in restaurants:
        exact_display_name_match = _is_exact_import_display_name_match(payee_name, restaurant)
        exact_address_match = _is_exact_import_address_match(restaurant_address, restaurant)
        score = _score_import_restaurant_match(payee_name, restaurant)
        match_basis = "name"

        restaurant_address_variants = [
            _normalize_import_match_text(restaurant.address or ""),
            _normalize_import_match_text(restaurant.full_address or ""),
        ]
        if exact_display_name_match and exact_address_match:
            score = max(score, 160)
            match_basis = "exact display name + address"
        elif exact_display_name_match:
            score = max(score, 130)
            match_basis = "exact display name"
        elif exact_address_match:
            score = max(score, 120)
            match_basis = "exact address"
        elif any(
            restaurant_address_text
            and (normalized_address in restaurant_address_text or restaurant_address_text in normalized_address)
            for restaurant_address_text in restaurant_address_variants
        ):
            score = max(score, 95)
            match_basis = "address"
        if score > 0:
            scored_matches.append((score, match_basis, restaurant))

    scored_matches.sort(key=lambda item: (-item[0], item[2].display_name.lower(), item[2].id))
    return [
        _serialize_restaurant_for_import_review(
            restaurant,
            score,
            match_basis,
            exact_display_name_match=_is_exact_import_display_name_match(payee_name, restaurant),
            exact_address_match=_is_exact_import_address_match(restaurant_address, restaurant),
        )
        for score, match_basis, restaurant in scored_matches[:limit]
    ]


def _find_duplicate_candidates_for_import_review(
    user_id: int,
    restaurant_id: int,
    amount: Decimal,
    expense_date: date,
    window_days: int = 3,
) -> list[Expense]:
    """Find likely duplicate expenses for an import review row after restaurant matching."""
    start_dt = datetime.combine(expense_date - timedelta(days=window_days), time.min, tzinfo=UTC)
    end_dt = datetime.combine(expense_date + timedelta(days=window_days + 1), time.min, tzinfo=UTC)

    stmt = (
        select(Expense)
        .options(joinedload(Expense.restaurant), joinedload(Expense.category))
        .where(Expense.user_id == user_id)
        .where(Expense.restaurant_id == restaurant_id)
        .where(Expense.amount == abs(amount))
        .where(Expense.date >= start_dt)
        .where(Expense.date < end_dt)
        .order_by(Expense.date.desc())
    )
    return list(db.session.scalars(stmt).all())


def _find_duplicate_candidates_for_import_review_any_restaurant(
    user_id: int,
    amount: Decimal,
    expense_date: date,
    window_days: int = 3,
) -> list[Expense]:
    """Find likely duplicate expenses for an import review row regardless of restaurant."""
    start_dt = datetime.combine(expense_date - timedelta(days=window_days), time.min, tzinfo=UTC)
    end_dt = datetime.combine(expense_date + timedelta(days=window_days + 1), time.min, tzinfo=UTC)

    stmt = (
        select(Expense)
        .options(joinedload(Expense.restaurant), joinedload(Expense.category))
        .where(Expense.user_id == user_id)
        .where(Expense.amount == abs(amount))
        .where(Expense.date >= start_dt)
        .where(Expense.date < end_dt)
        .order_by(Expense.date.desc(), Expense.id.desc())
    )
    return list(db.session.scalars(stmt).all())


def _serialize_duplicate_candidates_by_restaurant(
    user_id: int,
    restaurant_candidates: list[dict[str, Any]],
    amount: Decimal | None,
    duplicate_match_date: date | None,
    import_source_type: str,
    parsed_visit_date: date | None,
    parsed_cleared_date: date | None,
    parsed_visit_dt_utc: datetime | None,
    has_explicit_time: bool,
    category_name: str,
    meal_type: str,
    order_type: str,
    party_size: str,
    notes: str,
    normalized_tag_names: list[str],
) -> dict[str, list[dict[str, Any]]]:
    """Build duplicate-candidate payloads keyed by candidate restaurant id."""
    if amount is None or duplicate_match_date is None:
        return {}

    duplicates_by_restaurant: dict[str, list[dict[str, Any]]] = {}
    for candidate in restaurant_candidates:
        candidate_id = candidate.get("id")
        if candidate_id is None:
            continue

        duplicate_candidates = _find_duplicate_candidates_for_import_review(
            user_id=user_id,
            restaurant_id=int(candidate_id),
            amount=amount,
            expense_date=duplicate_match_date,
        )
        serialized_candidates: list[dict[str, Any]] = []
        for expense in duplicate_candidates:
            serialized_expense = _serialize_duplicate_expense_for_import_review(expense)
            serialized_expense["comparison"] = _build_duplicate_expense_comparison(
                expense,
                {
                    "import_source_type": import_source_type,
                    "parsed_visit_date": parsed_visit_date.isoformat() if parsed_visit_date else "",
                    "parsed_cleared_date": parsed_cleared_date.isoformat() if parsed_cleared_date else "",
                    "parsed_visit_datetime_utc": parsed_visit_dt_utc.isoformat() if parsed_visit_dt_utc else "",
                    "has_explicit_time": has_explicit_time,
                    "amount": f"{abs(amount):.2f}",
                    "category_name": category_name,
                    "meal_type": meal_type,
                    "order_type": order_type,
                    "party_size": party_size,
                    "notes": notes,
                },
                normalized_tag_names,
                str(candidate.get("display_name") or ""),
            )
            serialized_candidates.append(serialized_expense)
        duplicates_by_restaurant[str(candidate_id)] = serialized_candidates

    return duplicates_by_restaurant


def _serialize_all_duplicate_candidates_for_import_review(
    user_id: int,
    amount: Decimal | None,
    duplicate_match_date: date | None,
    import_source_type: str,
    parsed_visit_date: date | None,
    parsed_cleared_date: date | None,
    parsed_visit_dt_utc: datetime | None,
    has_explicit_time: bool,
    category_name: str,
    meal_type: str,
    order_type: str,
    party_size: str,
    notes: str,
    normalized_tag_names: list[str],
) -> list[dict[str, Any]]:
    """Build duplicate-candidate payloads without constraining restaurant identity."""
    if amount is None or duplicate_match_date is None:
        return []

    serialized_candidates: list[dict[str, Any]] = []
    for expense in _find_duplicate_candidates_for_import_review_any_restaurant(user_id, amount, duplicate_match_date):
        matched_restaurant_name = expense.restaurant.display_name if expense.restaurant else ""
        serialized_expense = _serialize_duplicate_expense_for_import_review(expense)
        serialized_expense["comparison"] = _build_duplicate_expense_comparison(
            expense,
            {
                "import_source_type": import_source_type,
                "parsed_visit_date": parsed_visit_date.isoformat() if parsed_visit_date else "",
                "parsed_cleared_date": parsed_cleared_date.isoformat() if parsed_cleared_date else "",
                "parsed_visit_datetime_utc": parsed_visit_dt_utc.isoformat() if parsed_visit_dt_utc else "",
                "has_explicit_time": has_explicit_time,
                "amount": f"{abs(amount):.2f}",
                "category_name": category_name,
                "meal_type": meal_type,
                "order_type": order_type,
                "party_size": party_size,
                "notes": notes,
            },
            normalized_tag_names,
            matched_restaurant_name,
        )
        serialized_candidates.append(serialized_expense)
    return serialized_candidates


def _recommend_expense_action_for_duplicates(duplicate_candidates: list[dict[str, Any]]) -> str:
    """Return the recommended expense action after restaurant selection."""
    if not duplicate_candidates:
        return "create"

    has_recommended_update = any(
        int(candidate.get("comparison", {}).get("change_count", 0) or 0) > 0 for candidate in duplicate_candidates
    )
    return "update" if has_recommended_update else "skip"


def build_expense_import_review(file: FileStorage, user_id: int) -> tuple[bool, dict[str, Any]]:
    """Parse an import file into row-by-row review data."""
    if not _validate_import_file(file):
        error_msg = "Invalid file type. Please upload a CSV or JSON file."
        return False, {"message": error_msg, "errors": [error_msg]}

    data, parse_error = _parse_import_file(file)
    if data is None:
        error_msg = parse_error or "Error parsing file. Please check the file format."
        return False, {"message": error_msg, "errors": [error_msg]}

    restaurants = _sort_restaurants_for_import_review(Restaurant.query.filter_by(user_id=user_id).all())
    existing_tag_names = {tag.name for tag in Tag.query.filter_by(user_id=user_id).all()}
    review_rows: list[dict[str, Any]] = []
    importable_count = 0
    duplicate_row_count = 0

    for row_number, row in enumerate(data, 1):
        if _is_blank_import_row(row):
            continue

        payee_name = str(row.get("restaurant_name") or "").strip()
        restaurant_address = str(row.get("restaurant_address") or "").strip()
        restaurant_city = str(row.get("restaurant_city") or "").strip()
        restaurant_state = str(row.get("restaurant_state") or "").strip()
        restaurant_postal_code = str(row.get("restaurant_postal_code") or "").strip()
        category_name = _normalize_import_category_name(row.get("category_name"))
        notes = str(row.get("notes") or "").strip()
        tags_value = str(row.get("tags") or "").strip()
        meal_type = str(row.get("meal_type") or "").strip()
        order_type = str(row.get("order_type") or "").strip()
        party_size = str(row.get("party_size") or "").strip()

        row_errors: list[str] = []
        row_warnings: list[str] = []
        import_source_type = _detect_import_source_type(row)
        parsed_visit_dt_utc, parsed_visit_date, parsed_cleared_date, date_error = _parse_import_review_dates(
            row, import_source_type
        )
        has_explicit_time = import_source_type == "standard" and _import_row_has_explicit_time(row)
        if date_error:
            row_errors.append(date_error)

        amount, amount_error = _parse_expense_amount(str(row.get("amount", "")).strip())
        if amount_error:
            row_errors.append(amount_error)

        tag_names, tag_error = _parse_import_tags(row.get("tags"))
        if tag_error:
            row_errors.append(tag_error)
            tag_names = []

        if not payee_name:
            row_errors.append("Restaurant / payee is required for import review.")

        restaurant_candidates = (
            _find_restaurant_candidates_for_import_review(payee_name, restaurant_address, restaurants)
            if payee_name
            else []
        )
        exact_display_name_candidates = [
            candidate for candidate in restaurant_candidates if candidate.get("exact_display_name_match")
        ]
        if len(exact_display_name_candidates) == 1:
            suggested_restaurant_id = exact_display_name_candidates[0]["id"]
        elif len(restaurant_candidates) == 1:
            suggested_restaurant_id = restaurant_candidates[0]["id"]
        else:
            suggested_restaurant_id = None
        requires_restaurant_confirmation = len(restaurant_candidates) > 1 and suggested_restaurant_id is None

        duplicate_match_date = parsed_visit_date if import_source_type == "standard" else parsed_cleared_date
        normalized_tag_names = _normalize_import_tag_names(tag_names or [])
        duplicate_candidates_by_restaurant = _serialize_duplicate_candidates_by_restaurant(
            user_id=user_id,
            restaurant_candidates=restaurant_candidates,
            amount=amount,
            duplicate_match_date=duplicate_match_date,
            import_source_type=import_source_type,
            parsed_visit_date=parsed_visit_date,
            parsed_cleared_date=parsed_cleared_date,
            parsed_visit_dt_utc=parsed_visit_dt_utc,
            has_explicit_time=has_explicit_time,
            category_name=category_name,
            meal_type=meal_type,
            order_type=order_type,
            party_size=party_size,
            notes=notes,
            normalized_tag_names=normalized_tag_names,
        )
        all_duplicate_candidates = _serialize_all_duplicate_candidates_for_import_review(
            user_id=user_id,
            amount=amount,
            duplicate_match_date=duplicate_match_date,
            import_source_type=import_source_type,
            parsed_visit_date=parsed_visit_date,
            parsed_cleared_date=parsed_cleared_date,
            parsed_visit_dt_utc=parsed_visit_dt_utc,
            has_explicit_time=has_explicit_time,
            category_name=category_name,
            meal_type=meal_type,
            order_type=order_type,
            party_size=party_size,
            notes=notes,
            normalized_tag_names=normalized_tag_names,
        )
        duplicate_candidates = (
            duplicate_candidates_by_restaurant.get(str(suggested_restaurant_id), []) if suggested_restaurant_id else []
        )
        warning_candidates: list[dict[str, Any]] = list(duplicate_candidates)

        if (
            import_source_type == "simplifi"
            and parsed_cleared_date is not None
            and amount is not None
            and suggested_restaurant_id is not None
        ):
            extended_warning_candidates = _find_duplicate_candidates_for_import_review(
                user_id=user_id,
                restaurant_id=int(suggested_restaurant_id),
                amount=amount,
                expense_date=parsed_cleared_date,
                window_days=14,
            )
            seen_warning_ids = {
                candidate_id
                for candidate in warning_candidates
                for candidate_id in [candidate.get("id")]
                if isinstance(candidate_id, int)
            }
            for candidate in extended_warning_candidates:
                if candidate.id in seen_warning_ids:
                    continue
                warning_candidates.append(_serialize_duplicate_expense_for_import_review(candidate))
                seen_warning_ids.add(candidate.id)

        direct_warning = _build_cleared_date_warning(parsed_visit_date, parsed_cleared_date)
        if direct_warning:
            row_warnings.append(direct_warning)

        if parsed_cleared_date is not None:
            for expense in warning_candidates:
                candidate_visit_date_raw = str(expense.get("visit_date") or expense.get("date") or "").strip()
                candidate_visit_date = (
                    date.fromisoformat(candidate_visit_date_raw) if candidate_visit_date_raw else None
                )
                candidate_warning = _build_cleared_date_warning(
                    candidate_visit_date,
                    parsed_cleared_date,
                    f"Expense #{expense.get('id')}",
                )
                if candidate_warning:
                    row_warnings.append(candidate_warning)

        if any(duplicate_candidates_by_restaurant.values()):
            duplicate_row_count += 1

        default_decision = "skip"
        if not row_errors:
            if requires_restaurant_confirmation:
                default_decision = "skip"
            elif duplicate_candidates:
                default_decision = "skip"
            elif suggested_restaurant_id is not None:
                default_decision = "match"

        restaurant_default_action = "match"
        expense_default_action = "skip"
        if not row_errors:
            if suggested_restaurant_id is not None:
                restaurant_default_action = "match"
            elif requires_restaurant_confirmation:
                restaurant_default_action = "match"
            if suggested_restaurant_id is not None:
                expense_default_action = _recommend_expense_action_for_duplicates(duplicate_candidates)
            elif requires_restaurant_confirmation:
                expense_default_action = "skip"

        if not row_errors and suggested_restaurant_id is not None:
            importable_count += 1

        existing_review_tags = [tag_name for tag_name in normalized_tag_names if tag_name in existing_tag_names]
        new_review_tags = [tag_name for tag_name in normalized_tag_names if tag_name not in existing_tag_names]

        review_rows.append(
            {
                "row_number": row_number,
                "import_source_type": import_source_type,
                "source": {
                    "date": str(row.get("date") or ""),
                    "visit_date": str(row.get("visit_date") or ""),
                    "cleared_date": str(row.get("cleared_date") or ""),
                    "amount": str(row.get("amount") or ""),
                    "restaurant_name": payee_name,
                    "restaurant_address": restaurant_address,
                    "restaurant_city": restaurant_city,
                    "restaurant_state": restaurant_state,
                    "restaurant_postal_code": restaurant_postal_code,
                    "category_name": category_name,
                    "meal_type": meal_type,
                    "order_type": order_type,
                    "party_size": party_size,
                    "notes": notes,
                    "tags": tags_value,
                },
                "parsed_date": (
                    parsed_primary_date.isoformat()
                    if (parsed_primary_date := (parsed_visit_date or parsed_cleared_date)) is not None
                    else ""
                ),
                "parsed_visit_date": parsed_visit_date.isoformat() if parsed_visit_date else "",
                "parsed_cleared_date": parsed_cleared_date.isoformat() if parsed_cleared_date else "",
                "parsed_datetime_utc": parsed_visit_dt_utc.isoformat() if parsed_visit_dt_utc else "",
                "parsed_visit_datetime_utc": parsed_visit_dt_utc.isoformat() if parsed_visit_dt_utc else "",
                "parsed_time_display": (
                    parsed_visit_dt_utc.strftime("%H:%M UTC") if parsed_visit_dt_utc and has_explicit_time else ""
                ),
                "parsed_datetime_display": (
                    parsed_visit_dt_utc.strftime("%Y-%m-%d %H:%M UTC")
                    if parsed_visit_dt_utc and has_explicit_time
                    else ""
                ),
                "has_explicit_time": has_explicit_time,
                "amount": f"{abs(amount):.2f}" if amount is not None else "",
                "restaurant_address": restaurant_address,
                "restaurant_city": restaurant_city,
                "restaurant_state": restaurant_state,
                "restaurant_postal_code": restaurant_postal_code,
                "category_name": category_name,
                "meal_type": meal_type,
                "order_type": order_type,
                "party_size": party_size,
                "notes": notes,
                "tags": ", ".join(tag_names or []),
                "tag_count": len(normalized_tag_names),
                "tag_existing_count": len(existing_review_tags),
                "tag_new_count": len(new_review_tags),
                "tag_existing_names": existing_review_tags,
                "tag_new_names": new_review_tags,
                "restaurant_name": payee_name,
                "restaurant_candidates": [restaurant for restaurant in restaurant_candidates],
                "suggested_restaurant_id": suggested_restaurant_id,
                "duplicate_candidates": duplicate_candidates,
                "duplicate_candidates_by_restaurant": duplicate_candidates_by_restaurant,
                "all_duplicate_candidates": all_duplicate_candidates,
                "error_messages": row_errors,
                "warning_messages": row_warnings,
                "default_decision": default_decision,
                "restaurant_default_action": restaurant_default_action,
                "expense_default_action": expense_default_action,
                "can_create_restaurant": bool(payee_name),
                "restaurant_requires_confirmation": requires_restaurant_confirmation,
            }
        )

    return True, {
        "review_rows": review_rows,
        "total_rows": len(review_rows),
        "importable_rows": importable_count,
        "duplicate_rows": duplicate_row_count,
    }


def apply_expense_import_review(
    review_rows: list[dict[str, Any]], form_data: dict[str, Any], user_id: int
) -> dict[str, Any]:
    """Apply row-by-row decisions from an import review draft."""
    imported_count = 0
    updated_count = 0
    skipped_count = 0
    error_messages: list[str] = []
    restaurants_by_id = {restaurant.id: restaurant for restaurant in Restaurant.query.filter_by(user_id=user_id).all()}

    existing_tags = {tag.name: tag for tag in Tag.query.filter_by(user_id=user_id).all()}
    created_tags: set[str] = set()
    tag_counts: dict[str, int] = {}
    has_apply_row_controls = any(str(key).startswith("apply_row_") for key in form_data)

    for review_row in review_rows:
        row_number = int(review_row["row_number"])
        if has_apply_row_controls and form_data.get(f"apply_row_{row_number}") != "1":
            skipped_count += 1
            continue

        restaurant_action = str(
            form_data.get(
                f"restaurant_action_{row_number}",
                review_row.get("restaurant_default_action", "skip"),
            )
            or "skip"
        )
        expense_action = str(
            form_data.get(
                f"expense_action_{row_number}",
                review_row.get("expense_default_action", "skip"),
            )
            or "skip"
        )
        decision = str(form_data.get(f"decision_{row_number}", review_row.get("default_decision", "skip")) or "skip")

        if f"restaurant_action_{row_number}" not in form_data and f"expense_action_{row_number}" not in form_data:
            if decision == "skip":
                restaurant_action = "skip"
                expense_action = "skip"
            elif decision == "update":
                restaurant_action = "match"
                expense_action = "update"
            elif decision == "match":
                restaurant_action = "match"
                expense_action = "create"
            elif decision == "create":
                restaurant_action = "match"
                expense_action = "create"

        if expense_action == "skip":
            skipped_count += 1
            continue

        if review_row.get("error_messages"):
            error_messages.append(f"Row {row_number}: Cannot import until parsing errors are resolved.")
            continue

        import_source_type = str(review_row.get("import_source_type") or "standard")
        parsed_visit_date_raw = str(review_row.get("parsed_visit_date") or "").strip()
        parsed_cleared_date_raw = str(review_row.get("parsed_cleared_date") or "").strip()
        parsed_datetime_raw = str(
            review_row.get("parsed_visit_datetime_utc") or review_row.get("parsed_datetime_utc") or ""
        ).strip()
        amount_raw = str(review_row.get("amount") or "").strip()
        if (not parsed_visit_date_raw and not parsed_cleared_date_raw) or not amount_raw:
            error_messages.append(f"Row {row_number}: Missing parsed date or amount.")
            continue

        parsed_visit_date = date.fromisoformat(parsed_visit_date_raw) if parsed_visit_date_raw else None
        parsed_cleared_date = date.fromisoformat(parsed_cleared_date_raw) if parsed_cleared_date_raw else None
        amount = Decimal(amount_raw)
        has_explicit_time = bool(review_row.get("has_explicit_time"))

        if restaurant_action == "skip":
            error_messages.append(
                f"Row {row_number}: Reconcile the restaurant before importing or updating the expense."
            )
            continue

        restaurant: Restaurant | None = None
        update_expense: Expense | None = None
        pending_restaurant_id_raw = str(form_data.get(f"restaurant_id_{row_number}", "") or "").strip()
        if restaurant_action != "match":
            error_messages.append(f"Row {row_number}: Select a matched restaurant before applying changes.")
            continue
        if pending_restaurant_id_raw.isdigit():
            restaurant = restaurants_by_id.get(int(pending_restaurant_id_raw))
            if restaurant is None:
                error_messages.append(f"Row {row_number}: Selected restaurant was not found.")
                continue
        else:
            error_messages.append(f"Row {row_number}: Select a restaurant match before applying expense changes.")
            continue

        if expense_action == "update":
            update_expense_id_raw = str(form_data.get(f"update_expense_id_{row_number}", "") or "").strip()
            if not update_expense_id_raw.isdigit():
                error_messages.append(f"Row {row_number}: Select an existing expense to update.")
                continue

            duplicate_match_date = parsed_visit_date if import_source_type == "standard" else parsed_cleared_date
            if duplicate_match_date is None or restaurant.id is None:
                error_messages.append(f"Row {row_number}: Unable to validate duplicate expense candidates.")
                continue
            allowed_expense_ids = {
                expense.id
                for expense in _find_duplicate_candidates_for_import_review(
                    user_id=user_id,
                    restaurant_id=restaurant.id,
                    amount=amount,
                    expense_date=duplicate_match_date,
                )
            }
            update_expense_id = int(update_expense_id_raw)
            if update_expense_id not in allowed_expense_ids:
                error_messages.append(f"Row {row_number}: Selected expense is not a valid update target for this row.")
                continue

            update_expense = (
                Expense.query.options(
                    joinedload(Expense.restaurant),
                    joinedload(Expense.category),
                    joinedload(Expense.expense_tags).joinedload(ExpenseTag.tag),
                )
                .filter_by(id=update_expense_id, user_id=user_id)
                .first()
            )
            if update_expense is None:
                error_messages.append(f"Row {row_number}: Selected expense was not found.")
                continue
            if restaurant is None:
                restaurant = update_expense.restaurant
        elif restaurant is None:
            error_messages.append(f"Row {row_number}: Select a restaurant match before importing the expense.")
            continue
        elif expense_action != "create":
            error_messages.append(f"Row {row_number}: Unsupported expense action '{expense_action}'.")
            continue

        category = _find_category_by_name(_normalize_import_category_name(review_row.get("category_name")), user_id)
        expense_datetime: datetime | None = None
        if parsed_visit_date is not None:
            expense_datetime = _build_import_expense_datetime(
                parsed_visit_date,
                parsed_datetime_raw,
                has_explicit_time,
                update_expense,
            )
        elif import_source_type == "simplifi" and parsed_cleared_date is not None and update_expense is None:
            # New Simplifi rows have a cleared date but no known visit date yet; fall back to the cleared date.
            expense_datetime = _build_import_expense_datetime(parsed_cleared_date, "", False, None)
        normalized_notes = str(review_row.get("notes") or "").strip() or None
        normalized_meal_type = str(review_row.get("meal_type") or "").strip() or None
        normalized_order_type = str(review_row.get("order_type") or "").strip() or None
        party_size_raw = str(review_row.get("party_size") or "").strip()
        parsed_party_size = int(party_size_raw) if party_size_raw.isdigit() else None
        tag_names, tag_error = _parse_import_tags(review_row.get("tags"))
        if tag_error:
            error_messages.append(f"Row {row_number}: Tags error: {tag_error}")
            continue
        normalized_tags = _normalize_import_tag_names(tag_names or [])

        if update_expense is not None:
            if expense_datetime is not None and (import_source_type == "standard" or parsed_visit_date is not None):
                update_expense.date = expense_datetime
            update_expense.cleared_date = parsed_cleared_date
            update_expense.amount = amount
            update_expense.notes = normalized_notes
            update_expense.meal_type = normalized_meal_type
            update_expense.order_type = normalized_order_type
            update_expense.category = category if category else None
            update_expense.party_size = parsed_party_size
            if restaurant is not None:
                update_expense.restaurant = restaurant
            _replace_import_tags_on_expense(
                update_expense,
                user_id,
                normalized_tags,
                existing_tags,
                created_tags,
                tag_counts,
            )
            updated_count += 1
            continue

        expense = Expense(
            user_id=user_id,
            date=expense_datetime if expense_datetime is not None else datetime.now(UTC),
            cleared_date=parsed_cleared_date,
            amount=amount,
            notes=normalized_notes,
            meal_type=normalized_meal_type,
            order_type=normalized_order_type,
            category=category if category else None,
            restaurant=restaurant,
            party_size=parsed_party_size,
        )
        db.session.add(expense)
        imported_count += 1
        _apply_import_tags_to_expense(expense, user_id, normalized_tags, existing_tags, created_tags, tag_counts)

    if error_messages:
        db.session.rollback()
        return {
            "success": False,
            "imported_count": 0,
            "updated_count": 0,
            "skipped_count": skipped_count,
            "errors": error_messages,
        }

    db.session.commit()
    return {
        "success": True,
        "imported_count": imported_count,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "errors": [],
    }


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
