from __future__ import annotations

from typing import Any, Optional, Tuple, cast

from flask import Response, current_app, jsonify, request
from flask_login import current_user, login_required
from marshmallow import ValidationError

from app.auth.models import User
from app.categories import services as category_services
from app.expenses import services as expense_services
from app.restaurants import services as restaurant_services
from app.restaurants.models import Restaurant

from . import bp, validate_api_csrf
from .schemas import CategorySchema, ExpenseSchema, RestaurantSchema

# Schema instances
expense_schema = ExpenseSchema()
expenses_schema = ExpenseSchema(many=True)
restaurant_schema = RestaurantSchema()
restaurants_schema = RestaurantSchema(many=True)
category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)


def _get_current_user() -> User:
    """Get the current authenticated user with proper typing."""
    return cast(User, current_user._get_current_object())


def _create_api_response(
    data: Any = None, message: str = "Success", status: str = "success", code: int = 200
) -> Tuple[Response, int]:
    """Create a standardized API response."""
    response_data = {"status": status, "message": message}
    if data is not None:
        response_data["data"] = data
    return jsonify(response_data), code


def _handle_validation_error(error: ValidationError) -> Tuple[Response, int]:
    """Handle validation errors consistently."""
    return (
        jsonify({"status": "error", "message": "Validation failed", "errors": error.messages}),
        400,
    )


def _handle_service_error(error: Exception, operation: str) -> Tuple[Response, int]:
    """Handle service layer errors consistently."""
    current_app.logger.error(f"Error in {operation}: {str(error)}", exc_info=True)
    return (
        jsonify({"status": "error", "message": f"Failed to {operation}", "error": str(error)}),
        500,
    )


# Health Check
@bp.route("/health")
def health_check() -> Response:
    """API Health Check"""
    return jsonify({"status": "healthy"})


# Version Information
@bp.route("/version")
def version_info() -> Tuple[Response, int]:
    """Get application version information.

    Returns:
        JSON response with version from git tags and build timestamp
    """
    try:
        from app._version import __build_timestamp__, __version__

        version_data = {
            "version": __version__,
            "build_timestamp": __build_timestamp__,
        }
        return _create_api_response(data=version_data, message="Version information retrieved successfully")
    except ImportError as e:
        current_app.logger.warning(f"Could not import version information: {e}")
        version_data = {
            "version": "unknown",
            "build_timestamp": "Not set",
        }
        return _create_api_response(data=version_data, message="Version information retrieved successfully")
    except Exception as e:
        current_app.logger.error(f"Error retrieving version information: {e}")
        return _handle_service_error(e, "retrieve version information")


# Cuisine Data
@bp.route("/cuisines")
def get_cuisines() -> Response:
    """Get cuisine data for frontend consumption.

    Returns:
        JSON response with cuisine names, colors, icons, and Google Places mapping
    """
    import json
    import os

    try:
        # Load from static JSON file
        json_path = os.path.join(current_app.static_folder, "data", "cuisines.json")
        with open(json_path, "r") as f:
            cuisine_data = json.load(f)

        return _create_api_response(data=cuisine_data, message="Cuisine data retrieved successfully")
    except Exception as e:
        current_app.logger.error(f"Error loading cuisine data: {e}")
        return _create_api_response(message="Failed to load cuisine data", status="error", code=500)


# Generic CRUD operations for expenses
@bp.route("/expenses", methods=["GET"])
@login_required
def get_expenses() -> Response:
    """Get all expenses for the current user."""
    try:
        user = _get_current_user()
        expenses = expense_services.get_expenses_for_user(user.id)
        return _create_api_response(data=expenses_schema.dump(expenses), message="Expenses retrieved successfully")
    except Exception as e:
        return _handle_service_error(e, "retrieve expenses")


