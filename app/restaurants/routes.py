"""Restaurant-related routes for the application."""

import csv
import io
import json

import requests
from flask import (
    abort,
    current_app,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.orm import joinedload

# Import Expense model here to avoid circular imports
from app.extensions import db

# Comprehensive list of food-related business types for Google Places API searches
FOOD_BUSINESS_TYPES = [
    "restaurant",
    "cafe",
    "bakery",
    "bar",
    "fast_food_restaurant",
    "meal_delivery",
    "meal_takeaway",
    "food_court",
    "coffee_shop",
    "ice_cream_shop",
    "sandwich_shop",
    "deli",
    "donut_shop",
    "dessert_shop",
    "juice_shop",
    "wine_bar",
    "pub",
    "tea_house",
]
from app.restaurants import bp, services
from app.restaurants.exceptions import (
    DuplicateGooglePlaceIdError,
    DuplicateRestaurantError,
)
from app.restaurants.forms import RestaurantForm
from app.restaurants.models import Restaurant
from app.restaurants.services import (
    calculate_expense_stats,
    search_restaurants_by_location,
)
from app.utils.decorators import admin_required

# Constants
PER_PAGE = 10  # Number of restaurants per page
SHOW_ALL = -1  # Special value to show all restaurants


def _get_page_size_from_cookie(cookie_name="restaurant_page_size", default_size=PER_PAGE):
    """Get page size from cookie with validation and fallback."""
    try:
        cookie_value = request.cookies.get(cookie_name)
        if cookie_value:
            page_size = int(cookie_value)
            # Validate page size is in allowed values
            if page_size in [10, 25, 50, 100, SHOW_ALL]:
                return page_size
    except (ValueError, TypeError):
        pass
    return default_size


def _extract_location_from_query(query):
    """Extract location information from search query.

    Examples:
    - "McDonald's Dallas, TX" -> ("McDonald's", "Dallas, TX")
    - "Pizza near Austin" -> ("Pizza", "Austin")
    - "Starbucks" -> ("Starbucks", None)
    """
    import re

    # Pattern for explicit location indicators
    location_patterns = [
        r"(.+?)\s+in\s+(.+)$",  # "McDonald's in Dallas, TX"
        r"(.+?)\s+near\s+(.+)$",  # "Pizza near Austin"
        r"(.+?)\s+at\s+(.+)$",  # "Starbucks at Dallas"
        r"(.+?)\s+(.+?,\s*[A-Z]{2})$",  # "McDonald's Dallas, TX"
        r"(.+?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,?\s*[A-Z]{2,})$",  # "McDonald's Dallas TX"
    ]

    for pattern in location_patterns:
        match = re.match(pattern, query.strip(), re.IGNORECASE)
        if match:
            business_name = match.group(1).strip()
            location = match.group(2).strip()
            return business_name, location

    return query.strip(), None


def _build_search_params(query, cuisine, lat, lng, radius_miles, api_key):
    """Build search parameters using centralized Google Places service."""
    from app.services.google_places_service import get_google_places_service

    # Extract location from query if present
    business_query, extracted_location = _extract_location_from_query(query)

    if extracted_location:
        current_app.logger.info(f"Extracted location from query: '{business_query}' + '{extracted_location}'")

    # Build the search query
    search_query = business_query
    if cuisine:
        search_query += f" {cuisine} restaurant"

    # Add extracted location to search query for better results
    if extracted_location:
        search_query += f" {extracted_location}"

    # Use centralized service for search
    places_service = get_google_places_service()

    # Determine location for search
    location = None
    if lat and lng:
        location = (float(lat), float(lng))

    # Use the centralized search with fallback logic
    places = places_service.search_places_with_fallback(
        query=search_query, location=location, radius_miles=float(radius_miles), cuisine=cuisine, max_results=20
    )

    # Return the places data directly (the route will handle the response formatting)
    return places


def _build_photo_urls(photos, api_key):
    """Build photo URLs from Google Places photo references using centralized service."""
    from app.services.google_places_service import get_google_places_service

    places_service = get_google_places_service()
    return places_service.build_photo_urls(photos, api_key)


def _build_reviews_summary(reviews):
    """Build reviews summary from Google Places reviews using centralized service."""
    from app.services.google_places_service import get_google_places_service

    places_service = get_google_places_service()
    return places_service.build_reviews_summary(reviews)


def _validate_search_params():
    """Validate search parameters and return error response if invalid."""
    query = request.args.get("query", "")
    if not query:
        return None, jsonify({"error": "Query parameter is required"}), 400

    api_key = current_app.config.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return None, jsonify({"error": "Google Maps API key not configured"}), 500

    return (
        {
            "query": query,
            "lat": request.args.get("lat"),
            "lng": request.args.get("lng"),
            "radius_miles": request.args.get("radius_miles", "5"),
            "cuisine": request.args.get("cuisine", ""),
            "min_rating": request.args.get("minRating"),
            "max_price_level": request.args.get("maxPriceLevel"),
            "max_results": int(request.args.get("maxResults", "20")),
            "api_key": api_key,
        },
        None,
        None,
    )


def _filter_place_by_criteria(place, min_rating, max_price_level):
    """Filter place based on rating and price level criteria using centralized service."""
    from app.services.google_places_service import get_google_places_service

    places_service = get_google_places_service()
    return places_service.filter_places_by_criteria([place], min_rating, max_price_level)


def _process_search_result_place(place, api_key):
    """Process a single place from search results using centralized service."""
    from app.services.google_places_service import get_google_places_service

    places_service = get_google_places_service()
    return places_service.process_search_result_place(place)


@bp.route("/api/places/search", methods=["GET"])
@login_required
def search_places():
    """Search for places using Google Places API with comprehensive data."""
    # Validate parameters
    params, error_response, status_code = _validate_search_params()
    if error_response:
        return error_response, status_code

    try:
        from app.services.google_places_service import get_google_places_service

        # Get places using centralized service
        places = _build_search_params(
            params["query"], params["cuisine"], params["lat"], params["lng"], params["radius_miles"], params["api_key"]
        )

        # Process results using centralized service
        places_service = get_google_places_service()
        results = []

        for place in places[: params["max_results"]]:
            # Filter by criteria using centralized service
            if not places_service.filter_places_by_criteria([place], params["min_rating"], params["max_price_level"]):
                continue

            # Process place using centralized service
            processed_place = places_service.process_search_result_place(place)
            if processed_place:
                # Add additional processing for photos and reviews if needed
                processed_place["photos"] = places_service.build_photo_urls(place.get("photos", []))
                processed_place["reviews"] = places_service.build_reviews_summary(place.get("reviews", []))
                results.append(processed_place)

        return jsonify(
            {
                "data": {
                    "results": results,
                    "search_params": {
                        "query": params["query"],
                        "lat": params["lat"],
                        "lng": params["lng"],
                        "radius_miles": float(params["radius_miles"]) if params["radius_miles"] else None,
                        "cuisine": params["cuisine"],
                        "min_rating": float(params["min_rating"]) if params["min_rating"] else None,
                        "max_price_level": int(params["max_price_level"]) if params["max_price_level"] else None,
                    },
                },
                "status": "OK",
            }
        )

    except Exception as e:
        current_app.logger.error(f"Google Places API error: {e}")
        return jsonify({"error": "Failed to fetch places data"}), 500


@bp.route("/api/places/details/<place_id>", methods=["GET"])
@login_required
def get_place_details(place_id):
    """Get place details using Google Places API with comprehensive field mapping."""
    current_app.logger.info(f"=== get_place_details called with place_id: {place_id} ===")

    api_key = current_app.config.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        current_app.logger.error("Google Maps API key not configured")
        return jsonify({"error": "Google Maps API key not configured"}), 500

    try:
        from app.services.google_places_service import get_google_places_service

        # Use centralized service to get place details
        places_service = get_google_places_service()
        place = places_service.get_place_details(place_id, "comprehensive")

        if not place:
            current_app.logger.error(f"Failed to retrieve place details for {place_id}")
            return jsonify({"error": "Place not found"}), 404

        # Debug: Log the address components received from Google Places API
        address_components = place.get("addressComponents", [])
        current_app.logger.info(f"Raw address components from Google Places API: {address_components}")

        # Parse address components using service layer
        address_data = places_service.parse_address_components(address_components)
        current_app.logger.info(f"Parsed address data: {address_data}")

        # Get restaurant name from new API structure
        restaurant_name = (
            place.get("displayName", {}).get("text")
            if isinstance(place.get("displayName"), dict)
            else place.get("displayName", "")
        )

        # Determine cuisine and service level using centralized service
        current_app.logger.info(f"Analyzing restaurant types for place: {restaurant_name}")
        current_app.logger.info(f"Types from Google Places: {place.get('types', [])}")
        current_app.logger.info(f"Primary Type: {place.get('primaryType', 'Unknown')}")
        cuisine, service_level = places_service.analyze_restaurant_types(place.get("types", []), place)
        current_app.logger.info(f"Classification results - Cuisine: {cuisine}, Service Level: {service_level}")

        # Map all fields comprehensively for new API
        price_level_value = _convert_price_level_to_int(place.get("priceLevel"))
        current_app.logger.info(f"Price level conversion: {place.get('priceLevel')} -> {price_level_value}")
        current_app.logger.info(f"Address data being used in mapping: {address_data}")

        # Debug: Log key Google Places data
        current_app.logger.info("=== GOOGLE PLACES DATA DEBUG ===")
        current_app.logger.info(f"Place ID: {place_id}")
        current_app.logger.info(f"Name: {restaurant_name}")
        current_app.logger.info(f"Price Level (raw): {place.get('priceLevel')}")
        current_app.logger.info(f"Price Level (converted): {price_level_value}")
        current_app.logger.info(f"Rating: {place.get('rating')}")
        current_app.logger.info(f"Types: {place.get('types', [])}")
        current_app.logger.info(f"Primary Type: {place.get('primaryType')}")
        current_app.logger.info(f"Formatted Address: {place.get('formattedAddress')}")
        current_app.logger.info(f"Address Components Count: {len(address_components)}")
        current_app.logger.info(f"Parsed Address - Line 1: '{address_data.get('address_line_1')}'")
        current_app.logger.info(f"Parsed Address - Line 2: '{address_data.get('address_line_2')}'")
        current_app.logger.info(f"Parsed Address - City: '{address_data.get('city')}'")
        current_app.logger.info(f"Parsed Address - State: '{address_data.get('state')}'")
        current_app.logger.info(f"Parsed Address - Postal: '{address_data.get('postal_code')}'")
        current_app.logger.info(f"Parsed Address - Country: '{address_data.get('country')}'")
        current_app.logger.info("=== END GOOGLE PLACES DATA DEBUG ===")
        mapped_data = {
            # Basic Information
            "name": restaurant_name,
            "type": "restaurant",  # Default for Google Places restaurants
            "description": generate_description(place),
            # Location Information (parsed from addressComponents using standardized mapping)
            "address_line_1": address_data.get("address_line_1", ""),  # Primary street address
            "address_line_2": address_data.get("address_line_2", ""),  # Secondary address (apartment/suite)
            "city": address_data.get("city", ""),
            "state": address_data.get("state", ""),
            "postal_code": address_data.get("postal_code", ""),
            "country": address_data.get("country", ""),
            # Contact Information
            "phone": place.get("nationalPhoneNumber"),
            "website": place.get("websiteUri"),
            "email": None,  # Google Places doesn't provide email
            "google_place_id": place_id,
            # Business Details
            "cuisine": cuisine,
            "service_level": service_level,
            "is_chain": places_service.detect_chain_restaurant(restaurant_name, place),
            "rating": place.get("rating"),
            "notes": generate_notes(place),
            # Additional Google Data (new API structure)
            "formatted_address": place.get("formattedAddress"),
            "types": place.get("types", []),
            "primary_type": place.get("primaryType"),  # NEW: Primary business type
            "address_components": place.get("addressComponents", []),
            "price_level": price_level_value,
            "opening_hours": place.get("regularOpeningHours", {}),
            "current_opening_hours": place.get("currentOpeningHours", {}),
            "location": place.get("location", {}),
            # Extract coordinates from location for easier access
            "latitude": place.get("location", {}).get("latitude"),
            "longitude": place.get("location", {}).get("longitude"),
            "editorial_summary": place.get("editorialSummary", {}),
            "generative_summary": place.get("generativeSummary", {}),  # NEW: AI-generated summary
            "user_ratings_total": place.get("userRatingCount"),
            "plus_code": place.get("plusCode", {}),
            "photos": place.get("photos", []),
            "reviews": place.get("reviews", []),
            # NEW: Enhanced restaurant data
            "payment_options": place.get("paymentOptions", {}),
            "accessibility_options": place.get("accessibilityOptions", {}),
            "parking_options": place.get("parkingOptions", {}),
            "restroom": place.get("restroom"),
            "outdoor_seating": place.get("outdoorSeating"),
            "takeout": place.get("takeout"),
            "delivery": place.get("delivery"),
            "dine_in": place.get("dineIn"),
            "reservable": place.get("reservable"),
            # Service options
            "serves_breakfast": place.get("servesBreakfast"),
            "serves_lunch": place.get("servesLunch"),
            "serves_dinner": place.get("servesDinner"),
            "serves_beer": place.get("servesBeer"),
            "serves_wine": place.get("servesWine"),
            "serves_brunch": place.get("servesBrunch"),
            "serves_vegetarian_food": place.get("servesVegetarianFood"),
            # NEW: Additional attributes from Places API (New)
            "live_music": place.get("liveMusic"),
            "menu_for_children": place.get("menuForChildren"),
            "serves_cocktails": place.get("servesCocktails"),
            "serves_dessert": place.get("servesDessert"),
            "serves_coffee": place.get("servesCoffee"),
            "good_for_children": place.get("goodForChildren"),
            "allows_dogs": place.get("allowsDogs"),
            "good_for_groups": place.get("goodForGroups"),
            "good_for_watching_sports": place.get("goodForWatchingSports"),
            # Note: business_status is time-sensitive and not stored permanently
        }

        # Debug logging before JSON response
        current_app.logger.info(f"Final mapped_data price_level: {mapped_data.get('price_level')}")
        current_app.logger.info(
            f"Final mapped_data address fields: address_line_1='{mapped_data.get('address_line_1')}', address_line_2='{mapped_data.get('address_line_2')}', city='{mapped_data.get('city')}', state='{mapped_data.get('state')}', postal_code='{mapped_data.get('postal_code')}', country='{mapped_data.get('country')}'"
        )
        current_app.logger.info(f"Final mapped_data keys: {list(mapped_data.keys())}")
        current_app.logger.info(f"Final mapped_data description: {mapped_data.get('description')}")
        return jsonify(mapped_data)

    except requests.RequestException as e:
        current_app.logger.error(f"Google Places API error: {e}")
        return jsonify({"error": "Failed to fetch place details"}), 500


def get_cuisine_choices():
    """Get list of cuisine choices for dropdowns."""
    return [
        "Afghan",
        "Albanian",
        "American",
        "Argentine",
        "Bangladeshi",
        "Barbecue",
        "Bosnian",
        "Brazilian",
        "Bulgarian",
        "Cajun/Creole",
        "Cambodian",
        "Chinese",
        "Croatian",
        "Czech",
        "Danish",
        "Estonian",
        "Ethiopian",
        "Filipino",
        "Finnish",
        "French",
        "German",
        "Greek",
        "Hungarian",
        "Indian",
        "Indonesian",
        "Irish",
        "Italian",
        "Japanese",
        "Korean",
        "Lebanese",
        "Mediterranean",
        "Mexican",
        "Middle Eastern",
        "Mongolian",
        "Moroccan",
        "Myanmar",
        "Nepalese",
        "Norwegian",
        "Pakistani",
        "Peruvian",
        "Persian",
        "Pizza",
        "Polish",
        "Romanian",
        "Russian",
        "Seafood",
        "Spanish",
        "Steakhouse",
        "Sushi",
        "Swedish",
        "Taiwanese",
        "Tex-Mex",
        "Thai",
        "Turkish",
        "Ukrainian",
        "Vietnamese",
    ]


def _convert_price_level_to_int(price_level):
    """Convert Google Places price level to integer using centralized service."""
    from app.services.google_places_service import get_google_places_service

    places_service = get_google_places_service()
    return places_service.convert_price_level_to_int(price_level)


def detect_chain_restaurant(name, place_data=None):
    """Detect if restaurant is likely a chain using centralized service."""
    from app.services.google_places_service import get_google_places_service

    places_service = get_google_places_service()
    return places_service.detect_chain_restaurant(name, place_data)


def generate_description(place):
    """Generate a description from Google Places data using centralized service."""
    from app.services.google_places_service import get_google_places_service

    places_service = get_google_places_service()
    return places_service.generate_description(place)


def generate_notes(place):
    """Generate notes from Google Places data using centralized service."""
    from app.services.google_places_service import get_google_places_service

    places_service = get_google_places_service()
    return places_service.generate_notes(place)


@bp.route("/")
@login_required
def list_restaurants():
    """Show a list of all restaurants with pagination."""
    # Get pagination parameters with type hints
    page = request.args.get("page", 1, type=int)
    # Check for per_page in URL params first, then cookie, then default
    per_page = request.args.get("per_page", type=int)
    if per_page is None:
        per_page = _get_page_size_from_cookie("restaurant_page_size", PER_PAGE)

    # Get all restaurants and stats
    restaurants, stats = services.get_restaurants_with_stats(current_user.id, request.args)

    # Handle pagination or show all
    total_restaurants = len(restaurants)
    if per_page == SHOW_ALL:
        # Show all restaurants without pagination
        paginated_restaurants = restaurants
        total_pages = 1
        page = 1
    else:
        # Calculate pagination with bounds checking
        total_pages = max(1, (total_restaurants + per_page - 1) // per_page) if total_restaurants else 1
        page = max(1, min(page, total_pages))  # Ensure page is within bounds
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_restaurants = restaurants[start_idx:end_idx]

    # Get filter options for the filter form
    filter_options = services.get_filter_options(current_user.id)

    # Extract current filter values
    filters = services.get_restaurant_filters(request.args)

    return render_template(
        "restaurants/list.html",
        restaurants=paginated_restaurants,
        total_spent=stats.get("total_spent", 0),
        avg_price_per_person=stats.get("avg_price_per_person", 0),
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        total_restaurants=total_restaurants,
        search=filters["search"],
        cuisine=filters["cuisine"],
        service_level=filters["service_level"],
        city=filters["city"],
        is_chain=filters["is_chain"],
        rating_min=filters["rating_min"],
        rating_max=filters["rating_max"],
        **filter_options,
    )


def _create_ajax_success_response(restaurant, is_new):
    """Create AJAX success response for restaurant creation."""
    if is_new:
        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Restaurant added successfully!",
                    "restaurant_id": restaurant.id,
                    "redirect_url": url_for("restaurants.restaurant_details", restaurant_id=restaurant.id),
                }
            ),
            201,  # Created
        )

    # Restaurant already exists - return 409 Conflict
    return (
        jsonify(
            {
                "status": "conflict",
                "message": (
                    f"A restaurant with the name '{restaurant.name}' in "
                    f"'{restaurant.city or 'unknown location'}' already exists."
                ),
                "restaurant_id": restaurant.id,
                "redirect_url": url_for("restaurants.restaurant_details", restaurant_id=restaurant.id),
            }
        ),
        409,  # Conflict
    )


