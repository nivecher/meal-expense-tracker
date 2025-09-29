#!/usr/bin/env python3
"""
Google Places CLI Utility

A comprehensive command-line tool for exploring Google Places data using the new Google Places API.
Uses GOOGLE_MAPS_API_KEY from .env.

Features:
- Search places by text, location, or place ID
- Get comprehensive place details with all available fields
- Format output in multiple ways (JSON, table, summary, detailed, missing fields)
- Analyze place data for mapping insights
- Export data for further analysis
- Show missing fields analysis for data completeness
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
NEW_PLACES_API_BASE = "https://places.googleapis.com/v1/places"
GEOCODE_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# Field masks for different data categories (New API)
FIELD_MASKS = {
    "basic": "displayName,formattedAddress,location,rating,userRatingCount,priceLevel",
    "contact": "displayName,formattedAddress,nationalPhoneNumber,websiteUri,editorialSummary",
    "services": "displayName,paymentOptions,accessibilityOptions,parkingOptions,restroom,outdoorSeating",
    "food": "displayName,servesBreakfast,servesLunch,servesDinner,servesBeer,servesWine,servesBrunch,servesVegetarianFood",
    "comprehensive": "displayName,formattedAddress,nationalPhoneNumber,websiteUri,location,rating,userRatingCount,priceLevel,editorialSummary,paymentOptions,accessibilityOptions,parkingOptions,restroom,outdoorSeating,servesBreakfast,servesLunch,servesDinner,servesBeer,servesWine,servesBrunch,servesVegetarianFood,delivery,dineIn,takeout,reservable,businessStatus,primaryType,types,addressComponents,regularOpeningHours,currentOpeningHours,plusCode,photos,reviews,generativeSummary,liveMusic,menuForChildren,servesCocktails,servesDessert,servesCoffee,goodForChildren,allowsDogs,goodForGroups,goodForWatchingSports",
    "all": "*",  # Get all available fields
}

# All available fields for comprehensive data collection (New API structure)
ALL_PLACE_FIELDS = [
    # Basic Data Fields
    "id",
    "name",
    "displayName",
    "formattedAddress",
    "addressComponents",
    "location",
    "types",
    "primaryType",
    "googleMapsUri",
    "plusCode",
    "utcOffsetMinutes",
    # Contact Data Fields
    "nationalPhoneNumber",
    "internationalPhoneNumber",
    "websiteUri",
    "regularOpeningHours",
    "currentOpeningHours",
    "currentSecondaryOpeningHours",
    "regularSecondaryOpeningHours",
    # Atmosphere Data Fields
    "rating",
    "userRatingCount",
    "priceLevel",
    "priceRange",
    "reviews",
    "photos",
    # Business Status Fields
    "businessStatus",
    "primaryTypeDisplayName",
    # Service & Dining Fields
    "servesBreakfast",
    "servesLunch",
    "servesDinner",
    "servesBeer",
    "servesWine",
    "servesBrunch",
    "servesDessert",
    "servesVegetarianFood",
    "servesCocktails",
    "servesCoffee",
    # Service Options
    "delivery",
    "takeout",
    "dineIn",
    "curbsidePickup",
    "reservable",
    # Accessibility & Amenities
    "accessibilityOptions",
    "parkingOptions",
    "paymentOptions",
    "restroom",
    "outdoorSeating",
    "liveMusic",
    "menuForChildren",
    "goodForChildren",
    "allowsDogs",
    "goodForGroups",
    "goodForWatchingSports",
    # Additional Fields
    "editorialSummary",
    "generativeSummary",
    "addressDescriptor",
    "googleMapsLinks",
    "reviewSummary",
    "timeZone",
    "postalAddress",
]

# Field categories for organized display (New API structure)
FIELD_CATEGORIES = {
    "basic_info": ["id", "name", "displayName", "formattedAddress", "googleMapsUri", "editorialSummary"],
    "contact": ["nationalPhoneNumber", "internationalPhoneNumber", "websiteUri"],
    "ratings": ["rating", "userRatingCount", "reviews", "reviewSummary"],
    "business": ["types", "primaryType", "priceLevel", "priceRange", "businessStatus", "primaryTypeDisplayName"],
    "location": ["location", "addressComponents", "plusCode", "utcOffsetMinutes", "addressDescriptor", "postalAddress"],
    "hours": [
        "regularOpeningHours",
        "currentOpeningHours",
        "currentSecondaryOpeningHours",
        "regularSecondaryOpeningHours",
    ],
    "media": ["photos", "generativeSummary"],
    "dining_services": [
        "servesBreakfast",
        "servesLunch",
        "servesDinner",
        "servesBrunch",
        "servesDessert",
        "servesVegetarianFood",
        "servesBeer",
        "servesWine",
        "servesCocktails",
        "servesCoffee",
    ],
    "service_options": ["delivery", "takeout", "dineIn", "curbsidePickup", "reservable"],
    "accessibility": ["accessibilityOptions", "parkingOptions", "paymentOptions", "restroom", "outdoorSeating"],
}


def _make_api_request(
    url: str, headers: Dict[str, str], data: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """Make a request to Google APIs with proper error handling.

    Args:
        url: API endpoint URL
        headers: Request headers
        data: Optional request data for POST requests

    Returns:
        Parsed JSON response or None if request fails
    """
    try:
        if data:
            response = requests.post(url, headers=headers, json=data, timeout=10)
        else:
            response = requests.get(url, headers=headers, timeout=10)

        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error {e.response.status_code}: {e.response.reason}")
        if e.response.status_code == 403:
            print("Check your API key and ensure Places API is enabled")
        elif e.response.status_code == 429:
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

    # Geocoding still uses the classic API
    params = {"address": address, "key": GOOGLE_MAPS_API_KEY}
    try:
        response = requests.get(GEOCODE_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error geocoding address: {e}")
        return None

    if data and data.get("status") == "OK" and data.get("results"):
        location = data["results"][0]["geometry"]["location"]
        return (location["lat"], location["lng"])
    return None


def search_places_by_text(
    query: str, location: Optional[Tuple[float, float]] = None, radius: int = 50000, max_results: int = 20
) -> List[Dict[str, Any]]:
    """Search for places using text query with new Google Places API.

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

    url = f"{NEW_PLACES_API_BASE}:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": FIELD_MASKS["comprehensive"],
    }

    payload = {"textQuery": query, "maxResultCount": min(max_results, 20), "includedType": "restaurant"}

    if location:
        payload["locationBias"] = {
            "circle": {"center": {"latitude": location[0], "longitude": location[1]}, "radius": min(radius, 50000.0)}
        }

    data = _make_api_request(url, headers, payload)
    if not data:
        print("Search failed: No response from API")
        return []

    return data.get("places", [])[:max_results]


