"""Restaurant-related routes for the application."""

import csv
import io
import json
import re

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


def _get_regional_bias_from_request():
    """Get regional bias for Google Places API from request headers or configuration.

    Returns:
        str: Country code for regional bias (e.g., 'us', 'ca', 'uk')
    """
    # For now, default to 'us' since this is a US-focused app
    # In the future, this could be enhanced with:
    # - IP geolocation lookup
    # - User profile settings
    # - Accept-Language header parsing
    return "us"


def _build_search_params(query, cuisine, lat, lng, radius_miles, api_key):
    """Build search parameters for NEW Google Places API with smart location handling."""
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

    # Always prioritize text-based search when there's a meaningful query
    if search_query and search_query.strip() and search_query.strip() != "restaurants":
        # Use text search with location bias for better text-based results
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.priceLevel",
        }
        payload = {"textQuery": search_query, "maxResultCount": 20}

        # Add location bias if coordinates are provided
        if lat and lng:
            payload["locationBias"] = {
                "circle": {
                    "center": {"latitude": float(lat), "longitude": float(lng)},
                    "radius": min(float(radius_miles) * 1609.34, 50000),  # Convert miles to meters
                }
            }
    elif lat and lng:
        # No meaningful query - use location-based search
        radius_meters = float(radius_miles) * 1609.34
        url = "https://places.googleapis.com/v1/places:searchNearby"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.priceLevel",
        }
        payload = {
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": float(lat), "longitude": float(lng)},
                    "radius": min(radius_meters, 50000),
                }
            },
            "includedTypes": FOOD_BUSINESS_TYPES,
            "maxResultCount": 20,
        }
    else:
        # Fallback: generic text search
        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.priceLevel",
        }
        payload = {"textQuery": "restaurants", "maxResultCount": 20}

        # For generic searches without location, try to add regional bias
        # This helps prioritize nearby results without requiring exact location
        region_bias = _get_regional_bias_from_request()
        if region_bias:
            payload["locationBias"] = {"region": region_bias}

    return url, headers, payload


def _build_photo_urls(photos, api_key):
    """Build photo URLs from Google Places photo references."""
    photo_list = []
    if photos:
        for photo in photos[:3]:
            photo_list.append(
                {
                    "photo_reference": photo.get("photo_reference"),
                    "url": f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photoreference={photo.get('photo_reference')}&key={api_key}",
                }
            )
    return photo_list


def _build_reviews_summary(reviews):
    """Build reviews summary from Google Places reviews."""
    reviews_list = []
    if reviews:
        for review in reviews[:3]:
            text = review.get("text", "")
            truncated_text = text[:200] + "..." if len(text) > 200 else text
            reviews_list.append(
                {
                    "author_name": review.get("author_name"),
                    "rating": review.get("rating"),
                    "text": truncated_text,
                    "time": review.get("time"),
                }
            )
    return reviews_list


def _get_place_details(place_id, api_key):
    """Get detailed place information including address_components."""
    if not place_id:
        return None

    try:
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            "place_id": place_id,
            "fields": "name,formatted_address,formatted_phone_number,website,rating,types,address_components,opening_hours,price_level,reviews,photos,geometry,vicinity,user_ratings_total,business_status",
            "key": api_key,
        }

        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "OK":
            result = data.get("result", {})
            current_app.logger.info(
                f"Successfully fetched place details for {place_id}: name={result.get('name')}, place_id={result.get('place_id')}"
            )
            current_app.logger.info(f"Place details result keys: {list(result.keys())}")
            return result
        else:
            current_app.logger.warning(f"Failed to get place details for {place_id}: {data.get('status')}")
            return None

    except Exception as e:
        current_app.logger.error(f"Error fetching place details for {place_id}: {e}")
        return None


def _process_place_data(place, api_key):
    """Process individual place data from Google Places API."""
    # Parse address components to extract structured address data
    address_data = parse_address_components(place.get("address_components", []))

    # Debug: Log place data to see what fields are available
    current_app.logger.info(f"Processing place data: place_id={place.get('place_id')}, name={place.get('name')}")
    current_app.logger.info(f"Place object keys: {list(place.keys())}")

    # Try different possible field names for place_id
    place_id = place.get("place_id") or place.get("placeId") or place.get("id")
    current_app.logger.info(f"Resolved place_id: {place_id}")

    return {
        "place_id": place_id,
        "name": place.get("name", "Unknown"),
        "formatted_address": place.get("formatted_address", ""),
        "vicinity": place.get("vicinity", ""),
        # Structured address data
        "address": address_data.get("street_address"),
        "city": address_data.get("city"),
        "state": address_data.get("state"),
        "postal_code": address_data.get("postal_code"),
        "country": address_data.get("country"),
        "address_components": place.get("address_components", []),
        "rating": place.get("rating"),
        "user_ratings_total": place.get("user_ratings_total"),
        "price_level": place.get("price_level"),
        "business_status": place.get("business_status"),
        "types": place.get("types", []),
        "geometry": place.get("geometry"),
        "photos": _build_photo_urls(place.get("photos"), api_key),
        "reviews": _build_reviews_summary(place.get("reviews")),
        "opening_hours": place.get("opening_hours", {}),
        "website": place.get("website"),
        "formatted_phone_number": place.get("formatted_phone_number"),
    }


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
    """Filter place based on rating and price level criteria (new API structure)."""
    # Convert price level to integer using the same logic as storage
    price_level = _convert_price_level_to_int(place.get("priceLevel", place.get("price_level", 0)))
    if price_level is None:
        price_level = 0  # Default to 0 if conversion fails
    if min_rating and place.get("rating", 0) < float(min_rating):
        return False
    if max_price_level and price_level > int(max_price_level):
        return False
    return True


