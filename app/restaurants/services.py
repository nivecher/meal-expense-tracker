"""Service layer for restaurant-related operations."""

import csv
import io
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app
from sqlalchemy import case, func, or_, select
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
from app.utils.service_level_detector import (
    ServiceLevelDetector,
    detect_restaurant_service_level,
)


def get_restaurant_filters(args: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and validate filter parameters from the request.

    Args:
        args: The request arguments

    Returns:
        Dict containing filter parameters
    """
    # Support both 'search' and 'q' parameters for search functionality
    search_term = args.get("search", "").strip() or args.get("q", "").strip()
    return {
        "search": search_term,
        "cuisine": args.get("cuisine", "").strip(),
        "service_level": args.get("service_level", "").strip(),
        "city": args.get("city", "").strip(),
        "is_chain": args.get("is_chain", "").strip(),
        "rating_min": args.get("rating_min", "").strip(),
        "rating_max": args.get("rating_max", "").strip(),
        "sort_by": args.get("sort", "name"),
        "sort_order": args.get("order", "asc"),
    }


def get_restaurants_with_stats(user_id: int, args: Dict[str, Any]) -> Tuple[list, dict]:
    """
    Get a list of restaurants for a user with calculated statistics.

    Args:
        user_id: The ID of the user.
        args: Request arguments for sorting and filtering.

    Returns:
        A tuple containing the list of restaurants (as dicts) and summary statistics.
    """
    # Extract filters
    filters = get_restaurant_filters(args)

    stmt = (
        select(
            Restaurant,
            func.count(Expense.id).label("visit_count"),
            func.coalesce(func.sum(Expense.amount), 0).label("total_spent"),
            func.max(Expense.date).label("last_visit"),
            func.coalesce(
                func.avg(
                    case(
                        (
                            Expense.party_size.isnot(None) & (Expense.party_size > 1),
                            Expense.amount / Expense.party_size,
                        ),
                        else_=None,
                    )
                ),
                0,
            ).label("avg_price_per_person"),
        )
        .outerjoin(
            Expense,
            (Expense.restaurant_id == Restaurant.id) & (Expense.user_id == user_id),
        )
        .where(Restaurant.user_id == user_id)
        .group_by(Restaurant.id)
    )

    # Apply filters
    stmt = apply_restaurant_filters(stmt, filters)

    # Apply sorting
    stmt = apply_restaurant_sorting(stmt, filters["sort_by"], filters["sort_order"])

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
                "avg_price_per_person": float(row.avg_price_per_person) if row.avg_price_per_person else 0.0,
            }
        )
        restaurants.append(restaurant)

    total_restaurants = len(restaurants)
    total_visits = sum(r.get("visit_count", 0) for r in restaurants)
    total_spent = sum(r.get("total_spent", 0) for r in restaurants)

    # Calculate overall average price per person
    avg_prices = [r.get("avg_price_per_person", 0) for r in restaurants if r.get("avg_price_per_person", 0) > 0]
    overall_avg_price_per_person = sum(avg_prices) / len(avg_prices) if avg_prices else 0.0

    stats = {
        "total_restaurants": total_restaurants,
        "total_visits": total_visits,
        "total_spent": total_spent,
        "avg_price_per_person": overall_avg_price_per_person,
    }
    return restaurants, stats


def _apply_search_filter(stmt, search_term: str):
    """Apply search filter to the query."""
    if not search_term:
        return stmt

    search_pattern = f"%{search_term}%"
    return stmt.where(
        or_(
            Restaurant.name.ilike(search_pattern),
            Restaurant.address.ilike(search_pattern),
            Restaurant.city.ilike(search_pattern),
            Restaurant.state.ilike(search_pattern),
            Restaurant.notes.ilike(search_pattern),
            Restaurant.cuisine.ilike(search_pattern),
        )
    )


def _apply_rating_filters(stmt, rating_min: str, rating_max: str):
    """Apply rating range filters to the query."""
    if rating_min:
        try:
            rating_min_val = float(rating_min)
            stmt = stmt.where(Restaurant.rating >= rating_min_val)
        except (ValueError, TypeError):
            pass

    if rating_max:
        try:
            rating_max_val = float(rating_max)
            stmt = stmt.where(Restaurant.rating <= rating_max_val)
        except (ValueError, TypeError):
            pass

    return stmt


def apply_restaurant_filters(stmt, filters: Dict[str, Any]):
    """Apply filters to the restaurant query.

    Args:
        stmt: The SQLAlchemy select statement
        filters: Dictionary of filter parameters

    Returns:
        The modified select statement with filters applied
    """
    # Apply search filter
    stmt = _apply_search_filter(stmt, filters["search"])

    # Apply exact match filters
    if filters["cuisine"]:
        stmt = stmt.where(Restaurant.cuisine == filters["cuisine"])

    if filters["service_level"]:
        stmt = stmt.where(Restaurant.service_level == filters["service_level"])

    if filters["city"]:
        stmt = stmt.where(Restaurant.city.ilike(f"%{filters['city']}%"))

    if filters["is_chain"]:
        is_chain_value = filters["is_chain"].lower() == "true"
        stmt = stmt.where(Restaurant.is_chain == is_chain_value)

    # Apply rating filters
    stmt = _apply_rating_filters(stmt, filters["rating_min"], filters["rating_max"])

    return stmt


def _get_sort_field(sort_by: str):
    """Get the appropriate sort field for restaurant sorting.

    Args:
        sort_by: Field to sort by

    Returns:
        SQLAlchemy sort field or None
    """
    sort_mapping = {
        "name": Restaurant.name,
        "city": Restaurant.city,
        "cuisine": Restaurant.cuisine,
        "rating": Restaurant.rating,
        "visits": func.count(Expense.id),
        "spent": func.coalesce(func.sum(Expense.amount), 0),
        "last_visit": func.max(Expense.date),
        "avg_price_per_person": func.coalesce(
            func.avg(
                case(
                    (Expense.party_size.isnot(None) & (Expense.party_size > 1), Expense.amount / Expense.party_size),
                    else_=None,
                )
            ),
            0,
        ),
        "created_at": Restaurant.created_at,
    }
    return sort_mapping.get(sort_by)


def apply_restaurant_sorting(stmt, sort_by: str, sort_order: str):
    """Apply sorting to the restaurant query.

    Args:
        stmt: The SQLAlchemy select statement
        sort_by: Field to sort by
        sort_order: Sort order ('asc' or 'desc')

    Returns:
        The modified select statement with sorting applied
    """
    sort_field = _get_sort_field(sort_by)
    if not sort_field:
        return stmt

    is_desc = sort_order.lower() == "desc"
    return stmt.order_by(sort_field.desc() if is_desc else sort_field.asc())


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


def get_unique_cities(user_id: int) -> list[str]:
    """Get a list of unique cities for a user."""
    return [
        city
        for city in db.session.scalars(
            select(Restaurant.city)
            .where(Restaurant.user_id == user_id, Restaurant.city.isnot(None))
            .distinct()
            .order_by(Restaurant.city)
        ).all()
        if city is not None
    ]


def get_unique_service_levels(user_id: int) -> list[str]:
    """Get a list of unique service levels for a user."""
    return [
        service_level
        for service_level in db.session.scalars(
            select(Restaurant.service_level)
            .where(Restaurant.user_id == user_id, Restaurant.service_level.isnot(None))
            .distinct()
            .order_by(Restaurant.service_level)
        ).all()
        if service_level is not None
    ]


def get_filter_options(user_id: int) -> Dict[str, Any]:
    """
    Get filter options for the restaurants list.

    Args:
        user_id: ID of the current user

    Returns:
        Dictionary containing filter options:
        - cuisines: List of cuisine names
        - cities: List of city names
        - service_levels: List of service level names
    """
    return {
        "cuisines": get_unique_cuisines(user_id),
        "cities": get_unique_cities(user_id),
        "service_levels": get_unique_service_levels(user_id),
    }


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

    # Handle service level auto-detection
    _auto_detect_service_level(restaurant)

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

    # Handle service level auto-detection for updates
    _auto_detect_service_level(restaurant)

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


def _find_existing_restaurant(
    name: str, address: str, city: str, google_place_id: str, user_id: int
) -> Optional[Restaurant]:
    """Find existing restaurant using smart duplicate detection.

    Checks for duplicates by:
    1. Google Place ID (if provided)
    2. Name + Address combination
    3. Name + City combination (as fallback)

    Args:
        name: Restaurant name
        address: Restaurant address
        city: Restaurant city
        google_place_id: Google Place ID
        user_id: User ID

    Returns:
        Existing restaurant if found, None otherwise
    """
    # Strategy 1: Match by Google Place ID (most reliable)
    if google_place_id:
        existing = Restaurant.query.filter_by(user_id=user_id, google_place_id=google_place_id).first()
        if existing:
            return existing

    # Strategy 2: Match by name + address (if both provided)
    if name and address:
        existing = Restaurant.query.filter_by(user_id=user_id, name=name, address=address).first()
        if existing:
            return existing

    # Strategy 3: Match by name + city (existing constraint)
    if name and city:
        existing = Restaurant.query.filter_by(user_id=user_id, name=name, city=city).first()
        if existing:
            return existing

    return None


def _process_restaurant_row(row: dict, user_id: int) -> Tuple[bool, str, Optional[Restaurant]]:
    """Process a single restaurant row from CSV with smart duplicate detection.

    Args:
        row: Dictionary containing restaurant data
        user_id: ID of the user importing the restaurants

    Returns:
        Tuple of (success, error_message, restaurant_or_none)
    """
    try:
        is_valid, error = _validate_restaurant_row(row)
        if not is_valid:
            return False, error, None

        # Extract and clean data
        name = row.get("name", "").strip()
        address = row.get("address", "").strip() or None
        city = row.get("city", "").strip() or None
        google_place_id = row.get("google_place_id", "").strip() or None

        # Check for existing restaurant using smart detection
        existing_restaurant = _find_existing_restaurant(name, address, city, google_place_id, user_id)

        if existing_restaurant:
            # Skip duplicate - return success but no restaurant to add
            return True, f"Skipped duplicate restaurant: {name}", None

        # Create new restaurant
        restaurant = Restaurant(
            user_id=user_id,
            name=name,
            city=city,
            address=address,
            state=row.get("state", "").strip() or None,
            postal_code=row.get("postal_code", "").strip() or None,
            country=row.get("country", "").strip() or None,
            phone=row.get("phone", "").strip() or None,
            email=row.get("email", "").strip() or None,
            website=row.get("website", "").strip() or None,
            cuisine=row.get("cuisine", "").strip() or None,
            service_level=row.get("service_level", "").strip() or None,
            rating=safe_import_float(row.get("rating")),
            is_chain=safe_import_bool(row.get("is_chain")),
            google_place_id=google_place_id,
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


def _import_restaurants_from_reader(csv_reader: csv.DictReader, user_id: int) -> Tuple[int, int, List[str]]:
    """Import restaurants from a CSV reader with smart duplicate detection.

    Args:
        csv_reader: CSV reader with restaurant data
        user_id: ID of the user importing the restaurants

    Returns:
        Tuple of (success_count, skipped_count, errors)
    """
    success_count = 0
    skipped_count = 0
    errors = []

    for i, row in enumerate(csv_reader, 2):  # Start from line 2 (1-based + header)
        success, message, restaurant = _process_restaurant_row(row, user_id)

        if success:
            if restaurant:
                # New restaurant to add
                db.session.add(restaurant)
                success_count += 1
            else:
                # Duplicate skipped
                skipped_count += 1
        else:
            # Error processing row
            errors.append(f"Line {i}: {message}")

    return success_count, skipped_count, errors


def _generate_import_result(success_count: int, skipped_count: int, errors: List[str]) -> Tuple[bool, Dict[str, Any]]:
    """Generate the result of the import operation.

    Args:
        success_count: Number of successfully imported restaurants
        skipped_count: Number of skipped duplicate restaurants
        errors: List of error messages

    Returns:
        Tuple of (success, result_data)
    """
    if success_count > 0:
        db.session.commit()

    # Build result data with separate components
    result_data = {
        "success_count": success_count,
        "skipped_count": skipped_count,
        "error_count": len(errors),
        "errors": errors,
        "has_warnings": skipped_count > 0,
        "has_errors": len(errors) > 0,
    }

    # Build main message
    parts = []
    if success_count > 0:
        parts.append(f"{success_count} restaurants imported successfully")

    if skipped_count > 0:
        parts.append(f"{skipped_count} duplicates skipped")

    if errors:
        parts.append(f"{len(errors)} errors occurred")

    if parts:
        result_data["message"] = ". ".join(parts) + "."
    else:
        result_data["message"] = "No restaurants processed."

    # Add error details if there are actual errors
    if errors:
        # Limit error details to avoid overwhelming the user
        error_limit = 5
        if len(errors) > error_limit:
            error_details = errors[:error_limit] + [f"... and {len(errors) - error_limit} more errors"]
        else:
            error_details = errors
        result_data["error_details"] = error_details

    # Determine success - it's successful if there are no actual errors
    is_success = len(errors) == 0
    return is_success, result_data


def import_restaurants_from_csv(file: FileStorage, user_id: int) -> Tuple[bool, Dict[str, Any]]:
    """Import restaurants from a CSV file.

    Args:
        file: The uploaded CSV file
        user_id: ID of the user importing the restaurants

    Returns:
        A tuple containing (success: bool, result_data: Dict[str, Any])
    """
    try:
        # Process the CSV file
        success, error, csv_reader = _process_csv_file(file)
        if not success:
            return False, {"message": error, "has_errors": True, "error_details": [error]}

        # Import restaurants from the CSV data
        success_count, skipped_count, errors = _import_restaurants_from_reader(csv_reader, user_id)

        # Generate the result data
        return _generate_import_result(success_count, skipped_count, errors)

    except Exception as e:
        db.session.rollback()
        error_msg = f"Error processing CSV file: {str(e)}"
        return False, {"message": error_msg, "has_errors": True, "error_details": [error_msg]}


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
            "service_level": r.service_level or "",
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
        service_level=data.get("service_level"),
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
        "service_level",
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


# Note: This logic could potentially be consolidated with get_restaurants_with_stats in future refactoring
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


def detect_service_level_from_google_data(google_data: Dict[str, Any]) -> Tuple[str, float]:
    """
    Centralized function to detect service level from Google Places data.

    Args:
        google_data: Dictionary containing Google Places API response data

    Returns:
        Tuple of (service_level, confidence_score)
    """
    try:
        google_places_data = {
            "price_level": google_data.get("price_level"),
            "types": google_data.get("types", []),
            "rating": google_data.get("rating"),
            "user_ratings_total": google_data.get("user_ratings_total"),
        }

        detected_level, confidence = detect_restaurant_service_level(google_places_data)
        return detected_level.value, confidence
    except Exception:
        return "unknown", 0.0


def validate_restaurant_service_level(
    restaurant: Restaurant, google_service_level: str, confidence: float
) -> Tuple[bool, str, Optional[str]]:
    """
    Validate restaurant service level against Google data.

    Args:
        restaurant: Restaurant instance to validate
        google_service_level: Service level detected from Google
        confidence: Confidence score of the detection

    Returns:
        Tuple of (has_mismatch: bool, mismatch_message: str, suggested_fix: Optional[str])
    """
    if google_service_level == "unknown" or confidence <= 0.3:
        return False, "", None

    if restaurant.service_level and restaurant.service_level != google_service_level:
        return (
            True,
            f"Service Level: '{restaurant.service_level}' vs Google: '{google_service_level}' (confidence: {confidence:.2f})",
            google_service_level,
        )
    elif not restaurant.service_level:
        return (
            True,
            f"Service Level: Not set vs Google: '{google_service_level}' (confidence: {confidence:.2f})",
            google_service_level,
        )

    return False, "", None


def _auto_detect_service_level(restaurant: Restaurant) -> None:
    """
    Auto-detect service level for a restaurant if not set and Google Place ID is available.

    Args:
        restaurant: Restaurant instance to update
    """
    if not restaurant.service_level and restaurant.google_place_id:
        google_data = _get_google_place_data_for_service_level(restaurant.google_place_id)
        if google_data:
            detected_level, confidence = detect_service_level_from_google_data(google_data)
            if confidence > 0.3:  # Only use if confidence is reasonable
                restaurant.service_level = detected_level
                current_app.logger.info(
                    f"Auto-detected service level '{detected_level}' for restaurant "
                    f"'{restaurant.name}' (confidence: {confidence:.2f})"
                )


def _get_google_place_data_for_service_level(place_id: str) -> Optional[Dict[str, Any]]:
    """
    Get Google Places data for service level detection.

    Args:
        place_id: Google Place ID

    Returns:
        Dictionary with Google Places data or None if failed
    """
    try:
        import googlemaps

        gmaps = googlemaps.Client(key=current_app.config["GOOGLE_MAPS_API_KEY"])

        # Get place details
        place = gmaps.place(
            place_id=place_id,
            fields=[
                "priceLevel",
                "rating",
                "userRatingsTotal",
                "types",
            ],
        )

        if not place or "result" not in place:
            return None

        result = place["result"]
        return {
            "price_level": result.get("priceLevel"),
            "types": result.get("types", []),
            "rating": result.get("rating"),
            "user_ratings_total": result.get("userRatingsTotal"),
        }
    except Exception as e:
        current_app.logger.warning(f"Failed to fetch Google Places data for service level detection: {str(e)}")
        return None


def get_service_level_display_info(service_level: str) -> Dict[str, str]:
    """
    Get display information for a service level.

    Args:
        service_level: Service level string value

    Returns:
        Dictionary with display_name and description
    """
    try:
        # Convert string to ServiceLevel enum
        level_enum = ServiceLevelDetector.get_service_level_from_string(service_level)
        return {
            "display_name": ServiceLevelDetector.get_service_level_display_name(level_enum),
            "description": ServiceLevelDetector.get_service_level_description(level_enum),
        }
    except (ValueError, AttributeError):
        return {
            "display_name": "Unknown",
            "description": "Service level could not be determined",
        }


def validate_restaurant_with_google_places(
    name: str, address: str, google_place_id: str = None
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validate restaurant information using Google Places API.

    This is the centralized validation function used by CLI, admin operations, and API routes.

    Args:
        name: Restaurant name to validate
        address: Restaurant address to validate
        google_place_id: Optional Google Place ID for direct validation

    Returns:
        Tuple of (success: bool, message: str, validation_data: Dict[str, Any])
        validation_data contains:
        - valid: bool
        - mismatches: List[str]
        - fixes: Dict[str, str]
        - google_data: Dict[str, Any]
    """
    try:
        import googlemaps

        # Get Google Maps client
        gmaps = googlemaps.Client(key=current_app.config["GOOGLE_MAPS_API_KEY"])

        if google_place_id:
            # Validate against specific Google Place ID
            return _validate_with_place_id(gmaps, google_place_id, name, address)
        else:
            # Search for restaurant using text search
            return _validate_with_text_search(gmaps, name, address)

    except Exception as e:
        current_app.logger.error(f"Error validating restaurant with Google Places: {e}")
        return False, f"Failed to validate restaurant: {str(e)}", {}


def _validate_with_place_id(gmaps, google_place_id: str, name: str, address: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate restaurant using Google Place ID."""
    try:
        place = gmaps.place(
            place_id=google_place_id,
            language="en",
            fields=[
                "name",
                "formatted_address",
                "geometry/location",
                "rating",
                "business_status",
                "type",
                "user_ratings_total",
                "opening_hours",
                "website",
                "international_phone_number",
                "price_level",
                "editorial_summary",
                "address_component",
            ],
        )

        if place and "result" in place:
            google_data = place["result"]
            return True, "Validation completed", _process_validation_results(name, address, google_data)
        else:
            return False, "Invalid Google Place ID", {}

    except Exception as e:
        current_app.logger.error(f"Error validating with Google Place ID: {e}")
        return False, f"Failed to validate with Google Places: {str(e)}", {}


def _validate_with_text_search(gmaps, name: str, address: str) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate restaurant using text search."""
    try:
        places_result = gmaps.places(query=f"{name} {address}", type="restaurant", language="en")

        if places_result.get("results"):
            # Use the first result
            place = places_result["results"][0]
            place_id = place.get("place_id")

            if place_id:
                # Get detailed information
                place_details = gmaps.place(
                    place_id=place_id,
                    language="en",
                    fields=[
                        "name",
                        "formatted_address",
                        "geometry/location",
                        "rating",
                        "business_status",
                        "type",
                        "user_ratings_total",
                        "opening_hours",
                        "website",
                        "international_phone_number",
                        "price_level",
                        "editorial_summary",
                        "address_component",
                    ],
                )

                if place_details and "result" in place_details:
                    google_data = place_details["result"]
                    return (
                        True,
                        "Validation completed",
                        _process_validation_results(name, address, google_data, place_id),
                    )

        return False, "No matching restaurant found in Google Places", {}

    except Exception as e:
        current_app.logger.error(f"Error searching for restaurant: {e}")
        return False, f"Failed to search for restaurant: {str(e)}", {}


def _process_validation_results(
    name: str, address: str, google_data: Dict[str, Any], google_place_id: str = None
) -> Dict[str, Any]:
    """Process validation results and return structured data."""
    try:
        # Extract Google data
        google_name = google_data.get("name", "")
        google_address = google_data.get("formatted_address", "")
        google_rating = google_data.get("rating")
        google_phone = google_data.get("international_phone_number", "")
        google_website = google_data.get("website", "")
        google_price_level = google_data.get("price_level")

        # Extract address components
        address_components = google_data.get("address_component", [])

        # Build street address from components
        street_number = next(
            (comp.get("long_name") for comp in address_components if "street_number" in comp.get("types", [])),
            None,
        )
        route = next(
            (comp.get("long_name") for comp in address_components if "route" in comp.get("types", [])),
            None,
        )
        google_street_address = " ".join(filter(None, [street_number, route]))

        # Extract other address components
        google_city = next(
            (comp.get("long_name") for comp in address_components if "locality" in comp.get("types", [])),
            None,
        )
        google_state = next(
            (
                comp.get("short_name")
                for comp in address_components
                if "administrative_area_level_1" in comp.get("types", [])
            ),
            None,
        )
        google_postal_code = next(
            (comp.get("long_name") for comp in address_components if "postal_code" in comp.get("types", [])),
            None,
        )
        google_country = next(
            (comp.get("long_name") for comp in address_components if "country" in comp.get("types", [])),
            None,
        )

        # Detect service level
        service_level, confidence = detect_service_level_from_google_data(google_data)

        # Check for mismatches and build fixes
        mismatches, fixes = _build_validation_mismatches_and_fixes(
            name,
            address,
            google_name,
            google_street_address,
            google_city,
            google_state,
            google_postal_code,
            google_country,
            google_phone,
            google_website,
            service_level,
            confidence,
            google_place_id,
        )

        # Prepare response data
        return {
            "valid": True,
            "mismatches": mismatches,
            "fixes": fixes,
            "google_data": {
                "name": google_name,
                "address": google_street_address,
                "full_address": google_address,
                "rating": google_rating,
                "phone": google_phone,
                "website": google_website,
                "price_level": google_price_level,
                "service_level": service_level,
                "confidence": confidence,
                "place_id": google_place_id,
            },
        }

    except Exception as e:
        current_app.logger.error(f"Error processing validation results: {e}")
        return {"valid": False, "mismatches": [], "fixes": {}, "google_data": {}}


def _build_validation_mismatches_and_fixes(
    name: str,
    address: str,
    google_name: str,
    google_street_address: str,
    google_city: str,
    google_state: str,
    google_postal_code: str,
    google_country: str,
    google_phone: str,
    google_website: str,
    service_level: str,
    confidence: float,
    google_place_id: str,
) -> Tuple[List[str], Dict[str, str]]:
    """Build mismatches list and fixes dictionary."""
    mismatches = []
    fixes = {}

    # Check for name and address mismatches
    _check_name_mismatch(name, google_name, mismatches, fixes)
    _check_address_mismatch(address, google_street_address, mismatches, fixes)

    # Add other potential fixes
    _add_google_data_fixes(
        fixes,
        google_city,
        google_state,
        google_postal_code,
        google_country,
        google_phone,
        google_website,
        service_level,
        confidence,
        google_place_id,
    )

    return mismatches, fixes


def _check_name_mismatch(name: str, google_name: str, mismatches: List[str], fixes: Dict[str, str]) -> None:
    """Check for name mismatch and add to lists if found."""
    if google_name and google_name.lower() != name.lower():
        mismatches.append(f"Name: '{name}' vs Google: '{google_name}'")
        fixes["name"] = google_name


def _check_address_mismatch(
    address: str, google_street_address: str, mismatches: List[str], fixes: Dict[str, str]
) -> None:
    """Check for address mismatch and add to lists if found."""
    if google_street_address and google_street_address.lower() != address.lower():
        mismatches.append(f"Address: '{address}' vs Google: '{google_street_address}'")
        fixes["address"] = google_street_address


def _add_google_data_fixes(
    fixes: Dict[str, str],
    google_city: str,
    google_state: str,
    google_postal_code: str,
    google_country: str,
    google_phone: str,
    google_website: str,
    service_level: str,
    confidence: float,
    google_place_id: str,
) -> None:
    """Add Google data fixes to the fixes dictionary."""
    if google_city:
        fixes["city"] = google_city
    if google_state:
        fixes["state"] = google_state
    if google_postal_code:
        fixes["postal_code"] = google_postal_code
    if google_country:
        fixes["country"] = google_country
    if google_phone:
        fixes["phone"] = google_phone
    if google_website:
        fixes["website"] = google_website
    if service_level != "unknown" and confidence > 0.3:
        fixes["service_level"] = service_level
    if google_place_id:
        fixes["google_place_id"] = google_place_id