def search_places_nearby(
    location: Tuple[float, float], radius: int = 5000, place_type: str = "restaurant", max_results: int = 20
) -> List[Dict[str, Any]]:
    """Search for places near a location using new Google Places API.

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

    url = f"{NEW_PLACES_API_BASE}:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": FIELD_MASKS["comprehensive"],
    }

    payload = {
        "locationRestriction": {
            "circle": {"center": {"latitude": location[0], "longitude": location[1]}, "radius": min(radius, 50000.0)}
        },
        "maxResultCount": min(max_results, 20),
        "includedTypes": [place_type],
    }

    data = _make_api_request(url, headers, payload)
    if not data:
        print("Search failed: No response from API")
        return []

    return data.get("places", [])[:max_results]


def get_place_details(place_id: str, field_mask: str = "all") -> Optional[Dict[str, Any]]:
    """Get comprehensive details for a specific place using new Google Places API.

    Args:
        place_id: Google Place ID
        field_mask: Field mask to specify which data to retrieve

    Returns:
        Place details dictionary or None if not found
    """
    if not GOOGLE_MAPS_API_KEY:
        print("Error: GOOGLE_MAPS_API_KEY environment variable is not set")
        return None

    url = f"{NEW_PLACES_API_BASE}/{place_id}"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": FIELD_MASKS.get(field_mask, field_mask) if field_mask != "all" else "*",
    }

    data = _make_api_request(url, headers)
    if not data:
        print("Failed to get place details: No response from API")
        return None

    return data


def _format_price_level(price_level: str) -> str:
    """Format price level to readable text."""
    if not price_level:
        return "Not specified"

    price_mapping = {
        "PRICE_LEVEL_FREE": "Free",
        "PRICE_LEVEL_INEXPENSIVE": "Inexpensive ($)",
        "PRICE_LEVEL_MODERATE": "Moderate ($$)",
        "PRICE_LEVEL_EXPENSIVE": "Expensive ($$$)",
        "PRICE_LEVEL_VERY_EXPENSIVE": "Very Expensive ($$$$)",
    }

    return price_mapping.get(price_level, price_level)


def _format_opening_hours(place: Dict[str, Any]) -> str:
    """Format opening hours information."""
    regular_hours = place.get("regularOpeningHours", {})
    if not regular_hours:
        return "Hours not available"

    weekday_descriptions = regular_hours.get("weekdayDescriptions", [])
    if weekday_descriptions:
        return "\n".join([f"   • {desc}" for desc in weekday_descriptions])

    return "Hours not available"


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


def _analyze_missing_fields(place: Dict[str, Any]) -> Dict[str, List[str]]:
    """Analyze which fields are missing from the place data.

    Args:
        place: Place data dictionary

    Returns:
        Dictionary with missing fields categorized
    """
    missing = {
        "basic_info": [],
        "contact": [],
        "ratings": [],
        "business": [],
        "location": [],
        "hours": [],
        "media": [],
        "dining_services": [],
        "service_options": [],
        "accessibility": [],
    }

    # Check each category
    for category, fields in FIELD_CATEGORIES.items():
        for field in fields:
            if field not in place or place[field] is None or place[field] == "":
                missing[category].append(field)

    return missing


def _format_missing_fields_analysis(place: Dict[str, Any]) -> List[str]:
    """Format missing fields analysis for display.

    Args:
        place: Place data dictionary

    Returns:
        List of formatted strings showing missing fields
    """
    missing = _analyze_missing_fields(place)
    result = []

    result.append("\n📊 MISSING FIELDS ANALYSIS:")
    result.append("-" * 40)

    total_missing = sum(len(fields) for fields in missing.values())
    total_possible = len(ALL_PLACE_FIELDS)
    completion_rate = ((total_possible - total_missing) / total_possible) * 100

    result.append(
        f"Data Completeness: {completion_rate:.1f}% ({total_possible - total_missing}/{total_possible} fields)"
    )
    result.append("")

    # Show missing fields by category
    for category, fields in missing.items():
        if fields:
            category_name = category.replace("_", " ").title()
            result.append(f"❌ {category_name}:")
            for field in fields[:5]:  # Limit to 5 fields per category
                result.append(f"   • {field}")
            if len(fields) > 5:
                result.append(f"   ... and {len(fields) - 5} more")
            result.append("")

    # Show fields that are present
    present_fields = []
    for field in ALL_PLACE_FIELDS:
        if field in place and place[field] is not None and place[field] != "":
            present_fields.append(field)

    if present_fields:
        result.append("✅ AVAILABLE FIELDS:")
        result.append("-" * 20)
        for field in present_fields[:10]:  # Show first 10
            result.append(f"   • {field}")
        if len(present_fields) > 10:
            result.append(f"   ... and {len(present_fields) - 10} more")
        result.append("")

    return result


def _format_basic_restaurant_info(place: Dict[str, Any]) -> List[str]:
    """Format basic restaurant information."""
    display_name = place.get("displayName", {})
    name = (
        display_name.get("text")
        if isinstance(display_name, dict)
        else str(display_name) if display_name else "Unknown Restaurant"
    )
    address = place.get("formattedAddress", "Address not available")
    phone = place.get("nationalPhoneNumber", "Phone not available")
    website = place.get("websiteUri", "Website not available")
    rating = place.get("rating", "N/A")
    review_count = place.get("userRatingCount", "N/A")
    price_level = place.get("priceLevel", "")
    price_str = _format_price_level(price_level)
    business_status = place.get("businessStatus", "Status unknown")

    return [
        "**Restaurant Details:**",
        f"- **Name**: {name}",
        f"- **Address**: {address}",
        f"- **Phone**: {phone}",
        f"- **Website**: {website}",
        f"- **Rating**: {rating}/5 ({review_count} reviews)",
        f"- **Price Level**: {price_str}",
        f"- **Business Status**: {business_status}",
        "",
    ]


def _format_business_info(place: Dict[str, Any]) -> List[str]:
    """Format business information."""
    types = place.get("types", [])
    business_types = ", ".join([t.replace("_", " ").title() for t in types[:5]]) if types else "Not specified"
    business_status = place.get("businessStatus", "Status unknown")

    # Location info
    location = place.get("location", {})
    latitude = location.get("latitude", "N/A")
    longitude = location.get("longitude", "N/A")

    return [
        "**Business Information:**",
        f"- **Types**: {business_types}",
        f"- **Coordinates**: {latitude}, {longitude}",
        f"- **Business Status**: {business_status}",
        "",
    ]


def _format_service_options(place: Dict[str, Any]) -> List[str]:
    """Format service options."""
    service_options = []
    if place.get("delivery"):
        service_options.append("✅ Delivery")
    else:
        service_options.append("❌ Delivery")

    if place.get("takeout"):
        service_options.append("✅ Takeout")
    else:
        service_options.append("❌ Takeout")

    if place.get("dineIn"):
        service_options.append("✅ Dine In")
    else:
        service_options.append("❌ Dine In")

    if place.get("curbsidePickup"):
        service_options.append("✅ Curbside Pickup")
    else:
        service_options.append("❌ Curbside Pickup")

    if place.get("reservable"):
        service_options.append("✅ Reservations")
    else:
        service_options.append("❌ Reservations")

    return service_options


def _format_dining_services(place: Dict[str, Any]) -> List[str]:
    """Format dining services."""
    dining_services = []
    if place.get("servesBreakfast"):
        dining_services.append("✅ Serves Breakfast")
    else:
        dining_services.append("❌ Serves Breakfast")

    if place.get("servesLunch"):
        dining_services.append("✅ Serves Lunch")
    else:
        dining_services.append("❌ Serves Lunch")

    if place.get("servesDinner"):
        dining_services.append("✅ Serves Dinner")
    else:
        dining_services.append("❌ Serves Dinner")

    if place.get("servesBrunch"):
        dining_services.append("✅ Serves Brunch")
    else:
        dining_services.append("❌ Serves Brunch")

    if place.get("servesBeer"):
        dining_services.append("✅ Serves Beer")
    else:
        dining_services.append("❌ Serves Beer")

    if place.get("servesWine"):
        dining_services.append("✅ Serves Wine")
    else:
        dining_services.append("❌ Serves Wine")

    if place.get("servesDessert"):
        dining_services.append("✅ Serves Dessert")
    else:
        dining_services.append("❌ Serves Dessert")

    if place.get("servesVegetarianFood"):
        dining_services.append("✅ Serves Vegetarian Food")
    else:
        dining_services.append("❌ Serves Vegetarian Food")

    return dining_services


def _format_services_and_hours(place: Dict[str, Any]) -> List[str]:
    """Format services and hours information."""
    result = ["**Services Available:**"]

    # Get service options and dining services
    service_options = _format_service_options(place)
    dining_services = _format_dining_services(place)

    # Special features
    special_features = []
    if place.get("wheelchairAccessibleEntrance"):
        special_features.append("✅ Wheelchair Accessible")
    else:
        special_features.append("❌ Wheelchair Accessible")

    # Add all services
    result.extend(service_options)
    result.extend(dining_services)
    result.extend(special_features)
    result.append("")

    # Operating Hours
    result.append("**Operating Hours:**")
    hours_info = _format_opening_hours(place)
    if hours_info:
        result.append(hours_info)
    else:
        result.append("Hours not available")
    result.append("")

    return result


def _format_additional_features(place: Dict[str, Any]) -> List[str]:
    """Format additional features."""
    result = ["**Additional Features:**"]

    # Accessibility
    accessibility_info = _format_accessibility_info(place)
    if accessibility_info:
        result.append("♿ **Accessibility:**")
        for info in accessibility_info:
            result.append(f"   • {info}")
        result.append("")

    # Cuisine information
    cuisines = _extract_cuisine_types(place)
    if cuisines:
        result.append("🍽️ **Cuisine Types:**")
        for cuisine in cuisines[:5]:
            result.append(f"   • {cuisine}")
        result.append("")

    # Description
    description = _format_description(place)
    if description != "No description available":
        result.extend(["📝 **Description:**", f"   {description}", ""])

    return result


def _format_reviews_and_links(place: Dict[str, Any]) -> List[str]:
    """Format reviews and media information."""
    result = []

    # Media information
    photos_count = len(place.get("photos", []))
    reviews_count = len(place.get("reviews", []))

    if photos_count > 0 or reviews_count > 0:
        result.append("📸 **Media:**")
        if photos_count > 0:
            result.append(f"   • {photos_count} photos available")
        if reviews_count > 0:
            result.append(f"   • {reviews_count} recent reviews")
        result.append("")

    return result


def _format_place_detailed_info(place: Dict[str, Any]) -> List[str]:
    """Format place information in a clean, detailed way like the new API example.

    Args:
        place: Place data dictionary

    Returns:
        List of formatted strings
    """
    result = []

    # Header
    result.extend(["=" * 80, "📍 GOOGLE PLACES API - DETAILED RESTAURANT INFORMATION (NEW API)", "=" * 80, ""])

    # Format different sections
    result.extend(_format_basic_restaurant_info(place))
    result.extend(_format_business_info(place))
    result.extend(_format_services_and_hours(place))
    result.extend(_format_additional_features(place))
    result.extend(_format_reviews_and_links(place))

    # Missing fields analysis
    result.extend(_format_missing_fields_analysis(place))

    result.append("=" * 80)
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


def format_place_detailed(place: Dict[str, Any]) -> str:
    """Format place data into a detailed, clean summary with missing fields analysis.

    Args:
        place: Place data dictionary

    Returns:
        Formatted string summary with detailed information
    """
    result = _format_place_detailed_info(place)
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
            "--format",
            choices=["json", "table", "summary", "detailed", "missing"],
            default="summary",
            help="Output format (default: summary)",
        )
        subparser.add_argument("--analyze", action="store_true", help="Show data analysis")
        subparser.add_argument("--export", help="Export results to file")
        subparser.add_argument(
            "--export-format", choices=["json", "csv"], default="json", help="Export format (default: json)"
        )
        subparser.add_argument(
            "--field-mask",
            choices=list(FIELD_MASKS.keys()) + ["all"],
            default="comprehensive",
            help="Field mask to use",
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
    place = get_place_details(args.place_id, getattr(args, "field_mask", "all"))
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
    elif format_type == "detailed":
        for place in places:
            print(format_place_detailed(place))
    elif format_type == "missing":
        for place in places:
            print(format_place_detailed(place))  # Detailed format includes missing fields analysis
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