def _process_search_result_place(place, api_key):
    """Process a single place from search results (new API structure)."""
    # Debug: Log the raw place data from search results
    place_id = place.get("id")
    display_name = (
        place.get("displayName", {}).get("text")
        if isinstance(place.get("displayName"), dict)
        else place.get("displayName", "")
    )
    current_app.logger.info(f"Raw place from search: place_id={place_id}, name={display_name}")

    # Get detailed information including address_components
    if not place_id:
        current_app.logger.warning(f"Place has no place_id, skipping: {display_name}")
        return None

    detailed_place = _get_place_details(place_id, api_key)
    if detailed_place:
        # Preserve the original place_id from search results
        detailed_place["id"] = place_id
        return _process_place_data(detailed_place, api_key)
    else:
        # Fallback to basic place data if details fetch fails
        return _process_place_data(place, api_key)


@bp.route("/api/places/search", methods=["GET"])
@login_required
def search_places():
    """Search for places using Google Places API with comprehensive data."""
    # Validate parameters
    params, error_response, status_code = _validate_search_params()
    if error_response:
        return error_response, status_code

    try:
        # Build search parameters and make API request
        url, headers, payload = _build_search_params(
            params["query"], params["cuisine"], params["lat"], params["lng"], params["radius_miles"], params["api_key"]
        )
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Process results (new API structure)
        results = []
        if "places" in data:
            for place in data.get("places", [])[: params["max_results"]]:
                if not _filter_place_by_criteria(place, params["min_rating"], params["max_price_level"]):
                    continue

                processed_place = _process_search_result_place(place, params["api_key"])
                if processed_place:
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
                "status": data.get("status"),
            }
        )

    except requests.RequestException as e:
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
        # Make request to NEW Google Places API with comprehensive fields
        url = f"https://places.googleapis.com/v1/places/{place_id}"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "displayName,formattedAddress,nationalPhoneNumber,websiteUri,location,rating,userRatingCount,priceLevel,editorialSummary,paymentOptions,accessibilityOptions,parkingOptions,restroom,outdoorSeating,servesBreakfast,servesLunch,servesDinner,servesBeer,servesWine,servesBrunch,servesVegetarianFood,delivery,dineIn,takeout,reservable,primaryType,types,addressComponents,regularOpeningHours,currentOpeningHours,plusCode,photos,reviews,generativeSummary",
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        place = response.json()

        # Parse address components (new API structure)
        address_data = parse_address_components(place.get("addressComponents", []))

        # Get restaurant name from new API structure
        restaurant_name = (
            place.get("displayName", {}).get("text")
            if isinstance(place.get("displayName"), dict)
            else place.get("displayName", "")
        )

        # Determine cuisine and service level from types and service options
        current_app.logger.info(f"Analyzing restaurant types for place: {restaurant_name}")
        current_app.logger.info(f"Types from Google Places: {place.get('types', [])}")
        current_app.logger.info(f"Primary Type: {place.get('primaryType', 'Unknown')}")
        cuisine, service_level = analyze_restaurant_types(place.get("types", []), place)
        current_app.logger.info(f"Classification results - Cuisine: {cuisine}, Service Level: {service_level}")

        # If no cuisine detected from types, try name-based detection
        if not cuisine:
            cuisine = detect_cuisine_from_name(restaurant_name)
            current_app.logger.info(f"Detected cuisine from name: {cuisine}")

        # Map all fields comprehensively for new API
        mapped_data = {
            # Basic Information
            "name": restaurant_name,
            "type": "restaurant",  # Default for Google Places restaurants
            "description": generate_description(place),
            # Location Information (parsed from addressComponents)
            "address": address_data.get("street_address"),
            "city": address_data.get("city"),
            "state": address_data.get("state"),
            "postal_code": address_data.get("postal_code"),
            "country": address_data.get("country"),
            # Contact Information
            "phone": place.get("nationalPhoneNumber"),
            "website": place.get("websiteUri"),
            "email": None,  # Google Places doesn't provide email
            "google_place_id": place_id,
            # Business Details
            "cuisine": cuisine,
            "service_level": service_level,
            "is_chain": detect_chain_restaurant(restaurant_name, place),
            "rating": place.get("rating"),
            "notes": generate_notes(place),
            # Additional Google Data (new API structure)
            "formatted_address": place.get("formattedAddress"),
            "types": place.get("types", []),
            "primary_type": place.get("primaryType"),  # NEW: Primary business type
            "address_components": place.get("addressComponents", []),
            "price_level": _convert_price_level_to_int(place.get("priceLevel")),
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
            # Note: business_status is time-sensitive and not stored permanently
        }

        return jsonify(mapped_data)

    except requests.RequestException as e:
        current_app.logger.error(f"Google Places API error: {e}")
        return jsonify({"error": "Failed to fetch place details"}), 500


