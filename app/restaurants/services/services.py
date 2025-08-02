"""Service layer for restaurant-related operations."""

import csv
import io
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import exists, func, select
from werkzeug.datastructures import FileStorage

from app.expenses.models import Expense
from app.extensions import db
from app.restaurants.models import Restaurant


def get_restaurants_with_stats(user_id: int, args: Dict[str, Any]) -> Tuple[list, dict]:
    """
    Get a list of restaurants for a user with calculated statistics.

    Args:
        user_id: The ID of the user.
        args: Request arguments for sorting and filtering.

    Returns:
        A tuple containing the list of restaurants (as dicts) and summary statistics.
    """
    sort_by = args.get("sort", "name")
    sort_order = args.get("order", "asc")
    cuisine_filter = args.get("cuisine")

    stmt = (
        select(
            Restaurant,
            func.count(Expense.id).label("visit_count"),
            func.coalesce(func.sum(Expense.amount), 0).label("total_spent"),
            func.max(Expense.date).label("last_visit"),
        )
        .outerjoin(
            Expense,
            (Expense.restaurant_id == Restaurant.id) & (Expense.user_id == user_id),
        )
        .where(Restaurant.user_id == user_id)
        .group_by(Restaurant.id)
    )

    if cuisine_filter:
        stmt = stmt.where(Restaurant.cuisine == cuisine_filter)

    sort_column = {
        "name": Restaurant.name,
        "visits": func.count(Expense.id),
        "spent": func.coalesce(func.sum(Expense.amount), 0),
        "last_visit": func.max(Expense.date),
    }.get(sort_by, Restaurant.name)

    sort_direction = sort_order.upper() if sort_order in ["asc", "desc"] else "ASC"
    # Ensure sort_column is not None before calling asc() or desc()
    if sort_column is not None:
        stmt = stmt.order_by(
            sort_column.asc() if sort_direction == "ASC" else sort_column.desc(),
            Restaurant.name.asc(),
        )
    else:
        stmt = stmt.order_by(Restaurant.name.asc())

    # Execute query and convert results to list of dicts
    results = db.session.execute(stmt).all()

    # Convert results to list of dictionaries with all required attributes
    restaurants = []
    for row in results:
        restaurant = row[0].__dict__.copy()
        # Remove SQLAlchemy instance state
        restaurant.pop("_sa_instance_state", None)
        # Add the aggregated fields
        restaurant.update(
            {
                "visit_count": row.visit_count,
                "total_spent": float(row.total_spent) if row.total_spent else 0.0,
                "last_visit": row.last_visit,
            }
        )
        restaurants.append(restaurant)

    total_restaurants = len(restaurants)
    total_visits = sum(r.get("visit_count", 0) for r in restaurants)
    total_spent = sum(r.get("total_spent", 0) for r in restaurants)

    stats = {
        "total_restaurants": total_restaurants,
        "total_visits": total_visits,
        "total_spent": total_spent,
    }
    return restaurants, stats


def get_unique_cuisines(user_id: int) -> list[str]:
    """Get a list of unique cuisines for a user."""
    return [
        cuisine
        for cuisine in db.session.scalars(
            select(Restaurant.cuisine)
            .where(Restaurant.user_id == user_id, Restaurant.cuisine.isnot(None))
            .distinct()
            .order_by(Restaurant.cuisine)
        ).all()
        if cuisine is not None
    ]


def restaurant_exists(user_id: int, name: str, city: str) -> Optional[Restaurant]:
    """Check if a restaurant with the same name and city already exists for the user.

    Args:
        user_id: ID of the user
        name: Name of the restaurant
        city: City of the restaurant

    Returns:
        The existing restaurant if found, None otherwise
    """
    return db.session.scalar(
        select(Restaurant).where(
            Restaurant.user_id == user_id,
            func.lower(Restaurant.name) == func.lower(name),
            func.lower(Restaurant.city) == func.lower(city) if city else True,
        )
    )


