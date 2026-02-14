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
from app.utils.address_utils import (
    compare_addresses_semantic,
    normalize_country_to_iso2,
    normalize_state_to_usps,
)
from app.utils.phone_utils import normalize_phone_for_comparison
from app.utils.url_utils import normalize_website_for_comparison

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
) -> tuple[Response, int]:
    """Create a standardized API response."""
    response_data = {"status": status, "message": message}
    if data is not None:
        response_data["data"] = data
    return jsonify(response_data), code


def _handle_validation_error(error: ValidationError) -> tuple[Response, int]:
    """Handle validation errors consistently."""
    return (
        jsonify({"status": "error", "message": "Validation failed", "errors": error.messages}),
        400,
    )


def _handle_service_error(error: Exception, operation: str) -> tuple[Response, int]:
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
    return cast(Response, jsonify({"status": "healthy"}))


# Version Information
@bp.route("/version")
def version_info() -> tuple[Response, int]:
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
def get_cuisines() -> tuple[Response, int]:
    """Get cuisine data for frontend consumption.

    Returns:
        JSON response with cuisine names, colors, icons, and Google Places mapping
    """
    import json
    import os

    try:
        # Load from static JSON file
        static_folder = current_app.static_folder
        if not static_folder:
            raise ValueError("Static folder not configured")
        json_path = os.path.join(static_folder, "data", "cuisines.json")
        with open(json_path) as f:
            cuisine_data = json.load(f)

        return _create_api_response(data=cuisine_data, message="Cuisine data retrieved successfully")
    except Exception as e:
        current_app.logger.error(f"Error loading cuisine data: {e}")
        return _create_api_response(message="Failed to load cuisine data", status="error", code=500)


# Generic CRUD operations for expenses
@bp.route("/expenses", methods=["GET"])
@login_required
def get_expenses() -> tuple[Response, int]:
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
def create_expense() -> tuple[Response, int]:
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
def get_expense(expense_id: int) -> tuple[Response, int]:
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
def update_expense(expense_id: int) -> tuple[Response, int]:
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
def delete_expense(expense_id: int) -> Response | tuple[Response, int]:
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
def get_restaurants() -> Response | tuple[Response, int]:
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
def create_restaurant() -> Response | tuple[Response, int]:
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
def get_restaurant(restaurant_id: int) -> Response | tuple[Response, int]:
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


@bp.route("/restaurants/<int:restaurant_id>/default-category", methods=["GET"])
@login_required
def get_restaurant_default_category(restaurant_id: int) -> Response | tuple[Response, int]:
    """Get the default category for a restaurant based on past expenses."""
    try:
        user = _get_current_user()
        # Verify restaurant exists and belongs to user
        restaurant = restaurant_services.get_restaurant_for_user(restaurant_id, user.id)
        if not restaurant:
            return jsonify({"status": "error", "message": "Restaurant not found"}), 404

        category_id = restaurant_services.get_default_category_for_restaurant(restaurant_id, user.id)
        return _create_api_response(
            data={"category_id": category_id}, message="Default category retrieved successfully"
        )
    except Exception as e:
        return _handle_service_error(e, "retrieve default category")


@bp.route("/restaurants/<int:restaurant_id>", methods=["PUT"])
@login_required
@validate_api_csrf
def update_restaurant(restaurant_id: int) -> tuple[Response, int]:
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
def delete_restaurant(restaurant_id: int) -> tuple[Response, int]:
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
def check_restaurant_exists() -> Response | tuple[Response, int]:
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
def validate_restaurant() -> Response | tuple[Response, int]:
    """Validate restaurant information using Google Places API."""
    try:
        # Validate input data
        validation_error = _validate_restaurant_input()
        if validation_error:
            return validation_error

        data = request.get_json()
        restaurant_id = data.get("restaurant_id")
        google_place_id = data.get("google_place_id", "").strip()

        # Get restaurant and place_id (edit flow) or use place_id only (add flow)
        restaurant, place_id_to_use = _get_and_validate_restaurant()
        if place_id_to_use is None:
            # Add flow: use place_id from request directly
            if google_place_id:
                place_id_to_use = google_place_id
            else:
                return _create_api_response(message="Place ID is required", status="error", code=400)
        elif not restaurant and restaurant_id:
            return _create_api_response(message="Restaurant not found", status="error", code=404)

        validation_result = _validate_restaurant_with_google_api(place_id_to_use)
        if not validation_result.get("valid"):
            return _create_api_response(data=validation_result, message="Validation failed", status="error", code=400)

        return _process_validation_results(restaurant, validation_result)

    except Exception as e:
        current_app.logger.error(f"Error validating restaurant: {e}")
        return _create_api_response(message=f"Failed to validate restaurant: {str(e)}", status="error", code=500)


