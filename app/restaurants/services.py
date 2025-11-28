"""Service layer for restaurant-related operations."""

import csv
import io
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import Select
from werkzeug.datastructures import FileStorage

from app.constants.cuisines import format_cuisine_type
from app.expenses.models import Expense
from app.extensions import db
from app.restaurants.exceptions import (
    DuplicateGooglePlaceIdError,
    DuplicateRestaurantError,
)
from app.restaurants.models import Restaurant
from app.utils.geo_utils import calculate_distance_km, validate_coordinates
from app.utils.service_level_detector import ServiceLevel, ServiceLevelDetector


def normalize_service_level_value(value: str) -> str | None:
    """
    Normalize service level value to enum format.

    Converts display names like 'Casual Dining' to enum values like 'casual_dining'.
    Also handles already-normalized values and validates them.

    Args:
        value: Service level value (display name or enum value)

    Returns:
        Normalized enum value or None if invalid
    """
    if not value or not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    # Mapping from display names to enum values
    display_to_enum = {
        "Fine Dining": ServiceLevel.FINE_DINING.value,
        "Casual Dining": ServiceLevel.CASUAL_DINING.value,
        "Fast Casual": ServiceLevel.FAST_CASUAL.value,
        "Quick Service": ServiceLevel.QUICK_SERVICE.value,
        "Unknown": ServiceLevel.UNKNOWN.value,
        # Also handle some variations
        "Fine": ServiceLevel.FINE_DINING.value,
        "Casual": ServiceLevel.CASUAL_DINING.value,
        "Fast": ServiceLevel.FAST_CASUAL.value,
        "Quick": ServiceLevel.QUICK_SERVICE.value,
    }

    # Check if it's already an enum value (validate it)
    valid_enum_values = {level.value for level in ServiceLevel}
    if value in valid_enum_values:
        return value

    # Try exact match with display names (case-insensitive)
    for display_name, enum_value in display_to_enum.items():
        if value.lower() == display_name.lower():
            return enum_value

    # Try partial matches for flexibility
    value_lower = value.lower()
    if "fine" in value_lower or "upscale" in value_lower:
        return ServiceLevel.FINE_DINING.value
    elif "casual" in value_lower and "fast" not in value_lower:
        return ServiceLevel.CASUAL_DINING.value
    elif "fast" in value_lower or "counter" in value_lower:
        return ServiceLevel.FAST_CASUAL.value
    elif "quick" in value_lower or "takeout" in value_lower or "drive" in value_lower:
        return ServiceLevel.QUICK_SERVICE.value

    # Return None for invalid values (will be handled by validation)
    return None