def parse_address_components(address_components):
    """Parse Google Places address components into structured data."""
    address_data = {"street_address": "", "city": "", "state": "", "postal_code": "", "country": ""}

    for component in address_components:
        types = component.get("types", [])
        long_name = component.get("long_name", "")

        if "street_number" in types:
            address_data["street_address"] = long_name
        elif "route" in types:
            address_data["street_address"] += f" {long_name}"
        elif "locality" in types or "sublocality" in types:
            address_data["city"] = long_name
        elif "administrative_area_level_1" in types:
            address_data["state"] = long_name
        elif "postal_code" in types:
            address_data["postal_code"] = long_name
        elif "country" in types:
            address_data["country"] = long_name

    return address_data


def get_cuisine_choices():
    """Get list of cuisine choices for dropdowns."""
    return [
        "American",
        "Bar",
        "Barbecue",
        "Brazilian",
        "Chinese",
        "Ethiopian",
        "Fast Food",
        "French",
        "German",
        "Greek",
        "Indian",
        "Italian",
        "Japanese",
        "Korean",
        "Lebanese",
        "Mediterranean",
        "Mexican",
        "Moroccan",
        "Peruvian",
        "Pizza",
        "Seafood",
        "Spanish",
        "Steakhouse",
        "Sushi",
        "Thai",
        "Turkish",
        "Vietnamese",
    ]


def _get_specific_cuisine_types():
    """Get mapping of specific Google Places cuisine types to formatted names."""
    return {
        # Primary cuisine types from Google Places API
        "chinese_restaurant": "Chinese",
        "italian_restaurant": "Italian",
        "japanese_restaurant": "Japanese",
        "mexican_restaurant": "Mexican",
        "indian_restaurant": "Indian",
        "thai_restaurant": "Thai",
        "french_restaurant": "French",
        "korean_restaurant": "Korean",
        "vietnamese_restaurant": "Vietnamese",
        "mediterranean_restaurant": "Mediterranean",
        "greek_restaurant": "Greek",
        "spanish_restaurant": "Spanish",
        "german_restaurant": "German",
        "turkish_restaurant": "Turkish",
        "lebanese_restaurant": "Lebanese",
        "ethiopian_restaurant": "Ethiopian",
        "moroccan_restaurant": "Moroccan",
        "brazilian_restaurant": "Brazilian",
        "peruvian_restaurant": "Peruvian",
        # Food type restaurants
        "barbecue_restaurant": "Barbecue",
        "pizza_restaurant": "Pizza",
        "seafood_restaurant": "Seafood",
        "sushi_restaurant": "Sushi",
        "steak_house": "Steakhouse",
        # Fast food and casual
        "fast_food_restaurant": "American",  # Fast food is typically American
        "fast_casual_restaurant": "American",  # Fast casual is typically American
        # Bars and drinks
        "bar": "Bar",
        "night_club": "Bar",
        "cocktail_bar": "Bar",
        "wine_bar": "Bar",
        "brewery": "Bar",
        "brewpub": "Bar",
        # Other food establishments
        "bakery": "Bakery",
        "cafe": "Coffee",
        "coffee_shop": "Coffee",
        "ice_cream_shop": "Dessert",
        "dessert_shop": "Dessert",
    }


def _detect_cuisine_from_chain_name(restaurant_name):
    """Detect cuisine from restaurant name using keyword patterns."""
    restaurant_name_lower = restaurant_name.lower()

    # Fast food chains (highest priority)
    fast_food_chains = [
        "mcdonald's",
        "burger king",
        "wendy's",
        "subway",
        "kfc",
        "taco bell",
        "domino's",
        "pizza hut",
        "chick-fil-a",
        "popeyes",
        "arby's",
        "jack in the box",
        "in-n-out",
        "five guys",
        "shake shack",
        "chipotle",
        "qdoba",
        "panera bread",
    ]

    if any(chain in restaurant_name_lower for chain in fast_food_chains):
        return "American"

    # Cuisine keyword patterns (more maintainable than hardcoded lists)
    cuisine_patterns = {
        "Mexican": ["taco", "burrito", "mexican", "enchilada", "quesadilla"],
        "Pizza": ["pizza", "pizzeria"],
        "Chinese": ["chinese", "panda", "wok", "dim sum"],
        "Coffee": ["coffee", "espresso", "latte", "cappuccino", "brew", "roast"],
        "Italian": ["italian", "pasta", "spaghetti", "lasagna", "trattoria"],
        "Japanese": ["japanese", "sushi", "ramen", "tempura", "bento"],
        "Indian": ["indian", "curry", "tandoori", "masala", "naan"],
        "Thai": ["thai", "pad thai", "tom yum"],
        "American": ["burger", "fries", "grill", "diner", "bbq", "barbecue", "steak"],
    }

    # Check for cuisine patterns
    for cuisine, keywords in cuisine_patterns.items():
        if any(keyword in restaurant_name_lower for keyword in keywords):
            return cuisine

    return None


def _detect_cuisine_from_description(description):
    """Detect cuisine from Google Places editorial summary/description."""
    if not description:
        current_app.logger.info("No description provided for cuisine detection")
        return None

    current_app.logger.info(f"Analyzing description for cuisine: {description}")
    description_lower = description.lower()

    # Cuisine keywords in description
    cuisine_keywords = {
        "American": ["american", "burger", "fries", "grill", "diner", "bbq", "barbecue", "steak"],
        "Mexican": ["mexican", "taco", "burrito", "enchilada", "quesadilla", "salsa"],
        "Italian": ["italian", "pizza", "pasta", "spaghetti", "lasagna", "trattoria"],
        "Chinese": ["chinese", "panda", "wok", "dim sum", "kung pao", "lo mein"],
        "Japanese": ["japanese", "sushi", "ramen", "tempura", "bento", "sashimi"],
        "Indian": ["indian", "curry", "tandoori", "masala", "naan", "biryani"],
        "Thai": ["thai", "pad thai", "tom yum", "curry", "coconut"],
        "Coffee": ["coffee", "espresso", "latte", "cappuccino", "brew", "roast"],
    }

    # Check for cuisine keywords
    for cuisine, keywords in cuisine_keywords.items():
        for keyword in keywords:
            if keyword in description_lower:
                current_app.logger.info(f"Found cuisine keyword '{keyword}' in description, detecting as {cuisine}")
                return cuisine

    current_app.logger.info("No cuisine keywords found in description")
    return None