def _create_ajax_error_response(exception, restaurant_id=None):
    """Create AJAX error response for restaurant creation errors."""
    if isinstance(exception, (DuplicateGooglePlaceIdError, DuplicateRestaurantError)):
        return (
            jsonify(
                {
                    "status": "conflict",
                    "message": exception.message,
                    "restaurant_id": exception.existing_restaurant.id,
                    "redirect_url": url_for(
                        "restaurants.restaurant_details", restaurant_id=exception.existing_restaurant.id
                    ),
                }
            ),
            409,  # Conflict
        )

    # Generic error
    return jsonify({"status": "error", "message": f"Error saving restaurant: {str(exception)}"}), 400


def _handle_restaurant_creation_success(restaurant, is_new, is_ajax):
    """Handle successful restaurant creation based on request type."""
    if is_ajax:
        return _create_ajax_success_response(restaurant, is_new)

    # Regular form submission - redirect without flash messages
    if is_new:
        return redirect(url_for("restaurants.list_restaurants"))
    return redirect(url_for("restaurants.restaurant_details", restaurant_id=restaurant.id))


def _handle_restaurant_creation_error(exception, is_ajax):
    """Handle restaurant creation errors based on request type."""
    if is_ajax:
        return _create_ajax_error_response(exception)

    # Regular form submission - flash message
    if isinstance(exception, (DuplicateGooglePlaceIdError, DuplicateRestaurantError)):
        flash(exception.message, "warning")
    else:
        flash(f"Error saving restaurant: {str(exception)}", "error")

    return None