def _validate_restaurant_input() -> tuple[Response, int] | None:
    """Validate input parameters for restaurant validation."""
    data = request.get_json()
    if not data:
        return _create_api_response(message="JSON data required", status="error", code=400)

    restaurant_id = data.get("restaurant_id")
    google_place_id = data.get("google_place_id", "").strip()

    # Either restaurant_id (edit) or google_place_id (add) is required
    if not restaurant_id and not google_place_id:
        return _create_api_response(message="Restaurant ID or Google Place ID is required", status="error", code=400)

    form_data = data.get("form_data")
    if not form_data:
        return _create_api_response(message="form_data is required for validation", status="error", code=400)

    return None


def _get_and_validate_restaurant() -> tuple[Restaurant | None, str | None]:
    """Get restaurant and validate user permissions. Returns (restaurant, place_id)."""
    data = request.get_json()
    restaurant_id = data.get("restaurant_id")
    google_place_id = data.get("google_place_id", "").strip()

    # Add flow: no restaurant_id, use place_id from request
    if not restaurant_id:
        return None, google_place_id if google_place_id else None

    restaurant = Restaurant.query.get(restaurant_id)
    if not restaurant:
        return None, None

    user = _get_current_user()
    if restaurant.user_id != user.id:
        return None, None

    place_id_to_use = google_place_id or restaurant.google_place_id
    if not place_id_to_use:
        return None, None

    return restaurant, place_id_to_use


def _process_validation_results(restaurant: Any | None, validation_result: dict[str, Any]) -> tuple[Response, int]:
    """Process validation results and return response."""
    data = request.get_json()
    form_data = data.get("form_data")
    fix_mismatches = data.get("fix_mismatches", False)

    current_data = form_data
    mismatches, fixes_to_apply = _check_restaurant_mismatches_api(current_data, validation_result)

    # Apply fixes only when we have a restaurant (edit flow)
    if fix_mismatches and fixes_to_apply and restaurant:
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
            "google_cuisine": google_data.get("cuisine_type"),
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


def _check_restaurant_mismatches_api(
    current_data: dict[str, Any], validation_result: dict[str, Any]
) -> tuple[list[str], dict[str, str]]:
    """Check for mismatches between current data and Google data."""
    mismatches: list[str] = []
    fixes_to_apply: dict[str, str] = {}

    # Check name mismatch
    _check_name_mismatch_api(current_data, validation_result, mismatches, fixes_to_apply)

    # Check address mismatches
    _check_address_mismatches_api(current_data, validation_result, mismatches, fixes_to_apply)

    # Check service level mismatch
    _check_service_level_mismatch_api(current_data, validation_result, mismatches, fixes_to_apply)

    # Check state mismatch
    _check_state_mismatch_api(current_data, validation_result, mismatches, fixes_to_apply)

    # Check website, phone, cuisine, type, price level
    _check_website_mismatch_api(current_data, validation_result, mismatches, fixes_to_apply)
    _check_phone_mismatch_api(current_data, validation_result, mismatches, fixes_to_apply)
    _check_cuisine_mismatch_api(current_data, validation_result, mismatches, fixes_to_apply)
    _check_type_mismatch_api(current_data, validation_result, mismatches, fixes_to_apply)
    _check_price_level_mismatch_api(current_data, validation_result, mismatches, fixes_to_apply)
    _check_rating_mismatch_api(current_data, validation_result, mismatches, fixes_to_apply)

    return mismatches, fixes_to_apply


