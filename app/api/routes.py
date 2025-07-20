from __future__ import annotations

from typing import Tuple, cast

from flask import Response, jsonify, request, current_app
from flask_login import current_user, login_required
from marshmallow import ValidationError
import googlemaps
from typing import List, Dict, Any, Optional

from app.auth.models import User

from . import bp, services
from .schemas import CategorySchema, ExpenseSchema, RestaurantSchema

# Initialize Google Maps client
gmaps = None


def get_gmaps_client():
    """Initialize and return Google Maps client."""
    global gmaps
    if gmaps is None and current_app.config.get("GOOGLE_MAPS_API_KEY"):
        gmaps = googlemaps.Client(key=current_app.config["GOOGLE_MAPS_API_KEY"])
    return gmaps


expense_schema = ExpenseSchema()
expenses_schema = ExpenseSchema(many=True)
restaurant_schema = RestaurantSchema()
restaurants_schema = RestaurantSchema(many=True)
category_schema = CategorySchema()
categories_schema = CategorySchema(many=True)


@bp.route("/health")
def health_check() -> Response:
    """API Health Check"""
    return jsonify({"status": "healthy"})


@bp.route("/address-autocomplete")
@login_required
def address_autocomplete() -> Response:
    """
    Get address autocomplete suggestions from Google Places API.

    Query parameters:
        query: The search query string
        language: (optional) Language code for results (default: 'en')

    Returns:
        JSON array of address suggestions with place_id and description
    """
    query = request.args.get("query")
    if not query:
        return jsonify({"error": "Missing required parameter: query"}), 400

    language = request.args.get("language", "en")

    try:
        gmaps = get_gmaps_client()
        if not gmaps:
            return jsonify({"error": "Google Maps API not configured"}), 500

        # Get place predictions
        predictions = gmaps.places_autocomplete(input_text=query, language=language)

        # Format the response
        suggestions = [
            {
                "place_id": pred["place_id"],
                "description": pred["description"],
                "main_text": pred.get("structured_formatting", {}).get("main_text", ""),
                "secondary_text": pred.get("structured_formatting", {}).get("secondary_text", ""),
            }
            for pred in predictions
        ]

        return jsonify(suggestions)

    except Exception as e:
        current_app.logger.error(f"Error in address autocomplete: {str(e)}")
        return jsonify({"error": "Failed to fetch address suggestions"}), 500


@bp.route("/place-details")
@login_required
def place_details() -> Response:
    """
    Get detailed information about a place from Google Places API.

    Query parameters:
        place_id: The Google Place ID
        language: (optional) Language code for results (default: 'en')

    Returns:
        JSON object with place details
    """
    place_id = request.args.get("place_id")
    if not place_id:
        return jsonify({"error": "Missing required parameter: place_id"}), 400

    language = request.args.get("language", "en")

    try:
        gmaps = get_gmaps_client()
        if not gmaps:
            return jsonify({"error": "Google Maps API not configured"}), 500

        # Get place details with valid field names
        place = gmaps.place(
            place_id=place_id,
            language=language,
            fields=["name", "formatted_address", "geometry/location", "address_component"],
        )

        if not place or "result" not in place:
            return jsonify({"error": "Place not found"}), 404

        # Format the response with the full address components array
        result = {
            "name": place["result"].get("name", ""),
            "formatted_address": place["result"].get("formatted_address", ""),
            "location": place["result"].get("geometry", {}).get("location", {}),
            "address_components": place["result"].get("address_component", []),
        }

        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"Error fetching place details: {str(e)}")
        return jsonify({"error": "Failed to fetch place details"}), 500


@bp.route("/expenses", methods=["GET"])
@login_required
def get_expenses() -> Response:
    """Get all expenses for the current user."""
    user = cast(User, current_user._get_current_object())
    expenses = services.get_expenses_for_user(user.id)
    return jsonify(expenses_schema.dump(expenses))


@bp.route("/expenses", methods=["POST"])
@login_required
def create_expense() -> tuple[Response, int]:
    """Create a new expense."""
    user = cast(User, current_user._get_current_object())
    try:
        data = expense_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400
    expense = services.create_expense_for_user(user.id, data)
    return jsonify(expense_schema.dump(expense)), 201


@bp.route("/expenses/<int:expense_id>", methods=["GET"])
@login_required
def get_expense(expense_id: int) -> Response:
    """Get a single expense."""
    user = cast(User, current_user._get_current_object())
    expense = services.get_expense_by_id_for_user(expense_id, user.id)
    return jsonify(expense_schema.dump(expense))