def _process_restaurant_form_submission(form, is_ajax):
    """Process restaurant form submission and return appropriate response."""
    try:
        restaurant, is_new = services.create_restaurant(current_user.id, form)
        return _handle_restaurant_creation_success(restaurant, is_new, is_ajax)
    except (DuplicateGooglePlaceIdError, DuplicateRestaurantError, Exception) as e:
        return _handle_restaurant_creation_error(e, is_ajax)


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add_restaurant():
    """Add a new restaurant or redirect to existing one.

    If a restaurant with the same name and city already exists for the user,
    redirects to the existing restaurant's page instead of creating a duplicate.
    Handles both regular form submissions and AJAX requests.
    """
    form = RestaurantForm()
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if form.validate_on_submit():
        response = _process_restaurant_form_submission(form, is_ajax)
        if response:
            return response

    # Handle form validation errors for AJAX requests
    if request.method == "POST" and is_ajax:
        return jsonify({"status": "error", "message": "Form validation failed", "errors": form.errors}), 400

    return render_template("restaurants/form.html", form=form, is_edit=False, cuisine_choices=get_cuisine_choices())


@bp.route("/<int:restaurant_id>", methods=["GET", "POST"])
@login_required
def restaurant_details(restaurant_id):
    """View and update restaurant details with expenses.

    GET: Display restaurant details with expenses
    POST: Update restaurant details
    """
    # Get the restaurant with its expenses relationship loaded
    stmt = (
        select(Restaurant)
        .options(joinedload(Restaurant.expenses))
        .where(Restaurant.id == restaurant_id, Restaurant.user_id == current_user.id)
    )
    restaurant = db.session.scalar(stmt)

    if not restaurant:
        abort(404, "Restaurant not found")

    # Handle form submission
    if request.method == "POST":
        form = RestaurantForm()
        if form.validate_on_submit():
            try:
                # Update restaurant with form data
                services.update_restaurant(restaurant.id, current_user.id, form)
                flash("Restaurant updated successfully!", "success")
                return redirect(url_for("restaurants.restaurant_details", restaurant_id=restaurant.id))
            except Exception as e:
                flash(f"Error updating restaurant: {str(e)}", "danger")
        else:
            # Form validation failed
            for field, errors in form.errors.items():
                for error in errors:
                    field_obj = getattr(form, field, None)
                    if field_obj and hasattr(field_obj, "label") and field_obj.label:
                        field_name = field_obj.label.text
                    else:
                        field_name = field.replace("_", " ").title()
                    flash(f"{field_name}: {error}", "danger")

            # Pre-populate form with submitted data
            form = RestaurantForm(data=request.form)
            return render_template(
                "restaurants/detail.html",
                restaurant=restaurant,
                expenses=sorted(restaurant.expenses, key=lambda x: x.date, reverse=True),
                form=form,
                is_edit=True,
            )

    # Load expenses for the restaurant
    expenses = sorted(restaurant.expenses, key=lambda x: x.date, reverse=True)

    # Calculate expense statistics
    expense_stats = calculate_expense_stats(restaurant_id, current_user.id)

    return render_template(
        "restaurants/detail.html",
        restaurant=restaurant,
        expenses=expenses,
        expense_stats=expense_stats,
        form=RestaurantForm(obj=restaurant),
    )


