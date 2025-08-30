"""Service layer for restaurant-related operations."""

import csv
import io
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from werkzeug.datastructures import FileStorage

from app.expenses.models import Expense
from app.extensions import db
from app.restaurants.exceptions import (
    DuplicateGooglePlaceIdError,
    DuplicateRestaurantError,
)
from app.restaurants.models import Restaurant
from app.utils.cuisine_formatter import format_cuisine_type


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


def restaurant_exists(user_id: int, name: str, city: str, google_place_id: str = None) -> Optional[Restaurant]:
    """Check if a restaurant already exists for the user.

    Prioritizes checking by google_place_id if provided, then falls back to name and city.

    Args:
        user_id: ID of the user
        name: Name of the restaurant
        city: City of the restaurant
        google_place_id: Google Place ID of the restaurant (optional)

    Returns:
        The existing restaurant if found, None otherwise
    """
    # First check by Google Place ID if provided
    if google_place_id:
        existing_by_place_id = db.session.scalar(
            select(Restaurant).where(
                Restaurant.user_id == user_id,
                Restaurant.google_place_id == google_place_id,
            )
        )
        if existing_by_place_id:
            return existing_by_place_id

    # Fallback to checking by name and city
    return db.session.scalar(
        select(Restaurant).where(
            Restaurant.user_id == user_id,
            func.lower(Restaurant.name) == func.lower(name),
            func.lower(Restaurant.city) == func.lower(city) if city else True,
        )
    )


def validate_restaurant_uniqueness(
    user_id: int, name: str, city: str, google_place_id: str = None, exclude_id: int = None
) -> None:
    """Validate that a restaurant doesn't violate uniqueness constraints.

    Args:
        user_id: ID of the user
        name: Name of the restaurant
        city: City of the restaurant
        google_place_id: Google Place ID of the restaurant (optional)
        exclude_id: Restaurant ID to exclude from validation (for updates)

    Raises:
        DuplicateGooglePlaceIdError: If Google Place ID already exists
        DuplicateRestaurantError: If restaurant name/city combination already exists
    """
    # Check for Google Place ID duplicates first (higher priority)
    if google_place_id:
        existing_stmt = select(Restaurant).where(
            Restaurant.user_id == user_id,
            Restaurant.google_place_id == google_place_id,
        )
        if exclude_id:
            existing_stmt = existing_stmt.where(Restaurant.id != exclude_id)

        existing_by_place_id = db.session.scalar(existing_stmt)
        if existing_by_place_id:
            raise DuplicateGooglePlaceIdError(google_place_id, existing_by_place_id)

    # Check for name/city duplicates
    existing_stmt = select(Restaurant).where(
        Restaurant.user_id == user_id,
        func.lower(Restaurant.name) == func.lower(name),
        func.lower(Restaurant.city) == func.lower(city) if city else True,
    )
    if exclude_id:
        existing_stmt = existing_stmt.where(Restaurant.id != exclude_id)

    existing_by_name_city = db.session.scalar(existing_stmt)
    if existing_by_name_city:
        raise DuplicateRestaurantError(name, city, existing_by_name_city)


def create_restaurant(user_id: int, form: Any) -> Tuple[Restaurant, bool]:
    """Create a new restaurant or return existing one.

    Args:
        user_id: ID of the user creating the restaurant
        form: Form containing restaurant data

    Returns:
        A tuple of (restaurant, is_new) where is_new is True if the restaurant was created

    Raises:
        DuplicateGooglePlaceIdError: If Google Place ID already exists
        DuplicateRestaurantError: If restaurant name/city combination already exists
    """
    # Get form data
    google_place_id = getattr(form, "google_place_id", None)
    google_place_id_value = google_place_id.data if google_place_id else None
    name = form.name.data
    city = form.city.data

    # Validate uniqueness constraints - this will raise exceptions if duplicates found
    validate_restaurant_uniqueness(user_id, name, city, google_place_id_value)

    # Create new restaurant
    restaurant = Restaurant(user_id=user_id)
    form.populate_obj(restaurant)

    # Format cuisine type for consistency
    if hasattr(restaurant, "cuisine") and restaurant.cuisine:
        restaurant.cuisine = format_cuisine_type(restaurant.cuisine)

    try:
        db.session.add(restaurant)
        db.session.commit()
        return restaurant, True
    except IntegrityError as e:
        db.session.rollback()
        # Handle database constraint violations
        if "uix_restaurant_google_place_id_user" in str(e.orig):
            # Re-query to get the existing restaurant for the exception
            existing = db.session.scalar(
                select(Restaurant).where(
                    Restaurant.user_id == user_id,
                    Restaurant.google_place_id == google_place_id_value,
                )
            )
            if existing:
                raise DuplicateGooglePlaceIdError(google_place_id_value, existing)
        elif "uix_restaurant_name_city_user" in str(e.orig):
            # Re-query to get the existing restaurant for the exception
            existing = db.session.scalar(
                select(Restaurant).where(
                    Restaurant.user_id == user_id,
                    func.lower(Restaurant.name) == func.lower(name),
                    func.lower(Restaurant.city) == func.lower(city) if city else True,
                )
            )
            if existing:
                raise DuplicateRestaurantError(name, city, existing)
        # Re-raise original error if we can't handle it
        raise


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
    numeric_fields = {"rating"}
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

    # Format cuisine type for consistency
    if hasattr(restaurant, "cuisine") and restaurant.cuisine:
        restaurant.cuisine = format_cuisine_type(restaurant.cuisine)

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


# Helper function to safely convert to float
def safe_import_float(value):
    if not value or str(value).strip() == "":
        return None
    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return None


