"""Restaurant-related routes for the application.

This module handles all restaurant-related routes including CRUD operations,
search functionality, and Google Places API integration.
"""

# Standard library imports
import logging
import os
from datetime import datetime

import requests

# Third-party imports
from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import exists, func, select

# Local application imports
from app import db
from app.expenses.models import Expense
from app.restaurants.models import Restaurant
from app.utils.decorators import db_transaction
from app.utils.messages import FlashMessages

# Local imports
from . import bp
from .services import (
    export_restaurants_to_csv,
    get_restaurant,
    import_restaurants_from_csv,
)

# Set up logger
logger = logging.getLogger(__name__)


# Restaurant CRUD routes
@bp.route("/")
@login_required
def list_restaurants():
    """Show a list of all restaurants with stats and filtering options."""
    # Get filter and sort parameters
    sort_by = request.args.get("sort", "name")
    sort_order = request.args.get("order", "asc")
    cuisine_filter = request.args.get("cuisine")

    # Base query for all restaurants with stats
    stmt = (
        select(
            Restaurant,
            func.count(Expense.id).label("visit_count"),
            func.coalesce(func.sum(Expense.amount), 0).label("total_spent"),
            func.max(Expense.date).label("last_visit"),
        )
        .outerjoin(Expense, (Expense.restaurant_id == Restaurant.id) & (Expense.user_id == current_user.id))
        .where(Restaurant.user_id == current_user.id)
        .group_by(Restaurant.id)
    )

    # Apply cuisine filter if provided
    if cuisine_filter:
        stmt = stmt.where(Restaurant.cuisine == cuisine_filter)

    # Apply sorting
    sort_column = {
        "name": Restaurant.name,
        "visits": func.count(Expense.id),
        "spent": func.coalesce(func.sum(Expense.amount), 0),
        "last_visit": func.max(Expense.date),
    }.get(sort_by, Restaurant.name)

    sort_direction = sort_order.upper() if sort_order.lower() in ["asc", "desc"] else "ASC"
    stmt = stmt.order_by(
        sort_column.asc() if sort_direction == "ASC" else sort_column.desc(),
        Restaurant.name.asc(),  # Secondary sort by name for consistent ordering
    )

    # Get all matching restaurants
    restaurants = db.session.execute(stmt).all()

    # Get unique cuisines for filter dropdown
    cuisines = db.session.scalars(
        select(Restaurant.cuisine)
        .where(Restaurant.user_id == current_user.id, Restaurant.cuisine.isnot(None))
        .distinct()
        .order_by(Restaurant.cuisine)
    ).all()

    # Calculate summary stats
    total_restaurants = len(restaurants)
    total_visits = sum(r.visit_count for r in restaurants)
    total_spent = sum(r.total_spent or 0 for r in restaurants)

    return render_template(
        "restaurants/list.html",
        restaurants=restaurants,
        cuisines=cuisines,
        sort_by=sort_by,
        sort_order=sort_order,
        cuisine_filter=cuisine_filter,
        total_restaurants=total_restaurants,
        total_visits=total_visits,
        total_spent=total_spent,
        now=datetime.utcnow(),
    )


@bp.route("/add", methods=["GET", "POST"])
@login_required
@db_transaction(success_message=FlashMessages.RESTAURANT_ADDED, error_message=FlashMessages.RESTAURANT_ADD_ERROR)
def add_restaurant():
    """Add a new restaurant."""
    from .forms import RestaurantForm

    form = RestaurantForm()
    if request.method == "POST" and form.validate_on_submit():
        restaurant = Restaurant(
            user_id=current_user.id,
            name=form.name.data,
            type=form.type.data,
            price_range=form.price_range.data,
            cuisine=form.cuisine.data,
            description=form.description.data,
            address=form.address.data,
            city=form.city.data,
            state=form.state_province.data,
            postal_code=form.postal_code.data,
            country=form.country.data or "US",
            phone=form.phone.data,
            website=form.website.data,
            is_chain=form.is_chain.data,
            notes=form.notes.data,
            google_place_id=form.google_place_id.data or None,
            place_name=form.place_name.data or None,
            latitude=float(form.latitude.data) if form.latitude.data else None,
            longitude=float(form.longitude.data) if form.longitude.data else None,
        )
        db.session.add(restaurant)
        return redirect(url_for("restaurants.restaurant_details", restaurant_id=restaurant.id))
    return render_template(
        "restaurants/form.html",
        form=form,
        restaurant=None,
        is_edit=False,
        google_maps_api_key=current_app.config.get("GOOGLE_MAPS_API_KEY", ""),
    )