@bp.route("/expenses", methods=["POST"])
@login_required
@validate_api_csrf
def create_expense() -> Tuple[Response, int]:
    """Create a new expense."""
    try:
        user = _get_current_user()
        data = expense_schema.load(request.get_json())
        expense = expense_services.create_expense_for_user(user.id, data)
        return _create_api_response(data=expense_schema.dump(expense), message="Expense created successfully", code=201)
    except ValidationError as e:
        return _handle_validation_error(e)
    except Exception as e:
        return _handle_service_error(e, "create expense")


@bp.route("/expenses/<int:expense_id>", methods=["GET"])
@login_required
def get_expense(expense_id: int) -> Response:
    """Get a single expense."""
    try:
        user = _get_current_user()
        expense = expense_services.get_expense_by_id_for_user(expense_id, user.id)
        if not expense:
            return jsonify({"status": "error", "message": "Expense not found"}), 404
        return _create_api_response(data=expense_schema.dump(expense), message="Expense retrieved successfully")
    except Exception as e:
        return _handle_service_error(e, "retrieve expense")


@bp.route("/expenses/<int:expense_id>", methods=["PUT"])
@login_required
@validate_api_csrf
def update_expense(expense_id: int) -> Tuple[Response, int]:
    """Update an expense."""
    try:
        user = _get_current_user()
        expense = expense_services.get_expense_by_id_for_user(expense_id, user.id)
        if not expense:
            return jsonify({"status": "error", "message": "Expense not found"}), 404

        data = expense_schema.load(request.get_json())
        updated_expense = expense_services.update_expense_for_user(expense, data)
        return _create_api_response(data=expense_schema.dump(updated_expense), message="Expense updated successfully")
    except ValidationError as e:
        return _handle_validation_error(e)
    except Exception as e:
        return _handle_service_error(e, "update expense")


@bp.route("/expenses/<int:expense_id>", methods=["DELETE"])
@login_required
@validate_api_csrf
def delete_expense(expense_id: int) -> Tuple[Response, int]:
    """Delete an expense."""
    try:
        user = _get_current_user()
        expense = expense_services.get_expense_by_id_for_user(expense_id, user.id)
        if not expense:
            return jsonify({"status": "error", "message": "Expense not found"}), 404

        expense_services.delete_expense_for_user(expense)
        return _create_api_response(message="Expense deleted successfully", code=204)
    except Exception as e:
        return _handle_service_error(e, "delete expense")


# Generic CRUD operations for restaurants
@bp.route("/restaurants", methods=["GET"])
@login_required
def get_restaurants() -> Response:
    """Get all restaurants for the current user."""
    try:
        user = _get_current_user()
        restaurants = restaurant_services.get_restaurants_for_user(user.id)
        return _create_api_response(
            data=restaurants_schema.dump(restaurants), message="Restaurants retrieved successfully"
        )
    except Exception as e:
        return _handle_service_error(e, "retrieve restaurants")


@bp.route("/restaurants", methods=["POST"])
@login_required
@validate_api_csrf
def create_restaurant() -> Tuple[Response, int]:
    """Create a new restaurant."""
    try:
        user = _get_current_user()
        data = restaurant_schema.load(request.get_json())
        restaurant = restaurant_services.create_restaurant_for_user(user.id, data)
        return _create_api_response(
            data=restaurant_schema.dump(restaurant),
            message="Restaurant created successfully",
            code=201,
        )
    except ValidationError as e:
        return _handle_validation_error(e)
    except Exception as e:
        return _handle_service_error(e, "create restaurant")


@bp.route("/restaurants/<int:restaurant_id>", methods=["GET"])
@login_required
def get_restaurant(restaurant_id: int) -> Response:
    """Get a single restaurant."""
    try:
        user = _get_current_user()
        restaurant = restaurant_services.get_restaurant_for_user(restaurant_id, user.id)
        if not restaurant:
            return jsonify({"status": "error", "message": "Restaurant not found"}), 404
        return _create_api_response(
            data=restaurant_schema.dump(restaurant), message="Restaurant retrieved successfully"
        )
    except Exception as e:
        return _handle_service_error(e, "retrieve restaurant")