def _detect_cuisine_from_google_types(types_lower):
    """Detect cuisine from Google Places types."""
    current_app.logger.info(f"Analyzing types for cuisine: {types_lower}")
    specific_cuisine_types = _get_specific_cuisine_types()

    for google_type in types_lower:
        if google_type in specific_cuisine_types:
            cuisine = specific_cuisine_types[google_type]
            current_app.logger.info(f"Detected specific cuisine type: {cuisine} from {google_type}")
            return cuisine

    current_app.logger.info(f"No specific cuisine types found in: {types_lower}")
    return None


def _detect_cuisine_from_primary_type(primary_type):
    """Detect cuisine from Google Places primary type (new API feature)."""
    if not primary_type:
        return None

    primary_type_lower = primary_type.lower()
    current_app.logger.info(f"Analyzing primary type: {primary_type}")

    # Primary type to cuisine mapping
    primary_type_mappings = {
        # Coffee and beverages
        "coffee_shop": "coffee",
        "cafe": "coffee",
        "tea_house": "tea",
        # Fast food and casual
        "fast_food_restaurant": "fast_food",
        "hamburger_restaurant": "fast_food",
        "pizza_restaurant": "pizza",
        "sandwich_shop": "sandwiches",
        "hot_dog_restaurant": "fast_food",
        "chicken_restaurant": "fast_food",
        "taco_restaurant": "mexican",
        "burrito_restaurant": "mexican",
        # Ethnic cuisines
        "chinese_restaurant": "chinese",
        "japanese_restaurant": "japanese",
        "korean_restaurant": "korean",
        "thai_restaurant": "thai",
        "vietnamese_restaurant": "vietnamese",
        "indian_restaurant": "indian",
        "italian_restaurant": "italian",
        "mexican_restaurant": "mexican",
        "french_restaurant": "french",
        "german_restaurant": "german",
        "greek_restaurant": "greek",
        "mediterranean_restaurant": "mediterranean",
        "middle_eastern_restaurant": "middle_eastern",
        "american_restaurant": "american",
        "barbecue_restaurant": "bbq",
        "seafood_restaurant": "seafood",
        "steak_house": "steakhouse",
        "sushi_restaurant": "sushi",
        # Specialty
        "breakfast_restaurant": "breakfast",
        "brunch_restaurant": "brunch",
        "diner": "american",
        "bakery": "bakery",
        "dessert_shop": "desserts",
        "ice_cream_shop": "ice_cream",
        # Bars and drinks
        "bar": "bar",
        "pub": "pub",
        "wine_bar": "wine_bar",
        "cocktail_lounge": "cocktail_bar",
        "brewery": "brewery",
        "distillery": "distillery",
    }

    cuisine = primary_type_mappings.get(primary_type_lower)
    if cuisine:
        current_app.logger.info(f"Cuisine detected from primary type '{primary_type}': {cuisine}")
        return cuisine

    current_app.logger.info(f"No cuisine mapping found for primary type: {primary_type}")
    return None


def _convert_price_level_to_int(price_level):
    """Convert Google Places price level to integer (handles both old and new API formats)."""
    if price_level is None:
        return None

    # If it's already an integer, return it
    if isinstance(price_level, int):
        return price_level

    # If it's a string number, convert to int
    if isinstance(price_level, str) and price_level.isdigit():
        return int(price_level)

    # Handle new API string format (PRICE_LEVEL_MODERATE -> 2)
    if isinstance(price_level, str):
        price_level_map = {
            "PRICE_LEVEL_FREE": 0,
            "PRICE_LEVEL_INEXPENSIVE": 1,
            "PRICE_LEVEL_MODERATE": 2,
            "PRICE_LEVEL_EXPENSIVE": 3,
            "PRICE_LEVEL_VERY_EXPENSIVE": 4,
        }
        return price_level_map.get(price_level, None)

    return None


def _detect_cuisine_from_types(types_lower, restaurant_name="", place_data=None, primary_type=""):
    """Detect cuisine from Google Places types array and primary type."""
    # Check primary type first (new API feature - highest priority)
    if primary_type:
        cuisine = _detect_cuisine_from_primary_type(primary_type)
        if cuisine:
            return cuisine

    # Check description for cuisine indicators (high priority for fast food)
    if place_data and "editorialSummary" in place_data and place_data["editorialSummary"]:
        editorial_text = (
            place_data["editorialSummary"].get("overview", "")
            if isinstance(place_data["editorialSummary"], dict)
            else str(place_data["editorialSummary"])
        )
        if editorial_text:
            cuisine = _detect_cuisine_from_description(editorial_text)
            if cuisine:
                current_app.logger.info(f"Cuisine detected from description: {cuisine}")
                return cuisine

    # Check restaurant name patterns (high priority for chains)
    if restaurant_name:
        cuisine = _detect_cuisine_from_chain_name(restaurant_name)
        if cuisine:
            current_app.logger.info(f"Cuisine detected from name patterns: {cuisine}")
            return cuisine

    # Check for specific cuisine restaurant types (lower priority)
    cuisine = _detect_cuisine_from_google_types(types_lower)
    if cuisine:
        current_app.logger.info(f"Cuisine detected from Google types: {cuisine}")
        return cuisine

    # Default cuisine for restaurants
    if "restaurant" in types_lower or "food" in types_lower:
        return "American"

    # Check for broader patterns
    return _detect_cuisine_from_broader_patterns(types_lower)


