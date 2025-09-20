#!/usr/bin/env python3
"""
Google Places New API CLI Tool

Test script to explore the new Google Places API (2024+) and compare
with the classic API to see what additional data is available.

Usage:
    python scripts/google_places_new_api_cli.py search "Starbucks Dallas TX"
    python scripts/google_places_new_api_cli.py details <place_id>
    python scripts/google_places_new_api_cli.py compare <place_id>
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Optional, Any

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


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="Google Places New API CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for places")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--location-bias", help="Location bias (lat,lng)")

    # Details command
    details_parser = subparsers.add_parser("details", help="Get place details")
    details_parser.add_argument("place_id", help="Google Place ID")
    details_parser.add_argument(
        "--field-mask", choices=list(FIELD_MASKS.keys()) + ["all"], default="comprehensive", help="Field mask to use"
    )

    # Compare command
    compare_parser = subparsers.add_parser("compare", help="Compare new vs classic API")
    compare_parser.add_argument("place_id", help="Google Place ID")

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
            results = search_places_new_api(args.query, args.location_bias)
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

        elif args.command == "details":
            details = get_place_details_new_api(args.place_id, args.field_mask)
            print_place_summary(details, "NEW")

            print("\n📋 FULL RESPONSE:")
            print(json.dumps(details, indent=2))

        elif args.command == "compare":
            compare_apis(args.place_id)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