@bp.route("/expenses/<int:expense_id>", methods=["PUT"])
@login_required
def update_expense(expense_id: int) -> Tuple[Response, int]:
    """Update an expense."""
    user = cast(User, current_user._get_current_object())
    expense = services.get_expense_by_id_for_user(expense_id, user.id)
    try:
        data = expense_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400
    updated_expense = services.update_expense_for_user(expense, data)
    return jsonify(expense_schema.dump(updated_expense)), 200


@bp.route("/expenses/<int:expense_id>", methods=["DELETE"])
@login_required
def delete_expense(expense_id: int) -> Tuple[Response, int]:
    """Delete an expense."""
    user = cast(User, current_user._get_current_object())
    expense = services.get_expense_by_id_for_user(expense_id, user.id)
    services.delete_expense_for_user(expense)
    return jsonify({}), 204


@bp.route("/restaurants", methods=["GET"])
@login_required
def get_restaurants() -> Response:
    """Get all restaurants for the current user."""
    user = cast(User, current_user._get_current_object())
    restaurants = services.get_restaurants_for_user(user.id)
    return jsonify(restaurants_schema.dump(restaurants))


@bp.route("/restaurants", methods=["POST"])
@login_required
def create_restaurant() -> tuple[Response, int]:
    """Create a new restaurant."""
    user = cast(User, current_user._get_current_object())
    try:
        data = restaurant_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400
    restaurant = services.create_restaurant_for_user(user.id, data)
    return jsonify(restaurant_schema.dump(restaurant)), 201


@bp.route("/restaurants/<int:restaurant_id>", methods=["GET"])
@login_required
def get_restaurant(restaurant_id: int) -> Response:
    """Get a single restaurant."""
    user = cast(User, current_user._get_current_object())
    restaurant = services.get_restaurant_for_user(restaurant_id, user.id)
    return jsonify(restaurant_schema.dump(restaurant))


@bp.route("/restaurants/<int:restaurant_id>", methods=["PUT"])
@login_required
def update_restaurant(restaurant_id: int) -> tuple[Response, int]:
    """Update a restaurant."""
    user = cast(User, current_user._get_current_object())
    restaurant = services.get_restaurant_for_user(restaurant_id, user.id)
    try:
        data = restaurant_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400
    updated_restaurant = services.update_restaurant_for_user(restaurant, data)
    return jsonify(restaurant_schema.dump(updated_restaurant)), 200


@bp.route("/restaurants/<int:restaurant_id>", methods=["DELETE"])
@login_required
def delete_restaurant(restaurant_id: int) -> tuple[Response, int]:
    """Delete a restaurant."""
    user = cast(User, current_user._get_current_object())
    restaurant = services.get_restaurant_for_user(restaurant_id, user.id)
    services.delete_restaurant_for_user(restaurant)
    return jsonify({}), 204


@bp.route("/categories", methods=["GET"])
@login_required
def get_categories() -> Response:
    """Get all categories for the current user."""
    user = cast(User, current_user._get_current_object())
    categories = services.get_categories_for_user(user.id)
    return jsonify(categories_schema.dump(categories))


@bp.route("/categories", methods=["POST"])
@login_required
def create_category() -> tuple[Response, int]:
    """Create a new category."""
    user = cast(User, current_user._get_current_object())
    try:
        data = category_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400
    category = services.create_category_for_user(user.id, data)
    return jsonify(category_schema.dump(category)), 201


@bp.route("/categories/<int:category_id>", methods=["GET"])
@login_required
def get_category(category_id: int) -> Response:
    """Get a single category."""
    user = cast(User, current_user._get_current_object())
    category = services.get_category_by_id_for_user(category_id, user.id)
    return jsonify(category_schema.dump(category))


@bp.route("/categories/<int:category_id>", methods=["PUT"])
@login_required
def update_category(category_id: int) -> tuple[Response, int]:
    """Update a category."""
    user = cast(User, current_user._get_current_object())
    category = services.get_category_by_id_for_user(category_id, user.id)
    try:
        data = category_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400
    updated_category = services.update_category_for_user(category, data)
    return jsonify(category_schema.dump(updated_category)), 200


@bp.route("/categories/<int:category_id>", methods=["DELETE"])
@login_required
def delete_category(category_id: int) -> tuple[Response, int]:
    """Delete a category."""
    user = cast(User, current_user._get_current_object())
    category = services.get_category_by_id_for_user(category_id, user.id)
    services.delete_category_for_user(category)
    return jsonify({}), 204
