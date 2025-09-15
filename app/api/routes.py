from __future__ import annotations

from typing import Any, Tuple, cast

from flask import Response, current_app, jsonify, request
from flask_login import current_user, login_required
from marshmallow import ValidationError

from app.auth.models import User
from app.categories import services as category_services
from app.expenses import services as expense_services
from app.restaurants import services as restaurant_services

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
    return jsonify({"status": "error", "message": "Validation failed", "errors": error.messages}), 400


def _handle_service_error(error: Exception, operation: str) -> Tuple[Response, int]:
    """Handle service layer errors consistently."""
    current_app.logger.error(f"Error in {operation}: {str(error)}", exc_info=True)
    return jsonify({"status": "error", "message": f"Failed to {operation}", "error": str(error)}), 500


# Health Check
@bp.route("/health")
def health_check() -> Response:
    """API Health Check"""
    return jsonify({"status": "healthy"})


# Version Information
@bp.route("/version")
def version_info() -> Response:
    """Get application version information.

    Returns:
        JSON response with version from git tags
    """
    from app._version import __version__

    version_data = {"version": __version__}
    return _create_api_response(data=version_data, message="Version information retrieved successfully")


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
            data=restaurant_schema.dump(restaurant), message="Restaurant created successfully", code=201
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
            data=restaurant_schema.dump(updated_restaurant), message="Restaurant updated successfully"
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
        restaurant = restaurant_services.get_restaurant_for_user(restaurant_id, user.id)
        if not restaurant:
            return jsonify({"status": "error", "message": "Restaurant not found"}), 404

        restaurant_services.delete_restaurant_for_user(restaurant)
        return _create_api_response(message="Restaurant deleted successfully", code=204)
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
        data = request.get_json()
        if not data:
            return _create_api_response(message="JSON data required", status="error", code=400)

        name = data.get("name", "").strip()
        address = data.get("address", "").strip()

        if not name:
            return _create_api_response(message="Restaurant name is required", status="error", code=400)

        if not address:
            return _create_api_response(message="Address is required", status="error", code=400)

        # Restaurant validation is now handled by the centralized field mapping
        # in the routes.py file when Google Places data is fetched
        return _create_api_response(
            data={"valid": True, "mismatches": [], "fixes": {}, "google_data": {}},
            message="Restaurant validation is handled during Google Places data fetching.",
        )

    except Exception as e:
        current_app.logger.error(f"Error validating restaurant: {e}")
        return _create_api_response(message=f"Failed to validate restaurant: {str(e)}", status="error", code=500)


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