def create_restaurant(user_id: int, form: Any) -> Tuple[Restaurant, bool]:
    """Create a new restaurant or return existing one.

    Args:
        user_id: ID of the user creating the restaurant
        form: Form containing restaurant data

    Returns:
        A tuple of (restaurant, is_new) where is_new is True if the restaurant was created
    """
    # Check if restaurant with same name and city already exists
    existing = restaurant_exists(user_id, form.name.data, form.city.data)
    if existing:
        return existing, False

    # Create new restaurant
    restaurant = Restaurant(user_id=user_id)
    form.populate_obj(restaurant)
    db.session.add(restaurant)
    db.session.commit()
    return restaurant, True


def update_restaurant(restaurant_id: int, user_id: int, form: Any) -> Restaurant:
    """Update an existing restaurant.

    Args:
        restaurant_id: ID of the restaurant to update
        user_id: ID of the user making the update
        form: Form containing the updated restaurant data

    Returns:
        The updated Restaurant object

    Raises:
        ValueError: If the restaurant is not found or the user doesn't have permission
    """
    restaurant = get_restaurant_for_user(restaurant_id, user_id)
    if not restaurant:
        raise ValueError("Restaurant not found or access denied")

    # Create a dictionary of form data, converting empty strings to None for numeric fields
    form_data = {}
    numeric_fields = {"rating", "latitude", "longitude"}
    boolean_fields = {"is_chain"}

    for field in form:
        if field.name in numeric_fields:
            # Convert empty strings to None for numeric fields
            form_data[field.name] = float(field.data) if field.data and str(field.data).strip() else None
        elif field.name in boolean_fields:
            # Ensure boolean fields are properly converted
            form_data[field.name] = bool(field.data) if field.data is not None else False
        else:
            # For all other fields, use the value as is or empty string
            form_data[field.name] = field.data if field.data is not None else ""

    # Update the restaurant object with the processed form data
    for key, value in form_data.items():
        if hasattr(restaurant, key):
            setattr(restaurant, key, value)

    db.session.commit()
    return restaurant