def _detect_cuisine_from_broader_patterns(types_lower):
    """Detect cuisine from broader patterns in types."""
    cuisine_keywords = {
        "italian": ["italian", "pizza", "pasta"],
        "chinese": ["chinese"],
        "japanese": ["japanese", "sushi", "ramen", "tempura", "bento"],
        "mexican": ["mexican", "taco", "burrito", "enchilada"],
        "indian": ["indian", "curry", "tandoori"],
        "thai": ["thai"],
        "mediterranean": ["mediterranean", "greek", "lebanese", "falafel"],
        "french": ["french", "bistro"],
        "seafood": ["seafood", "fish", "oyster", "lobster"],
        "barbecue": ["barbecue", "bbq", "smokehouse"],
        "american": ["american", "burger", "steakhouse", "sandwich", "fast_food"],
        "vegetarian": ["vegetarian", "vegan"],
        "dessert": ["dessert", "ice_cream", "bakery", "pastry"],
        "coffee": ["coffee", "cafe", "espresso"],
        "bar": ["night_club", "cocktail_bar", "wine_bar"],
    }

    for cuisine_name, keywords in cuisine_keywords.items():
        if any(keyword in types_lower for keyword in keywords):
            cuisine = cuisine_name.title()
            current_app.logger.info(f"Detected cuisine from keywords: {cuisine}")
            return cuisine

    # Special handling for bar/pub establishments
    if any(bar_type in types_lower for bar_type in ["bar", "pub", "brewery"]):
        food_types = ["restaurant", "food", "meal_delivery", "meal_takeaway"]
        if any(food_type in types_lower for food_type in food_types):
            current_app.logger.info("Detected as pub establishment (bar + restaurant)")
            return "Pub"
        else:
            current_app.logger.info("Detected as primarily a bar establishment")
            return "Bar"

    return None


def _detect_service_level_from_chain_name(restaurant_name):
    """Detect service level from restaurant name using patterns and service indicators."""
    restaurant_name_lower = restaurant_name.lower()

    # Service level indicators based on restaurant characteristics
    quick_service_indicators = [
        "drive",
        "drive-in",
        "drive thru",
        "drive-thru",
        "express",
        "quick",
        "fast",
        "takeout",
        "delivery",
        "grab",
        "go",
        "counter",
    ]

    fast_casual_indicators = ["fresh", "healthy", "organic", "natural", "artisan", "craft"]

    fine_dining_indicators = [
        "fine dining",
        "restaurant",
        "bistro",
        "brasserie",
        "steakhouse",
        "grill",
        "chophouse",
        "supper club",
    ]

    # Check for service level indicators
    if any(indicator in restaurant_name_lower for indicator in quick_service_indicators):
        return "quick_service"

    if any(indicator in restaurant_name_lower for indicator in fast_casual_indicators):
        return "fast_casual"

    if any(indicator in restaurant_name_lower for indicator in fine_dining_indicators):
        return "fine_dining"

    return None


def _detect_service_level_from_description(description):
    """Detect service level from Google Places editorial summary/description."""
    if not description:
        current_app.logger.info("No description provided for service level detection")
        return None

    current_app.logger.info(f"Analyzing description for service level: {description}")
    description_lower = description.lower()

    # Fine Dining indicators in description (check first - higher priority)
    fine_dining_keywords = [
        "fine dining",
        "upscale",
        "elegant",
        "sophisticated",
        "gourmet",
        "chef",
        "haute cuisine",
        "white tablecloth",
        "formal dining",
        "full service",
        "table service",
        "servers",
        "waiter",
        "waitress",
    ]

    for keyword in fine_dining_keywords:
        if keyword in description_lower:
            current_app.logger.info(f"Found fine dining keyword '{keyword}' in description")
            return "fine_dining"

    # Quick Service indicators in description (more specific)
    quick_service_keywords = [
        "fast food",
        "fast-food",
        "quick service",
        "counter service",
        "drive-thru",
        "drive thru",
        "grab and go",
        "order at counter",
        "fast casual",
        "quick bite",
        "fast service",
        "no table service",
    ]

    for keyword in quick_service_keywords:
        if keyword in description_lower:
            current_app.logger.info(f"Found quick service keyword '{keyword}' in description")
            return "quick_service"

    # Fast Casual indicators in description
    fast_casual_keywords = ["fast casual", "counter service", "order at counter", "casual dining"]

    for keyword in fast_casual_keywords:
        if keyword in description_lower:
            current_app.logger.info(f"Found fast casual keyword '{keyword}' in description")
            return "fast_casual"

    current_app.logger.info("No service level keywords found in description")
    return None