def recalculate_restaurant_statistics(user_id: int) -> None:
    """Recalculate statistics for all restaurants belonging to a user.

    This function should be called whenever expenses are created, updated, or deleted
    to ensure restaurant statistics are up to date.

    Args:
        user_id: The ID of the user whose restaurant statistics should be recalculated
    """
    # Get all restaurants for the user with their current statistics
    stmt = (
        select(
            Restaurant,
            func.count(Expense.id).label("visit_count"),
            func.coalesce(func.sum(Expense.amount), 0).label("total_spent"),
            func.max(Expense.date).label("last_visit"),
            func.coalesce(
                case(
                    (
                        func.sum(Expense.party_size).isnot(None) & (func.sum(Expense.party_size) > 0),
                        func.sum(Expense.amount) / func.sum(Expense.party_size),
                    ),
                    else_=None,
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

    result = db.session.execute(stmt).all()

    # Update each restaurant with new statistics
    for row in result:
        restaurant = row.Restaurant
        restaurant.visit_count = row.visit_count
        restaurant.total_spent = float(row.total_spent) if row.total_spent else 0.0
        restaurant.last_visit = row.last_visit
        restaurant.avg_price_per_person = float(row.avg_price_per_person) if row.avg_price_per_person else 0.0

    db.session.commit()


def get_restaurant_filters(args: dict[str, Any]) -> dict[str, Any]:
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


def get_restaurants_with_stats(user_id: int, args: dict[str, Any]) -> tuple[list, dict]:
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
                case(
                    (
                        func.sum(Expense.party_size).isnot(None) & (func.sum(Expense.party_size) > 0),
                        func.sum(Expense.amount) / func.sum(Expense.party_size),
                    ),
                    else_=None,
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
        restaurant_obj = row[0]
        restaurant = restaurant_obj.__dict__.copy()
        # Remove SQLAlchemy instance state
        restaurant.pop("_sa_instance_state", None)
        # Add the computed address property and individual address lines
        restaurant["address"] = restaurant_obj.address
        restaurant["address_line_1"] = restaurant_obj.address_line_1
        restaurant["address_line_2"] = restaurant_obj.address_line_2
        # Add the aggregated fields
        restaurant.update(
            {
                "visit_count": row.visit_count,
                "total_spent": float(row.total_spent) if row.total_spent else 0.0,
                "last_visit": row.last_visit,
                "avg_price_per_person": (float(row.avg_price_per_person) if row.avg_price_per_person else 0.0),
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


def _apply_search_filter(stmt: Select, search_term: str) -> Select:
    """Apply search filter to the query."""
    if not search_term:
        return stmt

    search_pattern = f"%{search_term}%"
    return stmt.where(
        or_(
            Restaurant.name.ilike(search_pattern),
            Restaurant.address_line_1.ilike(search_pattern),
            Restaurant.address_line_2.ilike(search_pattern),
            Restaurant.city.ilike(search_pattern),
            Restaurant.state.ilike(search_pattern),
            Restaurant.notes.ilike(search_pattern),
            Restaurant.cuisine.ilike(search_pattern),
        )
    )


def _apply_rating_filters(stmt: Select, rating_min: str, rating_max: str) -> Select:
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


def apply_restaurant_filters(stmt: Select, filters: dict[str, Any]) -> Select:
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


def _get_sort_field(sort_by: str) -> Any | None:
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
                    (
                        Expense.party_size.isnot(None) & (Expense.party_size > 1),
                        Expense.amount / Expense.party_size,
                    ),
                    else_=None,
                )
            ),
            0,
        ),
        "created_at": Restaurant.created_at,
    }
    return sort_mapping.get(sort_by)


def apply_restaurant_sorting(stmt: Select, sort_by: str, sort_order: str) -> Select:
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


def get_filter_options(user_id: int) -> dict[str, Any]:
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


def restaurant_exists(user_id: int, name: str, city: str, google_place_id: str | None = None) -> Restaurant | None:
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
    stmt = select(Restaurant).where(
        Restaurant.user_id == user_id,
        func.lower(Restaurant.name) == func.lower(name),
    )
    if city:
        stmt = stmt.where(func.lower(Restaurant.city) == func.lower(city))
    return db.session.scalar(stmt)


def validate_restaurant_uniqueness(
    user_id: int, name: str, city: str, google_place_id: str | None = None, exclude_id: int | None = None
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
    )
    if city:
        existing_stmt = existing_stmt.where(func.lower(Restaurant.city) == func.lower(city))
    if exclude_id:
        existing_stmt = existing_stmt.where(Restaurant.id != exclude_id)

    existing_by_name_city = db.session.scalar(existing_stmt)
    if existing_by_name_city:
        raise DuplicateRestaurantError(name, city, existing_by_name_city)


def create_restaurant(user_id: int, form: Any) -> tuple[Restaurant, bool]:
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
        # Reset session state to avoid PendingRollbackError
        # This is necessary because after rollback, the session is in an invalid state
        db.session.expunge_all()  # Remove all objects from session

        # Handle database constraint violations
        if "uix_restaurant_google_place_id_user" in str(e.orig):
            # Re-query to get the existing restaurant for the exception
            existing = db.session.scalar(
                select(Restaurant).where(
                    Restaurant.user_id == user_id,
                    Restaurant.google_place_id == google_place_id_value,
                )
            )
            if existing and google_place_id_value:
                raise DuplicateGooglePlaceIdError(google_place_id_value, existing)
        elif "uix_restaurant_name_city_user" in str(e.orig):
            # Re-query to get the existing restaurant for the exception
            stmt = select(Restaurant).where(
                Restaurant.user_id == user_id,
                func.lower(Restaurant.name) == func.lower(name),
            )
            if city:
                stmt = stmt.where(func.lower(Restaurant.city) == func.lower(city))
            existing = db.session.scalar(stmt)
            if existing:
                raise DuplicateRestaurantError(name, city, existing)
        # Re-raise original error if we can't handle it
        raise


def _process_form_data_for_update(form: Any) -> dict[str, Any]:
    """Process form data for restaurant update, converting types appropriately.

    Args:
        form: Form containing the updated restaurant data

    Returns:
        Dictionary of processed form data
    """
    form_data: dict[str, Any] = {}
    numeric_fields = {"rating"}
    boolean_fields = {"is_chain"}

    for field in form:
        if field.name in numeric_fields:
            # Convert empty strings to None for numeric fields
            if field.data and str(field.data).strip():
                try:
                    form_data[field.name] = float(field.data)
                except (ValueError, TypeError):
                    form_data[field.name] = None
            else:
                form_data[field.name] = None
        elif field.name in boolean_fields:
            # Ensure boolean fields are properly converted
            form_data[field.name] = bool(field.data) if field.data is not None else False
        else:
            # For all other fields, use the value as is or empty string
            form_data[field.name] = field.data if field.data is not None else ""

    return form_data


def _apply_form_data_to_restaurant(restaurant: Restaurant, form_data: dict[str, Any]) -> None:
    """Apply processed form data to restaurant object.

    Args:
        restaurant: Restaurant object to update
        form_data: Dictionary of processed form data
    """
    for key, value in form_data.items():
        if hasattr(restaurant, key):
            setattr(restaurant, key, value)


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

    form_data = _process_form_data_for_update(form)
    _apply_form_data_to_restaurant(restaurant, form_data)

    # Handle service level auto-detection for updates
    _auto_detect_service_level(restaurant)

    # Format cuisine type for consistency
    if hasattr(restaurant, "cuisine") and restaurant.cuisine:
        restaurant.cuisine = format_cuisine_type(restaurant.cuisine)

    db.session.commit()
    return restaurant


def _validate_restaurant_row(row: dict[str, Any]) -> tuple[bool, str]:
    """Validate a single restaurant row from CSV.

    Args:
        row: Dictionary containing restaurant data

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not row.get("name", "").strip():
        return False, "Name is required"
    # City is optional - restaurants can exist without city information
    return True, ""


# Helper function to safely convert to float
def safe_import_float(value: Any) -> float | None:
    if not value or str(value).strip() == "":
        return None
    try:
        return float(str(value).strip())
    except (ValueError, TypeError):
        return None


# Helper function to safely convert to bool
def safe_import_bool(value: Any) -> bool | None:
    if not value or str(value).strip() == "":
        return None
    return str(value).strip().lower() in ("true", "1", "yes", "on")


# Helper function to safely convert to int
def safe_import_int(value: Any) -> int | None:
    if not value or str(value).strip() == "":
        return None
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def _find_existing_restaurant(
    name: str, address: str | None, city: str | None, google_place_id: str | None, user_id: int
) -> Restaurant | None:
    """Find existing restaurant using smart duplicate detection.

    Checks for duplicates by:
    1. Google Place ID (if provided)
    2. Name + Address combination
    3. Name + City combination (as fallback) - case-insensitive

    Note: This only checks committed database records. Uses expire_on_commit=False
    to ensure we query the database directly, not cached session objects.

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
        stmt = select(Restaurant).where(
            Restaurant.user_id == user_id,
            Restaurant.google_place_id == google_place_id,
        )
        existing = db.session.scalar(stmt)
        if existing:
            return existing

    # Strategy 2: Match by name + address (if both provided) - case-insensitive
    if name and address:
        stmt = select(Restaurant).where(
            Restaurant.user_id == user_id,
            func.lower(Restaurant.name) == func.lower(name),
            func.lower(Restaurant.address_line_1) == func.lower(address),
        )
        existing = db.session.scalar(stmt)
        if existing:
            return existing

    # Strategy 3: Match by name + city (existing constraint) - case-insensitive
    # Only check this if city is provided and we haven't found a match yet
    if name and city:
        stmt = select(Restaurant).where(
            Restaurant.user_id == user_id,
            func.lower(Restaurant.name) == func.lower(name),
            func.lower(Restaurant.city) == func.lower(city),
        )
        existing = db.session.scalar(stmt)
        if existing:
            return existing

    return None


def _process_restaurant_row(row: dict, user_id: int) -> tuple[bool, str, Restaurant | None]:
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

        # Create new restaurant with normalized service level
        service_level_raw = row.get("service_level", "").strip() or None
        service_level_normalized = normalize_service_level_value(service_level_raw) if service_level_raw else None

        restaurant = Restaurant(
            user_id=user_id,
            name=name,
            city=city,
            address_line_1=address,
            state=row.get("state", "").strip() or None,
            postal_code=row.get("postal_code", "").strip() or None,
            country=row.get("country", "").strip() or None,
            phone=row.get("phone", "").strip() or None,
            email=row.get("email", "").strip() or None,
            website=row.get("website", "").strip() or None,
            cuisine=row.get("cuisine", "").strip() or None,
            service_level=service_level_normalized,
            rating=safe_import_float(row.get("rating")),
            price_level=safe_import_int(row.get("price_level")),
            primary_type=row.get("primary_type", "").strip() or None,
            latitude=safe_import_float(row.get("latitude")),
            longitude=safe_import_float(row.get("longitude")),
            is_chain=safe_import_bool(row.get("is_chain")),
            google_place_id=google_place_id,
            notes=row.get("notes", "").strip() or None,
        )
        return True, "", restaurant

    except Exception as e:
        return False, str(e), None


def _process_csv_file(file: FileStorage) -> tuple[bool, str, csv.DictReader | None]:
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


def _handle_integrity_error(e: IntegrityError, row: dict, line_num: int) -> tuple[str, bool]:
    """Handle IntegrityError and return error message and whether it was a duplicate.

    Args:
        e: The IntegrityError exception
        row: The CSV row data
        line_num: Line number in CSV file

    Returns:
        Tuple of (error_message, is_duplicate)
    """
    error_str = str(e.orig)
    if "uix_restaurant_name_city_user" in error_str:
        name = row.get("name", "").strip()
        city = row.get("city", "").strip() or "Unknown"
        return f"Line {line_num}: Duplicate restaurant '{name}' in '{city}' already exists", True
    if "uix_restaurant_google_place_id_user" in error_str:
        google_place_id = row.get("google_place_id", "").strip() or "Unknown"
        return f"Line {line_num}: Duplicate Google Place ID '{google_place_id}' already exists", True
    return f"Line {line_num}: Database constraint violation - {str(e)}", False


def _add_restaurant_with_savepoint(
    restaurant: Restaurant, savepoint: Any, batch_size: int, success_count: int
) -> tuple[bool, IntegrityError | None]:
    """Add a restaurant using a savepoint for error isolation.

    Args:
        restaurant: Restaurant to add
        savepoint: SQLAlchemy savepoint
        batch_size: Batch size for commits
        success_count: Current success count

    Returns:
        Tuple of (success, IntegrityError_or_None)
    """
    try:
        db.session.add(restaurant)
        db.session.flush()  # Flush to catch errors early
        savepoint.commit()  # Commit the savepoint

        # Commit main transaction in batches
        if (success_count + 1) % batch_size == 0:
            db.session.commit()

        return True, None
    except IntegrityError as e:
        savepoint.rollback()
        db.session.expunge(restaurant)  # Remove the failed restaurant
        return False, e


def _process_import_row(
    row: dict, user_id: int, line_num: int, savepoint: Any, batch_size: int, success_count: int
) -> tuple[int, int, list[str]]:
    """Process a single row from the CSV import.

    Args:
        row: CSV row data
        user_id: User ID
        line_num: Line number in CSV
        savepoint: SQLAlchemy savepoint
        batch_size: Batch size for commits
        success_count: Current success count

    Returns:
        Tuple of (success_delta, skipped_delta, errors)
    """
    success_delta = 0
    skipped_delta = 0
    errors = []

    try:
        success, message, restaurant = _process_restaurant_row(row, user_id)

        if success:
            if restaurant:
                add_success, error = _add_restaurant_with_savepoint(restaurant, savepoint, batch_size, success_count)
                if add_success:
                    success_delta = 1
                else:
                    if error:
                        error_msg, is_duplicate = _handle_integrity_error(error, row, line_num)
                        errors.append(error_msg)
                        if is_duplicate:
                            skipped_delta = 1
            else:
                savepoint.commit()  # Commit empty savepoint
                skipped_delta = 1
        else:
            savepoint.rollback()
            errors.append(f"Line {line_num}: {message}")
    except IntegrityError as e:
        savepoint.rollback()
        error_msg, is_duplicate = _handle_integrity_error(e, row, line_num)
        errors.append(error_msg)
        if is_duplicate:
            skipped_delta = 1
    except Exception as e:
        savepoint.rollback()
        errors.append(f"Line {line_num}: Unexpected error - {str(e)}")

    return success_delta, skipped_delta, errors


def _import_restaurants_from_reader(csv_reader: csv.DictReader, user_id: int) -> tuple[int, int, list[str]]:
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
    batch_size = 50  # Commit in batches to avoid losing progress on errors

    # Use no_autoflush to prevent premature flushes that could cause IntegrityError
    with db.session.no_autoflush:
        for i, row in enumerate(csv_reader, 2):  # Start from line 2 (1-based + header)
            savepoint = db.session.begin_nested()
            success_delta, skipped_delta, row_errors = _process_import_row(
                row, user_id, i, savepoint, batch_size, success_count
            )
            success_count += success_delta
            skipped_count += skipped_delta
            errors.extend(row_errors)

    # Commit any remaining uncommitted restaurants
    if success_count > 0 and success_count % batch_size != 0:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            errors.append(f"Error committing final batch: {str(e)}")

    return success_count, skipped_count, errors


def _generate_import_result(success_count: int, skipped_count: int, errors: list[str]) -> tuple[bool, dict[str, Any]]:
    """Generate the result of the import operation.

    Args:
        success_count: Number of successfully imported restaurants
        skipped_count: Number of skipped duplicate restaurants
        errors: List of error messages

    Returns:
        Tuple of (success, result_data)

    Note:
        Commits are handled in _import_restaurants_from_reader, so no commit needed here.
    """

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


def import_restaurants_from_csv(file: FileStorage, user_id: int) -> tuple[bool, dict[str, Any]]:
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
        if csv_reader is None:
            return False, {"message": "Failed to process CSV file", "has_errors": True, "error_details": []}
        success_count, skipped_count, errors = _import_restaurants_from_reader(csv_reader, user_id)

        # Generate the result data
        return _generate_import_result(success_count, skipped_count, errors)

    except Exception as e:
        # Ensure session is properly rolled back and reset
        try:
            db.session.rollback()
            db.session.expunge_all()  # Reset session state after rollback
        except Exception:
            # If rollback fails, create a new session
            db.session.close()
        error_msg = f"Error processing CSV file: {str(e)}"
        return False, {"message": error_msg, "has_errors": True, "error_details": [error_msg]}


def export_restaurants_for_user(user_id: int) -> list[dict[str, Any]]:
    """Get all restaurants for a user in a format suitable for export.

    Args:
        user_id: The ID of the user whose restaurants to export

    Returns:
        A list of dictionaries containing restaurant data
    """
    restaurants = db.session.scalars(
        select(Restaurant).where(Restaurant.user_id == user_id).order_by(Restaurant.name)
    ).all()

    def safe_float(value: Any) -> float | None:
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
            "price_level": r.price_level if r.price_level is not None else "",
            "primary_type": r.primary_type or "",
            "latitude": safe_float(r.latitude) if r.latitude is not None else "",
            "longitude": safe_float(r.longitude) if r.longitude is not None else "",
            "is_chain": bool(r.is_chain) if r.is_chain is not None else "",
            "google_place_id": r.google_place_id or "",
            "notes": r.notes or "",
            "created_at": r.created_at.isoformat() if r.created_at else "",
            "updated_at": r.updated_at.isoformat() if r.updated_at else "",
        }
        for r in restaurants
    ]


def get_restaurants_for_user(user_id: int) -> list[Restaurant]:
    """
    Get all restaurants for a specific user.

    Args:
        user_id: ID of the current user

    Returns:
        List of restaurants belonging to the user
    """
    restaurants = Restaurant.query.filter_by(user_id=user_id).order_by(Restaurant.name).all()
    from typing import cast

    return cast(list[Restaurant], list(restaurants))


def create_restaurant_for_user(user_id: int, data: dict[str, Any]) -> Restaurant:
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
        located_within=data.get("located_within"),
        address_line_1=data.get("address_line_1"),
        address_line_2=data.get("address_line_2"),
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
        price_level=data.get("price_level"),
        primary_type=data.get("primary_type"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        is_chain=data.get("is_chain", False),
        notes=data.get("notes"),
    )

    db.session.add(restaurant)
    db.session.commit()

    return restaurant


def update_restaurant_for_user(restaurant: Restaurant, data: dict[str, Any]) -> Restaurant:
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
        "located_within",
        "address_line_1",
        "address_line_2",
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
        "price_level",
        "primary_type",
        "latitude",
        "longitude",
        "is_chain",
        "notes",
    ]

    for field in updateable_fields:
        if field in data:
            setattr(restaurant, field, data[field])

    db.session.commit()

    return restaurant