@bp.route("/restaurants/<int:restaurant_id>", methods=["PUT"])
@login_required
@validate_api_csrf
def update_restaurant(restaurant_id: int) -> Tuple[Response, int]:
    """Update a restaurant."""
    try:
        user = _get_current_user()
        restaurant = restaurant_services.get_restaurant_for_user(restaurant_id, user.id)
        if not restaurant:
            return jsonify({"status": "error", "message": "Restaurant not found"}), 404

        data = restaurant_schema.load(request.get_json())
        updated_restaurant = restaurant_services.update_restaurant_for_user(restaurant, data)
        return _create_api_response(
            data=restaurant_schema.dump(updated_restaurant),
            message="Restaurant updated successfully",
        )
    except ValidationError as e:
        return _handle_validation_error(e)
    except Exception as e:
        return _handle_service_error(e, "update restaurant")


@bp.route("/restaurants/<int:restaurant_id>", methods=["DELETE"])
@login_required
@validate_api_csrf
def delete_restaurant(restaurant_id: int) -> Tuple[Response, int]:
    """Delete a restaurant."""
    try:
        user = _get_current_user()
        success, message = restaurant_services.delete_restaurant_by_id(restaurant_id, user.id)

        if not success:
            return jsonify({"status": "error", "message": message}), 404

        return _create_api_response(message=message, code=204)
    except Exception as e:
        return _handle_service_error(e, "delete restaurant")


@bp.route("/restaurants/check", methods=["GET"])
@login_required
def check_restaurant_exists() -> Response:
    """Check if a restaurant already exists for the current user by Google Place ID."""
    place_id = request.args.get("place_id")
    if not place_id:
        return jsonify({"status": "error", "message": "Missing place_id parameter"}), 400

    try:
        user = _get_current_user()
        from app.restaurants.models import Restaurant

        existing_restaurant = Restaurant.query.filter_by(google_place_id=place_id, user_id=user.id).first()

        result = {
            "exists": bool(existing_restaurant),
            "restaurant_id": existing_restaurant.id if existing_restaurant else None,
            "name": existing_restaurant.name if existing_restaurant else None,
        }

        return _create_api_response(data=result, message="Restaurant check completed successfully")

    except Exception as e:
        return _handle_service_error(e, "check restaurant existence")


@bp.route("/restaurants/validate", methods=["POST"])
@login_required
@validate_api_csrf
def validate_restaurant() -> Tuple[Response, int]:
    """Validate restaurant information using Google Places API."""
    try:
        # Validate input data
        validation_error = _validate_restaurant_input()
        if validation_error:
            return validation_error

        # Get and validate restaurant
        restaurant, place_id_to_use = _get_and_validate_restaurant()
        if not restaurant:
            return _create_api_response(message="Restaurant not found", status="error", code=404)

        # Validate with Google Places API
        validation_result = _validate_restaurant_with_google_api(place_id_to_use)
        if not validation_result.get("valid"):
            return _create_api_response(data=validation_result, message="Validation failed", status="error", code=400)

        # Process validation results
        return _process_validation_results(restaurant, validation_result)

    except Exception as e:
        current_app.logger.error(f"Error validating restaurant: {e}")
        return _create_api_response(message=f"Failed to validate restaurant: {str(e)}", status="error", code=500)


def _validate_restaurant_input() -> Optional[Tuple[Response, int]]:
    """Validate input parameters for restaurant validation."""
    data = request.get_json()
    if not data:
        return _create_api_response(message="JSON data required", status="error", code=400)

    restaurant_id = data.get("restaurant_id")
    if not restaurant_id:
        return _create_api_response(message="Restaurant ID is required", status="error", code=400)

    form_data = data.get("form_data")
    if not form_data:
        return _create_api_response(message="form_data is required for validation", status="error", code=400)

    return None


