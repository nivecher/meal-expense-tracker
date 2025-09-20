#!/usr/bin/env python3
"""
Google Places CLI Utility

A comprehensive command-line tool for exploring Google Places data to help with
mapping design and gaining insights about places. Uses GOOGLE_MAPS_API_KEY from .env.

Features:
- Search places by text, location, or place ID
- Get comprehensive place details with all available fields
- Format output in multiple ways (JSON, table, summary)
- Analyze place data for mapping insights
- Export data for further analysis
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# Load environment variables from .env file if it exists
from dotenv import load_dotenv

load_dotenv()

# Configuration
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
PLACES_API_BASE_URL = "https://maps.googleapis.com/maps/api/place"
GEOCODE_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# All available fields for comprehensive data collection
ALL_PLACE_FIELDS = [
    # Basic Data Fields
    "place_id",
    "name",
    "formatted_address",
    "address_components",
    "geometry",
    "types",
    "url",
    "vicinity",
    "plus_code",
    "utc_offset",
    # Contact Data Fields
    "formatted_phone_number",
    "international_phone_number",
    "website",
    "opening_hours",
    "current_opening_hours",
    "secondary_opening_hours",
    # Atmosphere Data Fields
    "rating",
    "user_ratings_total",
    "price_level",
    "reviews",
    "photos",
    # Business Status Fields
    "business_status",
    "permanently_closed",
    # Service & Dining Fields (Enterprise tier - very valuable for meal tracking!)
    "serves_breakfast",
    "serves_lunch",
    "serves_dinner",
    "serves_beer",
    "serves_wine",
    "serves_brunch",
    "serves_dessert",
    "serves_vegetarian_food",
    # Service Options (Enterprise tier)
    "delivery",
    "takeout",
    "dine_in",
    "curbside_pickup",
    "reservable",
    # Accessibility & Amenities
    "wheelchair_accessible_entrance",
    "parking_options",
    "payment_options",
    # Additional Enterprise Fields
    "editorial_summary",
    "current_opening_hours",
    "secondary_opening_hours",
]

# Field categories for organized display
FIELD_CATEGORIES = {
    "basic_info": ["place_id", "name", "formatted_address", "vicinity", "url", "editorial_summary"],
    "contact": ["formatted_phone_number", "international_phone_number", "website"],
    "ratings": ["rating", "user_ratings_total", "reviews"],
    "business": ["types", "price_level", "business_status", "permanently_closed"],
    "location": ["geometry", "address_components", "plus_code", "utc_offset"],
    "hours": ["opening_hours", "current_opening_hours", "secondary_opening_hours"],
    "media": ["photos"],
    "dining_services": [
        "serves_breakfast",
        "serves_lunch",
        "serves_dinner",
        "serves_brunch",
        "serves_dessert",
        "serves_vegetarian_food",
        "serves_beer",
        "serves_wine",
    ],
    "service_options": ["delivery", "takeout", "dine_in", "curbside_pickup", "reservable"],
    "accessibility": ["wheelchair_accessible_entrance", "parking_options", "payment_options"],
}


def _make_api_request(url: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Make a request to Google APIs with proper error handling.

    Args:
        url: API endpoint URL
        params: Query parameters

    Returns:
        Parsed JSON response or None if request fails
    """
    try:
        full_url = f"{url}?{urlencode(params)}"
        response = urlopen(Request(full_url, headers={"User-Agent": "GooglePlacesCLI/1.0"}))
        return json.loads(response.read().decode())
    except HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        if e.code == 403:
            print("Check your API key and ensure Places API is enabled")
        elif e.code == 429:
            print("API quota exceeded. Try again later.")
    except Exception as e:
        print(f"Error making API request: {str(e)}")
    return None


def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """Convert an address to latitude and longitude coordinates.

    Args:
        address: Address string to geocode

    Returns:
        Tuple of (latitude, longitude) or None if geocoding fails
    """
    if not GOOGLE_MAPS_API_KEY:
        print("Error: GOOGLE_MAPS_API_KEY environment variable is not set")
        return None

    params = {"address": address, "key": GOOGLE_MAPS_API_KEY}
    data = _make_api_request(GEOCODE_API_URL, params)

    if data and data.get("status") == "OK" and data.get("results"):
        location = data["results"][0]["geometry"]["location"]
        return (location["lat"], location["lng"])
    return None