def get_restaurant_for_user(restaurant_id: int, user_id: int) -> Restaurant | None:
    """Get a restaurant by ID if it belongs to the user."""
    return db.session.scalar(select(Restaurant).where(Restaurant.id == restaurant_id, Restaurant.user_id == user_id))


def delete_restaurant_by_id(restaurant_id: int, user_id: int) -> tuple[bool, str]:
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
                return (
                    True,
                    f"Restaurant and {expense_count} associated expenses deleted successfully.",
                )
        else:
            # No expenses, just delete the restaurant
            db.session.delete(restaurant)
            db.session.commit()
            return True, "Restaurant deleted successfully."

    except Exception as e:
        db.session.rollback()
        raise e


# Note: This logic could potentially be consolidated with get_restaurants_with_stats in future refactoring
def calculate_expense_stats(restaurant_id: int, user_id: int) -> dict[str, Any]:
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


def detect_service_level_from_google_data(google_data: dict[str, Any]) -> tuple[str, float]:
    """
    Centralized function to detect service level from Google Places data using GooglePlacesService.

    Args:
        google_data: Dictionary containing Google Places API response data

    Returns:
        Tuple of (service_level, confidence_score)
    """
    try:
        from app.services.google_places_service import get_google_places_service

        places_service = get_google_places_service()
        return places_service.detect_service_level_from_data(google_data)
    except Exception:
        return "unknown", 0.0