def _get_and_validate_restaurant() -> Tuple[Optional[Restaurant], Optional[str]]:
    """Get restaurant and validate user permissions."""
    data = request.get_json()
    restaurant_id = data.get("restaurant_id")
    google_place_id = data.get("google_place_id", "").strip()

    restaurant = Restaurant.query.get(restaurant_id)

    if not restaurant:
        return None, None

    # Check if user owns this restaurant
    user = _get_current_user()
    if restaurant.user_id != user.id:
        return None, None

    # Use the restaurant's Google Place ID or the one provided
    place_id_to_use = google_place_id or restaurant.google_place_id
    if not place_id_to_use:
        return None, None

    return restaurant, place_id_to_use


def _process_validation_results(restaurant, validation_result) -> Tuple[Response, int]:
    """Process validation results and return response."""
    data = request.get_json()
    form_data = data.get("form_data")
    fix_mismatches = data.get("fix_mismatches", False)

    # Use form data for comparison
    current_data = form_data

    # Check for mismatches
    mismatches, fixes_to_apply = _check_restaurant_mismatches_api(current_data, validation_result)

    # Apply fixes if requested
    if fix_mismatches and fixes_to_apply:
        _apply_restaurant_fixes_api(restaurant, fixes_to_apply)

    # Prepare Google data in the same format for comparison
    google_data = {
        "name": validation_result.get("google_name"),
        "address_line_1": validation_result.get("google_address_line_1"),
        "address_line_2": validation_result.get("google_address_line_2"),
        "city": validation_result.get("google_city"),
        "state": validation_result.get("google_state"),
        "state_long": validation_result.get("google_state_long"),
        "state_short": validation_result.get("google_state_short"),
        "postal_code": validation_result.get("google_postal_code"),
        "country": validation_result.get("google_country"),
        "type": validation_result.get("primary_type"),
        "cuisine": validation_result.get("google_cuisine"),
        "service_level": (
            validation_result.get("google_service_level", [None, 0.0])[0]
            if validation_result.get("google_service_level")
            else None
        ),
        "rating": validation_result.get("google_rating"),
        "price_level": validation_result.get("google_price_level"),
        "phone": validation_result.get("google_phone"),
        "website": validation_result.get("google_website"),
        "description": None,  # Google Places doesn't provide descriptions
    }

    return _create_api_response(
        data={
            "valid": True,
            "mismatches": mismatches,
            "fixes": fixes_to_apply,
            "current_data": current_data,
            "google_data": google_data,
            "restaurant_updated": fix_mismatches and bool(fixes_to_apply),
        },
        message="Restaurant validated successfully",
    )


def _validate_restaurant_with_google_api(google_place_id: str) -> dict:
    """Validate restaurant information using centralized Google Places service.

    Args:
        google_place_id: Google Place ID to validate

    Returns:
        Dictionary with validation results
    """
    try:
        from app.services.google_places_service import get_google_places_service

        places_service = get_google_places_service()
        place = places_service.get_place_details(google_place_id)

        if not place:
            return {
                "valid": False,
                "errors": ["Failed to retrieve place data from Google Places API"],
            }

        # Extract restaurant data using the service
        google_data = places_service.extract_restaurant_data(place)

        return {
            "valid": True,
            "google_name": google_data.get("name"),
            "google_address": google_data.get("formatted_address"),
            "google_address_line_1": google_data.get("address_line_1"),
            "google_address_line_2": google_data.get("address_line_2"),
            "google_city": google_data.get("city"),
            "google_state": google_data.get("state"),
            "google_state_long": google_data.get("state_long"),
            "google_state_short": google_data.get("state_short"),
            "google_postal_code": google_data.get("postal_code"),
            "google_country": google_data.get("country"),
            "google_rating": google_data.get("rating"),
            "google_status": google_data.get("business_status", "OPERATIONAL"),
            "types": google_data.get("types", []),
            "primary_type": google_data.get("primary_type"),
            "google_phone": google_data.get("phone_number"),
            "google_website": google_data.get("website"),
            "google_price_level": google_data.get("price_level"),
            "google_street_address": google_data.get("street_address"),  # Legacy field
            "google_service_level": places_service.detect_service_level_from_data(place),
            "errors": [],
        }

    except ImportError:
        return {"valid": False, "errors": ["Google Places API service not available"]}
    except Exception as e:
        current_app.logger.error(f"Error validating restaurant with place ID {google_place_id}: {str(e)}")
        return {"valid": False, "errors": [f"Unexpected error: {str(e)}"]}