@bp.route("/<int:restaurant_id>/edit", methods=["GET", "POST"])
@login_required
def edit_restaurant(restaurant_id):
    """Edit restaurant details using the same form as add_restaurant.

    GET: Display form pre-populated with restaurant data
    POST: Update restaurant with form data
    """
    # Get the restaurant
    restaurant = db.session.scalar(
        select(Restaurant).where(Restaurant.id == restaurant_id, Restaurant.user_id == current_user.id)
    )

    if not restaurant:
        abort(404, "Restaurant not found")

    form = RestaurantForm()

    if form.validate_on_submit():
        try:
            # Update restaurant with form data
            services.update_restaurant(restaurant.id, current_user.id, form)
            # Redirect without flash message - success feedback handled by destination page
            return redirect(url_for("restaurants.restaurant_details", restaurant_id=restaurant.id))
        except Exception as e:
            flash(f"Error updating restaurant: {str(e)}", "danger")
    elif request.method == "GET":
        # Pre-populate form with existing data
        form = RestaurantForm(obj=restaurant)

    return render_template(
        "restaurants/form.html", form=form, is_edit=True, restaurant=restaurant, cuisine_choices=get_cuisine_choices()
    )


@bp.route("/delete/<int:restaurant_id>", methods=["POST"])
@login_required
def delete_restaurant(restaurant_id):
    """Delete a restaurant.

    This endpoint handles both HTML form submissions and JSON API requests.
    For HTML, it redirects to the restaurant list with a flash message.
    For JSON, it returns a JSON response with the result.
    """
    try:
        success, message = services.delete_restaurant_by_id(restaurant_id, current_user.id)

        if request.is_json or request.content_type == "application/json":
            if success:
                return jsonify(
                    {"success": True, "message": str(message), "redirect": url_for("restaurants.list_restaurants")}
                )
            else:
                return jsonify({"success": False, "error": str(message)}), 400

        # For HTML form submissions
        flash(message, "success" if success else "error")
        return redirect(url_for("restaurants.list_restaurants"))

    except Exception as e:
        current_app.logger.error(f"Error deleting restaurant {restaurant_id}: {str(e)}")
        if request.is_json or request.content_type == "application/json":
            return jsonify({"success": False, "error": "An error occurred while deleting the restaurant"}), 500

        flash("An error occurred while deleting the restaurant", "error")
        return redirect(url_for("restaurants.list_restaurants"))