def _detect_service_level_from_types_and_options(types_lower, place_data=None):
    """Detect service level from Google Places types and service options."""
    # Check Google Places types first (most reliable)
    service_level = _detect_service_level_from_google_types(types_lower)
    if service_level:
        current_app.logger.info(f"Service level detected from Google types: {service_level}")
        return service_level

    # Check service options for restaurants (reliable indicator based on price/reservations)
    if "restaurant" in types_lower and place_data:
        service_level = _detect_service_level_from_service_options(place_data)
        if service_level:
            current_app.logger.info(f"Service level detected from service options: {service_level}")
            return service_level

    # Check description for service level indicators (only for obvious cases)
    if place_data and "editorial_summary" in place_data and place_data["editorial_summary"]:
        editorial_text = (
            place_data["editorial_summary"].get("overview", "")
            if isinstance(place_data["editorial_summary"], dict)
            else str(place_data["editorial_summary"])
        )
        if editorial_text:
            service_level = _detect_service_level_from_description(editorial_text)
            # Only use description if it's very clear (fine dining or obvious fast food)
            if service_level in ["fine_dining"] or (
                service_level == "quick_service" and "fast food" in editorial_text.lower()
            ):
                current_app.logger.info(f"Service level detected from description: {service_level}")
                return service_level

    # Check name patterns as fallback (only for edge cases)
    if place_data and "name" in place_data:
        service_level = _detect_service_level_from_chain_name(place_data["name"])
        if service_level:
            current_app.logger.info(f"Service level detected from name patterns: {service_level}")
            return service_level

    # Default fallback
    default_level = "casual_dining" if "restaurant" in types_lower else None
    current_app.logger.info(f"Using default service level: {default_level}")
    return default_level


def _detect_service_level_from_google_types(types_lower):
    """Detect service level from Google Places types."""
    current_app.logger.info(f"Analyzing types for service level: {types_lower}")

    # Quick Service (Fast Food) - Google's primary indicators
    quick_service_types = ["fast_food_restaurant", "fast_food", "food_court", "convenience_store"]
    if any(indicator in types_lower for indicator in quick_service_types):
        current_app.logger.info(f"Found quick service type in: {types_lower}")
        return "quick_service"

    # Fast Casual - Counter service but higher quality
    fast_casual_types = ["fast_casual_restaurant", "fast_casual"]
    if any(indicator in types_lower for indicator in fast_casual_types):
        current_app.logger.info(f"Found fast casual type in: {types_lower}")
        return "fast_casual"

    # Fine Dining - Upscale establishments
    fine_dining_types = ["fine_dining_restaurant", "fine_dining", "upscale_restaurant"]
    if any(indicator in types_lower for indicator in fine_dining_types):
        current_app.logger.info(f"Found fine dining type in: {types_lower}")
        return "fine_dining"

    current_app.logger.info(f"No specific service level types found in: {types_lower}")
    return None


def _detect_service_level_from_service_options(place_data):
    """Detect service level from Google Places service options."""
    takeout = place_data.get("takeout", False)
    dine_in = place_data.get("dine_in", False)
    reservable = place_data.get("reservable", False)
    price_level = place_data.get("price_level")
    delivery = place_data.get("delivery", False)

    current_app.logger.info(
        f"Service options - takeout: {takeout}, dine_in: {dine_in}, reservable: {reservable}, price_level: {price_level}, delivery: {delivery}"
    )

    # SIMPLIFIED LOGIC - Price level is the primary indicator

    # Fine dining: Price level 4+ ($$$$)
    if price_level is not None and price_level >= 4:
        current_app.logger.info("Detected fine dining from price level 4+")
        return "fine_dining"

    # Casual dining: Price level 3+ ($$$) OR reservations OR price level 2 with dine-in
    if (price_level is not None and price_level >= 3) or reservable or (price_level == 2 and dine_in):
        current_app.logger.info("Detected casual dining from price level 3+/reservations/price level 2 with dine-in")
        return "casual_dining"

    # Fast casual: Price level 2 ($$) without dine-in (counter service only)
    if price_level == 2 and not dine_in:
        current_app.logger.info("Detected fast casual from price level 2 without dine-in")
        return "fast_casual"

    # Quick service: Price level 1 ($)
    if price_level == 1:
        current_app.logger.info("Detected quick service from price level 1")
        return "quick_service"

    # Default fallback
    current_app.logger.info("Defaulting to casual dining from service options")
    return "casual_dining"


def _detect_service_level_from_types(types_lower):
    """Legacy function - use _detect_service_level_from_types_and_options instead."""
    return _detect_service_level_from_types_and_options(types_lower)


def analyze_restaurant_types(types, place_data=None):
    """Analyze Google Places types and service options to determine cuisine and service level."""
    current_app.logger.info(f"Analyzing restaurant types: {types}")
    current_app.logger.info(f"Place data keys: {list(place_data.keys()) if place_data else 'None'}")
    if place_data and "editorialSummary" in place_data:
        current_app.logger.info(f"Editorial summary: {place_data['editorialSummary']}")

    types_lower = [t.lower() for t in types]
    current_app.logger.info(f"Types lower: {types_lower}")

    # Get restaurant name from place data (handle new API structure)
    restaurant_name = ""
    if place_data:
        if "displayName" in place_data and isinstance(place_data["displayName"], dict):
            restaurant_name = place_data["displayName"].get("text", "")
        elif "name" in place_data:
            restaurant_name = place_data["name"]

    # Use primaryType if available (new API feature)
    primary_type = ""
    if place_data and "primaryType" in place_data:
        primary_type = place_data["primaryType"]
        current_app.logger.info(f"Primary type: {primary_type}")

    # Detect cuisine from types, primary type, description, and name
    cuisine = _detect_cuisine_from_types(types_lower, restaurant_name, place_data, primary_type)

    if not cuisine:
        current_app.logger.info("No cuisine detected from types, will try name-based detection")

    # Detect service level from types and service options
    service_level = _detect_service_level_from_types_and_options(types_lower, place_data)
    current_app.logger.info(f"Detected service level: {service_level}")

    return cuisine, service_level