def validate_restaurant_service_level(
    current_data: dict, google_service_level: str, confidence: float
) -> tuple[bool, str, str | None]:
    """
    Validate restaurant service level against Google data.

    Args:
        current_data: Current form data dictionary to validate
        google_service_level: Service level detected from Google
        confidence: Confidence score of the detection

    Returns:
        Tuple of (has_mismatch: bool, mismatch_message: str, suggested_fix: Optional[str])
    """
    # Ensure confidence is a float for comparison
    # confidence is already typed as float, but ensure it's actually a float value
    confidence = float(confidence)

    if google_service_level == "unknown" or confidence <= 0.3:
        return False, "", None

    current_service_level = current_data.get("service_level")
    if current_service_level and current_service_level != google_service_level:
        return (
            True,
            f"Service Level: '{current_service_level}' vs Google: '{google_service_level}' (confidence: {confidence:.2f})",
            google_service_level,
        )
    elif not current_service_level:
        return (
            True,
            f"Service Level: Not set vs Google: '{google_service_level}' (confidence: {confidence:.2f})",
            google_service_level,
        )

    return False, "", None


def _auto_detect_service_level(restaurant: Restaurant) -> None:
    """
    Auto-detect service level for a restaurant if not set.

    Args:
        restaurant: Restaurant instance to update
    """
    # Service level auto-detection is now handled by the centralized field mapping
    # in the routes.py file when Google Places data is fetched