def _check_name_mismatch_api(
    current_data: dict[str, Any],
    validation_result: dict[str, Any],
    mismatches: list[str],
    fixes_to_apply: dict[str, str],
) -> None:
    """Check for name mismatch."""
    google_name = validation_result.get("google_name")
    current_name = current_data.get("name")
    if google_name and current_name and google_name.lower() != current_name.lower():
        mismatches.append(f"Name: '{current_name}' vs Google: '{google_name}'")
        fixes_to_apply["name"] = google_name


def _check_state_mismatch_api(
    current_data: dict[str, Any],
    validation_result: dict[str, Any],
    mismatches: list[str],
    fixes_to_apply: dict[str, str],
) -> None:
    """Check for state field mismatches using multiple comparison methods."""
    from app.restaurants.cli import (
        _states_match_directly,
        _states_match_with_us_library,
    )

    google_state = validation_result.get("google_state")
    google_state_long = validation_result.get("google_state_long")
    google_state_short = validation_result.get("google_state_short")
    current_state = current_data.get("state")

    if not (google_state or google_state_long or google_state_short):
        return

    # Stored is empty but Google has state - suggest fix (same as city/postal_code)
    if not current_state or not str(current_state).strip():
        google_display = google_state_long or google_state or google_state_short
        mismatches.append(f"State: 'N/A' vs Google: '{google_display}'")
        two_letter = validation_result.get("google_state_short") or normalize_state_to_usps(
            validation_result.get("google_state") or validation_result.get("google_state_long") or ""
        )
        fixes_to_apply["state"] = two_letter or google_state_long or google_state or google_state_short
        return

    if not isinstance(current_state, str):
        return

    # Check direct string matches first
    if _states_match_directly(
        current_state,
        google_state or "",
        google_state_long or "",
        google_state_short or "",
    ):
        return

    # Try US library matching as fallback
    if _states_match_with_us_library(
        current_state,
        google_state or "",
        google_state_long or "",
        google_state_short or "",
    ):
        return

    # If no matches found, report mismatch; suggest USPS 2-letter state for fix
    google_display = google_state_long or google_state or google_state_short or "Unknown"
    mismatches.append(f"State: '{current_state}' vs Google: '{google_display}'")
    two_letter = validation_result.get("google_state_short") or normalize_state_to_usps(
        validation_result.get("google_state") or validation_result.get("google_state_long") or ""
    )
    if two_letter:
        fixes_to_apply["state"] = two_letter
    else:
        state_fix = google_state_long or google_state or google_state_short
        if state_fix and isinstance(state_fix, str):
            fixes_to_apply["state"] = state_fix


