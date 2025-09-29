#!/usr/bin/env python3
"""
Google Places New API CLI Tool

Enhanced script to explore the new Google Places API (2024+) with clean,
formatted output and comparison capabilities.

Usage:
    python scripts/google_places_new_api_cli.py search "Starbucks Dallas TX"
    python scripts/google_places_new_api_cli.py details <place_id>
    python scripts/google_places_new_api_cli.py info <place_id>    # Clean formatted output
    python scripts/google_places_new_api_cli.py compare <place_id>
    python scripts/google_places_new_api_cli.py raw <place_id>     # Raw JSON output
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
NEW_PLACES_API_BASE = "https://places.googleapis.com/v1/places"
CLASSIC_PLACES_API_BASE = "https://maps.googleapis.com/maps/api/place"

# New API field masks for different data categories (corrected field names)
FIELD_MASKS = {
    "basic": "displayName,formattedAddress,location,rating,userRatingCount,priceLevel",
    "contact": "displayName,formattedAddress,nationalPhoneNumber,websiteUri,editorialSummary",
    "services": "displayName,paymentOptions,accessibilityOptions,parkingOptions,restroom,outdoorSeating",
    "food": "displayName,servesBreakfast,servesLunch,servesDinner,servesBeer,servesWine,servesBrunch,servesVegetarianFood",
    "comprehensive": "displayName,formattedAddress,nationalPhoneNumber,websiteUri,location,rating,userRatingCount,priceLevel,editorialSummary,paymentOptions,accessibilityOptions,parkingOptions,restroom,outdoorSeating,servesBreakfast,servesLunch,servesDinner,servesBeer,servesWine,servesBrunch,servesVegetarianFood,delivery,dineIn,takeout,reservable",
    "all": "*",  # Get all available fields
}


def search_places_new_api(query: str, location_bias: Optional[str] = None) -> Dict[str, Any]:
    """
    Search for places using the new Google Places API.

    Args:
        query: Search query
        location_bias: Optional location bias (lat,lng)

    Returns:
        Search results from new API
    """
    if not GOOGLE_MAPS_API_KEY:
        raise ValueError("GOOGLE_MAPS_API_KEY environment variable not set")

    # Use the correct search endpoint
    url = f"{NEW_PLACES_API_BASE}:searchText"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.priceLevel",
    }

    payload = {"textQuery": query, "maxResultCount": 10, "includedType": "restaurant"}

    if location_bias:
        lat, lng = location_bias.split(",")
        payload["locationBias"] = {
            "circle": {"center": {"latitude": float(lat), "longitude": float(lng)}, "radius": 50000.0}  # 50km radius
        }

    print(f"🔍 Searching with NEW API: {query}")
    print(f"📡 URL: {url}")
    print(f"📋 Field Mask: {headers['X-Goog-FieldMask']}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error with new API: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Response: {e.response.text}")
        raise


def get_place_details_new_api(place_id: str, field_mask: str = "comprehensive") -> Dict[str, Any]:
    """
    Get place details using the new Google Places API.

    Args:
        place_id: Google Place ID
        field_mask: Field mask to specify which data to retrieve

    Returns:
        Place details from new API
    """
    if not GOOGLE_MAPS_API_KEY:
        raise ValueError("GOOGLE_MAPS_API_KEY environment variable not set")

    url = f"{NEW_PLACES_API_BASE}/{place_id}"

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": FIELD_MASKS.get(field_mask, field_mask) if field_mask != "all" else "*",
    }

    print(f"🏢 Getting details with NEW API: {place_id}")
    print(f"📡 URL: {url}")
    print(f"📋 Field Mask: {headers['X-Goog-FieldMask']}")

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error with new API: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Response: {e.response.text}")
        raise


def get_place_details_classic_api(place_id: str) -> Dict[str, Any]:
    """
    Get place details using the classic Google Places API for comparison.

    Args:
        place_id: Google Place ID

    Returns:
        Place details from classic API
    """
    if not GOOGLE_MAPS_API_KEY:
        raise ValueError("GOOGLE_MAPS_API_KEY environment variable not set")

    url = f"{CLASSIC_PLACES_API_BASE}/details/json"

    # Use the same fields you're currently using
    fields = "name,formatted_address,formatted_phone_number,website,rating,types,address_components,opening_hours,price_level,reviews,photos,geometry,editorial_summary,current_opening_hours,utc_offset,vicinity,url,place_id,plus_code,adr_address,international_phone_number,user_ratings_total,serves_breakfast,serves_lunch,serves_dinner,serves_beer,serves_wine,serves_brunch,serves_vegetarian_food,delivery,takeout,dine_in,curbside_pickup,reservable,wheelchair_accessible_entrance"

    params = {
        "place_id": place_id,
        "fields": fields,
        "key": GOOGLE_MAPS_API_KEY,
    }

    print(f"🏢 Getting details with CLASSIC API: {place_id}")
    print(f"📡 URL: {url}")
    print(f"📋 Fields: {fields[:100]}...")

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error with classic API: {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Response: {e.response.text}")
        raise


def _extract_basic_info(place_data: Dict[str, Any], api_type: str) -> Dict[str, str]:
    """Extract basic place information from API response."""
    if api_type == "NEW":
        # New API structure
        name_obj = place_data.get("displayName", {})
        name = name_obj.get("text") if isinstance(name_obj, dict) else str(name_obj) if name_obj else "Unknown"
        return {
            "name": name,
            "address": place_data.get("formattedAddress", "Unknown"),
            "rating": place_data.get("rating", "N/A"),
            "user_count": place_data.get("userRatingCount", "N/A"),
            "price_level": place_data.get("priceLevel", "N/A"),
            "phone": place_data.get("nationalPhoneNumber", "N/A"),
            "website": place_data.get("websiteUri", "N/A"),
        }
    else:
        # Classic API structure
        return {
            "name": place_data.get("name", "Unknown"),
            "address": place_data.get("formatted_address", "Unknown"),
            "rating": place_data.get("rating", "N/A"),
            "user_count": place_data.get("user_ratings_total", "N/A"),
            "price_level": place_data.get("price_level", "N/A"),
            "phone": place_data.get("formatted_phone_number", "N/A"),
            "website": place_data.get("website", "N/A"),
        }


def _print_basic_info(info: Dict[str, str]) -> None:
    """Print basic place information."""
    print(f"🏢 Name: {info['name']}")
    print(f"📍 Address: {info['address']}")
    print(f"⭐ Rating: {info['rating']} ({info['user_count']} reviews)")
    print(f"💰 Price Level: {info['price_level']}")
    print(f"📞 Phone: {info['phone']}")
    print(f"🌐 Website: {info['website']}")


def _print_payment_options(place_data: Dict[str, Any]) -> None:
    """Print payment options from new API."""
    payment = place_data.get("paymentOptions", {})
    if not payment:
        return

    print("💳 Payment Options:")
    for method, available in payment.items():
        if available:
            print(f"   • {method.replace('_', ' ').title()}")


def _print_accessibility_options(place_data: Dict[str, Any]) -> None:
    """Print accessibility options from new API."""
    accessibility = place_data.get("accessibilityOptions", {})
    if not accessibility:
        return

    print("♿ Accessibility:")
    for feature, available in accessibility.items():
        if available:
            print(f"   • {feature.replace('_', ' ').title()}")


def _print_parking_options(place_data: Dict[str, Any]) -> None:
    """Print parking options from new API."""
    parking = place_data.get("parkingOptions", {})
    if not parking:
        return

    print("🅿️ Parking:")
    for option, available in parking.items():
        if available:
            print(f"   • {option.replace('_', ' ').title()}")


def _print_services_and_food(place_data: Dict[str, Any]) -> None:
    """Print services and food options from new API."""
    # Additional services
    services = ["restroom", "outdoorSeating", "takeout", "delivery", "dineIn"]
    for service in services:
        if place_data.get(service):
            print(f"✅ {service.replace('_', ' ').title()}: Available")

    # Food services
    food_services = [
        "servesBreakfast",
        "servesLunch",
        "servesDinner",
        "servesBeer",
        "servesWine",
        "servesBrunch",
        "servesVegetarianFood",
    ]
    food_available = [service for service in food_services if place_data.get(service)]
    if food_available:
        print("🍽️ Food Services:")
        for service in food_available:
            print(f"   • {service.replace('serves', '').replace('_', ' ').title()}")


def _print_price_range_and_summary(place_data: Dict[str, Any]) -> None:
    """Print price range and AI summary from new API."""
    # Price range
    price_range = place_data.get("priceRange", {})
    if price_range:
        start_price = price_range.get("startPrice", {}).get("units", "")
        end_price = price_range.get("endPrice", {}).get("units", "")
        if start_price and end_price:
            print(f"💰 Price Range: ${start_price}-${end_price}")

    # Generative summary
    gen_summary = place_data.get("generativeSummary", {}).get("overview", {})
    if gen_summary:
        summary_text = gen_summary.get("text", "")
        if summary_text:
            print(f"🤖 AI Summary: {summary_text}")


def _print_nearby_landmarks(place_data: Dict[str, Any]) -> None:
    """Print nearby landmarks from new API."""
    landmarks = place_data.get("addressDescriptor", {}).get("landmarks", [])
    if not landmarks:
        return

    print("🏢 Nearby Landmarks:")
    for landmark in landmarks[:3]:  # Show first 3
        landmark_name = landmark.get("displayName", {}).get("text", "Unknown")
        distance = landmark.get("straightLineDistanceMeters", 0)
        print(f"   • {landmark_name} ({distance:.0f}m away)")


def _format_opening_hours(place_data: Dict[str, Any]) -> str:
    """Format opening hours information."""
    regular_hours = place_data.get("regularOpeningHours", {})
    if not regular_hours:
        return "Hours not available"

    weekday_descriptions = regular_hours.get("weekdayDescriptions", [])
    if weekday_descriptions:
        return "\n".join([f"   • {desc}" for desc in weekday_descriptions])

    return "Hours not available"


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


def _format_business_types(types: List[str]) -> str:
    """Format business types to readable text."""
    if not types:
        return "Not specified"

    # Filter out generic types and format the meaningful ones
    meaningful_types = []
    for type_name in types:
        if type_name not in ["establishment", "point_of_interest", "food"]:
            formatted = type_name.replace("_", " ").title()
            meaningful_types.append(formatted)

    return ", ".join(meaningful_types[:3]) if meaningful_types else "Restaurant"


def _format_services(place_data: Dict[str, Any]) -> Dict[str, bool]:
    """Extract and format service availability."""
    services = {}

    # Dining options
    services["Takeout"] = place_data.get("takeout", False)
    services["Dine In"] = place_data.get("dineIn", False)
    services["Delivery"] = place_data.get("delivery", False)
    services["Curbside Pickup"] = place_data.get("curbsidePickup", False)
    services["Reservations"] = place_data.get("reservable", False)

    # Meal services
    services["Serves Breakfast"] = place_data.get("servesBreakfast", False)
    services["Serves Lunch"] = place_data.get("servesLunch", False)
    services["Serves Dinner"] = place_data.get("servesDinner", False)
    services["Serves Brunch"] = place_data.get("servesBrunch", False)

    # Beverage services
    services["Serves Beer"] = place_data.get("servesBeer", False)
    services["Serves Wine"] = place_data.get("servesWine", False)
    services["Serves Cocktails"] = place_data.get("servesCocktails", False)
    services["Serves Coffee"] = place_data.get("servesCoffee", False)

    # Special features
    services["Good for Children"] = place_data.get("goodForChildren", False)
    services["Good for Groups"] = place_data.get("goodForGroups", False)
    services["Outdoor Seating"] = place_data.get("outdoorSeating", False)
    services["Live Music"] = place_data.get("liveMusic", False)
    services["Restrooms"] = place_data.get("restroom", False)

    return services


def _format_accessibility(place_data: Dict[str, Any]) -> Dict[str, bool]:
    """Extract accessibility features."""
    accessibility = place_data.get("accessibilityOptions", {})

    features = {}
    features["Wheelchair Accessible Parking"] = accessibility.get("wheelchairAccessibleParking", False)
    features["Wheelchair Accessible Entrance"] = accessibility.get("wheelchairAccessibleEntrance", False)
    features["Wheelchair Accessible Restroom"] = accessibility.get("wheelchairAccessibleRestroom", False)
    features["Wheelchair Accessible Seating"] = accessibility.get("wheelchairAccessibleSeating", False)

    return features


def _format_payment_options(place_data: Dict[str, Any]) -> Dict[str, bool]:
    """Extract payment options."""
    payment = place_data.get("paymentOptions", {})

    options = {}
    options["Accepts Credit Cards"] = payment.get("acceptsCreditCards", False)
    options["Accepts Debit Cards"] = payment.get("acceptsDebitCards", False)
    options["Accepts NFC"] = payment.get("acceptsNfc", False)
    options["Cash Only"] = payment.get("acceptsCashOnly", False)

    return options


def _format_parking_options(place_data: Dict[str, Any]) -> Dict[str, bool]:
    """Extract parking options."""
    parking = place_data.get("parkingOptions", {})

    options = {}
    options["Free Parking Lot"] = parking.get("freeParkingLot", False)
    options["Free Street Parking"] = parking.get("freeStreetParking", False)
    options["Paid Street Parking"] = parking.get("paidStreetParking", False)

    return options


def _print_basic_restaurant_info(place_data: Dict[str, Any]) -> None:
    """Print basic restaurant information."""
    display_name = place_data.get("displayName", {})
    name = (
        display_name.get("text")
        if isinstance(display_name, dict)
        else str(display_name) if display_name else "Unknown Restaurant"
    )

    formatted_address = place_data.get("formattedAddress", "Address not available")
    phone = place_data.get("nationalPhoneNumber", "Phone not available")
    website = place_data.get("websiteUri", "Website not available")
    rating = place_data.get("rating", "N/A")
    review_count = place_data.get("userRatingCount", "N/A")
    price_level = _format_price_level(place_data.get("priceLevel", ""))
    business_status = place_data.get("businessStatus", "Status unknown")

    print("**Restaurant Details:**")
    print(f"- **Name**: {name}")
    print(f"- **Address**: {formatted_address}")
    print(f"- **Phone**: {phone}")
    print(f"- **Website**: {website}")
    print(f"- **Rating**: {rating}/5 ({review_count} reviews)")
    print(f"- **Price Level**: {price_level}")
    print(f"- **Business Status**: {business_status}")
    print()


def _print_business_info(place_data: Dict[str, Any]) -> None:
    """Print business information."""
    location = place_data.get("location", {})
    latitude = location.get("latitude", "N/A")
    longitude = location.get("longitude", "N/A")

    types = place_data.get("types", [])
    primary_type = place_data.get("primaryType", "")
    business_types = _format_business_types(types)
    business_status = place_data.get("businessStatus", "Status unknown")

    print("**Business Information:**")
    print(f"- **Types**: {business_types}")
    print(f"- **Primary Type**: {primary_type.replace('_', ' ').title() if primary_type else 'Not specified'}")
    print(f"- **Business Status**: {business_status}")
    print(f"- **Coordinates**: {latitude}, {longitude}")
    print()


def _print_services_and_hours(place_data: Dict[str, Any]) -> None:
    """Print services and operating hours."""
    print("**Services Available:**")
    services = _format_services(place_data)
    for service, available in services.items():
        status = "✅" if available else "❌"
        print(f"{status} {service}")
    print()

    print("**Operating Hours:**")
    hours_text = _format_opening_hours(place_data)
    print(hours_text)
    print()

    # Happy Hour (if available)
    secondary_hours = place_data.get("regularSecondaryOpeningHours", [])
    if secondary_hours:
        print("**Happy Hour:**")
        for hours_info in secondary_hours:
            if hours_info.get("secondaryHoursType") == "HAPPY_HOUR":
                descriptions = hours_info.get("weekdayDescriptions", [])
                for desc in descriptions:
                    print(f"   • {desc}")
        print()


def _print_accessibility_features(place_data: Dict[str, Any]) -> None:
    """Print accessibility features."""
    accessibility = _format_accessibility(place_data)
    if any(accessibility.values()):
        print("♿ **Accessibility:**")
        for feature, available in accessibility.items():
            if available:
                print(f"   • {feature}")
        print()


def _print_payment_features(place_data: Dict[str, Any]) -> None:
    """Print payment options."""
    payment = _format_payment_options(place_data)
    if any(payment.values()):
        print("💳 **Payment Options:**")
        for option, available in payment.items():
            if available:
                print(f"   • {option}")
        print()


def _print_parking_features(place_data: Dict[str, Any]) -> None:
    """Print parking options."""
    parking = _format_parking_options(place_data)
    if any(parking.values()):
        print("🅿️ **Parking:**")
        for option, available in parking.items():
            if available:
                print(f"   • {option}")
        print()


def _print_price_and_summary(place_data: Dict[str, Any]) -> None:
    """Print price range and AI summary."""
    # Price Range (if available)
    price_range = place_data.get("priceRange", {})
    if price_range:
        start_price = price_range.get("startPrice", {}).get("units", "")
        end_price = price_range.get("endPrice", {}).get("units", "")
        if start_price and end_price:
            print(f"💰 **Price Range**: ${start_price}-${end_price}")
            print()

    # AI Summary (if available)
    gen_summary = place_data.get("generativeSummary", {}).get("overview", {})
    if gen_summary and gen_summary.get("text"):
        print(f"🤖 **AI Summary**: {gen_summary['text']}")
        print()


def _print_additional_features(place_data: Dict[str, Any]) -> None:
    """Print additional features like accessibility, payment, parking."""
    print("**Additional Features:**")

    _print_accessibility_features(place_data)
    _print_payment_features(place_data)
    _print_parking_features(place_data)
    _print_price_and_summary(place_data)


def _print_reviews_and_links(place_data: Dict[str, Any]) -> None:
    """Print reviews and Google Maps links."""
    # Nearby Landmarks
    landmarks = place_data.get("addressDescriptor", {}).get("landmarks", [])
    if landmarks:
        print("🏢 **Nearby Landmarks:**")
        for landmark in landmarks[:3]:  # Show first 3
            landmark_name = landmark.get("displayName", {}).get("text", "Unknown")
            distance = landmark.get("straightLineDistanceMeters", 0)
            print(f"   • {landmark_name} ({distance:.0f}m away)")
        print()

    # Recent Reviews (if available)
    reviews = place_data.get("reviews", [])
    if reviews:
        print("📝 **Recent Reviews:**")
        for i, review in enumerate(reviews[:3], 1):  # Show first 3
            author = review.get("authorAttribution", {}).get("displayName", "Anonymous")
            rating = review.get("rating", "N/A")
            text = review.get("text", {}).get("text", "")
            time_desc = review.get("relativePublishTimeDescription", "")

            print(f"   {i}. **{author}** ({rating}/5) - {time_desc}")
            if text:
                # Truncate long reviews
                display_text = text[:150] + "..." if len(text) > 150 else text
                print(f'      "{display_text}"')
        print()

    # Google Maps Links
    google_links = place_data.get("googleMapsLinks", {})
    if google_links:
        print("🗺️ **Google Maps Links:**")
        if google_links.get("placeUri"):
            print(f"   • [View on Google Maps]({google_links['placeUri']})")
        if google_links.get("directionsUri"):
            print(f"   • [Get Directions]({google_links['directionsUri']})")
        if google_links.get("writeAReviewUri"):
            print(f"   • [Write a Review]({google_links['writeAReviewUri']})")
        print()


def print_formatted_place_info(place_data: Dict[str, Any]) -> None:
    """Print place information in a clean, formatted way like the example above."""
    print("=" * 80)
    print("📍 GOOGLE PLACES API - DETAILED RESTAURANT INFORMATION")
    print("=" * 80)
    print()

    _print_basic_restaurant_info(place_data)
    _print_business_info(place_data)
    _print_services_and_hours(place_data)
    _print_additional_features(place_data)
    _print_reviews_and_links(place_data)

    print("=" * 80)


def print_place_summary(place_data: Dict[str, Any], api_type: str) -> None:
    """Print a summary of place data."""
    print(f"\n{'=' * 60}")
    print(f"📍 {api_type.upper()} API RESULTS")
    print(f"{'=' * 60}")

    # Extract and print basic information
    info = _extract_basic_info(place_data, api_type)
    _print_basic_info(info)

    # Print new API specific fields
    if api_type == "NEW":
        print("\n🆕 NEW API SPECIFIC FIELDS:")
        _print_payment_options(place_data)
        _print_accessibility_options(place_data)
        _print_parking_options(place_data)
        _print_services_and_food(place_data)
        _print_price_range_and_summary(place_data)
        _print_nearby_landmarks(place_data)


def compare_apis(place_id: str):
    """Compare data from both APIs for the same place."""
    print(f"\n🔄 COMPARING APIs FOR PLACE ID: {place_id}")
    print("=" * 80)

    try:
        # Get data from both APIs
        print("\n📡 Fetching from NEW API...")
        new_data = get_place_details_new_api(place_id, "comprehensive")

        print("\n📡 Fetching from CLASSIC API...")
        classic_data = get_place_details_classic_api(place_id)

        # Print summaries
        print_place_summary(new_data, "NEW")
        print_place_summary(classic_data, "CLASSIC")

        # Show field differences
        print("\n🔍 FIELD COMPARISON:")
        print("=" * 60)

        new_fields = set(new_data.keys())
        classic_result = classic_data.get("result", {})
        classic_fields = set(classic_result.keys()) if classic_result else set()

        only_new = new_fields - classic_fields
        only_classic = classic_fields - new_fields
        common = new_fields & classic_fields

        print(f"📊 Total fields - NEW: {len(new_fields)}, CLASSIC: {len(classic_fields)}")
        print(f"🤝 Common fields: {len(common)}")
        print(f"🆕 Only in NEW API: {len(only_new)}")
        print(f"📜 Only in CLASSIC API: {len(only_classic)}")

        if only_new:
            print("\n🆕 NEW API EXCLUSIVE FIELDS:")
            for field in sorted(only_new):
                print(f"   • {field}")

        if only_classic:
            print("\n📜 CLASSIC API EXCLUSIVE FIELDS:")
            for field in sorted(only_classic):
                print(f"   • {field}")

        # Show key differences
        print("\n🆚 KEY DIFFERENCES:")
        print("=" * 60)

        # Price level comparison
        new_price = new_data.get("priceLevel", "N/A")
        classic_price = classic_result.get("price_level", "N/A")
        print(f"💰 Price Level - NEW: {new_price}, CLASSIC: {classic_price}")

        # Rating comparison
        new_rating = new_data.get("rating", "N/A")
        classic_rating = classic_result.get("rating", "N/A")
        print(f"⭐ Rating - NEW: {new_rating}, CLASSIC: {classic_rating}")

        # Review count comparison
        new_reviews = new_data.get("userRatingCount", "N/A")
        classic_reviews = classic_result.get("user_ratings_total", "N/A")
        print(f"📝 Review Count - NEW: {new_reviews}, CLASSIC: {classic_reviews}")

        # Business status comparison
        new_status = new_data.get("businessStatus", "N/A")
        classic_status = classic_result.get("business_status", "N/A")
        print(f"🏪 Business Status - NEW: {new_status}, CLASSIC: {classic_status}")

        # Show raw data for inspection
        print("\n📋 RAW DATA COMPARISON:")
        print("=" * 60)
        print("NEW API (first 500 chars):")
        print(json.dumps(new_data, indent=2)[:500] + "...")

        print("\nCLASSIC API (first 500 chars):")
        print(json.dumps(classic_data, indent=2)[:500] + "...")

    except Exception as e:
        print(f"❌ Error comparing APIs: {e}")


def _setup_argument_parser() -> argparse.ArgumentParser:
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(description="Google Places New API CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for places")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--location-bias", help="Location bias (lat,lng)")

    # Details command
    details_parser = subparsers.add_parser("details", help="Get place details (basic summary)")
    details_parser.add_argument("place_id", help="Google Place ID")
    details_parser.add_argument(
        "--field-mask", choices=list(FIELD_MASKS.keys()) + ["all"], default="comprehensive", help="Field mask to use"
    )

    # Info command (new formatted output)
    info_parser = subparsers.add_parser("info", help="Get formatted place information (clean output)")
    info_parser.add_argument("place_id", help="Google Place ID")
    info_parser.add_argument(
        "--field-mask", choices=list(FIELD_MASKS.keys()) + ["all"], default="all", help="Field mask to use"
    )

    # Raw command (new raw JSON output)
    raw_parser = subparsers.add_parser("raw", help="Get raw JSON response")
    raw_parser.add_argument("place_id", help="Google Place ID")
    raw_parser.add_argument(
        "--field-mask", choices=list(FIELD_MASKS.keys()) + ["all"], default="all", help="Field mask to use"
    )

    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare new vs classic API")
    compare_parser.add_argument("place_id", help="Google Place ID")

    return parser


def _handle_search_command(query: str, location_bias: Optional[str]) -> None:
    """Handle search command."""
    results = search_places_new_api(query, location_bias)
    print("\n🔍 SEARCH RESULTS:")
    print("=" * 60)

    places = results.get("places", [])
    print(f"Found {len(places)} places:")

    for i, place in enumerate(places, 1):
        name = place.get("displayName", "Unknown")
        place_id = place.get("id", "No ID")
        rating = place.get("rating", "N/A")
        print(f"{i}. {name} (ID: {place_id}) - Rating: {rating}")

        if i == 1:  # Show details for first result
            print("\n📋 First result details:")
            print(json.dumps(place, indent=2))


def _handle_details_command(place_id: str, field_mask: str) -> None:
    """Handle details command."""
    details = get_place_details_new_api(place_id, field_mask)
    print_place_summary(details, "NEW")

    print("\n📋 FULL RESPONSE:")
    print(json.dumps(details, indent=2))


def _handle_info_command(place_id: str, field_mask: str) -> None:
    """Handle info command."""
    details = get_place_details_new_api(place_id, field_mask)
    print_formatted_place_info(details)


def _handle_raw_command(place_id: str, field_mask: str) -> None:
    """Handle raw command."""
    details = get_place_details_new_api(place_id, field_mask)
    print("FULL JSON RESPONSE FROM GOOGLE PLACES API:")
    print("=" * 80)
    print(json.dumps(details, indent=2, ensure_ascii=False))


def _handle_compare_command(place_id: str) -> None:
    """Handle compare command."""
    compare_apis(place_id)


def main():
    """Main CLI function."""
    parser = _setup_argument_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if not GOOGLE_MAPS_API_KEY:
        print("❌ Error: GOOGLE_MAPS_API_KEY environment variable not set")
        print("Please set your Google Maps API key in .env file")
        sys.exit(1)

    try:
        if args.command == "search":
            _handle_search_command(args.query, args.location_bias)
        elif args.command == "details":
            _handle_details_command(args.place_id, args.field_mask)
        elif args.command == "info":
            _handle_info_command(args.place_id, args.field_mask)
        elif args.command == "raw":
            _handle_raw_command(args.place_id, args.field_mask)
        elif args.command == "compare":
            _handle_compare_command(args.place_id)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