def get_service_level_display_info(service_level: str) -> dict[str, str]:
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


def _validate_location_search_params(latitude: float, longitude: float, radius_km: float, limit: int) -> None:
    """Validate location search parameters.

    Args:
        latitude: Center latitude for search
        longitude: Center longitude for search
        radius_km: Search radius in kilometers
        limit: Maximum number of results to return

    Raises:
        ValueError: If any parameter is invalid
    """
    if not validate_coordinates(latitude, longitude):
        raise ValueError("Invalid coordinates provided")

    if radius_km <= 0:
        raise ValueError("Radius must be positive")

    if limit <= 0:
        raise ValueError("Limit must be positive")


def _create_restaurant_dict_with_distance(restaurant: Restaurant, distance_km: float) -> dict[str, Any]:
    """Create a restaurant dictionary with distance information.

    Args:
        restaurant: The restaurant object
        distance_km: Distance from search center in kilometers

    Returns:
        Dictionary with restaurant data and distance information
    """
    return {
        "id": restaurant.id,
        "name": restaurant.name,
        "address": restaurant.address,
        "city": restaurant.city,
        "state": restaurant.state,
        "cuisine": restaurant.cuisine,
        "service_level": restaurant.service_level,
        "rating": restaurant.rating,
        "price_level": restaurant.price_level,
        "latitude": restaurant.latitude,
        "longitude": restaurant.longitude,
        "distance_km": round(distance_km, 2),
        "distance_miles": round(distance_km * 0.621371, 2),
    }