def search_places_by_text(
    query: str, location: Optional[Tuple[float, float]] = None, radius: int = 50000, max_results: int = 20
) -> List[Dict[str, Any]]:
    """Search for places using text query.

    Args:
        query: Text query to search for
        location: Optional (lat, lng) tuple for location bias
        radius: Search radius in meters (max 50000)
        max_results: Maximum number of results to return

    Returns:
        List of place data dictionaries
    """
    if not GOOGLE_MAPS_API_KEY:
        print("Error: GOOGLE_MAPS_API_KEY environment variable is not set")
        return []

    url = f"{PLACES_API_BASE_URL}/textsearch/json"
    params = {"query": query, "key": GOOGLE_MAPS_API_KEY, "fields": ",".join(ALL_PLACE_FIELDS)}

    if location:
        params["location"] = f"{location[0]},{location[1]}"
        params["radius"] = min(radius, 50000)

    data = _make_api_request(url, params)
    if not data or data.get("status") != "OK":
        print(f"Search failed: {data.get('status', 'Unknown error') if data else 'No response'}")
        return []

    return data.get("results", [])[:max_results]


def search_places_nearby(
    location: Tuple[float, float], radius: int = 5000, place_type: str = "restaurant", max_results: int = 20
) -> List[Dict[str, Any]]:
    """Search for places near a location.

    Args:
        location: (latitude, longitude) tuple
        radius: Search radius in meters (max 50000)
        place_type: Type of place to search for
        max_results: Maximum number of results to return

    Returns:
        List of place data dictionaries
    """
    if not GOOGLE_MAPS_API_KEY:
        print("Error: GOOGLE_MAPS_API_KEY environment variable is not set")
        return []

    url = f"{PLACES_API_BASE_URL}/nearbysearch/json"
    params = {
        "location": f"{location[0]},{location[1]}",
        "radius": min(radius, 50000),
        "type": place_type,
        "key": GOOGLE_MAPS_API_KEY,
        "fields": ",".join(ALL_PLACE_FIELDS),
    }

    data = _make_api_request(url, params)
    if not data or data.get("status") != "OK":
        print(f"Search failed: {data.get('status', 'Unknown error') if data else 'No response'}")
        return []

    return data.get("results", [])[:max_results]


def get_place_details(place_id: str) -> Optional[Dict[str, Any]]:
    """Get comprehensive details for a specific place.

    Args:
        place_id: Google Place ID

    Returns:
        Place details dictionary or None if not found
    """
    if not GOOGLE_MAPS_API_KEY:
        print("Error: GOOGLE_MAPS_API_KEY environment variable is not set")
        return None

    url = f"{PLACES_API_BASE_URL}/details/json"
    params = {"place_id": place_id, "fields": ",".join(ALL_PLACE_FIELDS), "key": GOOGLE_MAPS_API_KEY}

    data = _make_api_request(url, params)
    if not data or data.get("status") != "OK":
        print(f"Failed to get place details: {data.get('status', 'Unknown error') if data else 'No response'}")
        return None

    return data.get("result")


def _format_opening_hours(place: Dict[str, Any]) -> str:
    """Format opening hours information."""
    if "opening_hours" not in place:
        return ""

    hours = place["opening_hours"]
    if hours.get("weekday_text"):
        return "\n".join([f"  {day}" for day in hours["weekday_text"]])
    elif hours.get("open_now") is not None:
        return f"Open now: {hours['open_now']}"
    return ""