@bp.route("/<int:restaurant_id>", methods=["GET", "POST"])
@login_required
@db_transaction(success_message=FlashMessages.RESTAURANT_UPDATED, error_message=FlashMessages.RESTAURANT_UPDATE_ERROR)
def restaurant_details(restaurant_id):
    """Show details for a specific restaurant with inline editing."""
    from .forms import RestaurantForm

    restaurant = get_restaurant(restaurant_id)
    form = RestaurantForm(obj=restaurant)
    if request.method == "POST" and form.validate_on_submit():
        form.populate_obj(restaurant)
        return redirect(url_for("restaurants.restaurant_details", restaurant_id=restaurant.id))
    expenses = (
        Expense.query.filter_by(restaurant_id=restaurant_id, user_id=current_user.id)
        .order_by(Expense.date.desc())
        .limit(10)
        .all()
    )
    return render_template(
        "restaurants/detail.html",
        restaurant=restaurant,
        expenses=expenses,
        form=form,
        is_editing=request.args.get("edit") == "true",
        google_maps_api_key=current_app.config.get("GOOGLE_MAPS_API_KEY", ""),
    )


@bp.route("/<int:restaurant_id>/sync-google", methods=["POST"])
@login_required
def sync_google_places(restaurant_id):
    """Sync restaurant data from Google Places."""
    restaurant = get_restaurant(restaurant_id)

    if not restaurant.google_place_id:
        return jsonify({"success": False, "message": "No Google Place ID associated with this restaurant"}), 400

    places_service = PlacesService(current_app.config.get("GOOGLE_PLACES_API_KEY"))
    success = places_service.sync_restaurant_from_google(restaurant)

    if success:
        return jsonify(
            {
                "success": True,
                "message": "Restaurant data synced successfully",
                "restaurant": {
                    "name": restaurant.name,
                    "address": restaurant.address,
                    "city": restaurant.city,
                    "state": restaurant.state,
                    "postal_code": restaurant.postal_code,
                    "phone": restaurant.phone,
                    "website": restaurant.website,
                    "rating": restaurant.rating,
                    "type": restaurant.type,
                },
            }
        )

    return jsonify({"success": False, "message": "Failed to sync restaurant data"}), 400


@bp.route("/<int:restaurant_id>/edit", methods=["GET", "POST"])
@login_required
@db_transaction(success_message=FlashMessages.RESTAURANT_UPDATED, error_message=FlashMessages.RESTAURANT_UPDATE_ERROR)
def edit_restaurant(restaurant_id):
    """Edit a restaurant's details."""
    from .forms import RestaurantForm

    restaurant = get_restaurant(restaurant_id)
    form = RestaurantForm(obj=restaurant)
    if request.method == "POST" and form.validate_on_submit():
        restaurant.name = form.name.data
        restaurant.type = form.type.data
        restaurant.price_range = form.price_range.data
        restaurant.cuisine = form.cuisine.data
        restaurant.description = form.description.data
        restaurant.address = form.address.data
        restaurant.city = form.city.data
        restaurant.state = form.state_province.data
        restaurant.postal_code = form.postal_code.data
        restaurant.country = form.country.data or "US"
        restaurant.phone = form.phone.data
        restaurant.website = form.website.data
        restaurant.is_chain = form.is_chain.data
        restaurant.notes = form.notes.data
        restaurant.google_place_id = form.google_place_id.data or None
        restaurant.place_name = form.place_name.data or None
        restaurant.latitude = float(form.latitude.data) if form.latitude.data else None
        restaurant.longitude = float(form.longitude.data) if form.longitude.data else None
        return redirect(url_for("restaurants.restaurant_details", restaurant_id=restaurant.id))
    return render_template(
        "restaurants/form.html",
        form=form,
        restaurant=restaurant,
        is_edit=True,
        google_maps_api_key=current_app.config.get("GOOGLE_MAPS_API_KEY", ""),
    )


@bp.route("/<int:restaurant_id>/delete", methods=["POST"])
@login_required
@db_transaction(success_message=FlashMessages.RESTAURANT_DELETED, error_message=FlashMessages.RESTAURANT_DELETE_ERROR)
def delete_restaurant(restaurant_id):
    """Delete a restaurant."""
    restaurant = get_restaurant(restaurant_id)
    has_expenses = db.session.scalar(select(exists().where(Expense.restaurant_id == restaurant_id)))
    if has_expenses:
        flash(FlashMessages.CANNOT_DELETE_WITH_EXPENSES, "error")
    else:
        db.session.delete(restaurant)
    return redirect(url_for("restaurants.list_restaurants"))