def _check_restaurant_mismatches_api(current_data, validation_result: dict) -> tuple[list[str], dict[str, str]]:
    """Check for mismatches between current data and Google data."""
    mismatches = []
    fixes_to_apply = {}

    # Check name mismatch
    _check_name_mismatch_api(current_data, validation_result, mismatches, fixes_to_apply)

    # Check address mismatches
    _check_address_mismatches_api(current_data, validation_result, mismatches, fixes_to_apply)

    # Check service level mismatch
    _check_service_level_mismatch_api(current_data, validation_result, mismatches, fixes_to_apply)

    # Check state mismatch
    _check_state_mismatch_api(current_data, validation_result, mismatches, fixes_to_apply)

    return mismatches, fixes_to_apply


def _check_name_mismatch_api(current_data, validation_result, mismatches, fixes_to_apply):
    """Check for name mismatch."""
    google_name = validation_result.get("google_name")
    current_name = current_data.get("name")
    if google_name and google_name.lower() != current_name.lower():
        mismatches.append(f"Name: '{current_name}' vs Google: '{google_name}'")
        fixes_to_apply["name"] = google_name


def _check_state_mismatch_api(current_data, validation_result, mismatches, fixes_to_apply):
    """Check for state field mismatches using multiple comparison methods."""
    from app.restaurants.cli import (
        _states_match_directly,
        _states_match_with_us_library,
    )

    google_state = validation_result.get("google_state")
    google_state_long = validation_result.get("google_state_long")
    google_state_short = validation_result.get("google_state_short")
    current_state = current_data.get("state")

    if not ((google_state or google_state_long or google_state_short) and current_state):
        return

    # Check direct string matches first
    if _states_match_directly(current_state, google_state, google_state_long, google_state_short):
        return

    # Try US library matching as fallback
    if _states_match_with_us_library(current_state, google_state, google_state_long, google_state_short):
        return

    # If no matches found, report mismatch
    google_display = google_state_long or google_state or google_state_short or "Unknown"
    mismatches.append(f"State: '{current_state}' vs Google: '{google_display}'")
    fixes_to_apply["state"] = google_state_long or google_state or google_state_short


def _check_address_mismatches_api(current_data, validation_result, mismatches, fixes_to_apply):
    """Check for address field mismatches."""
    address_fields = [
        ("google_address_line_1", "address_line_1", "Address Line 1"),
        ("google_address_line_2", "address_line_2", "Address Line 2"),
        ("google_city", "city", "City"),
        ("google_state", "state", "State"),
        ("google_postal_code", "postal_code", "Postal Code"),
        ("google_country", "country", "Country"),
    ]

    for google_field, current_field, display_name in address_fields:
        google_value = validation_result.get(google_field)
        current_value = current_data.get(current_field)

        if google_value and current_value and google_value.lower() != current_value.lower():
            mismatches.append(f"{display_name}: '{current_value}' vs Google: '{google_value}'")
            fixes_to_apply[current_field] = google_value


def _check_service_level_mismatch_api(current_data, validation_result, mismatches, fixes_to_apply):
    """Check for service level mismatch."""
    google_service_level_data = validation_result.get("google_service_level")
    if google_service_level_data:
        google_service_level, confidence = google_service_level_data
        from app.restaurants.services import validate_restaurant_service_level

        has_mismatch, mismatch_message, suggested_fix = validate_restaurant_service_level(
            current_data, google_service_level, confidence
        )

        if has_mismatch:
            mismatches.append(mismatch_message)
            if suggested_fix:
                fixes_to_apply["service_level"] = suggested_fix