def _format_dining_services(place: Dict[str, Any]) -> List[str]:
    """Format dining services information with icons and better categorization."""
    service_mapping = {
        "serves_breakfast": "🌅 Breakfast",
        "serves_lunch": "🍽️ Lunch",
        "serves_dinner": "🌙 Dinner",
        "serves_brunch": "🥞 Brunch",
        "serves_dessert": "🍰 Dessert",
        "serves_vegetarian_food": "🥗 Vegetarian",
        "serves_beer": "🍺 Beer",
        "serves_wine": "🍷 Wine",
    }

    dining_services = []
    for field, display_name in service_mapping.items():
        if place.get(field):
            dining_services.append(display_name)

    return dining_services


def _format_service_options(place: Dict[str, Any]) -> List[str]:
    """Format service options information with icons and better categorization."""
    option_mapping = {
        "delivery": "🚚 Delivery",
        "takeout": "🥡 Takeout",
        "dine_in": "🍽️ Dine-in",
        "curbside_pickup": "🚗 Curbside",
        "reservable": "📅 Reservations",
    }

    service_options = []
    for field, display_name in option_mapping.items():
        if place.get(field):
            service_options.append(display_name)

    return service_options


def _format_accessibility_info(place: Dict[str, Any]) -> List[str]:
    """Format accessibility information with icons and better display."""
    accessibility_info = []

    if place.get("wheelchair_accessible_entrance"):
        accessibility_info.append("♿ Wheelchair Accessible")

    if place.get("parking_options"):
        parking_options = place.get("parking_options", [])
        if isinstance(parking_options, list) and parking_options:
            parking_types = [opt.get("name", "Parking") for opt in parking_options if isinstance(opt, dict)]
            accessibility_info.append(f"🅿️ {', '.join(parking_types[:2])}")  # Limit to 2 parking types
        else:
            accessibility_info.append("🅿️ Parking Available")

    if place.get("payment_options"):
        payment_methods = place.get("payment_options", [])
        if isinstance(payment_methods, list) and payment_methods:
            # Format payment methods nicely
            payment_display = []
            for method in payment_methods[:3]:  # Limit to 3 payment methods
                if isinstance(method, dict):
                    payment_display.append(method.get("name", "Payment"))
                else:
                    payment_display.append(str(method))
            accessibility_info.append(f"💳 {', '.join(payment_display)}")

    return accessibility_info


def _categorize_place_types(types: List[str]) -> Dict[str, List[str]]:
    """Categorize place types into different groups.

    Args:
        types: List of type strings

    Returns:
        Dictionary with categorized types
    """
    primary_keywords = ["restaurant", "food", "meal_takeaway", "meal_delivery"]
    establishment_keywords = ["establishment", "point_of_interest", "store"]
    food_keywords = [
        "cafe",
        "bakery",
        "bar",
        "pizza",
        "sandwich",
        "burger",
        "chinese",
        "italian",
        "mexican",
        "indian",
        "thai",
        "japanese",
        "korean",
        "vietnamese",
        "mediterranean",
        "american",
        "french",
        "greek",
        "turkish",
        "lebanese",
        "vegetarian",
        "vegan",
        "seafood",
        "steakhouse",
        "diner",
        "fast_food",
        "fine_dining",
        "casual_dining",
    ]
    service_keywords = ["delivery", "takeout", "dine_in", "reservation", "booking"]

    categorized = {"primary": [], "establishment": [], "food": [], "service": [], "other": []}

    for type_name in types:
        formatted_name = type_name.replace("_", " ").title()

        if type_name in primary_keywords:
            categorized["primary"].append(formatted_name)
        elif type_name in establishment_keywords:
            categorized["establishment"].append(formatted_name)
        elif any(food in type_name for food in food_keywords):
            categorized["food"].append(formatted_name)
        elif any(service in type_name for service in service_keywords):
            categorized["service"].append(formatted_name)
        else:
            categorized["other"].append(formatted_name)

    return categorized