@bp.route("/clear-place-id/<int:restaurant_id>", methods=["POST"])
@login_required
@admin_required
def clear_place_id(restaurant_id):
    """Clear the Google Place ID for a restaurant (admin only).

    This endpoint allows admin users to remove the Google Place ID association
    from a restaurant, which will disable Google Maps integration.
    """
    try:
        # Get the restaurant and verify it belongs to the user or user is admin
        restaurant = services.get_restaurant_for_user(restaurant_id, current_user.id)
        if not restaurant and not current_user.is_admin:
            flash("Restaurant not found.", "error")
            return redirect(url_for("restaurants.list_restaurants"))

        # If not found by user_id, try to find it as admin
        if not restaurant and current_user.is_admin:
            restaurant = db.session.get(Restaurant, restaurant_id)
            if not restaurant:
                flash("Restaurant not found.", "error")
                return redirect(url_for("restaurants.list_restaurants"))

        # Clear the Google Place ID
        old_place_id = restaurant.google_place_id
        restaurant.google_place_id = None
        db.session.commit()

        flash(f"Google Place ID cleared successfully for {restaurant.name}.", "success")
        current_app.logger.info(
            f"Admin {current_user.username} cleared Google Place ID {old_place_id} for restaurant {restaurant.name} (ID: {restaurant_id})"
        )

        return redirect(url_for("restaurants.restaurant_details", restaurant_id=restaurant_id))

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error clearing Google Place ID for restaurant {restaurant_id}: {str(e)}")
        flash("An error occurred while clearing the Google Place ID.", "error")
        return redirect(url_for("restaurants.restaurant_details", restaurant_id=restaurant_id))