def _check_address_mismatches_api(
    current_data: dict[str, Any],
    validation_result: dict[str, Any],
    mismatches: list[str],
    fixes_to_apply: dict[str, str],
) -> None:
    """Check for address field mismatches (semantic for address lines, normalized for country)."""
    # Address lines: semantic comparison
    for google_field, current_field, display_name in [
        ("google_address_line_1", "address_line_1", "Address Line 1"),
        ("google_address_line_2", "address_line_2", "Address Line 2"),
    ]:
        google_value = validation_result.get(google_field)
        current_value = current_data.get(current_field)
        if not google_value and not current_value:
            continue
        if not google_value:
            continue
        is_match, _ = compare_addresses_semantic(current_value or "", google_value or "")
        if is_match:
            continue
        if current_value:
            mismatches.append(f"{display_name}: '{current_value}' vs Google: '{google_value}'")
            fixes_to_apply[current_field] = google_value
        else:
            mismatches.append(f"{display_name}: '{current_value or 'N/A'}' vs Google: '{google_value}'")
            fixes_to_apply[current_field] = google_value

    # City and postal code: suggest Google value when stored is empty
    for google_field, current_field, display_name in [
        ("google_city", "city", "City"),
        ("google_postal_code", "postal_code", "Postal Code"),
    ]:
        google_value = validation_result.get(google_field)
        current_value = current_data.get(current_field)
        if not google_value:
            continue
        if not current_value:
            mismatches.append(f"{display_name}: 'N/A' vs Google: '{google_value}'")
            fixes_to_apply[current_field] = google_value
        elif google_value.lower() != current_value.lower():
            mismatches.append(f"{display_name}: '{current_value}' vs Google: '{google_value}'")
            fixes_to_apply[current_field] = google_value

    # Country: normalize to ISO 2-letter for comparison and fix (state handled by _check_state_mismatch_api)
    google_country = validation_result.get("google_country")
    current_country = current_data.get("country")
    norm_google = normalize_country_to_iso2(google_country or "")
    norm_current = normalize_country_to_iso2(current_country or "")
    if norm_google and norm_current and norm_google != norm_current:
        mismatches.append(f"Country: '{current_country}' vs Google: '{google_country}'")
        fixes_to_apply["country"] = norm_google
    elif norm_google and not norm_current:
        mismatches.append(f"Country: 'N/A' vs Google: '{google_country}'")
        fixes_to_apply["country"] = norm_google


def _check_service_level_mismatch_api(
    current_data: dict[str, Any],
    validation_result: dict[str, Any],
    mismatches: list[str],
    fixes_to_apply: dict[str, str],
) -> None:
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


def _check_website_mismatch_api(
    current_data: dict[str, Any],
    validation_result: dict[str, Any],
    mismatches: list[str],
    fixes_to_apply: dict[str, str],
) -> None:
    """Check for website mismatches (normalized: strip params, trailing slash)."""
    google_website = validation_result.get("google_website")
    if google_website is None:
        return
    current_website = current_data.get("website")
    norm_current = normalize_website_for_comparison(current_website)
    norm_google = normalize_website_for_comparison(google_website)
    if norm_google and norm_current != norm_google:
        mismatches.append(f"Website: '{current_website or 'Not set'}' vs Google: '{google_website}'")
        fixes_to_apply["website"] = google_website


def _check_phone_mismatch_api(
    current_data: dict[str, Any],
    validation_result: dict[str, Any],
    mismatches: list[str],
    fixes_to_apply: dict[str, str],
) -> None:
    """Check for phone mismatches (normalized: digits-only comparison)."""
    google_phone = validation_result.get("google_phone")
    if google_phone is None:
        return
    current_phone = current_data.get("phone")
    norm_current = normalize_phone_for_comparison(current_phone)
    norm_google = normalize_phone_for_comparison(google_phone)
    if norm_google and norm_current != norm_google:
        mismatches.append(f"Phone: '{current_phone or 'Not set'}' vs Google: '{google_phone}'")
        fixes_to_apply["phone"] = google_phone


def _check_cuisine_mismatch_api(
    current_data: dict[str, Any],
    validation_result: dict[str, Any],
    mismatches: list[str],
    fixes_to_apply: dict[str, str],
) -> None:
    """Check for cuisine mismatches (case-insensitive)."""
    google_cuisine = validation_result.get("google_cuisine")
    if google_cuisine is None:
        return
    current_cuisine = current_data.get("cuisine")
    if not current_cuisine or current_cuisine.strip().lower() != google_cuisine.strip().lower():
        mismatches.append(f"Cuisine: '{current_cuisine or 'Not set'}' vs Google: '{google_cuisine}'")
        fixes_to_apply["cuisine"] = google_cuisine