def _format_types_detailed(place: Dict[str, Any]) -> str:
    """Format types information with better categorization and display.

    Args:
        place: Place data dictionary

    Returns:
        Formatted types string with categories
    """
    types = place.get("types", [])
    if not types:
        return "No types specified"

    categorized = _categorize_place_types(types)

    # Build formatted result with limits
    result_parts = []

    if categorized["primary"]:
        result_parts.append(f"Primary: {', '.join(categorized['primary'][:3])}")

    if categorized["food"]:
        result_parts.append(f"Food: {', '.join(categorized['food'][:4])}")

    if categorized["service"]:
        result_parts.append(f"Services: {', '.join(categorized['service'][:3])}")

    if categorized["establishment"]:
        result_parts.append(f"Establishment: {', '.join(categorized['establishment'][:2])}")

    if categorized["other"]:
        result_parts.append(f"Other: {', '.join(categorized['other'][:3])}")

    return " | ".join(result_parts)


def _build_basic_info(place: Dict[str, Any]) -> List[str]:
    """Build basic information section."""
    name = place.get("name", "Unknown")
    address = place.get("formatted_address", "No address")
    phone = place.get("formatted_phone_number", "No phone")
    website = place.get("website", "No website")
    rating = place.get("rating", "N/A")
    total_ratings = place.get("user_ratings_total", 0)
    price_level = place.get("price_level")
    price_str = "?" * price_level if price_level else "Not specified"
    business_status = place.get("business_status", "Unknown")

    return [
        f"\n{'=' * 80}",
        f"Name: {name}",
        f"Address: {address}",
        f"Phone: {phone}",
        f"Website: {website}",
        f"Rating: {rating}/5 ({total_ratings} reviews)",
        f"Price Level: {price_str}",
        f"Business Status: {business_status}",
    ]


def _extract_cuisine_types(place: Dict[str, Any]) -> List[str]:
    """Extract cuisine types from place data.

    Args:
        place: Place data dictionary

    Returns:
        List of cuisine types
    """
    types = place.get("types", [])
    cuisine_keywords = [
        "chinese",
        "italian",
        "mexican",
        "indian",
        "thai",
        "japanese",
        "korean",
        "vietnamese",
        "mediterranean",
        "american",
        "french",
        "greek",
        "turkish",
        "lebanese",
        "vegetarian",
        "vegan",
        "seafood",
        "steakhouse",
        "pizza",
        "sandwich",
        "burger",
        "cafe",
        "bakery",
        "bar",
        "diner",
        "fast_food",
        "fine_dining",
        "casual_dining",
        "bbq",
        "sushi",
        "ramen",
        "tapas",
        "spanish",
        "german",
        "russian",
        "brazilian",
        "peruvian",
        "ethiopian",
    ]

    cuisines = []
    for type_name in types:
        if any(cuisine in type_name.lower() for cuisine in cuisine_keywords):
            formatted_cuisine = type_name.replace("_", " ").title()
            cuisines.append(formatted_cuisine)

    return cuisines


def _format_description(place: Dict[str, Any]) -> str:
    """Format description from editorial_summary.

    Args:
        place: Place data dictionary

    Returns:
        Formatted description string
    """
    editorial_summary = place.get("editorial_summary")
    if not editorial_summary:
        return "No description available"

    if isinstance(editorial_summary, dict):
        return editorial_summary.get("overview", "No description available")

    return str(editorial_summary)


def _build_additional_info(place: Dict[str, Any]) -> List[str]:
    """Build additional information section."""
    result = []

    # Add description prominently if available
    description = _format_description(place)
    if description != "No description available":
        result.append(f"\nDescription: {description}")

    # Add cuisine information prominently
    cuisines = _extract_cuisine_types(place)
    if cuisines:
        # Remove duplicates and limit to 5 most relevant
        unique_cuisines = list(dict.fromkeys(cuisines))[:5]
        result.append(f"\nCuisine: {', '.join(unique_cuisines)}")

    # Add detailed types information
    types_info = _format_types_detailed(place)
    if types_info:
        result.append(f"\nTypes: {types_info}")

    # Add service information
    dining_services = _format_dining_services(place)
    if dining_services:
        result.append(f"\nDining Services: {', '.join(dining_services)}")

    service_options = _format_service_options(place)
    if service_options:
        result.append(f"Service Options: {', '.join(service_options)}")

    accessibility_info = _format_accessibility_info(place)
    if accessibility_info:
        result.append(f"Accessibility: {', '.join(accessibility_info)}")

    return result