def _apply_restaurant_fixes_api(restaurant, fixes_to_apply: dict[str, str]) -> bool:
    """Apply fixes to restaurant data and return success status."""
    try:
        from app.extensions import db

        # Apply all fixes
        _apply_restaurant_field_fixes_api(restaurant, fixes_to_apply)

        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error applying fixes to restaurant {restaurant.id}: {e}")
        return False


def _apply_restaurant_field_fixes_api(restaurant, fixes_to_apply: dict[str, str]) -> None:
    """Apply individual field fixes to restaurant."""
    field_mapping = {
        "name": "name",
        "address_line_1": "address_line_1",
        "address_line_2": "address_line_2",
        "city": "city",
        "state": "state",
        "postal_code": "postal_code",
        "country": "country",
        "service_level": "service_level",
    }

    for fix_key, restaurant_field in field_mapping.items():
        if fix_key in fixes_to_apply:
            setattr(restaurant, restaurant_field, fixes_to_apply[fix_key])


# Generic CRUD operations for categories
@bp.route("/categories", methods=["GET"])
@login_required
def get_categories() -> Response:
    """Get all categories for the current user."""
    try:
        user = _get_current_user()
        categories = category_services.get_categories_for_user(user.id)
        return _create_api_response(
            data=categories_schema.dump(categories), message="Categories retrieved successfully"
        )
    except Exception as e:
        return _handle_service_error(e, "retrieve categories")


@bp.route("/categories", methods=["POST"])
@login_required
@validate_api_csrf
def create_category() -> Tuple[Response, int]:
    """Create a new category."""
    try:
        user = _get_current_user()
        data = category_schema.load(request.get_json())
        category = category_services.create_category_for_user(user.id, data)
        return _create_api_response(
            data=category_schema.dump(category), message="Category created successfully", code=201
        )
    except ValidationError as e:
        return _handle_validation_error(e)
    except Exception as e:
        return _handle_service_error(e, "create category")


@bp.route("/categories/<int:category_id>", methods=["GET"])
@login_required
def get_category(category_id: int) -> Response:
    """Get a single category."""
    try:
        user = _get_current_user()
        category = category_services.get_category_by_id_for_user(category_id, user.id)
        if not category:
            return jsonify({"status": "error", "message": "Category not found"}), 404
        return _create_api_response(data=category_schema.dump(category), message="Category retrieved successfully")
    except Exception as e:
        return _handle_service_error(e, "retrieve category")


@bp.route("/categories/<int:category_id>", methods=["PUT"])
@login_required
@validate_api_csrf
def update_category(category_id: int) -> Tuple[Response, int]:
    """Update a category."""
    try:
        user = _get_current_user()
        category = category_services.get_category_by_id_for_user(category_id, user.id)
        if not category:
            return jsonify({"status": "error", "message": "Category not found"}), 404

        data = category_schema.load(request.get_json())
        updated_category = category_services.update_category_for_user(category, data)
        return _create_api_response(
            data=category_schema.dump(updated_category), message="Category updated successfully"
        )
    except ValidationError as e:
        return _handle_validation_error(e)
    except Exception as e:
        return _handle_service_error(e, "update category")


@bp.route("/categories/<int:category_id>", methods=["DELETE"])
@login_required
@validate_api_csrf
def delete_category(category_id: int) -> Tuple[Response, int]:
    """Delete a category."""
    try:
        user = _get_current_user()
        category = category_services.get_category_by_id_for_user(category_id, user.id)
        if not category:
            return jsonify({"status": "error", "message": "Category not found"}), 404

        category_services.delete_category_for_user(category)
        return _create_api_response(message="Category deleted successfully", code=204)
    except Exception as e:
        return _handle_service_error(e, "delete category")