def _check_type_mismatch_api(
    current_data: dict[str, Any],
    validation_result: dict[str, Any],
    mismatches: list[str],
    fixes_to_apply: dict[str, str],
) -> None:
    """Check for type mismatches (direct comparison with Google primary_type)."""
    google_primary_type = validation_result.get("primary_type")
    if google_primary_type is None:
        return
    current_type = current_data.get("type")
    if current_type != google_primary_type:
        mismatches.append(f"Type: '{current_type or 'Not set'}' vs Google: '{google_primary_type}'")
        fixes_to_apply["type"] = google_primary_type


def _check_price_level_mismatch_api(
    current_data: dict[str, Any],
    validation_result: dict[str, Any],
    mismatches: list[str],
    fixes_to_apply: dict[str, str],
) -> None:
    """Check for price level mismatches (normalize to int 0-4 for comparison)."""
    google_price_level = validation_result.get("google_price_level")
    if google_price_level is None:
        return

    from app.services.google_places_service import get_google_places_service

    places_service = get_google_places_service()
    google_price_level_int = places_service.convert_price_level_to_int(google_price_level)

    current_raw = current_data.get("price_level")
    current_int = None
    if current_raw is not None and current_raw != "":
        try:
            current_int = int(current_raw) if isinstance(current_raw, (int, float)) else int(str(current_raw), 10)
        except (ValueError, TypeError):
            pass

    if current_int != google_price_level_int:
        current_display = _format_price_level_display_api(current_int)
        google_display = _format_price_level_display_api(google_price_level_int)
        mismatches.append(f"Price Level: '{current_display}' vs Google: '{google_display}'")
        fixes_to_apply["price_level"] = str(google_price_level_int)


def _check_rating_mismatch_api(
    current_data: dict[str, Any],
    validation_result: dict[str, Any],
    mismatches: list[str],
    fixes_to_apply: dict[str, str],
) -> None:
    """Check for rating mismatches (user's rating vs Google's aggregate rating)."""
    google_rating = validation_result.get("google_rating")
    if google_rating is None:
        return

    current_raw = current_data.get("rating")
    current_rating = None
    if current_raw is not None and current_raw != "":
        try:
            current_rating = float(current_raw) if isinstance(current_raw, (int, float)) else float(str(current_raw))
        except (ValueError, TypeError):
            pass

    try:
        google_float = float(google_rating)
    except (ValueError, TypeError):
        return

    if current_rating is not None and abs(current_rating - google_float) > 0.05:
        mismatches.append(f"Rating: Your {current_rating:.1f} vs Google {google_float:.1f}")
        fixes_to_apply["rating"] = str(google_float)
    elif current_rating is None and google_float is not None:
        mismatches.append(f"Rating: Not set vs Google {google_float:.1f}")
        fixes_to_apply["rating"] = str(google_float)


def _format_price_level_display_api(price_level: int | None) -> str:
    """Format price level for display in mismatch messages."""
    if price_level is None:
        return "Not set"
    mapping = {
        0: "Free",
        1: "$ (Budget)",
        2: "$$ (Moderate)",
        3: "$$$ (Expensive)",
        4: "$$$$ (Very Expensive)",
    }
    return mapping.get(price_level, str(price_level))


def _apply_restaurant_fixes_api(restaurant: Restaurant, fixes_to_apply: dict[str, str]) -> bool:
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


def _apply_restaurant_field_fixes_api(restaurant: Restaurant, fixes_to_apply: dict[str, str]) -> None:
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
        "website": "website",
        "phone": "phone",
        "cuisine": "cuisine",
        "type": "type",
        "price_level": "price_level",
        "rating": "rating",
    }

    for fix_key, restaurant_field in field_mapping.items():
        if fix_key in fixes_to_apply:
            value = fixes_to_apply[fix_key]
            if restaurant_field == "rating" and value is not None:
                try:
                    value = float(value) if isinstance(value, (int, float)) else float(str(value))
                except (ValueError, TypeError):
                    value = None
            elif restaurant_field == "price_level" and value is not None:
                try:
                    value = int(value, 10) if isinstance(value, str) else int(value)
                except (ValueError, TypeError):
                    value = None
            setattr(restaurant, restaurant_field, value)