def _build_media_info(place: Dict[str, Any]) -> List[str]:
    """Build media and reviews information section."""
    result = []

    # Format photos and reviews info
    if "photos" in place and place["photos"]:
        result.append(f"\nPhotos available: {len(place['photos'])}")

    if "reviews" in place and place["reviews"]:
        result.append(f"\nRecent reviews: {len(place['reviews'])}")

    return result


def format_place_summary(place: Dict[str, Any]) -> str:
    """Format place data into a readable summary.

    Args:
        place: Place data dictionary

    Returns:
        Formatted string summary
    """
    result = _build_basic_info(place)
    result.extend(_build_additional_info(place))

    # Add hours information
    hours_info = _format_opening_hours(place)
    if hours_info:
        result.extend(["\nOpening Hours:", hours_info])

    # Add media information
    result.extend(_build_media_info(place))

    result.append("=" * 80)
    return "\n".join(result)


def format_place_table(places: List[Dict[str, Any]]) -> str:
    """Format multiple places into a table format.

    Args:
        places: List of place data dictionaries

    Returns:
        Formatted table string
    """
    if not places:
        return "No places found."

    # Define table columns with more relevant fields
    headers = ["Name", "Description", "Cuisine", "Rating", "Price", "Services", "Status"]
    rows = []

    for place in places:
        # Name (truncated)
        name = (
            place.get("name", "Unknown")[:25] + "..."
            if len(place.get("name", "")) > 25
            else place.get("name", "Unknown")
        )

        # Description (editorial_summary or first part of address)
        description = _format_description(place)
        description = description[:35] + "..." if len(description) > 35 else description

        # Cuisine (extracted from types)
        cuisines = _extract_cuisine_types(place)
        cuisine = ", ".join(cuisines[:3]) if cuisines else "N/A"
        cuisine = cuisine[:20] + "..." if len(cuisine) > 20 else cuisine

        # Rating
        rating = f"{place.get('rating', 'N/A')}/5 ({place.get('user_ratings_total', 0)})"

        # Price level
        price = "?" * place.get("price_level", 0) if place.get("price_level") else "N/A"

        # Service options (key services only)
        service_options = _format_service_options(place)
        dining_services = _format_dining_services(place)
        all_services = service_options + dining_services
        services = ", ".join(all_services[:3]) if all_services else "N/A"
        services = services[:25] + "..." if len(services) > 25 else services

        # Status
        status = place.get("business_status", "Unknown")

        rows.append([name, description, cuisine, rating, price, services, status])

    # Calculate column widths
    col_widths = [len(header) for header in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    # Build table
    result = []

    # Header
    header_row = " | ".join(header.ljust(col_widths[i]) for i, header in enumerate(headers))
    result.append(header_row)
    result.append("-" * len(header_row))

    # Data rows
    for row in rows:
        data_row = " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
        result.append(data_row)

    return "\n".join(result)


def _collect_place_statistics(
    places: List[Dict[str, Any]],
) -> Tuple[List[float], List[int], List[str], List[str], Dict[str, int]]:
    """Collect basic statistics from places data."""
    ratings = [p.get("rating") for p in places if p.get("rating")]
    price_levels = [p.get("price_level") for p in places if p.get("price_level") is not None]
    all_types = []
    business_statuses = []
    field_availability = {}

    for place in places:
        all_types.extend(place.get("types", []))
        business_statuses.append(place.get("business_status", "Unknown"))

        for field in ALL_PLACE_FIELDS:
            if field in place and place[field] is not None:
                field_availability[field] = field_availability.get(field, 0) + 1

    return ratings, price_levels, all_types, business_statuses, field_availability


def _calculate_rating_stats(ratings: List[float]) -> Dict[str, Any]:
    """Calculate rating statistics."""
    if not ratings:
        return {}

    return {
        "average": round(sum(ratings) / len(ratings), 2),
        "min": min(ratings),
        "max": max(ratings),
        "count": len(ratings),
    }


def _calculate_price_stats(price_levels: List[int]) -> Dict[str, Any]:
    """Calculate price level statistics."""
    if not price_levels:
        return {}

    return {
        "average": round(sum(price_levels) / len(price_levels), 2),
        "distribution": {str(i): price_levels.count(i) for i in range(5)},
    }


def _add_rating_insights(analysis: Dict[str, Any], insights: List[str]) -> None:
    """Add rating-related insights."""
    if analysis.get("rating_stats"):
        avg_rating = analysis["rating_stats"]["average"]
        if avg_rating >= 4.0:
            insights.append(f"High average rating: {avg_rating}/5")
        elif avg_rating <= 2.5:
            insights.append(f"Low average rating: {avg_rating}/5")


def _add_business_insights(analysis: Dict[str, Any], places: List[Dict[str, Any]], insights: List[str]) -> None:
    """Add business-related insights."""
    if analysis.get("type_frequency"):
        top_type = list(analysis["type_frequency"].keys())[0]
        insights.append(f"Most common type: {top_type} ({analysis['type_frequency'][top_type]} places)")

    if "OPERATIONAL" in analysis.get("business_status_counts", {}):
        operational_count = analysis["business_status_counts"]["OPERATIONAL"]
        if operational_count < len(places) * 0.8:
            insights.append(f"Only {operational_count}/{len(places)} places are operational")


def _count_services(places: List[Dict[str, Any]]) -> Tuple[Dict[str, int], Dict[str, int]]:
    """Count dining services and service options."""
    dining_services_count = {}
    service_options_count = {}

    for place in places:
        # Count dining services
        for field in [
            "serves_breakfast",
            "serves_lunch",
            "serves_dinner",
            "serves_brunch",
            "serves_dessert",
            "serves_vegetarian_food",
        ]:
            if place.get(field):
                service_name = field.replace("serves_", "").replace("_", " ").title()
                dining_services_count[service_name] = dining_services_count.get(service_name, 0) + 1

        # Count service options
        for field in ["delivery", "takeout", "dine_in", "curbside_pickup"]:
            if place.get(field):
                option_name = field.replace("_", " ").title()
                service_options_count[option_name] = service_options_count.get(option_name, 0) + 1

    return dining_services_count, service_options_count


def _add_service_insights(places: List[Dict[str, Any]], insights: List[str]) -> None:
    """Add service-related insights."""
    dining_services_count, service_options_count = _count_services(places)

    if dining_services_count:
        top_service = max(dining_services_count.items(), key=lambda x: x[1])
        insights.append(f"Most common dining service: {top_service[0]} ({top_service[1]}/{len(places)} places)")

    if service_options_count:
        top_option = max(service_options_count.items(), key=lambda x: x[1])
        insights.append(f"Most common service option: {top_option[0]} ({top_option[1]}/{len(places)} places)")


def _add_accessibility_insights(places: List[Dict[str, Any]], insights: List[str]) -> None:
    """Add accessibility-related insights."""
    accessible_count = sum(1 for place in places if place.get("wheelchair_accessible_entrance"))
    if accessible_count > 0:
        insights.append(f"Accessibility: {accessible_count}/{len(places)} places are wheelchair accessible")


def _add_field_availability_insights(
    analysis: Dict[str, Any], places: List[Dict[str, Any]], insights: List[str]
) -> None:
    """Add field availability insights."""
    if analysis.get("field_availability"):
        most_available = max(analysis["field_availability"].items(), key=lambda x: x[1])
        least_available = min(analysis["field_availability"].items(), key=lambda x: x[1])
        insights.append(f"Most available field: {most_available[0]} ({most_available[1]}/{len(places)})")
        insights.append(f"Least available field: {least_available[0]} ({least_available[1]}/{len(places)})")


def _generate_insights(analysis: Dict[str, Any], places: List[Dict[str, Any]]) -> List[str]:
    """Generate insights from analysis data."""
    insights = []

    _add_rating_insights(analysis, insights)
    _add_business_insights(analysis, places, insights)
    _add_service_insights(places, insights)
    _add_accessibility_insights(places, insights)
    _add_field_availability_insights(analysis, places, insights)

    return insights


def analyze_place_data(places: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze place data for insights.

    Args:
        places: List of place data dictionaries

    Returns:
        Dictionary with analysis results
    """
    if not places:
        return {"error": "No places to analyze"}

    # Collect basic statistics
    ratings, price_levels, all_types, business_statuses, field_availability = _collect_place_statistics(places)

    # Calculate statistics
    rating_stats = _calculate_rating_stats(ratings)
    price_level_stats = _calculate_price_stats(price_levels)

    # Type frequency
    type_counts = {}
    for place_type in all_types:
        type_counts[place_type] = type_counts.get(place_type, 0) + 1
    type_frequency = dict(sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10])

    # Business status counts
    business_status_counts = {}
    for status in business_statuses:
        business_status_counts[status] = business_status_counts.get(status, 0) + 1

    # Build analysis result
    analysis = {
        "total_places": len(places),
        "rating_stats": rating_stats,
        "price_level_stats": price_level_stats,
        "type_frequency": type_frequency,
        "business_status_counts": business_status_counts,
        "field_availability": field_availability,
        "insights": [],
    }

    # Generate insights
    analysis["insights"] = _generate_insights(analysis, places)

    return analysis


def export_data(places: List[Dict[str, Any]], filename: str, format_type: str = "json") -> bool:
    """Export place data to a file.

    Args:
        places: List of place data dictionaries
        filename: Output filename
        format_type: Export format ("json" or "csv")

    Returns:
        True if export successful, False otherwise
    """
    try:
        if format_type == "json":
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(places, f, indent=2, ensure_ascii=False)
        elif format_type == "csv":
            import csv

            if not places:
                return False

            # Get all possible field names
            all_fields = set()
            for place in places:
                all_fields.update(place.keys())

            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=sorted(all_fields))
                writer.writeheader()
                for place in places:
                    # Flatten nested data for CSV
                    flat_place = {}
                    for key, value in place.items():
                        if isinstance(value, (list, dict)):
                            flat_place[key] = json.dumps(value)
                        else:
                            flat_place[key] = value
                    writer.writerow(flat_place)
        else:
            print(f"Unsupported format: {format_type}")
            return False

        print(f"Data exported to {filename}")
        return True
    except Exception as e:
        print(f"Error exporting data: {str(e)}")
        return False


def _setup_argument_parser() -> argparse.ArgumentParser:
    """Setup command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Google Places CLI - Explore Google Places data for mapping insights",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search for restaurants by text
  python google_places_cli.py search "pizza near me" --location "New York, NY"

  # Search nearby places
  python google_places_cli.py nearby --lat 40.7128 --lng -74.0060 --radius 1000

  # Get detailed info for a specific place
  python google_places_cli.py details ChIJN1t_tDeuEmsRUsoyG83frY4

  # Analyze multiple places
  python google_places_cli.py search "coffee shops" --analyze --export results.json

  # Export to CSV for analysis
  python google_places_cli.py nearby --lat 40.7128 --lng -74.0060 --export results.csv --format csv
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search places by text query")
    search_parser.add_argument("query", help="Text query to search for")
    search_parser.add_argument("--location", help="Location for search bias (address or lat,lng)")
    search_parser.add_argument("--radius", type=int, default=50000, help="Search radius in meters (default: 50000)")
    search_parser.add_argument("--max", type=int, default=20, help="Maximum results (default: 20)")

    # Nearby command
    nearby_parser = subparsers.add_parser("nearby", help="Search places near a location")
    nearby_parser.add_argument("--lat", type=float, required=True, help="Latitude")
    nearby_parser.add_argument("--lng", type=float, required=True, help="Longitude")
    nearby_parser.add_argument("--radius", type=int, default=5000, help="Search radius in meters (default: 5000)")
    nearby_parser.add_argument("--type", default="restaurant", help="Place type (default: restaurant)")
    nearby_parser.add_argument("--max", type=int, default=20, help="Maximum results (default: 20)")

    # Details command
    details_parser = subparsers.add_parser("details", help="Get detailed information for a place")
    details_parser.add_argument("place_id", help="Google Place ID")

    # Common options
    for subparser in [search_parser, nearby_parser, details_parser]:
        subparser.add_argument(
            "--format", choices=["json", "table", "summary"], default="summary", help="Output format (default: summary)"
        )
        subparser.add_argument("--analyze", action="store_true", help="Show data analysis")
        subparser.add_argument("--export", help="Export results to file")
        subparser.add_argument(
            "--export-format", choices=["json", "csv"], default="json", help="Export format (default: json)"
        )

    return parser


def _parse_location(location_str: str) -> Optional[Tuple[float, float]]:
    """Parse location string into coordinates."""
    if "," in location_str and len(location_str.split(",")) == 2:
        try:
            lat, lng = map(float, location_str.split(","))
            return (lat, lng)
        except ValueError:
            return geocode_address(location_str)
    else:
        return geocode_address(location_str)


def _execute_search_command(args) -> List[Dict[str, Any]]:
    """Execute search command."""
    location = None
    if args.location:
        location = _parse_location(args.location)
        if not location:
            print(f"Could not geocode location: {args.location}")
            sys.exit(1)

    return search_places_by_text(args.query, location, args.radius, args.max)


def _execute_nearby_command(args) -> List[Dict[str, Any]]:
    """Execute nearby command."""
    return search_places_nearby((args.lat, args.lng), args.radius, args.type, args.max)


def _execute_details_command(args) -> List[Dict[str, Any]]:
    """Execute details command."""
    place = get_place_details(args.place_id)
    if place:
        return [place]
    else:
        print("Place not found or error occurred")
        sys.exit(1)


def _output_results(places: List[Dict[str, Any]], format_type: str) -> None:
    """Output results in specified format."""
    if format_type == "json":
        print(json.dumps(places, indent=2, ensure_ascii=False))
    elif format_type == "table":
        print(format_place_table(places))
    else:  # summary
        for place in places:
            print(format_place_summary(place))


def _display_analysis(places: List[Dict[str, Any]]) -> None:
    """Display data analysis."""
    print("\n" + "=" * 80)
    print("DATA ANALYSIS")
    print("=" * 80)
    analysis = analyze_place_data(places)

    print(f"Total places: {analysis['total_places']}")

    if analysis.get("rating_stats"):
        stats = analysis["rating_stats"]
        print(f"Rating stats: {stats['average']}/5 (min: {stats['min']}, max: {stats['max']}, count: {stats['count']})")

    if analysis.get("price_level_stats"):
        stats = analysis["price_level_stats"]
        print(f"Price level average: {stats['average']}")
        print(f"Price distribution: {stats['distribution']}")

    if analysis.get("type_frequency"):
        print("\nTop place types:")
        for place_type, count in list(analysis["type_frequency"].items())[:5]:
            print(f"  {place_type}: {count}")

    if analysis.get("business_status_counts"):
        print("\nBusiness status:")
        for status, count in analysis["business_status_counts"].items():
            print(f"  {status}: {count}")

    if analysis.get("insights"):
        print("\nInsights:")
        for insight in analysis["insights"]:
            print(f"  • {insight}")


def main():
    """Main CLI function."""
    parser = _setup_argument_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if not GOOGLE_MAPS_API_KEY:
        print("Error: GOOGLE_MAPS_API_KEY environment variable is not set")
        print("Please set it in your .env file or environment")
        sys.exit(1)

    # Execute command
    if args.command == "search":
        places = _execute_search_command(args)
    elif args.command == "nearby":
        places = _execute_nearby_command(args)
    elif args.command == "details":
        places = _execute_details_command(args)
    else:
        print(f"Unknown command: {args.command}")
        return

    if not places:
        print("No places found.")
        return

    # Output results
    _output_results(places, args.format)

    # Analysis
    if args.analyze:
        _display_analysis(places)

    # Export
    if args.export:
        export_data(places, args.export, args.export_format)


if __name__ == "__main__":
    main()