@bp.route("/export")
@login_required
def export_restaurants():
    """Export restaurants as CSV or JSON."""
    format_type = request.args.get("format", "csv").lower()

    # Get the data from the service
    restaurants = services.export_restaurants_for_user(current_user.id)

    if not restaurants:
        flash("No restaurants found to export", "warning")
        return redirect(url_for("restaurants.list_restaurants"))

    if format_type == "json":
        response = make_response(json.dumps(restaurants, indent=2))
        response.headers["Content-Type"] = "application/json"
        response.headers["Content-Disposition"] = "attachment; filename=restaurants.json"
        return response

    # Default to CSV format
    output = io.StringIO()
    writer = csv.DictWriter(
        output, fieldnames=restaurants[0].keys() if restaurants else [], quoting=csv.QUOTE_NONNUMERIC
    )
    writer.writeheader()
    writer.writerows(restaurants)

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = "attachment; filename=restaurants.csv"
    return response


def _validate_import_file(file):
    """Validate the uploaded file for restaurant import.

    Args:
        file: Uploaded file object

    Returns:
        bool: True if file is valid, False otherwise
    """
    if not file or file.filename == "":
        flash("No file selected", "error")
        return False

    if not file.filename.lower().endswith((".csv", ".json")):
        flash("Unsupported file type. Please upload a CSV or JSON file.", "error")
        return False
    return True


def _process_import_file(file, user_id):
    """Process the uploaded file and return import results.

    Args:
        file: Uploaded file object
        user_id: Current user ID

    Returns:
        tuple: (success, result_data) indicating outcome
    """
    current_app.logger.info("Validating file...")
    if not _validate_import_file(file):
        current_app.logger.warning("File validation failed")
        return False, {"message": "File validation failed"}

    current_app.logger.info("File validation passed")

    # Process and save restaurants
    current_app.logger.info("Processing restaurants...")
    success, result_data = services.import_restaurants_from_csv(file, user_id)
    current_app.logger.info(f"Import result: success={success}, data={result_data}")

    return success, result_data


def _handle_import_success(result_data):
    """Handle successful import results and show appropriate messages.

    Args:
        result_data: Dictionary containing import results

    Returns:
        Flask redirect response
    """
    # Show success message for imported restaurants
    if result_data.get("success_count", 0) > 0:
        flash(f"Successfully imported {result_data['success_count']} restaurants.", "success")

    # Show warning toast for skipped duplicates
    if result_data.get("has_warnings", False):
        flash(f"{result_data['skipped_count']} duplicate restaurants were skipped.", "warning")

    return redirect(url_for("restaurants.list_restaurants"))


def _handle_import_error(result_data):
    """Handle import errors and log details.

    Args:
        result_data: Dictionary containing error information
    """
    error_message = result_data.get("message", "Import failed")
    flash(error_message, "danger")

    # Log detailed errors for debugging
    if result_data.get("error_details"):
        current_app.logger.error(f"Import errors: {result_data['error_details']}")


@bp.route("/import", methods=["GET", "POST"])
@login_required
def import_restaurants():
    """Handle restaurant import from file upload."""
    from app.restaurants.forms import RestaurantImportForm

    form = RestaurantImportForm()

    if request.method == "POST" and form.validate_on_submit():
        file = form.file.data
        current_app.logger.info(f"Import request received for file: {file.filename if file else 'None'}")

        if file and file.filename:
            try:
                success, result_data = _process_import_file(file, current_user.id)

                if success:
                    return _handle_import_success(result_data)
                else:
                    _handle_import_error(result_data)

            except ValueError as e:
                current_app.logger.error("ValueError during import: %s", str(e))
                flash(str(e), "danger")
            except Exception as e:
                current_app.logger.error("Error importing restaurants: %s", str(e), exc_info=True)
                flash("An error occurred while importing restaurants.", "danger")
        else:
            current_app.logger.warning("No file selected for import")
            flash("No file selected", "danger")

    return render_template("restaurants/import.html", form=form)


@bp.route("/find-places", methods=["GET", "POST"])
@login_required
def find_places():
    """Search for restaurants using Google Places API.

    This route renders a page where users can search for restaurants
    using Google Places API and add them to their list.

    Returns:
        Rendered template with the Google Places search interface
    """
    # Check if Google Maps API key is configured
    google_maps_api_key = current_app.config.get("GOOGLE_MAPS_API_KEY")
    google_maps_map_id = current_app.config.get("GOOGLE_MAPS_MAP_ID")
    if not google_maps_api_key:
        current_app.logger.warning("Google Maps API key is not configured")
        flash("Google Maps integration is not properly configured. Please contact support.", "warning")

    # Render the Google Places search template
    return render_template(
        "restaurants/places_search.html",
        google_maps_api_key=google_maps_api_key or "",
        google_maps_map_id=google_maps_map_id or "",
    )


def _validate_google_places_request():
    """Validate the incoming Google Places request and return the JSON data.

    Returns:
        tuple: (data, error_response) where error_response is None if validation passes.
              data is a dictionary containing the parsed JSON and CSRF token.
    """
    current_app.logger.info("Validating Google Places request")

    if not request.is_json:
        error_msg = f"Invalid content type: {request.content_type}. Expected application/json"
        current_app.logger.warning(error_msg)
        return None, (jsonify({"success": False, "message": error_msg}), 400)

    try:
        data = request.get_json()
        current_app.logger.debug(f"Received data: {data}")
    except Exception as e:
        error_msg = f"Failed to parse JSON data: {str(e)}"
        current_app.logger.error(error_msg)
        return None, (jsonify({"success": False, "message": error_msg}), 400)

    if not data:
        error_msg = "No data provided in request"
        current_app.logger.warning(error_msg)
        return None, (jsonify({"success": False, "message": error_msg}), 400)

    csrf_token = request.headers.get("X-CSRFToken")
    current_app.logger.debug(f"CSRF Token from headers: {csrf_token}")

    if not csrf_token:
        error_msg = "CSRF token is missing from request headers"
        current_app.logger.warning(error_msg)
        return None, (jsonify({"success": False, "message": error_msg}), 403)

    # Return both the data and CSRF token as a dictionary
    return {"data": data, "csrf_token": csrf_token}, None