def _matches_cuisine_pattern(name_lower: str, pattern: str) -> bool:
    """Return True when pattern matches as a whole word; for multi-word patterns,
    fallback to substring. Prevents false matches like 'bar' in 'barbecue'."""
    tokenized = not any(ch.isspace() for ch in pattern)
    if tokenized and pattern.isalpha():
        return re.search(rf"\b{re.escape(pattern)}\b", name_lower) is not None
    return pattern in name_lower


def detect_cuisine_from_name(name):
    """Detect cuisine type from restaurant name."""
    if not name:
        return None

    name_lower = name.lower()

    # Cuisine detection patterns
    cuisine_patterns = {
        "japanese": ["sushi", "ramen", "tempura", "bento", "japanese", "hibachi", "teppanyaki"],
        "chinese": ["chinese", "dim sum", "wok", "kung pao", "szechuan", "cantonese"],
        "italian": ["pizza", "pasta", "italian", "ristorante", "trattoria", "osteria"],
        "mexican": ["mexican", "taco", "burrito", "enchilada", "quesadilla", "fajita"],
        "indian": ["indian", "curry", "tandoori", "masala", "biryani"],
        "thai": ["thai", "pad thai", "tom yum", "green curry"],
        "mediterranean": ["mediterranean", "greek", "lebanese", "falafel", "kebab"],
        "american": [
            "american",
            "burger",
            "steakhouse",
            "diner",
            "arbys",
            "mcdonalds",
            "burger king",
            "wendys",
            "subway",
            "kfc",
            "taco bell",
            "dominos",
            "pizza hut",
            "chipotle",
            "panera",
            "olive garden",
            "applebee",
            "chilis",
            "outback",
            "red lobster",
            "buffalo wild wings",
        ],
        "french": ["french", "bistro", "brasserie", "creperie"],
        "seafood": ["seafood", "fish", "oyster", "lobster", "crab", "shrimp"],
        "barbecue": ["barbecue", "bbq", "smokehouse", "pit"],
        "vegetarian": ["vegetarian", "vegan", "plant-based"],
        "dessert": ["dessert", "ice cream", "bakery", "pastry", "cake"],
        "coffee": ["coffee", "cafe", "espresso", "latte", "starbucks", "dunkin", "tim hortons", "peets", "caribou"],
        "pub": ["pub", "grill", "gastropub", "sports bar", "tavern"],  # Pub patterns
        "bar": ["cocktail bar", "wine bar"],  # More specific bar patterns
    }

    for cuisine_name, patterns in cuisine_patterns.items():
        if any(_matches_cuisine_pattern(name_lower, pattern) for pattern in patterns):
            # Special handling for bar/pub establishments
            if cuisine_name == "bar":
                # Check if name also contains restaurant/food indicators
                food_indicators = ["restaurant", "grill", "kitchen", "food", "eatery", "dining", "cafe", "bistro"]
                if any(indicator in name_lower for indicator in food_indicators):
                    # Has food indicators - classify as Pub instead of Bar
                    return "Pub"
            elif cuisine_name == "pub":
                # Pub patterns already indicate food+drink combination
                return "Pub"
            return cuisine_name.title()

    return None


# TODO find a better way
def detect_chain_restaurant(name, place_data=None):
    """Detect if restaurant is likely a chain using multiple detection methods."""
    current_app.logger.info(f"Detecting chain status for: {name}")

    # Method 1: Description-based detection (highest priority)
    if place_data and "editorial_summary" in place_data and place_data["editorial_summary"]:
        editorial_text = (
            place_data["editorial_summary"].get("overview", "")
            if isinstance(place_data["editorial_summary"], dict)
            else str(place_data["editorial_summary"])
        )
        if editorial_text:
            is_chain = _detect_chain_from_description(editorial_text)
            if is_chain is not None:
                current_app.logger.info(f"Chain detected from description: {is_chain}")
                return is_chain

    # Method 2: Name pattern analysis (secondary)
    is_chain = _detect_chain_from_name_patterns(name)
    if is_chain is not None:
        current_app.logger.info(f"Chain detected from name patterns: {is_chain}")
        return is_chain

    # Method 3: Corporate indicators (tertiary)
    is_chain = _detect_chain_from_corporate_indicators(name, place_data)
    if is_chain is not None:
        current_app.logger.info(f"Chain detected from corporate indicators: {is_chain}")
        return is_chain

    # Default: assume not a chain (conservative approach)
    current_app.logger.info("No clear chain indicators found, defaulting to False")
    return False