# Import/Export routes
@bp.route("/import", methods=["GET", "POST"])
@login_required
def import_restaurants():
    """Handle importing restaurants from CSV."""
    if request.method == "POST":
        if "file" not in request.files:
            flash("No file selected", "danger")
            return redirect(request.url)

        file = request.files["file"]
        if file.filename == "":
            flash("No file selected", "danger")
            return redirect(request.url)

        if file and file.filename.endswith(".csv"):
            success, message = import_restaurants_from_csv(file.stream, current_user)
            if success:
                flash(message, "success")
                return redirect(url_for("restaurants.list_restaurants"))
            else:
                flash(message, "danger")

    return render_template("restaurants/import.html")


@bp.route("/export")
@login_required
def export_restaurants():
    """Export restaurants to CSV."""
    try:
        response = export_restaurants_to_csv(current_user.id)
        # Update the filename to include timestamp
        filename = f'restaurants_export_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        return response
    except Exception as e:
        logger.error(f"Error exporting restaurants: {str(e)}", exc_info=True)
        flash("An error occurred while exporting restaurants. Please try again.", "error")
        return redirect(url_for("restaurants.list_restaurants"))


# Search routes
@bp.route("/search/restaurants")
@login_required
def search_restaurants():
    """Render the map-based restaurant search page.

    Query Parameters:
        lat (float): Default latitude for the map center
        lng (float): Default longitude for the map center
        zoom (int): Default zoom level for the map
        q (str): Initial search query

    Returns:
        Rendered template with the map search interface
    """
    # Get parameters with defaults
    lat = request.args.get("lat", "40.7128")
    lng = request.args.get("lng", "-74.0060")
    zoom = request.args.get("zoom", "12")
    query = request.args.get("q", "")

    # Get Google Maps API key from config - try both possible config keys
    google_maps_api_key = current_app.config.get("GOOGLE_MAPS_API_KEY") or current_app.config.get(
        "GOOGLE_PLACES_API_KEY"
    )

    # Log the status of the API key for debugging
    if not google_maps_api_key:
        current_app.logger.warning("Google Maps API key is not configured in Flask config")
        current_app.logger.warning(
            "Environment variables: %s", {k: v for k, v in os.environ.items() if "GOOGLE" in k or "API" in k}
        )

        # Try to get from environment directly as fallback
        google_maps_api_key = os.environ.get("GOOGLE_MAPS_API_KEY") or os.environ.get("GOOGLE_PLACES_API_KEY")
        if google_maps_api_key:
            current_app.logger.info("Found Google Maps API key in environment variables")
            current_app.config["GOOGLE_MAPS_API_KEY"] = google_maps_api_key
        else:
            current_app.logger.error("Google Maps API key is not configured in environment or config")
    else:
        current_app.logger.info("Google Maps API key is configured in Flask config")

    current_app.logger.debug(
        "Rendering template with lat=%s, lng=%s, zoom=%s, query=%s, has_api_key=%s",
        lat,
        lng,
        zoom,
        query,
        bool(google_maps_api_key),
    )

    # Ensure we have a valid API key
    if not google_maps_api_key:
        current_app.logger.error("Google Maps API key is required but not found in config or environment variables")
        flash("Google Maps integration is not properly configured. Please contact support.", "error")
        return redirect(url_for("restaurants.list_restaurants"))

    return render_template(
        "restaurants/search.html",
        lat=lat,
        lng=lng,
        zoom=zoom,
        query=query,
        google_maps_api_key=google_maps_api_key,
    )


def _validate_search_params(args):
    """Validate search parameters.

    Args:
        args: The request args

    Returns:
        tuple: (lat, lng, radius, keyword) if valid, None if invalid with error response
    """
    if not all(args.get(param) for param in ["lat", "lng"]):
        return None, (jsonify({"error": "Missing required parameters: lat and lng are required"}), 400)

    try:
        lat = float(args.get("lat"))
        lng = float(args.get("lng"))
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            msg = "Invalid coordinates: lat must be between -90 and 90, lng between -180 and 180"
            return None, (jsonify({"error": msg}), 400)

        radius = min(max(int(args.get("radius", 1000)), 1), 50000)
        keyword = args.get("keyword", "").strip()
        return (lat, lng, radius, keyword), None

    except (ValueError, TypeError) as e:
        return None, (jsonify({"error": f"Invalid parameter values: {str(e)}"}), 400)