# Receipt OCR endpoint
@bp.route("/receipts/ocr", methods=["POST"])
@login_required
@validate_api_csrf
def process_receipt_ocr() -> tuple[Response, int]:
    """Process receipt image/PDF with OCR to extract expense data.

    Returns:
        JSON response with extracted receipt data
    """
    try:
        # Check if OCR is enabled
        if not current_app.config.get("OCR_ENABLED", True):
            return _create_api_response(message="OCR is disabled", status="error", code=503)

        # Get uploaded file
        if "receipt_file" not in request.files:
            return _create_api_response(message="No receipt file provided", status="error", code=400)

        receipt_file = request.files["receipt_file"]
        if not receipt_file or not receipt_file.filename:
            return _create_api_response(message="No receipt file provided", status="error", code=400)

        # Validate file type (AWS Textract supports PNG, JPEG, and PDF only)
        allowed_extensions = {".jpg", ".jpeg", ".png", ".pdf"}
        file_ext = "." + receipt_file.filename.rsplit(".", 1)[1].lower() if "." in receipt_file.filename else ""
        if file_ext not in allowed_extensions:
            return _create_api_response(
                message=f"Invalid file type. AWS Textract supports: PNG, JPEG, and PDF only. Received: {file_ext or 'unknown'}",
                status="error",
                code=400,
            )

        # Validate file size (5MB max)
        receipt_file.seek(0, 2)  # Seek to end
        file_size = receipt_file.tell()
        receipt_file.seek(0)  # Reset

        max_size = current_app.config.get("MAX_CONTENT_LENGTH", 5 * 1024 * 1024)
        if file_size > max_size:
            return _create_api_response(
                message=f"File too large. Max size: {max_size / 1024 / 1024}MB", status="error", code=400
            )

        # Get form hints from request if provided (for better matching)
        form_hints: dict[str, Any] | None = None
        form_restaurant_id: int | None = None
        if request.form:
            hints_dict: dict[str, str] = {}
            form_amount = request.form.get("form_amount")
            form_date = request.form.get("form_date")
            form_restaurant = request.form.get("form_restaurant_name")
            form_restaurant_id_str = request.form.get("form_restaurant_id")

            if form_amount:
                hints_dict["amount"] = form_amount
            if form_date:
                hints_dict["date"] = form_date
            if form_restaurant:
                hints_dict["restaurant_name"] = form_restaurant
            if form_restaurant_id_str:
                try:
                    form_restaurant_id = int(form_restaurant_id_str)
                except ValueError:
                    pass

            # Only use hints if at least one is provided
            if hints_dict:
                form_hints = hints_dict

        # Process with OCR service
        try:
            from app.services.ocr_service import get_ocr_service

            ocr_service = get_ocr_service()
            if not ocr_service:
                return _create_api_response(
                    message="OCR service not available. AWS Textract is not configured. Please configure AWS credentials.",
                    status="error",
                    code=503,
                )

            receipt_data = ocr_service.extract_receipt_data(receipt_file, form_hints=form_hints)
        except RuntimeError as e:
            # Handle Textract not available error
            current_app.logger.error(f"OCR service error: {e}")
            return _create_api_response(message=str(e), status="error", code=503)
        except Exception as e:
            current_app.logger.error(f"Unexpected OCR error: {e}", exc_info=True)
            return _create_api_response(message=f"Failed to process receipt: {str(e)}", status="error", code=500)

        # If restaurant ID provided, get restaurant address for comparison
        restaurant_address_data = None
        if form_restaurant_id:
            try:
                from app.restaurants.models import Restaurant

                restaurant = Restaurant.query.filter_by(id=form_restaurant_id, user_id=current_user.id).first()
                if restaurant:
                    restaurant_address_data = {
                        "full_address": restaurant.full_address,
                        "address_line_1": restaurant.address_line_1,
                        "address_line_2": restaurant.address_line_2,
                        "city": restaurant.city,
                        "state": restaurant.state,
                        "postal_code": restaurant.postal_code,
                        "phone": restaurant.phone,
                        "website": restaurant.website,
                    }
            except Exception as e:
                current_app.logger.warning(f"Failed to get restaurant address: {e}")

        # Convert to JSON-serializable format
        receipt_dict = {
            "amount": str(receipt_data.amount) if receipt_data.amount else None,
            "date": receipt_data.date.isoformat() if receipt_data.date else None,
            "time": receipt_data.time,
            "restaurant_name": receipt_data.restaurant_name,
            "restaurant_address": receipt_data.restaurant_address,
            "restaurant_phone": receipt_data.restaurant_phone,
            "restaurant_website": receipt_data.restaurant_website,
            "items": receipt_data.items,
            "tax": str(receipt_data.tax) if receipt_data.tax else None,
            "tip": str(receipt_data.tip) if receipt_data.tip else None,
            "total": str(receipt_data.total) if receipt_data.total else None,
            "confidence_scores": receipt_data.confidence_scores,
            "raw_text": receipt_data.raw_text[:500],  # Limit raw text length
            "restaurant_address_data": restaurant_address_data,  # For UI comparison
        }

        # Perform reconciliation if form data is available
        reconciliation_data = None
        if form_restaurant_id and form_hints:
            try:
                from datetime import datetime
                from decimal import Decimal

                from app.expenses.models import Expense
                from app.expenses.services import reconcile_receipt_with_expense

                # Get restaurant (already fetched above)
                restaurant = Restaurant.query.filter_by(id=form_restaurant_id, user_id=current_user.id).first()
                if restaurant:
                    # Parse form hints
                    form_amount = Decimal(form_hints.get("amount", "0"))
                    form_date_str = form_hints.get("date")
                    if form_date_str:
                        try:
                            # Parse date string (could be ISO format or YYYY-MM-DD)
                            if "T" in form_date_str:
                                form_date = datetime.fromisoformat(form_date_str.replace("Z", "+00:00"))
                            else:
                                form_date = datetime.strptime(form_date_str, "%Y-%m-%d")
                        except (ValueError, TypeError):
                            form_date = datetime.now()
                    else:
                        form_date = datetime.now()

                    # Create minimal expense object for reconciliation
                    temp_expense = Expense(
                        user_id=current_user.id,
                        restaurant_id=restaurant.id,
                        restaurant=restaurant,
                        amount=form_amount,
                        date=form_date,
                    )
                    reconciliation_data = reconcile_receipt_with_expense(temp_expense, receipt_dict)
            except Exception as e:
                current_app.logger.warning(f"Failed to perform reconciliation: {e}", exc_info=True)

        data = receipt_dict
        if reconciliation_data:
            data["reconciliation"] = reconciliation_data

        return _create_api_response(data=data, message="Receipt processed successfully")

    except ValueError as e:
        return _create_api_response(message=str(e), status="error", code=400)
    except RuntimeError as e:
        current_app.logger.error(f"OCR processing error: {e}")
        return _create_api_response(message=f"OCR processing failed: {str(e)}", status="error", code=500)
    except Exception as e:
        return _handle_service_error(e, "process receipt OCR")


# Generic CRUD operations for categories
@bp.route("/categories", methods=["GET"])
@login_required
def get_categories() -> Response | tuple[Response, int]:
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
def create_category() -> tuple[Response, int]:
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
def get_category(category_id: int) -> tuple[Response, int]:
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
def update_category(category_id: int) -> tuple[Response, int]:
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
def delete_category(category_id: int) -> tuple[Response, int]:
    """Delete a category."""
    try:
        user: User = _get_current_user()
        category = category_services.get_category_by_id_for_user(category_id, user.id)
        if not category:
            return jsonify({"status": "error", "message": "Category not found"}), 404

        category_services.delete_category_for_user(category)
        return _create_api_response(message="Category deleted successfully", code=204)
    except Exception as e:
        return _handle_service_error(e, "delete category")
