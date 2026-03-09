"""Restaurant-related routes for the application."""

import csv
import io
import json
from typing import Any, Optional, Tuple, Union, cast
from urllib.parse import urlparse

from flask import (
    Response,
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
import requests
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
from app.constants.restaurant_types import get_restaurant_type_form_choices_grouped
from app.merchants import services as merchant_services
from app.merchants.models import Merchant
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
from app.utils.address_utils import normalize_state_to_usps
from app.utils.decorators import admin_required

# Constants
DEFAULT_LIST_PAGE_SIZE = 25
MAX_LIST_PAGE_SIZE = 100
LEGACY_COOKIE_PAGE_SIZES = {-1, 10, 25, 50}
_ROUTE_RESTAURANT_FORM = RestaurantForm


def _get_page_size_from_cookie() -> int:
    """Return the legacy restaurant page size preference from the request cookie."""
    raw_value = request.cookies.get("restaurant_page_size")
    try:
        page_size = int(raw_value) if raw_value is not None else 10
    except (TypeError, ValueError):
        return 10
    return page_size if page_size in LEGACY_COOKIE_PAGE_SIZES else 10


def _populate_merchant_choices(form: RestaurantForm, user_id: int) -> None:
    """Populate merchant choices for the form dropdown.

    Args:
        form: The RestaurantForm instance
        user_id: The current user's ID
    """
    if not current_user.has_advanced_features and not current_user.is_admin:
        form.merchant_id.choices = [("", "No Merchant (Basic)")]
        return

    merchants = merchant_services.get_merchants(user_id)
    choices: list[tuple[Any, str] | tuple[Any, str, dict[str, Any]]] = [("", "-- Select Merchant (Optional) --")]
    for m in merchants:
        choices.append((str(m.id), m.name))
    form.merchant_id.choices = choices


def _is_safe_redirect_path(url: str | None) -> bool:
    """Return True if url is a safe internal path for redirect."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if url.startswith(("http://", "https://", "//")):
        return False
    if not url.startswith("/"):
        return False

    parsed = urlparse(url)
    return bool(parsed.path and not parsed.netloc)


def _get_safe_redirect_path(url: str | None) -> str | None:
    """Return a sanitized internal redirect path or None."""
    if not _is_safe_redirect_path(url):
        return None
    return str(url).strip()


def _get_selected_merchant_for_form(form: RestaurantForm, restaurant: Restaurant | None = None) -> Merchant | None:
    """Resolve the merchant currently associated with the form."""
    if restaurant and restaurant.merchant:
        return restaurant.merchant

    merchant_id = getattr(form.merchant_id, "data", None)
    if not merchant_id:
        return None

    return db.session.get(Merchant, merchant_id)


def _render_restaurant_list(
    *,
    paginated_restaurants: list,
    stats: dict,
    total_restaurants: int,
    has_more: bool = False,
    next_offset: int = 0,
    filters: dict,
    filter_options: dict,
    active_tab: str = "restaurants",
    places_mode: str = "my",
    is_htmx: bool = False,
) -> str:
    """Render the restaurant list template with shared context."""
    return render_template(
        "restaurants/list.html",
        restaurants=paginated_restaurants,
        stats=stats,
        total_spent=stats.get("total_spent", 0),
        avg_price_per_person=stats.get("avg_price_per_person", 0),
        total_restaurants=total_restaurants,
        has_more=has_more,
        next_offset=next_offset,
        search=filters["search"],
        cuisine=filters["cuisine"],
        service_level=filters["service_level"],
        city=filters["city"],
        is_chain=filters["is_chain"],
        merchant_status=filters["merchant_status"],
        missing_location_name=filters["missing_location_name"],
        rating_min=filters["rating_min"],
        rating_max=filters["rating_max"],
        active_tab=active_tab,
        places_mode=places_mode,
        is_htmx=is_htmx,
        **filter_options,
    )


def _extract_location_from_query(query: str) -> tuple[str, str | None]:
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


def _build_search_params(
    query: str,
    cuisine: str | None,
    lat: float | None,
    lng: float | None,
    radius_miles: int | None,
    api_key: str | None,
) -> list[dict[str, Any]]:
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

    # Use the centralized search with fallback logic and optimized field masks
    radius_miles_float = float(radius_miles) if radius_miles is not None else 5.0
    cuisine_str = cuisine if cuisine else ""
    places = places_service.search_places_with_fallback(
        query=search_query,
        location=location,
        radius_miles=radius_miles_float,
        cuisine=cuisine_str,
        max_results=10,
    )

    # Return the places data directly (the route will handle the response formatting)
    return places


def _build_photo_urls(photos: list[dict[str, Any]], api_key: str | None) -> list[dict[str, str]]:
    """Build photo URLs from Google Places photo references."""
    from app.services.google_places_service import get_google_places_service

    service = get_google_places_service()
    result = service.build_photo_urls(photos, api_key)
    return result if isinstance(result, list) else []


def _build_reviews_summary(reviews: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build reviews summary from Google Places reviews."""
    from app.services.google_places_service import get_google_places_service

    service = get_google_places_service()
    result = service.build_reviews_summary(reviews)
    return result if isinstance(result, list) else []


def _validate_search_params() -> tuple[dict[str, Any] | None, Response | None, int | None]:
    """Validate search parameters and return error response if invalid."""
    query = request.args.get("query", "")
    if not query:
        return None, jsonify({"error": "Query parameter is required"}), 400

    api_key = current_app.config.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return None, jsonify({"error": "Google Maps API key not configured"}), 500

    requested_max_results = request.args.get("maxResults", "20")
    try:
        max_results = int(requested_max_results)
    except (TypeError, ValueError):
        max_results = 20

    max_results = max(1, min(40, max_results))

    return (
        {
            "query": query,
            "lat": request.args.get("lat"),
            "lng": request.args.get("lng"),
            "radius_miles": request.args.get("radius_miles") or request.args.get("radiusMiles", "5"),
            "cuisine": request.args.get("cuisine", ""),
            "min_rating": request.args.get("minRating"),
            "max_price_level": request.args.get("maxPriceLevel"),
            "max_results": max_results,
            "search_scope": request.args.get("searchScope", "combined"),
            "api_key": api_key,
        },
        None,
        None,
    )


def _filter_place_by_criteria(
    place: dict[str, Any], min_rating: float | None, max_price_level: int | None = None
) -> list[dict[str, Any]]:
    """Filter place based on rating and price level criteria.

    ENTERPRISE TIER: Uses rating field
    PRO TIER: Uses priceLevel field (may be deprecated in new API)
    """
    from app.services.google_places_service import get_google_places_service

    service = get_google_places_service()
    return service.filter_places_by_criteria([place], min_rating, max_price_level)


def _process_search_result_place(place: dict[str, Any], api_key: str | None) -> dict[str, Any] | None:
    """Process a single place from search results."""
    from app.services.google_places_service import get_google_places_service

    places_service = get_google_places_service()
    result = places_service.process_search_result_place(place)
    # Return None if service returns None (matches test expectations)
    return result


def _enhance_place_with_details(processed_place: dict[str, Any], places_service: Any) -> dict[str, Any]:
    """Enhance a processed place with detailed address and price level via extract_restaurant_data (lock-step with CLI/form)."""
    place_id = processed_place.get("place_id") or processed_place.get("google_place_id")
    if not place_id:
        return processed_place

    try:
        detailed_place = places_service.get_place_details(place_id)
        if not detailed_place:
            return processed_place

        google_data = places_service.extract_restaurant_data(detailed_place)
        price_level = google_data.get("price_level")
        price_level_int = _convert_price_level_to_int(price_level) if price_level is not None else None

        processed_place.update(
            {
                "address_line_1": google_data.get("address_line_1", ""),
                "address_line_2": google_data.get("address_line_2", ""),
                "city": google_data.get("city", ""),
                "state": google_data.get("state", ""),
                "postal_code": google_data.get("postal_code", ""),
                "country": google_data.get("country", ""),
                "address": google_data.get("address_line_1", ""),  # Legacy field
                "price_level": price_level_int,
            }
        )
    except Exception as e:
        current_app.logger.warning(f"Failed to get detailed address for {place_id}: {e}")

    return processed_place


def _process_search_results(
    places: list[dict[str, Any]], params: dict[str, Any], places_service: Any
) -> list[dict[str, Any]]:
    """Process search results and return cost-optimized place data.

    Important: do not call Place Details for each result here. That causes N+1
    Enterprise billing. We fetch details only when a user selects a specific place.
    """
    results = []

    for i, place in enumerate(places[: params["max_results"]]):
        # TEMP: Skip filtering to debug
        # Filter by criteria using centralized service
        # filtered = places_service.filter_places_by_criteria([place], params["min_rating"], params["max_price_level"])
        # if not filtered:
        #     continue

        # Process place using centralized service
        processed_place = places_service.process_search_result_place(place)
        if processed_place and processed_place.get("name"):
            # Add additional processing for photos and reviews if needed
            processed_place["photos"] = places_service.build_photo_urls(place.get("photos", []))
            processed_place["reviews"] = places_service.build_reviews_summary(place.get("reviews", []))
            results.append(processed_place)
        else:
            current_app.logger.warning(
                f"Place {i} failed processing: name={processed_place.get('name')}, id={processed_place.get('google_place_id')}"
            )

    return results


@bp.route("/api/places/debug", methods=["GET"])
@login_required
def debug_places() -> Response | tuple[Response, int]:
    """Debug endpoint for testing Google Places API."""
    from app.services.google_places_service import get_google_places_service

    try:
        places_service = get_google_places_service()
        # Test direct Google Places API call
        raw_places = places_service.search_places_by_text("cafe", None, 50000, 5)
        current_app.logger.info(f"Raw places from API: {len(raw_places)}")

        # Test the full processing pipeline
        params = {
            "query": "cafe",
            "lat": None,
            "lng": None,
            "radius_miles": 5,
            "cuisine": "",
            "min_rating": None,
            "max_price_level": None,
            "max_results": 10,
            "api_key": current_app.config.get("GOOGLE_MAPS_API_KEY"),
        }
        query_str = str(params["query"]) if params["query"] else ""
        cuisine_str = str(params["cuisine"]) if params["cuisine"] else None
        lat_float = float(params["lat"]) if params["lat"] is not None else None
        lng_float = float(params["lng"]) if params["lng"] is not None else None
        radius_int = int(params["radius_miles"]) if params["radius_miles"] is not None else None
        api_key_str = str(params["api_key"]) if params["api_key"] else None
        places = _build_search_params(query_str, cuisine_str, lat_float, lng_float, radius_int, api_key_str)
        results = _process_search_results(places, params, places_service)
        response = cast(
            Response,
            jsonify(
                {
                    "raw_count": len(raw_places),
                    "places_count": len(places),
                    "processed_count": len(results),
                    "results": results[:3],
                }
            ),
        )
        return response
    except Exception as e:
        current_app.logger.error(f"Debug endpoint error: {e}")
        error_response = jsonify({"error": str(e)})
        return error_response, 500


def _initialize_places_service() -> tuple[Any, tuple[Response, int] | None]:
    """Initialize Google Places service and handle API key errors."""
    from app.services.google_places_service import get_google_places_service

    try:
        service = get_google_places_service()
        return service, None
    except ValueError as e:
        if "API key" in str(e):
            error_response = jsonify(
                {"error": "Google Places API key not configured. Please configure GOOGLE_MAPS_API_KEY."}
            )
            return None, (error_response, 503)
        raise


def _extract_search_location(params: dict[str, Any]) -> tuple[float, float] | None:
    """Extract and convert location parameters."""
    if not (params.get("lat") and params.get("lng")):
        return None

    location = (float(params["lat"]), float(params["lng"]))
    current_app.logger.info(f"Using location: {location}")
    return location


def _calculate_search_radius(params: dict[str, Any]) -> int:
    """Calculate search radius in meters."""
    radius_miles = float(params.get("radius_miles", 31.0))
    radius_meters = int(radius_miles * 1609.34)
    current_app.logger.info(f"Using radius: {radius_meters} meters for query: {params['query']}")
    return radius_meters


def _perform_places_search(
    places_service: Any, params: dict[str, Any], location: tuple[float, float] | None, radius_meters: int
) -> list[dict[str, Any]]:
    """Perform Google Places search with low-cost combined strategy.

    Combined mode merges text and nearby results (de-duplicated) to improve recall
    while still limiting each upstream call to 20 results.
    """
    max_results = max(1, min(40, int(params.get("max_results", 20))))
    per_call_limit = min(20, max_results)
    search_scope = str(params.get("search_scope") or "combined").lower()

    places: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    def _append_unique(candidates: list[dict[str, Any]]) -> None:
        for candidate in candidates:
            place_id = str(candidate.get("id") or "").strip()
            if place_id and place_id in seen_ids:
                continue
            if place_id:
                seen_ids.add(place_id)
            places.append(candidate)

    should_search_text = search_scope in {"combined", "google", "find", "all"}
    should_search_nearby = bool(location) and search_scope in {"combined", "nearby", "my", "all"}

    if should_search_text:
        current_app.logger.info(
            f"Calling search_places_by_text with query='{params['query']}', location={location}, radius={radius_meters}, limit={per_call_limit}"
        )
        text_places = cast(
            list[dict[str, Any]],
            places_service.search_places_by_text(params["query"], location, radius_meters, per_call_limit),
        )
        _append_unique(text_places)

    if should_search_nearby:
        nearby_places = cast(
            list[dict[str, Any]],
            places_service.search_places_nearby(location, radius_meters, "restaurant", per_call_limit),
        )
        _append_unique(nearby_places)

    # Fallback: if user selected text-oriented scope but got nothing, try nearby once.
    if not places and location and not should_search_nearby:
        fallback_places = cast(
            list[dict[str, Any]],
            places_service.search_places_nearby(location, radius_meters, "restaurant", per_call_limit),
        )
        _append_unique(fallback_places)

    if len(places) > max_results:
        places = places[:max_results]

    return places


def _haversine_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points in miles."""
    import math

    radius_miles = 3959.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_miles * c


def _filter_results_by_radius(
    results: list[dict[str, Any]],
    location: tuple[float, float] | None,
    radius_miles: float | None,
) -> list[dict[str, Any]]:
    """Strictly enforce radius filtering around the requested center point."""
    if not location or radius_miles is None:
        return results

    center_lat, center_lng = location
    filtered: list[dict[str, Any]] = []
    for result in results:
        lat = result.get("latitude")
        lng = result.get("longitude")
        if lat is None or lng is None:
            continue

        try:
            distance = _haversine_miles(center_lat, center_lng, float(lat), float(lng))
        except (TypeError, ValueError):
            continue

        if distance <= radius_miles:
            filtered.append(result)

    return filtered


def _format_search_response(results: list[dict[str, Any]], params: dict[str, Any]) -> Response:
    """Format the search results into JSON response."""
    return jsonify(  # type: ignore[no-any-return]
        {
            "data": {
                "results": results,
                "search_params": {
                    "query": params["query"],
                    "lat": params["lat"],
                    "lng": params["lng"],
                    "radius_miles": (float(params["radius_miles"]) if params["radius_miles"] else None),
                    "cuisine": params["cuisine"],
                    "min_rating": float(params["min_rating"]) if params["min_rating"] else None,
                    "max_price_level": (int(params["max_price_level"]) if params["max_price_level"] else None),
                    "max_results": int(params.get("max_results", 20)),
                    "search_scope": params.get("search_scope", "combined"),
                },
                "meta": {
                    "result_count": len(results),
                    "has_more_hint": len(results) >= int(params.get("max_results", 20)),
                },
            },
            "status": "OK",
        }
    )


@bp.route("/api/places/search", methods=["GET"])
def search_places() -> Response | tuple[Response, int]:
    """Search for places using Google Places API with comprehensive data."""
    current_app.logger.info(f"Search API called with query: {request.args.get('query')}")

    # Validate parameters
    params, error_response, status_code = _validate_search_params()
    if error_response or params is None:
        if error_response and status_code:
            return error_response, status_code
        error_resp = jsonify({"error": "Invalid parameters"})
        return error_resp, 400

    try:
        # Initialize Google Places service
        places_service, service_error_response = _initialize_places_service()
        if service_error_response is not None:
            return service_error_response

        # Extract search parameters
        location = _extract_search_location(params)
        radius_meters = _calculate_search_radius(params)

        # Perform search with fallback logic
        places = _perform_places_search(places_service, params, location, radius_meters)

        # Process results
        results = _process_search_results(places, params, places_service)
        requested_radius = float(params["radius_miles"]) if params.get("radius_miles") else None
        results = _filter_results_by_radius(results, location, requested_radius)

        return _format_search_response(results, params)

    except Exception as e:
        current_app.logger.error(f"Google Places API error: {e}")
        error_resp = jsonify({"error": "Failed to fetch places data"})
        return error_resp, 500


def _map_google_primary_type_to_form_type(primary_type: str | None) -> str:
    """Map Google Places API primaryType to restaurant form type choices."""
    from app.constants.restaurant_types import map_google_primary_type_to_form_type

    return map_google_primary_type_to_form_type(primary_type)


def _log_place_debug_info(
    place_id: str,
    place: dict[str, Any],
    restaurant_name: str,
    address_data: dict[str, Any],
    price_level_value: int | None,
) -> None:
    """Log debug information for place details."""
    current_app.logger.info("=== GOOGLE PLACES DATA DEBUG ===")
    current_app.logger.info(f"Place ID: {place_id}")
    current_app.logger.info(f"Name: {restaurant_name}")
    current_app.logger.info(f"Price Level (raw): {place.get('priceLevel')}")
    current_app.logger.info(f"Price Level (converted): {price_level_value}")
    current_app.logger.info(f"Rating: {place.get('rating')}")
    current_app.logger.info(f"Types: {place.get('types', [])}")
    current_app.logger.info(f"Primary Type: {place.get('primaryType')}")
    current_app.logger.info(f"Formatted Address: {place.get('formattedAddress')}")
    current_app.logger.info(f"Address Components Count: {len(place.get('addressComponents', []))}")
    current_app.logger.info(f"Parsed Address - Line 1: '{address_data.get('address_line_1')}'")
    current_app.logger.info(f"Parsed Address - City: '{address_data.get('city')}'")
    current_app.logger.info(f"Parsed Address - State: '{address_data.get('state')}'")
    current_app.logger.info("=== END GOOGLE PLACES DATA DEBUG ===")


def _extract_restaurant_name(place: dict[str, Any]) -> str:
    """Extract restaurant name from Google Places data."""
    display_name = place.get("displayName", "")
    if isinstance(display_name, dict):
        result = display_name.get("text", "")
        return str(result) if result else ""
    return str(display_name) if display_name else ""


def _map_place_to_restaurant_data(place: dict[str, Any], place_id: str, places_service: Any) -> dict[str, Any]:
    """Map Google Places data to restaurant form data.

    Uses places_service.extract_restaurant_data(place) as the single source for address,
    name, phone, website, state, country, cuisine so CLI validate, UI validate, and
    add-from-search all see the same normalized data.
    """
    from app.utils.url_utils import canonicalize_website_for_storage

    # Single source of truth: same extraction as CLI and API validate
    google_data = places_service.extract_restaurant_data(place)

    # Form-only: type mapping, description, notes, service_level, raw place extras
    analysis_result = places_service.analyze_restaurant_types(place)
    service_level = analysis_result.get("service_level", "casual_dining")
    mapped_type = _map_google_primary_type_to_form_type(google_data.get("primary_type", ""))

    _log_place_debug_info(
        place_id,
        place,
        google_data.get("name"),
        google_data,
        _convert_price_level_to_int(google_data.get("price_level")),
    )

    return {
        # From extract_restaurant_data (lock-step with CLI/validate)
        "name": google_data.get("name", ""),
        "location_name": google_data.get("location_name", ""),
        "address_line_1": google_data.get("address_line_1", ""),
        "address_line_2": google_data.get("address_line_2", ""),
        "city": google_data.get("city", ""),
        "state": google_data.get("state", ""),
        "postal_code": google_data.get("postal_code", ""),
        "country": google_data.get("country", ""),
        "located_within": google_data.get("located_within", ""),
        "phone": google_data.get("phone_number"),
        "website": canonicalize_website_for_storage(google_data.get("website", "") or "") or "",
        "cuisine": google_data.get("cuisine_type", "american"),
        "rating": google_data.get("rating"),
        "formatted_address": google_data.get("formatted_address"),
        "types": google_data.get("types", []),
        "primary_type": google_data.get("primary_type", ""),
        "price_level": _convert_price_level_to_int(google_data.get("price_level")),
        "latitude": google_data.get("latitude"),
        "longitude": google_data.get("longitude"),
        "user_ratings_total": google_data.get("user_rating_count"),
        "google_place_id": google_data.get("google_place_id") or place_id,
        # Form-only fields
        "type": mapped_type,
        "description": generate_description(place),
        "notes": generate_notes(place),
        "email": None,
        "service_level": service_level,
        "address_components": place.get("addressComponents", []),
        "takeout": place.get("takeout"),
        "delivery": place.get("delivery"),
        "dine_in": place.get("dineIn"),
        "reservable": place.get("reservable"),
    }


@bp.route("/api/places/details/<place_id>", methods=["GET"])
@login_required
def get_place_details(place_id: str) -> Response | tuple[Response, int]:
    """Get place details using Google Places API with comprehensive field mapping."""
    current_app.logger.info(f"=== get_place_details called with place_id: {place_id} ===")

    api_key = current_app.config.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        current_app.logger.error("Google Maps API key not configured")
        return jsonify({"error": "Google Maps API key not configured"}), 500

    try:
        from app.services.google_places_service import get_google_places_service

        include_enterprise = str(request.args.get("include_enterprise", "false")).lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        user_has_advanced_features = bool(getattr(current_user, "has_advanced_features", False))
        # Use centralized service to get place details
        places_service = get_google_places_service()
        field_mask = places_service.get_place_details_field_mask(
            use_case="place_details",
            include_enterprise=include_enterprise,
            user_has_advanced_features=user_has_advanced_features,
        )
        place = places_service.get_place_details(place_id, field_mask)

        if not place:
            current_app.logger.error(f"Failed to retrieve place details for {place_id}")
            return jsonify({"error": "Place not found"}), 404

        # Map place data to restaurant format
        mapped_data = _map_place_to_restaurant_data(place, place_id, places_service)
        mapped_data["advanced_features_enabled"] = user_has_advanced_features
        mapped_data["enterprise_fields_requested"] = include_enterprise
        mapped_data["enterprise_fields_used"] = isinstance(field_mask, str) and "nationalPhoneNumber" in field_mask

        response: Response = cast(Response, jsonify(mapped_data))
        return response

    except requests.RequestException as e:
        current_app.logger.error(f"Google Places API error: {e}")
        return jsonify({"error": "Failed to fetch place details"}), 500


def _convert_price_level_to_int(price_level: Any | None) -> int | None:
    """Convert Google Places price level to integer."""
    if price_level is None:
        return None

    if isinstance(price_level, str):
        price_map = {
            "PRICE_LEVEL_FREE": 0,
            "PRICE_LEVEL_INEXPENSIVE": 1,
            "PRICE_LEVEL_MODERATE": 2,
            "PRICE_LEVEL_EXPENSIVE": 3,
            "PRICE_LEVEL_VERY_EXPENSIVE": 4,
        }
        return price_map.get(price_level)

    if isinstance(price_level, int):
        return max(0, min(4, price_level))

    return None


def get_cuisine_choices() -> list[str]:
    """Get list of cuisine choices for dropdowns using centralized constants."""
    from app.constants import get_cuisine_names

    return get_cuisine_names()


def detect_chain_restaurant(name: str, place_data: dict[str, Any] | None = None) -> bool:
    """Detect if restaurant is likely a chain using centralized service."""
    from app.services.google_places_service import get_google_places_service

    places_service = get_google_places_service()
    return places_service.detect_chain_restaurant(name, place_data)


def generate_description(place: dict[str, Any]) -> str:
    """Generate a description from Google Places data using centralized service."""
    from app.services.google_places_service import get_google_places_service

    places_service = get_google_places_service()
    return places_service.generate_description(place)


def generate_notes(place: dict[str, Any]) -> str:
    """Generate notes from Google Places data using centralized service."""
    from app.services.google_places_service import get_google_places_service

    places_service = get_google_places_service()
    notes = places_service.generate_notes(place)
    return notes if notes is not None else ""


@bp.route("/")
@login_required
def list_restaurants() -> Any:
    """Show a list of all restaurants with pagination and tab support."""
    # Get tab parameter (restaurants, places)
    tab = request.args.get("tab", "restaurants")
    if tab == "place":
        tab = "places"
    valid_tabs = ["restaurants", "places"]
    if tab not in valid_tabs:
        # Backwards-compatible merchants tab route now canonicalizes to
        # the dedicated merchants page implementation.
        if request.args.get("tab") == "merchants":
            if not current_user.has_advanced_features and not current_user.is_admin:
                flash("Merchants is an advanced feature", "warning")
                return redirect(url_for("restaurants.list_restaurants", tab="restaurants"))

            redirect_params = {}
            q = request.args.get("q", "").strip()
            category = request.args.get("category", "").strip()
            if q:
                redirect_params["q"] = q
            if category:
                redirect_params["category"] = category
            return redirect(url_for("merchants.list_merchants", **redirect_params))

        tab = "restaurants"

    offset = max(0, request.args.get("offset", 0, type=int))
    limit = min(
        max(1, request.args.get("limit", DEFAULT_LIST_PAGE_SIZE, type=int)),
        MAX_LIST_PAGE_SIZE,
    )

    if tab == "restaurants":
        (
            paginated_restaurants,
            total_restaurants,
            stats,
        ) = services.get_restaurants_with_stats_paginated(current_user.id, request.args, offset=offset, limit=limit)
        has_more = (offset + len(paginated_restaurants)) < total_restaurants
        next_offset = offset + limit
        filter_options = services.get_filter_options(current_user.id)
        filters = services.get_restaurant_filters(request.args)

        is_htmx = request.headers.get("HX-Request") == "true"
        if is_htmx and offset > 0:
            return render_template(
                "restaurants/_list_chunk.html",
                restaurants=paginated_restaurants,
                has_more=has_more,
                next_offset=next_offset,
                total_restaurants=total_restaurants,
                total_spent=stats.get("total_spent", 0),
                search=filters["search"],
                cuisine=filters["cuisine"],
                service_level=filters["service_level"],
                city=filters["city"],
                is_chain=filters["is_chain"],
                merchant_status=filters["merchant_status"],
                missing_location_name=filters["missing_location_name"],
                rating_min=filters["rating_min"],
                rating_max=filters["rating_max"],
            )
    else:
        paginated_restaurants = []
        total_restaurants = 0
        stats = {"total_spent": 0, "avg_price_per_person": 0}
        has_more = False
        next_offset = 0
        filters = services.get_restaurant_filters(request.args)
        filter_options = services.get_filter_options(current_user.id)

    places_mode = request.args.get("places_mode", "find").strip().lower()
    if places_mode not in ["my", "nearby", "find"]:
        places_mode = "my"

    return make_response(
        _render_restaurant_list(
            paginated_restaurants=paginated_restaurants,
            stats=stats,
            total_restaurants=total_restaurants,
            has_more=has_more,
            next_offset=next_offset,
            filters=filters,
            filter_options=filter_options,
            active_tab=tab,
            places_mode=places_mode,
            is_htmx=request.headers.get("HX-Request") == "true",
        )
    )


def _create_ajax_success_response(restaurant: Restaurant, is_new: bool) -> tuple[Response, int]:
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


def _create_ajax_error_response(exception: Exception, restaurant_id: int | None = None) -> tuple[Response, int]:
    """Create AJAX error response for restaurant creation errors."""
    if isinstance(exception, (DuplicateGooglePlaceIdError, DuplicateRestaurantError)):
        return (
            jsonify(
                {
                    "status": "conflict",
                    "message": exception.message,
                    "restaurant_id": exception.existing_restaurant.id,
                    "redirect_url": url_for(
                        "restaurants.restaurant_details",
                        restaurant_id=exception.existing_restaurant.id,
                    ),
                }
            ),
            409,  # Conflict
        )

    # Generic error
    return (
        jsonify({"status": "error", "message": f"Error saving restaurant: {str(exception)}"}),
        400,
    )


def _handle_restaurant_creation_success(
    restaurant: Restaurant, is_new: bool, is_ajax: bool
) -> Response | tuple[Response, int] | None:
    """Handle successful restaurant creation based on request type."""
    if is_ajax:
        return _create_ajax_success_response(restaurant, is_new)

    # Regular form submission - redirect without flash messages
    if is_new:
        return redirect(url_for("restaurants.list_restaurants"))  # type: ignore[return-value]  # type: ignore[return-value]
    return redirect(url_for("restaurants.restaurant_details", restaurant_id=restaurant.id))  # type: ignore[return-value]


def _handle_restaurant_creation_error(exception: Exception, is_ajax: bool) -> Response | tuple[Response, int] | None:
    """Handle restaurant creation errors based on request type."""
    if is_ajax:
        return _create_ajax_error_response(exception)

    # Regular form submission - flash message
    if isinstance(exception, (DuplicateGooglePlaceIdError, DuplicateRestaurantError)):
        flash(exception.message, "warning")
    else:
        flash(f"Error saving restaurant: {str(exception)}", "error")

    return None


def _process_restaurant_form_submission(form: RestaurantForm, is_ajax: bool) -> Response | tuple[Response, int] | None:
    """Process restaurant form submission and return appropriate response."""
    try:
        restaurant, is_new = services.create_restaurant(current_user.id, form)
        return _handle_restaurant_creation_success(restaurant, is_new, is_ajax)
    except (DuplicateGooglePlaceIdError, DuplicateRestaurantError, Exception) as e:
        return _handle_restaurant_creation_error(e, is_ajax)


@bp.route("/places")
@login_required
def list_restaurants_places() -> Any:
    """Redirect to places tab for backwards compatibility."""
    return redirect(url_for("restaurants.list_restaurants", tab="places"), code=302)


@bp.route("/merchants")
@login_required
def list_restaurants_merchants() -> Any:
    """Redirect legacy merchants path to canonical merchants endpoint."""
    if not current_user.has_advanced_features and not current_user.is_admin:
        flash("Merchants is an advanced feature", "warning")
        return redirect(url_for("restaurants.list_restaurants", tab="restaurants"), code=302)
    redirect_params = {}
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    if q:
        redirect_params["q"] = q
    if category:
        redirect_params["category"] = category
    return redirect(url_for("merchants.list_merchants", **redirect_params), code=302)


@bp.route("/add", methods=["GET", "POST"])
@login_required
def add_restaurant() -> str | Response | tuple[Response, int]:
    """Add a new restaurant or redirect to existing one.

    If a restaurant with the same name and city already exists for the user,
    redirects to the existing restaurant's page instead of creating a duplicate.
    Handles both regular form submissions and AJAX requests.
    """
    form = RestaurantForm()
    _populate_merchant_choices(form, current_user.id)
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if request.method == "GET":
        prefill_map = {
            "name": request.args.get("name", "").strip(),
            "location_name": request.args.get("location_name", "").strip(),
            "address_line_1": request.args.get("address_line_1", "").strip(),
            "city": request.args.get("city", "").strip(),
            "state": request.args.get("state", "").strip(),
            "postal_code": request.args.get("postal_code", "").strip(),
            "notes": request.args.get("notes", "").strip(),
            "website": request.args.get("website", "").strip(),
            "cuisine": request.args.get("cuisine", "").strip(),
            "service_level": request.args.get("service_level", "").strip(),
        }
        for field_name, field_value in prefill_map.items():
            if field_value and hasattr(form, field_name):
                getattr(form, field_name).data = field_value

        merchant_id = request.args.get("merchant_id", "").strip()
        if merchant_id.isdigit():
            form.merchant_id.data = int(merchant_id)

    if form.validate_on_submit():
        response = _process_restaurant_form_submission(form, is_ajax)
        if response:
            return response

    # Handle form validation errors for AJAX requests
    if request.method == "POST" and is_ajax:
        return (
            jsonify({"status": "error", "message": "Form validation failed", "errors": form.errors}),
            400,
        )

    return render_template(
        "restaurants/form.html",
        form=form,
        is_edit=False,
        selected_merchant=_get_selected_merchant_for_form(form),
        type_choices_grouped=get_restaurant_type_form_choices_grouped(),
        merchant_categories=merchant_services.get_merchant_categories(),
        merchant_format_category_groups=merchant_services.get_merchant_format_category_groups(),
        merchant_service_levels=merchant_services.get_merchant_service_levels(),
        merchant_cuisine_choices=get_cuisine_choices(),
        merchant_format_labels=merchant_services.MERCHANT_FORMAT_CATEGORY_LABELS,
        restaurant_search_prefill=request.args.get("search_query", "").strip() or request.args.get("name", "").strip(),
    )


@bp.route("/<int:restaurant_id>", methods=["GET", "POST"])
@login_required
def restaurant_details(restaurant_id: int) -> str | Response:
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
        _populate_merchant_choices(form, current_user.id)
        if form.validate_on_submit():
            try:
                # Update restaurant with form data
                services.update_restaurant(restaurant.id, current_user.id, form)
                flash("Restaurant updated successfully!", "success")
                return redirect(url_for("restaurants.restaurant_details", restaurant_id=restaurant.id))  # type: ignore[return-value]
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
                type_choices_grouped=get_restaurant_type_form_choices_grouped(),
                merchant_categories=merchant_services.get_merchant_categories(),
                merchant_format_category_groups=merchant_services.get_merchant_format_category_groups(),
                merchant_service_levels=merchant_services.get_merchant_service_levels(),
                merchant_cuisine_choices=get_cuisine_choices(),
                merchant_format_labels=merchant_services.MERCHANT_FORMAT_CATEGORY_LABELS,
            )

    # Load expenses for the restaurant
    expenses = sorted(restaurant.expenses, key=lambda x: x.date, reverse=True)

    # Calculate expense statistics
    expense_stats = calculate_expense_stats(restaurant_id, current_user.id)

    detail_form = RestaurantForm(obj=restaurant)
    _populate_merchant_choices(detail_form, current_user.id)

    return render_template(
        "restaurants/detail.html",
        restaurant=restaurant,
        expenses=expenses,
        expense_stats=expense_stats,
        form=detail_form,
        type_choices_grouped=get_restaurant_type_form_choices_grouped(),
        merchant_categories=merchant_services.get_merchant_categories(),
        merchant_format_category_groups=merchant_services.get_merchant_format_category_groups(),
        merchant_service_levels=merchant_services.get_merchant_service_levels(),
        merchant_cuisine_choices=get_cuisine_choices(),
        merchant_format_labels=merchant_services.MERCHANT_FORMAT_CATEGORY_LABELS,
    )


@bp.route("/<int:restaurant_id>/edit", methods=["GET", "POST"])
@login_required
def edit_restaurant(restaurant_id: int) -> str | Response:
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
    _populate_merchant_choices(form, current_user.id)

    if form.validate_on_submit():
        try:
            # Update restaurant with form data
            services.update_restaurant(restaurant.id, current_user.id, form)
            safe_next_url = _get_safe_redirect_path(request.form.get("next") or request.args.get("next"))
            if safe_next_url:
                return redirect(safe_next_url)  # type: ignore[return-value]
            # Redirect without flash message - success feedback handled by destination page
            return redirect(url_for("restaurants.restaurant_details", restaurant_id=restaurant.id))  # type: ignore[return-value]
        except (
            DuplicateGooglePlaceIdError,
            DuplicateRestaurantError,
        ) as e:
            # Handle duplicate errors with user-friendly messages
            flash(str(e), "danger")
            # Rollback session to avoid PendingRollbackError
            db.session.rollback()
        except Exception as e:
            flash(f"Error updating restaurant: {str(e)}", "danger")
            # Rollback session to avoid PendingRollbackError
            db.session.rollback()
    elif request.method == "GET":
        # Pre-populate form with existing data
        form = RestaurantForm(obj=restaurant)
        _populate_merchant_choices(form, current_user.id)
        # Normalize state to USPS code so the state picklist selects the right option
        if restaurant.state:
            form.state.data = normalize_state_to_usps(restaurant.state) or restaurant.state

    return render_template(
        "restaurants/form.html",
        form=form,
        is_edit=True,
        restaurant=restaurant,
        selected_merchant=_get_selected_merchant_for_form(form, restaurant),
        type_choices_grouped=get_restaurant_type_form_choices_grouped(),
        merchant_categories=merchant_services.get_merchant_categories(),
        merchant_format_category_groups=merchant_services.get_merchant_format_category_groups(),
        merchant_service_levels=merchant_services.get_merchant_service_levels(),
        merchant_cuisine_choices=get_cuisine_choices(),
        merchant_format_labels=merchant_services.MERCHANT_FORMAT_CATEGORY_LABELS,
        return_url=_get_safe_redirect_path(request.args.get("next")) or "",
    )


@bp.route("/delete/<int:restaurant_id>", methods=["POST"])
@login_required
def delete_restaurant(restaurant_id: int) -> Response | tuple[Response, int]:
    """Delete a restaurant.

    This endpoint handles both HTML form submissions and JSON API requests.
    For HTML, it redirects to the restaurant list with a flash message.
    For JSON, it returns a JSON response with the result.
    """
    try:
        success, message = services.delete_restaurant_by_id(restaurant_id, current_user.id)

        if request.is_json or request.content_type == "application/json":
            if success:
                response: Response = cast(
                    Response,
                    jsonify(
                        {
                            "success": True,
                            "message": str(message),
                            "redirect": url_for("restaurants.list_restaurants"),
                        }
                    ),
                )
                return response
            else:
                error_response: Response = cast(Response, jsonify({"success": False, "error": str(message)}))
                return error_response, 400

        # For HTML form submissions - determine redirect destination
        flash(message, "success" if success else "error")

        # Check if user came from restaurant details page (which would 404 after deletion)
        referrer = request.referrer or ""
        details_url_pattern = f"/restaurants/{restaurant_id}"

        # If referrer is the details page or contains the restaurant ID, go to list
        # Otherwise, try to redirect to referrer if it's safe, or default to list
        if details_url_pattern in referrer:
            redirect_url = url_for("restaurants.list_restaurants")
        elif referrer and referrer.startswith(request.url_root):
            # Safe to redirect to referrer if it's from our own site
            redirect_url = referrer
        else:
            redirect_url = url_for("restaurants.list_restaurants")

        return redirect(redirect_url)  # type: ignore[return-value]

    except Exception as e:
        current_app.logger.error(f"Error deleting restaurant {restaurant_id}: {str(e)}")
        if request.is_json or request.content_type == "application/json":
            return (
                jsonify({"success": False, "error": "An error occurred while deleting the restaurant"}),
                500,
            )

        flash("An error occurred while deleting the restaurant", "error")
        return redirect(url_for("restaurants.list_restaurants"))  # type: ignore[return-value]


@bp.route("/clear-place-id/<int:restaurant_id>", methods=["POST"])
@login_required
@admin_required
def clear_place_id(restaurant_id: int) -> Response | tuple[Response, int]:
    """Clear the Google Place ID for a restaurant (admin only).

    This endpoint allows admin users to remove the Google Place ID association
    from a restaurant, which will disable Google Maps integration.
    """
    try:
        # Get the restaurant and verify it belongs to the user or user is admin
        restaurant = services.get_restaurant_for_user(restaurant_id, current_user.id)
        if not restaurant and not current_user.is_admin:
            flash("Restaurant not found.", "error")
            return redirect(url_for("restaurants.list_restaurants"))  # type: ignore[return-value]  # type: ignore[return-value]

        # If not found by user_id, try to find it as admin
        if not restaurant and current_user.is_admin:
            restaurant = db.session.get(Restaurant, restaurant_id)
            if not restaurant:
                flash("Restaurant not found.", "error")
                return redirect(url_for("restaurants.list_restaurants"))  # type: ignore[return-value]  # type: ignore[return-value]

        # Clear the Google Place ID
        if restaurant:
            old_place_id = restaurant.google_place_id
            restaurant.google_place_id = None
            db.session.commit()

            flash(f"Google Place ID cleared successfully for {restaurant.name}.", "success")
            current_app.logger.info(
                f"Admin {current_user.username} cleared Google Place ID {old_place_id} for restaurant {restaurant.name} (ID: {restaurant_id})"
            )

        return redirect(url_for("restaurants.restaurant_details", restaurant_id=restaurant_id))  # type: ignore[return-value]

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error clearing Google Place ID for restaurant {restaurant_id}: {str(e)}")
        flash("An error occurred while clearing the Google Place ID.", "error")
        return redirect(url_for("restaurants.restaurant_details", restaurant_id=restaurant_id))  # type: ignore[return-value]


def _parse_export_ids(raw_ids: list[str]) -> list[int]:
    """Parse and sanitize export ID list."""
    ids: list[int] = []
    for raw_id in raw_ids:
        for part in raw_id.split(","):
            value = part.strip()
            if not value or not value.isdigit():
                continue
            ids.append(int(value))
    return list(dict.fromkeys(ids))


@bp.route("/export")
@login_required
def export_restaurants() -> Response:
    """Export restaurants as CSV or JSON."""
    format_type = request.args.get("format", "csv").lower()
    is_sample = request.args.get("sample", "false").lower() == "true"
    raw_ids = request.args.getlist("ids")
    restaurant_ids = _parse_export_ids(raw_ids)

    # If sample is requested, generate sample CSV with required fields
    if is_sample:
        sample_data = [
            {
                "name": "Joe's Pizza",
                "location_name": "Downtown",
                "located_within": "Union Square",
                "city": "New York",
                "type": "restaurant",
                "address": "123 Main St",
                "phone": "(555) 123-4567",
                "website": "https://joespizza.com",
                "cuisine": "Italian",
                "notes": "Great thin crust pizza",
            },
            {
                "name": "Coffee House",
                "location_name": "Market Street",
                "located_within": "Ferry Building",
                "city": "San Francisco",
                "type": "cafe",
                "address": "456 Market St",
                "phone": "",
                "website": "",
                "cuisine": "Coffee",
                "notes": "",
            },
        ]

        if format_type == "json":
            response = make_response(json.dumps(sample_data, indent=2))
            response.headers["Content-Type"] = "application/json"
            response.headers["Content-Disposition"] = "attachment; filename=sample_restaurants.json"
            return response

        # Default to CSV format - include required fields (name, city) first
        output = io.StringIO()
        fieldnames = [
            "name",
            "location_name",
            "located_within",
            "city",
            "type",
            "address",
            "phone",
            "website",
            "cuisine",
            "notes",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_NONNUMERIC)
        writer.writeheader()
        writer.writerows(sample_data)

        response = make_response(output.getvalue())
        response.headers["Content-Type"] = "text/csv"
        response.headers["Content-Disposition"] = "attachment; filename=sample_restaurants.csv"
        return response

    if raw_ids and not restaurant_ids:
        flash("No valid restaurants selected for export", "warning")
        return redirect(url_for("restaurants.list_restaurants"))  # type: ignore[return-value]

    # Get the data from the service
    restaurants = services.export_restaurants_for_user(
        current_user.id,
        restaurant_ids if raw_ids else None,
    )

    if not restaurants:
        flash("No restaurants found to export", "warning")
        return redirect(url_for("restaurants.list_restaurants"))  # type: ignore[return-value]

    if format_type == "json":
        response = make_response(json.dumps(restaurants, indent=2))
        response.headers["Content-Type"] = "application/json"
        response.headers["Content-Disposition"] = "attachment; filename=restaurants.json"
        return response

    # Default to CSV format
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=restaurants[0].keys() if restaurants else [],
        quoting=csv.QUOTE_NONNUMERIC,
    )
    writer.writeheader()
    writer.writerows(restaurants)

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv"
    response.headers["Content-Disposition"] = "attachment; filename=restaurants.csv"
    return response


def _validate_import_file(file: Any) -> bool:
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


def _process_import_file(file: Any, user_id: int) -> tuple[bool, dict[str, Any]]:
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


def _handle_import_success(result_data: dict[str, Any]) -> Response:
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

    return cast(Response, redirect(url_for("restaurants.list_restaurants")))


def _handle_import_error(result_data: dict[str, Any]) -> None:
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
def import_restaurants() -> str | Response:
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
def find_places() -> Any:
    """Search for restaurants using Google Places API.

    This route renders a page where users can search for restaurants
    using Google Places API and add them to their list.

    Returns:
        Rendered template with the Google Places search interface
    """
    return redirect(url_for("restaurants.list_restaurants", tab="places", places_mode="find"), code=302)


def _validate_google_places_request() -> tuple[dict[str, Any] | None, tuple[Response, int] | None]:
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


def _prepare_restaurant_form(
    data: dict[str, Any], csrf_token: str
) -> tuple[RestaurantForm | None, tuple[Response, int] | None]:
    """Prepare and validate the restaurant form with the provided data.

    Args:
        data: Dictionary containing restaurant data
        csrf_token: CSRF token for form validation

    Returns:
        tuple: (form, error_response) where error_response is None if validation passes
    """
    from flask import jsonify

    from app.restaurants import forms as restaurant_forms
    from app.utils.url_utils import canonicalize_website_for_storage

    # Detect service level from Google Places data if available (existing/same payload only, no extra Google call)
    # PRO TIER: primaryType, types, price_level. ENTERPRISE: rating, user_ratings_total.
    service_level = None
    if any(
        key in data for key in ["price_level", "types", "rating", "user_ratings_total", "primaryType", "primary_type"]
    ):
        from app.restaurants.services import detect_service_level_from_google_data

        google_places_data = {
            "price_level": data.get("price_level"),
            "priceLevel": data.get("priceLevel"),
            "types": data.get("types", []),
            "primaryType": data.get("primaryType") or data.get("primary_type"),
            "name": data.get("name"),
            "displayName": data.get("displayName"),
            "rating": data.get("rating"),
            "user_ratings_total": data.get("user_ratings_total"),
            "merchant_category": data.get("merchant_category"),
            "merchant_category_hint": data.get("merchant_category_hint"),
        }

        detected_level, confidence = detect_service_level_from_google_data(google_places_data)
        if confidence > 0.3:  # Only use if confidence is reasonable
            service_level = detected_level

    description = (data.get("description") or "").strip()
    form_data = {
        "name": data.get("name", ""),
        "type": data.get("type") or "restaurant",
        "address": data.get("formatted_address") or data.get("address", ""),
        "city": data.get("city", ""),
        "state": data.get("state", ""),
        "postal_code": data.get("postal_code", ""),
        "country": data.get("country", ""),
        "phone": data.get("nationalPhoneNumber") or data.get("phone", ""),
        "website": canonicalize_website_for_storage(data.get("websiteUri") or data.get("website", "")) or "",
        "google_place_id": data.get("id") or data.get("google_place_id", ""),
        "service_level": service_level,
        "description": description[:500] if description else "",
        # Note: coordinates would be looked up dynamically from Google Places API
        "csrf_token": csrf_token,
    }

    current_app.logger.debug(f"Form data prepared: {form_data}")

    form_class = RestaurantForm if RestaurantForm is not _ROUTE_RESTAURANT_FORM else restaurant_forms.RestaurantForm

    form = form_class(data=form_data)
    current_app.logger.debug("Form created. Validating...")

    if not form.validate():
        errors: dict[str, str] = {}
        for field, field_errors in form.errors.items():
            first_error = next(iter(field_errors), "Invalid value")
            errors[field] = str(first_error)
        current_app.logger.warning(f"Form validation failed: {errors}")
        return None, (
            jsonify({"success": False, "message": "Validation failed", "errors": errors}),
            400,
        )

    return form, None


def _create_restaurant_from_form(
    form: RestaurantForm,
) -> tuple[tuple[Restaurant, bool] | None, tuple[Response, int] | None]:
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
        return None, (
            jsonify({"success": False, "message": "An error occurred while creating the restaurant"}),
            500,
        )


@bp.route("/check-restaurant-exists", methods=["POST"])
@login_required
def check_restaurant_exists() -> Response | tuple[Response, int]:
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

    response: Response = jsonify(
        {
            "success": True,
            "exists": restaurant is not None,
            "restaurant_id": restaurant.id if restaurant else None,
            "restaurant_name": restaurant.name if restaurant else None,
        }
    )
    return response


def _check_existing_restaurant_by_place_id(
    data: dict[str, Any],
) -> tuple[Response, int] | None:
    """Check if a restaurant with the given Google Place ID already exists.

    Args:
        data: Dictionary containing restaurant data with optional google_place_id

    Returns:
        Error response tuple if duplicate found, None otherwise
    """
    if "google_place_id" not in data or not data["google_place_id"]:
        return None

    existing_restaurant = Restaurant.query.filter_by(
        google_place_id=data["google_place_id"], user_id=current_user.id
    ).first()

    if existing_restaurant:
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

    return None


def _create_google_places_success_response(restaurant: Restaurant, is_new: bool) -> Response:
    """Create success response for Google Places restaurant creation.

    Args:
        restaurant: The created or updated restaurant
        is_new: Whether the restaurant was newly created

    Returns:
        JSON response with success status and redirect URL
    """
    message = "Restaurant added successfully!" if is_new else "Restaurant updated with the latest information."

    return cast(
        Response,
        jsonify(
            {
                "success": True,
                "is_new": is_new,
                "exists": False,
                "restaurant_id": restaurant.id,
                "message": message,
                "redirect_url": url_for("restaurants.restaurant_details", restaurant_id=restaurant.id),
            }
        ),
    )


@bp.route("/add-from-google-places", methods=["POST"])
@login_required
def add_from_google_places() -> Response | tuple[Response, int]:
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
    if validation_result is None:
        return jsonify({"success": False, "message": "Invalid request"}), 400

    data = validation_result["data"]
    csrf_token = validation_result["csrf_token"]

    # Check if restaurant already exists by google_place_id
    duplicate_error = _check_existing_restaurant_by_place_id(data)
    if duplicate_error:
        return duplicate_error

    # Prepare the form data
    form, error_response = _prepare_restaurant_form(data, csrf_token)
    if error_response:
        return error_response
    if form is None:
        return jsonify({"success": False, "message": "Form validation failed"}), 400

    # Create the restaurant
    result, error_response = _create_restaurant_from_form(form)
    if error_response:
        return error_response
    if result is None:
        return jsonify({"success": False, "message": "Failed to create restaurant"}), 500

    restaurant, is_new = result

    try:
        # Update with Google Places data
        restaurant.update_from_google_places(data)
        db.session.commit()
        return _create_google_places_success_response(restaurant, is_new)

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Unexpected error in add_from_google_places: {str(e)}", exc_info=True)
        return jsonify({"success": False, "message": "An unexpected error occurred"}), 500


@bp.route("/api/search/location", methods=["GET"])
@login_required
def search_restaurants_by_location_api() -> Response | tuple[Response, int]:
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
            return (
                jsonify({"success": False, "message": "latitude and longitude are required parameters"}),
                400,
            )

        # Validate parameter ranges
        if not (-90 <= latitude <= 90):
            return (
                jsonify({"success": False, "message": "latitude must be between -90 and 90"}),
                400,
            )

        if not (-180 <= longitude <= 180):
            return (
                jsonify({"success": False, "message": "longitude must be between -180 and 180"}),
                400,
            )

        if radius_km <= 0:
            return jsonify({"success": False, "message": "radius_km must be positive"}), 400

        if limit <= 0:
            return jsonify({"success": False, "message": "limit must be positive"}), 400

        # Perform the search
        results = search_restaurants_by_location(
            user_id=current_user.id,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            limit=limit,
        )

        return cast(
            Response,
            jsonify(
                {
                    "success": True,
                    "results": results,
                    "count": len(results),
                    "search_params": {
                        "latitude": latitude,
                        "longitude": longitude,
                        "radius_km": radius_km,
                        "limit": limit,
                    },
                }
            ),
        )

    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400

    except Exception as e:
        current_app.logger.error(f"Error in location search: {str(e)}")
        return jsonify({"success": False, "message": "An unexpected error occurred"}), 500


@bp.route("/search", methods=["GET"])
@login_required
def search_restaurants() -> str:
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
        per_page = DEFAULT_LIST_PAGE_SIZE
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
        from sqlalchemy import or_

        stmt = stmt.filter(
            or_(
                Restaurant.name.ilike(search),
                Restaurant.city.ilike(search),
                Restaurant.cuisine.ilike(search),
                Restaurant.address_line_1.ilike(search),
                Restaurant.address_line_2.ilike(search),
            )
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