def _make_places_api_request(params, api_key):
    """Make request to Google Places API.

    Args:
        params: The request parameters
        api_key: The Google Places API key

    Returns:
        tuple: (response_data, error_response) if error occurs
    """
    try:
        response = requests.get(
            "https://maps.googleapis.com/maps/api/place/nearbysearch/json", params=params, timeout=15
        )
        response.raise_for_status()
        return response.json(), None

    except requests.exceptions.RequestException as e:
        logger.error("Error making request to Google Places API: %s", str(e))
        return None, (jsonify({"error": "Error connecting to the Google Places API service"}), 503)


@bp.route("/api/places/search")
@login_required
def search_places():
    """Search for places using Google Places API.

    Query Parameters:
        lat (float): Latitude of the search location (required)
        lng (float): Longitude of the search location (required)
        radius (int): Search radius in meters (default: 1000, max: 50000)
        keyword (str): Optional search term

    Returns:
        JSON response with list of places or error message
    """
    try:
        # Log the incoming request for debugging
        logger.debug("Received Places API search request with args: %s", request.args.to_dict())

        # Validate parameters
        params, error = _validate_search_params(request.args)
        if error:
            logger.warning("Invalid search parameters: %s", error[0].get_json())
            return error

        lat, lng, radius, keyword = params

        # Get and validate API key
        api_key = current_app.config.get("GOOGLE_PLACES_API_KEY")
        logger.debug("Using Google Places API key (truncated): %s...", api_key[:8] + "..." if api_key else "None")

        # Check if API key is missing or using default value
        if not api_key or api_key == "your_google_places_api_key_here":
            error_msg = "Google Places API key is not properly configured in server settings"
            logger.error(error_msg)
            return (
                jsonify(
                    {
                        "error": "Server configuration error: Missing or invalid Google Places API key",
                        "details": "Please contact the system administrator",
                        "status": "error",
                    }
                ),
                500,
            )

        # Build the API request
        request_params = {
            "location": f"{lat},{lng}",
            "radius": radius,
            "key": api_key,
            "type": "restaurant",
            "rankby": "prominence",
        }

        if keyword:
            request_params["keyword"] = keyword

        # Log the request without exposing the API key
        safe_params = request_params.copy()
        if "key" in safe_params:
            safe_params["key"] = "***REDACTED***"
        logger.debug("Making Places API request with params: %s", safe_params)

        # Make the API request
        data, error = _make_places_api_request(request_params, api_key)
        if error:
            logger.error("Error in Places API request: %s", error[0].get_json())
            return error

        # Handle API response
        status = data.get("status")
        if status != "OK":
            error_msg = data.get("error_message", f"Google Places API error: {status}")
            logger.warning("Places API error: %s", error_msg)
            return jsonify({"error": error_msg, "status": status, "details": data}), 400

        logger.debug("Successfully retrieved %d places", len(data.get("results", [])))
        return jsonify({"results": data.get("results", []), "status": "success"})

    except Exception as err:
        error_msg = f"Unexpected error in search_places: {str(err)}"
        logger.exception(error_msg)
        return (
            jsonify(
                {
                    "error": "An unexpected error occurred while searching for places",
                    "details": str(err),
                    "status": "error",
                }
            ),
            500,
        )


@bp.route("/api/places/<place_id>")
@login_required
def get_place_details(place_id):
    """Get details for a specific place using Google Places API.

    Args:
        place_id (str): Google Place ID

    Returns:
        JSON response with place details or error message
    """
    try:
        # Make the request to Google Places API
        response = requests.get(
            "https://maps.googleapis.com/maps/api/place/details/json",
            params={
                "place_id": place_id,
                "fields": (
                    "name,formatted_address,formatted_phone_number,website,"
                    "opening_hours,price_level,rating,types,geometry"
                ),
                "key": current_app.config.get("GOOGLE_PLACES_API_KEY"),
            },
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()

        if data.get("status") != "OK":
            return jsonify({"error": data.get("error_message", "Error getting place details")}), 400

        return jsonify(data.get("result", {}))

    except (ValueError, requests.RequestException) as e:
        logger.error("Error getting place details: %s", str(e))
        return jsonify({"error": str(e)}), 400