def _get_distance_for_sorting(restaurant_dict: dict[str, Any]) -> float:
    """Extract distance value for sorting.

    Args:
        restaurant_dict: Restaurant dictionary with distance_km key

    Returns:
        Distance as float, or 0.0 if invalid
    """
    distance_val = restaurant_dict.get("distance_km")
    if isinstance(distance_val, (int, float)):
        return float(distance_val)
    if isinstance(distance_val, str):
        try:
            return float(distance_val)
        except (ValueError, TypeError):
            return 0.0
    return 0.0


def search_restaurants_by_location(
    user_id: int, latitude: float, longitude: float, radius_km: float = 10.0, limit: int = 50
) -> list[dict[str, Any]]:
    """
    Search for restaurants within a specified radius of a location.

    Args:
        user_id: ID of the user whose restaurants to search
        latitude: Center latitude for search
        longitude: Center longitude for search
        radius_km: Search radius in kilometers (default: 10km)
        limit: Maximum number of results to return (default: 50)

    Returns:
        List of restaurant dictionaries with distance information
    """
    _validate_location_search_params(latitude, longitude, radius_km, limit)

    # Get all restaurants for the user that have coordinates
    restaurants = db.session.scalars(
        select(Restaurant).where(
            Restaurant.user_id == user_id,
            Restaurant.latitude.isnot(None),
            Restaurant.longitude.isnot(None),
        )
    ).all()

    results = []

    for restaurant in restaurants:
        # Calculate distance (skip if coordinates are missing)
        if restaurant.latitude is None or restaurant.longitude is None:
            continue
        distance = calculate_distance_km(latitude, longitude, restaurant.latitude, restaurant.longitude)

        # Check if within radius
        if distance <= radius_km:
            restaurant_dict = _create_restaurant_dict_with_distance(restaurant, distance)
            results.append(restaurant_dict)

    # Sort by distance (closest first)
    results.sort(key=_get_distance_for_sorting)

    # Apply limit
    return results[:limit]


def get_restaurants_with_coordinates(user_id: int) -> list[Restaurant]:
    """
    Get all restaurants for a user that have coordinates stored.

    Args:
        user_id: ID of the user

    Returns:
        List of restaurants with coordinates
    """
    return list(
        db.session.scalars(
            select(Restaurant)
            .where(
                Restaurant.user_id == user_id,
                Restaurant.latitude.isnot(None),
                Restaurant.longitude.isnot(None),
            )
            .order_by(Restaurant.name)
        ).all()
    )