def _detect_chain_from_description(description):
    """Detect chain status from Google Places editorial summary."""
    description_lower = description.lower()

    # Strong chain indicators
    chain_keywords = [
        "chain",
        "chains",
        "franchise",
        "franchises",
        "locations",
        "nationwide",
        "regional",
        "corporate",
        "brand",
        "brands",
        "restaurant group",
        "restaurant chain",
    ]

    # Anti-chain indicators (local, family-owned, etc.)
    anti_chain_keywords = [
        "family-owned",
        "family owned",
        "local",
        "locally owned",
        "independent",
        "mom and pop",
        "mom & pop",
        "small business",
    ]

    # Check for anti-chain indicators first
    for keyword in anti_chain_keywords:
        if keyword in description_lower:
            current_app.logger.info(f"Found anti-chain keyword: {keyword}")
            return False

    # Check for chain indicators
    for keyword in chain_keywords:
        if keyword in description_lower:
            current_app.logger.info(f"Found chain keyword: {keyword}")
            return True

    return None


def _detect_chain_from_name_patterns(name):
    """Detect chain status from restaurant name patterns."""
    name_lower = name.lower()

    # Corporate naming patterns
    corporate_patterns = [
        r"\b\w+\s+(kitchen|grill|house|restaurant|bistro|cafe)\b",  # "Joe's Kitchen", "Bob's Grill"
        r"\w+\s+&+\s+\w+",  # "Tom & Jerry's", "Mike & Son's"
        r"\b\w+\'s\s+\w+",  # "Joe's Place", "Mary's Diner"
    ]

    # Trademark indicators
    trademark_indicators = ["™", "®", "©"]

    # Check for trademarks (strong chain indicator)
    for indicator in trademark_indicators:
        if indicator in name:
            current_app.logger.info(f"Found trademark indicator: {indicator}")
            return True

    # Check for corporate patterns (moderate chain indicator)
    import re

    for pattern in corporate_patterns:
        if re.search(pattern, name_lower):
            current_app.logger.info(f"Found corporate pattern: {pattern}")
            return True

    return None


def _detect_chain_from_corporate_indicators(name, place_data=None):
    """Detect chain status from corporate/Google Places indicators."""
    # Check for corporate website patterns
    if place_data and "website" in place_data and place_data["website"]:
        website = place_data["website"].lower()
        corporate_domains = [
            ".com/",  # Corporate websites often have subpages
            "locations",  # Corporate sites often have locations pages
            "franchise",  # Franchise information
            "about",  # Corporate about pages
        ]

        for indicator in corporate_domains:
            if indicator in website:
                current_app.logger.info(f"Found corporate website indicator: {indicator}")
                return True

    # Check for multiple location indicators in name
    location_indicators = ["location", "branch", "store", "unit"]
    name_lower = name.lower()
    for indicator in location_indicators:
        if indicator in name_lower:
            current_app.logger.info(f"Found location indicator: {indicator}")
            return True

    return None


def generate_description(place):
    """Generate a description from Google Places data."""
    parts = []

    # Use editorial summary if available (new API structure)
    editorial_summary = place.get("editorialSummary", {})
    if isinstance(editorial_summary, dict) and editorial_summary.get("overview"):
        parts.append(editorial_summary.get("overview"))
    elif place.get("editorial_summary", {}).get("overview"):  # Legacy fallback
        parts.append(place.get("editorial_summary", {}).get("overview"))

    # Use generative summary if available (new API feature)
    generative_summary = place.get("generativeSummary", {})
    if isinstance(generative_summary, dict) and generative_summary.get("overview"):
        parts.append(generative_summary.get("overview").get("text", ""))

    if place.get("rating"):
        rating = place.get("rating")
        user_ratings_total = place.get("userRatingCount") or place.get("user_ratings_total")
        if user_ratings_total:
            parts.append(f"Google Rating: {rating}/5 ({user_ratings_total} reviews)")
        else:
            parts.append(f"Google Rating: {rating}/5")

    if place.get("price_level"):
        price_levels = {1: "$", 2: "$$", 3: "$$$", 4: "$$$$"}
        parts.append(f"Price Level: {price_levels.get(place.get('price_level'), 'N/A')}")

    if place.get("types"):
        # Filter out generic types and show interesting ones
        interesting_types = [
            t.replace("_", " ").title()
            for t in place.get("types")
            if t not in ["establishment", "food", "point_of_interest"]
        ]
        if interesting_types:
            parts.append(f"Categories: {', '.join(interesting_types[:3])}")

    return " | ".join(parts) if parts else "Restaurant from Google Places"


def generate_notes(place):
    """Generate notes from Google Places data."""
    notes = []

    if place.get("price_level"):
        price_levels = {1: "Budget-friendly", 2: "Moderate pricing", 3: "Upscale", 4: "Premium"}
        notes.append(price_levels.get(place.get("price_level"), ""))

    return " | ".join(notes) if notes else None


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


def _parse_import_file(file):
    """Parse the uploaded file and return the data."""
    try:
        if file.filename.lower().endswith(".json"):
            # Reset file pointer to beginning
            file.seek(0)
            data = json.load(file)
            if not isinstance(data, list):
                flash("Invalid JSON format. Expected an array of restaurants.", "error")
                return None
            return data

        # Parse CSV file
        # Reset file pointer to beginning
        file.seek(0)
        csv_data = file.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(csv_data))
        return list(reader)
    except UnicodeDecodeError:
        flash(
            "Error decoding the file. Please ensure it's a valid CSV or JSON file.",
            "error",
        )
        return None
    except Exception as e:
        flash(f"Error parsing file: {str(e)}", "error")
        return None


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
            | (Restaurant.address.ilike(search))
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