def _prepare_restaurant_form(data, csrf_token):
    """Prepare and validate the restaurant form with the provided data.

    Args:
        data: Dictionary containing restaurant data
        csrf_token: CSRF token for form validation

    Returns:
        tuple: (form, error_response) where error_response is None if validation passes
    """
    from app.restaurants.forms import RestaurantForm

    # Ensure data is a dictionary
    if not isinstance(data, dict):
        error_msg = "Invalid data format. Expected a dictionary."
        current_app.logger.error(error_msg)
        return None, (jsonify({"success": False, "message": error_msg}), 400)

    # Detect service level from Google Places data if available
    service_level = None
    if any(key in data for key in ["price_level", "types", "rating", "user_ratings_total"]):
        from app.restaurants.services import detect_service_level_from_google_data

        google_places_data = {
            "price_level": data.get("price_level"),
            "types": data.get("types", []),
            "rating": data.get("rating"),
            "user_ratings_total": data.get("user_ratings_total"),
        }

        detected_level, confidence = detect_service_level_from_google_data(google_places_data)
        if confidence > 0.3:  # Only use if confidence is reasonable
            service_level = detected_level

    form_data = {
        "name": data.get("name", ""),
        "address": data.get("formatted_address") or data.get("address", ""),
        "city": data.get("city", ""),
        "state": data.get("state", ""),
        "postal_code": data.get("postal_code", ""),
        "country": data.get("country", ""),
        "phone": data.get("formatted_phone_number") or data.get("phone", ""),
        "website": data.get("website", ""),
        "google_place_id": data.get("place_id") or data.get("google_place_id", ""),
        "service_level": service_level,
        # Note: coordinates would be looked up dynamically from Google Places API
        "csrf_token": csrf_token,
    }

    current_app.logger.debug(f"Form data prepared: {form_data}")

    form = RestaurantForm(data=form_data)
    current_app.logger.debug("Form created. Validating...")

    if not form.validate():
        errors = {field: errors[0] for field, errors in form.errors.items()}
        current_app.logger.warning(f"Form validation failed: {errors}")
        return None, (jsonify({"success": False, "message": "Validation failed", "errors": errors}), 400)

    return form, None


def _create_restaurant_from_form(form):
    """Create or update a restaurant from the validated form.

    Args:
        form: Validated RestaurantForm instance

    Returns:
        tuple: (restaurant, is_new) if successful, (None, error_response) if failed
    """
    from app.restaurants.services import create_restaurant

    try:
        current_app.logger.debug("Creating restaurant...")
        restaurant, is_new = create_restaurant(current_user.id, form)
        current_app.logger.info(f"Restaurant {'created' if is_new else 'updated'}: {restaurant.id}")
        return (restaurant, is_new), None
    except DuplicateGooglePlaceIdError as e:
        current_app.logger.warning(f"Duplicate Google Place ID: {e.google_place_id}")
        return None, (
            jsonify(
                {
                    "success": False,
                    "error": e.to_dict(),
                    "message": e.message,
                    "redirect_url": url_for("restaurants.restaurant_details", restaurant_id=e.existing_restaurant.id),
                }
            ),
            409,
        )
    except DuplicateRestaurantError as e:
        current_app.logger.warning(f"Duplicate restaurant: {e.name} in {e.city}")
        return None, (
            jsonify(
                {
                    "success": False,
                    "error": e.to_dict(),
                    "message": e.message,
                    "redirect_url": url_for("restaurants.restaurant_details", restaurant_id=e.existing_restaurant.id),
                }
            ),
            409,
        )
    except Exception as e:
        current_app.logger.error(f"Error creating restaurant: {str(e)}", exc_info=True)
        return None, (jsonify({"success": False, "message": "An error occurred while creating the restaurant"}), 500)


@bp.route("/check-restaurant-exists", methods=["POST"])
@login_required
def check_restaurant_exists():
    """Check if a restaurant with the given Google Place ID already exists.

    Expected JSON payload:
    {
        "google_place_id": "ChIJ..."
    }

    Returns:
        JSON response with exists (bool) and restaurant_id (int) if exists
    """
    data = request.get_json()
    if not data or "google_place_id" not in data:
        return jsonify({"success": False, "message": "Missing google_place_id"}), 400

    # Check if a restaurant with this Google Place ID already exists for the current user
    restaurant = Restaurant.query.filter_by(google_place_id=data["google_place_id"], user_id=current_user.id).first()

    return jsonify(
        {
            "success": True,
            "exists": restaurant is not None,
            "restaurant_id": restaurant.id if restaurant else None,
            "restaurant_name": restaurant.name if restaurant else None,
        }
    )