# Helper function to safely convert to bool
def safe_import_bool(value):
    if not value or str(value).strip() == "":
        return None
    return str(value).strip().lower() in ("true", "1", "yes", "on")


# Helper function to safely convert to int
def safe_import_int(value):
    if not value or str(value).strip() == "":
        return None
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


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
            state=row.get("state", "").strip() or None,
            postal_code=row.get("postal_code", "").strip() or None,
            country=row.get("country", "").strip() or None,
            phone=row.get("phone", "").strip() or None,
            email=row.get("email", "").strip() or None,
            website=row.get("website", "").strip() or None,
            cuisine=row.get("cuisine", "").strip() or None,
            rating=safe_import_float(row.get("rating")),
            is_chain=safe_import_bool(row.get("is_chain")),
            google_place_id=row.get("google_place_id", "").strip() or None,
            notes=row.get("notes", "").strip() or None,
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
            "rating": safe_float(r.rating) if r.rating is not None else "",
            "is_chain": bool(r.is_chain) if r.is_chain is not None else "",
            "google_place_id": r.google_place_id or "",
            "notes": r.notes or "",
            "created_at": r.created_at.isoformat() if r.created_at else "",
            "updated_at": r.updated_at.isoformat() if r.updated_at else "",
        }
        for r in restaurants
    ]


def get_restaurants_for_user(user_id: int) -> List[Restaurant]:
    """
    Get all restaurants for a specific user.

    Args:
        user_id: ID of the current user

    Returns:
        List of restaurants belonging to the user
    """
    return Restaurant.query.filter_by(user_id=user_id).order_by(Restaurant.name).all()


def create_restaurant_for_user(user_id: int, data: Dict[str, Any]) -> Restaurant:
    """
    Create a new restaurant for a user from API data.

    Args:
        user_id: ID of the current user
        data: Dictionary containing restaurant data

    Returns:
        The created restaurant
    """
    # Create a new restaurant object
    restaurant = Restaurant(
        user_id=user_id,
        name=data.get("name"),
        type=data.get("type"),
        description=data.get("description"),
        address=data.get("address"),
        address2=data.get("address2"),
        city=data.get("city"),
        state=data.get("state"),
        postal_code=data.get("postal_code"),
        country=data.get("country"),
        phone=data.get("phone"),
        email=data.get("email"),
        website=data.get("website"),
        google_place_id=data.get("google_place_id"),
        cuisine=data.get("cuisine"),
        rating=data.get("rating"),
        is_chain=data.get("is_chain", False),
        notes=data.get("notes"),
    )

    db.session.add(restaurant)
    db.session.commit()

    return restaurant


def update_restaurant_for_user(restaurant: Restaurant, data: Dict[str, Any]) -> Restaurant:
    """
    Update an existing restaurant for a user from API data.

    Args:
        restaurant: The restaurant to update
        data: Dictionary containing updated restaurant data

    Returns:
        The updated restaurant
    """
    # Update restaurant fields using a loop to reduce complexity
    updateable_fields = [
        "name",
        "type",
        "description",
        "address",
        "address2",
        "city",
        "state",
        "postal_code",
        "country",
        "phone",
        "email",
        "website",
        "google_place_id",
        "cuisine",
        "rating",
        "is_chain",
        "notes",
    ]

    for field in updateable_fields:
        if field in data:
            setattr(restaurant, field, data[field])

    db.session.commit()

    return restaurant


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

        # Check if restaurant has expenses
        expenses = db.session.scalars(
            select(Expense).where(Expense.restaurant_id == restaurant_id, Expense.user_id == user_id)
        ).all()
        expense_count = len(expenses)

        if expense_count > 0:
            # Delete all associated expenses first
            for expense in expenses:
                db.session.delete(expense)

            # Then delete the restaurant
            db.session.delete(restaurant)
            db.session.commit()

            if expense_count == 1:
                return True, "Restaurant and 1 associated expense deleted successfully."
            else:
                return True, f"Restaurant and {expense_count} associated expenses deleted successfully."
        else:
            # No expenses, just delete the restaurant
            db.session.delete(restaurant)
            db.session.commit()
            return True, "Restaurant deleted successfully."

    except Exception as e:
        db.session.rollback()
        raise e


# TODO consider consolidating logic with get_restaurants_with_stats
def calculate_expense_stats(restaurant_id: int, user_id: int) -> Dict[str, Any]:
    """Calculate expense statistics for a restaurant.

    Args:
        restaurant_id: The ID of the restaurant
        user_id: The ID of the user (for security)

    Returns:
        Dictionary containing expense statistics with the following keys:
        - visit_count: int - Number of visits to the restaurant
        - total_amount: float - Total amount spent at the restaurant
        - avg_per_visit: float - Average amount spent per visit
        - last_visit: Optional[datetime] - Date of the last visit, or None if no visits
    """
    stats = db.session.execute(
        select(
            func.count(Expense.id).label("visit_count"),
            func.sum(Expense.amount).label("total_amount"),
            func.max(Expense.date).label("last_visit"),
        ).where(Expense.restaurant_id == restaurant_id, Expense.user_id == user_id)
    ).first()

    avg_per_visit = 0.0
    if stats and stats.visit_count > 0 and stats.total_amount is not None:
        avg_per_visit = float(stats.total_amount) / stats.visit_count

    return {
        "visit_count": stats.visit_count if stats else 0,
        "total_amount": float(stats.total_amount) if stats and stats.total_amount else 0.0,
        "avg_per_visit": avg_per_visit,
        "last_visit": stats.last_visit if stats else None,
    }