def _validate_restaurant_row(row: dict) -> Tuple[bool, str]:
    """Validate a single restaurant row from CSV.

    Args:
        row: Dictionary containing restaurant data

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not row.get("name", "").strip():
        return False, "Name is required"
    if not row.get("city", "").strip():
        return False, "City is required"
    return True, ""


def _process_restaurant_row(row: dict, user_id: int) -> Tuple[bool, str, Restaurant]:
    """Process a single restaurant row from CSV.

    Args:
        row: Dictionary containing restaurant data
        user_id: ID of the user importing the restaurants

    Returns:
        Tuple of (success, error_message, restaurant)
    """
    try:
        is_valid, error = _validate_restaurant_row(row)
        if not is_valid:
            return False, error, None

        restaurant = Restaurant(
            user_id=user_id,
            name=row.get("name", "").strip(),
            city=row.get("city", "").strip(),
            address=row.get("address", "").strip() or None,
            phone=row.get("phone", "").strip() or None,
            website=row.get("website", "").strip() or None,
            cuisine=row.get("cuisine", "").strip() or None,
        )
        return True, "", restaurant
    except Exception as e:
        return False, str(e), None


def _process_csv_file(file: FileStorage) -> Tuple[bool, str, Optional[csv.DictReader]]:
    """Process the uploaded CSV file.

    Args:
        file: The uploaded CSV file

    Returns:
        Tuple of (success, error_message, csv_reader)
    """
    try:
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)

        required_columns = {"name", "city"}
        if not required_columns.issubset(set(csv_reader.fieldnames or [])):
            return False, "CSV file is missing required columns: name, city", None

        return True, "", csv_reader
    except Exception as e:
        return False, f"Error reading CSV file: {str(e)}", None


def _import_restaurants_from_reader(csv_reader: csv.DictReader, user_id: int) -> Tuple[int, List[str]]:
    """Import restaurants from a CSV reader.

    Args:
        csv_reader: CSV reader with restaurant data
        user_id: ID of the user importing the restaurants

    Returns:
        Tuple of (success_count, errors)
    """
    success_count = 0
    errors = []

    for i, row in enumerate(csv_reader, 2):  # Start from line 2 (1-based + header)
        success, error, restaurant = _process_restaurant_row(row, user_id)
        if success and restaurant:
            db.session.add(restaurant)
            success_count += 1
        else:
            errors.append(f"Line {i}: {error}")

    return success_count, errors


def _generate_import_result(success_count: int, errors: List[str]) -> Tuple[bool, str]:
    """Generate the result of the import operation.

    Args:
        success_count: Number of successfully imported restaurants
        errors: List of error messages

    Returns:
        Tuple of (success, message)
    """
    if success_count > 0:
        db.session.commit()

    if errors:
        error_msg = (
            f"{success_count} restaurants imported successfully, but {len(errors)} "
            f"rows had errors. Errors: {', '.join(errors)}"
        )
        return success_count > 0, error_msg

    return True, f"{success_count} restaurants imported successfully"


def import_restaurants_from_csv(file: FileStorage, user_id: int) -> Tuple[bool, str]:
    """Import restaurants from a CSV file.

    Args:
        file: The uploaded CSV file
        user_id: ID of the user importing the restaurants

    Returns:
        A tuple containing (success: bool, message: str)
    """
    try:
        # Process the CSV file
        success, error, csv_reader = _process_csv_file(file)
        if not success:
            return False, error

        # Import restaurants from the CSV data
        success_count, errors = _import_restaurants_from_reader(csv_reader, user_id)

        # Generate the result message
        return _generate_import_result(success_count, errors)

    except Exception as e:
        db.session.rollback()
        return False, f"Error processing CSV file: {str(e)}"


def export_restaurants_for_user(user_id: int) -> List[Dict[str, Any]]:
    """Get all restaurants for a user in a format suitable for export.

    Args:
        user_id: The ID of the user whose restaurants to export

    Returns:
        A list of dictionaries containing restaurant data
    """
    restaurants = db.session.scalars(
        select(Restaurant).where(Restaurant.user_id == user_id).order_by(Restaurant.name)
    ).all()

    def safe_float(value):
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    return [
        {
            "name": r.name or "",
            "address": r.address or "",
            "city": r.city or "",
            "state": r.state or "",
            "postal_code": r.postal_code or "",
            "country": r.country or "",
            "phone": r.phone or "",
            "email": r.email or "",
            "cuisine": r.cuisine or "",
            "website": r.website or "",
            "price_range": r.price_range or "",
            "rating": safe_float(r.rating) if r.rating is not None else "",
            "is_chain": bool(r.is_chain) if r.is_chain is not None else "",
            "latitude": safe_float(r.latitude) if r.latitude is not None else "",
            "longitude": safe_float(r.longitude) if r.longitude is not None else "",
            "notes": r.notes or "",
            "created_at": r.created_at.isoformat() if r.created_at else "",
            "updated_at": r.updated_at.isoformat() if r.updated_at else "",
        }
        for r in restaurants
    ]


def get_restaurant_for_user(restaurant_id: int, user_id: int) -> Optional[Restaurant]:
    """Get a restaurant by ID if it belongs to the user."""
    return db.session.scalar(select(Restaurant).where(Restaurant.id == restaurant_id, Restaurant.user_id == user_id))


def delete_restaurant_by_id(restaurant_id: int, user_id: int) -> Tuple[bool, str]:
    """Delete a restaurant by ID.

    Args:
        restaurant_id: The ID of the restaurant to delete
        user_id: The ID of the user making the request

    Returns:
        A tuple of (success: bool, message: str)
    """
    try:
        restaurant = get_restaurant_for_user(restaurant_id, user_id)
        if not restaurant:
            return False, "Restaurant not found or you don't have permission to delete it."

        has_expenses = db.session.scalar(select(exists().where(Expense.restaurant_id == restaurant_id)))
        if has_expenses:
            return False, "Cannot delete a restaurant with associated expenses. Please delete the expenses first."

        db.session.delete(restaurant)
        db.session.commit()
        return True, "Restaurant deleted successfully."

    except Exception as e:
        db.session.rollback()
        raise e