@bp.route("/add-from-google-places", methods=["POST"])
@login_required
def add_from_google_places():
    """Add a new restaurant from Google Places data.

    This endpoint is called via AJAX when a user selects a restaurant
    from the Google Places search results.

    Expected JSON payload:
    {
        "name": "Restaurant Name",
        "address": "123 Main St",
        "city": "City",
        "state": "State",
        "postal_code": "12345",
        "country": "Country",
        "phone": "+1234567890",
        "website": "https://example.com",
        "google_place_id": "ChIJ...",
        # Note: coordinates would be looked up dynamically from Google Places API
    }

    Returns:
        JSON response with success status and redirect URL
    """
    # Validate the request
    validation_result, error_response = _validate_google_places_request()
    if error_response:
        return error_response

    # Extract data and CSRF token from validation result
    data = validation_result["data"]
    csrf_token = validation_result["csrf_token"]

    # Check if restaurant already exists by google_place_id using enhanced error handling
    if "google_place_id" in data and data["google_place_id"]:
        existing_restaurant = Restaurant.query.filter_by(
            google_place_id=data["google_place_id"], user_id=current_user.id
        ).first()

        if existing_restaurant:
            # Return error response to trigger enhanced frontend handling
            error = DuplicateGooglePlaceIdError(data["google_place_id"], existing_restaurant)
            return (
                jsonify(
                    {
                        "success": False,
                        "error": error.to_dict(),
                        "message": error.message,
                        "redirect_url": url_for("restaurants.restaurant_details", restaurant_id=existing_restaurant.id),
                    }
                ),
                409,
            )

    # Prepare the form data
    form, error_response = _prepare_restaurant_form(data, csrf_token)
    if error_response:
        return error_response

    # Create the restaurant
    result, error_response = _create_restaurant_from_form(form)
    if error_response:
        return error_response

    restaurant, is_new = result

    try:
        # Update with Google Places data
        restaurant.update_from_google_places(data)
        db.session.commit()

        # Return success response with message for client-side handling
        message = "Restaurant added successfully!" if is_new else "Restaurant updated with the latest information."

        return jsonify(
            {
                "success": True,
                "is_new": is_new,
                "exists": False,
                "restaurant_id": restaurant.id,
                "message": message,
                "redirect_url": url_for("restaurants.restaurant_details", restaurant_id=restaurant.id),
            }
        )

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error in add_from_google_places: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "An unexpected error occurred"}), 500


@bp.route("/api/search/location", methods=["GET"])
@login_required
def search_restaurants_by_location_api():
    """Search for restaurants within a specified radius of a location.

    Query Parameters:
        latitude: Center latitude for search (required)
        longitude: Center longitude for search (required)
        radius_km: Search radius in kilometers (default: 10.0)
        limit: Maximum number of results (default: 50)

    Returns:
        JSON response with restaurants and distances
    """
    try:
        # Get and validate parameters
        latitude = request.args.get("latitude", type=float)
        longitude = request.args.get("longitude", type=float)
        radius_km = request.args.get("radius_km", 10.0, type=float)
        limit = request.args.get("limit", 50, type=int)

        # Validate required parameters
        if latitude is None or longitude is None:
            return jsonify({"success": False, "message": "latitude and longitude are required parameters"}), 400

        # Validate parameter ranges
        if not (-90 <= latitude <= 90):
            return jsonify({"success": False, "message": "latitude must be between -90 and 90"}), 400

        if not (-180 <= longitude <= 180):
            return jsonify({"success": False, "message": "longitude must be between -180 and 180"}), 400

        if radius_km <= 0:
            return jsonify({"success": False, "message": "radius_km must be positive"}), 400

        if limit <= 0:
            return jsonify({"success": False, "message": "limit must be positive"}), 400

        # Perform the search
        results = search_restaurants_by_location(
            user_id=current_user.id, latitude=latitude, longitude=longitude, radius_km=radius_km, limit=limit
        )

        return jsonify(
            {
                "success": True,
                "results": results,
                "count": len(results),
                "search_params": {"latitude": latitude, "longitude": longitude, "radius_km": radius_km, "limit": limit},
            }
        )

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400

    except Exception as e:
        current_app.logger.error(f"Error in location search: {str(e)}")
        return jsonify({"success": False, "message": "An unexpected error occurred"}), 500


@bp.route("/search", methods=["GET"])
@login_required
def search_restaurants():
    """Search for restaurants by name, cuisine, or location.

    Query Parameters:
        q: Search query string
        page: Page number for pagination
        per_page: Number of results per page
        sort: Field to sort by (name, city, cuisine, etc.)
        order: Sort order (asc or desc)

    Returns:
        Rendered template with search results
    """
    query = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    # Check for per_page in URL params first, then cookie, then default
    per_page = request.args.get("per_page", type=int)
    if per_page is None:
        per_page = _get_page_size_from_cookie("restaurant_page_size", 10)
    sort = request.args.get("sort", "name")
    order = request.args.get("order", "asc")

    # Validate sort field
    valid_sort_fields = ["name", "city", "cuisine", "created_at", "updated_at"]
    if sort not in valid_sort_fields:
        sort = "name"

    # Validate order
    order = order.lower()
    if order not in ["asc", "desc"]:
        order = "asc"

    # Build base query
    stmt = select(Restaurant).filter(Restaurant.user_id == current_user.id)

    # Apply search filters
    if query:
        search = f"%{query}%"
        stmt = stmt.filter(
            (Restaurant.name.ilike(search))
            | (Restaurant.city.ilike(search))
            | (Restaurant.cuisine.ilike(search))
            | (Restaurant.address_line_1.ilike(search))
            | (Restaurant.address_line_2.ilike(search))
        )

    # Import Type for type casting
    from typing import cast

    from sqlalchemy.sql.elements import ColumnElement

    # Apply sorting with proper type checking
    sort_field = getattr(Restaurant, sort, None) if sort else None

    # Ensure we have a valid sort field
    if sort_field is None or not hasattr(sort_field, "desc"):
        sort_field = Restaurant.name

    # Cast to ColumnElement to help mypy understand the type
    sort_field = cast(ColumnElement, sort_field)

    # Apply sort direction with type checking
    sort_expr = sort_field.desc() if order == "desc" else sort_field.asc()
    stmt = stmt.order_by(sort_expr)

    # Paginate results
    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    restaurants = pagination.items

    return render_template(
        "restaurants/search.html",
        restaurants=restaurants,
        query=query,
        pagination=pagination,
        sort=sort,
        order=order,
        per_page=per_page,
        google_maps_api_key=current_app.config.get("GOOGLE_MAPS_API_KEY"),
    )
