#!/usr/bin/env python3
"""
Restaurant Search Script

This script searches for nearby restaurants using the Google Places API.
It can filter results by keyword, radius, and location.
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# Load environment variables from .env file if it exists
from dotenv import load_dotenv

load_dotenv()

# Configuration
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
PLACES_API_BASE_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
DEFAULT_RADIUS = 5000  # 5km in meters
DEFAULT_MAX_RESULTS = 10


def _make_places_api_request(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Make a request to the Google Places API.

    Args:
        params: Query parameters for the API request

    Returns:
        Parsed JSON response or None if request fails
    """
    try:
        url = f"{PLACES_API_BASE_URL}?{urlencode(params)}"
        response = urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}))
        return json.loads(response.read().decode())
    except HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
    except Exception as e:
        print(f"Error making API request: {str(e)}")
    return None


def _process_places_response(
    data: Dict[str, Any], all_results: List[Dict[str, Any]], max_results: int
) -> Optional[str]:
    """Process the API response and update results.

    Args:
        data: API response data
        all_results: List to store processed results
        max_results: Maximum number of results to collect

    Returns:
        Next page token if available, None otherwise
    """
    if data.get("status") != "OK":
        print(f"Error from Google Places API: {data.get('status', 'Unknown error')}")
        if data.get("status") == "OVER_QUERY_LIMIT":
            print("You may have exceeded your API quota.")
        return None

    for place in data.get("results", []):
        if place_id := place.get("place_id"):
            if place_details := get_place_details(place_id):
                all_results.append(place_details)
                if len(all_results) >= max_results:
                    return None

    return data.get("next_page_token")


def _get_next_page_params(next_page_token: str) -> Dict[str, str]:
    """Get parameters for the next page request."""
    return {"pagetoken": next_page_token, "key": GOOGLE_MAPS_API_KEY}


def get_nearby_places(
    location: str,
    radius: int = DEFAULT_RADIUS,
    keyword: Optional[str] = None,
    max_results: int = DEFAULT_MAX_RESULTS,
) -> List[Dict[str, Any]]:
    """
    Search for places near a location using Google Places API.

    Args:
        location: Latitude and longitude as "lat,lng" or an address string (for search purposes)
        radius: Search radius in meters (max 50000)
        keyword: Optional filter for the search (e.g., 'restaurant', 'pizza')
        max_results: Maximum number of results to return

    Returns:
        List of place details
    """
    if not GOOGLE_MAPS_API_KEY:
        print("Error: GOOGLE_MAPS_API_KEY environment variable is not set")
        sys.exit(1)

    # If location is not in lat,lng format, geocode it
    if not all(coord.strip().replace(".", "").replace("-", "").isdigit() for coord in location.split(",")):
        location = geocode_address(location)
        if not location:
            print(f"Error: Could not find coordinates for location: {location}")
            return []

    params = {
        "location": location,
        "radius": min(radius, 50000),  # Max 50km
        "key": GOOGLE_MAPS_API_KEY,
        "type": "restaurant",
    }

    if keyword:
        params["keyword"] = keyword

    all_results: List[Dict[str, Any]] = []
    next_page_token = None

    try:
        while len(all_results) < max_results:
            current_params = _get_next_page_params(next_page_token) if next_page_token else params
            data = _make_places_api_request(current_params)

            if not data:
                break

            next_page_token = _process_places_response(data, all_results, max_results)

            if not next_page_token or len(all_results) >= max_results:
                break

            # Wait before making the next request (required by Google's API)
            import time

            time.sleep(2)

    except Exception as e:
        print(f"Unexpected error: {str(e)}")

    return all_results[:max_results]


def get_place_details(place_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed information about a place using its place_id."""
    try:
        params = {
            "place_id": place_id,
            "fields": "name,formatted_address,formatted_phone_number,website,rating,userRatingsTotal,"
            "opening_hours,priceLevel,types",
            "key": GOOGLE_MAPS_API_KEY,
        }
        url = f"{PLACE_DETAILS_URL}?{urlencode(params)}"
        response = urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}))
        data = json.loads(response.read().decode())

        if data.get("status") == "OK":
            return data.get("result")
        return None
    except Exception as e:
        print(f"Error getting place details: {str(e)}")
        return None


def geocode_address(address: str) -> Optional[str]:
    """Convert an address to latitude and longitude for search purposes."""
    try:
        params = {"address": address, "key": GOOGLE_MAPS_API_KEY}
        url = f"https://maps.googleapis.com/maps/api/geocode/json?{urlencode(params)}"
        response = urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}))
        data = json.loads(response.read().decode())

        if data.get("status") == "OK" and data.get("results"):
            location = data["results"][0]["geometry"]["location"]
            return f"{location['lat']},{location['lng']}"
        return None
    except Exception as e:
        print(f"Geocoding error: {str(e)}")
        return None


def format_restaurant(restaurant: Dict[str, Any]) -> str:
    """Format a restaurant's details into a readable string."""
    name = restaurant.get("name", "Unknown")
    address = restaurant.get("formatted_address", "No address available")
    phone = restaurant.get("formatted_phone_number", "No phone number")
    rating = restaurant.get("rating", "N/A")
    total_ratings = restaurant.get("userRatingsTotal", 0)
    price_level = "?" * restaurant.get("priceLevel", 0) or "Not specified"
    website = restaurant.get("website", "No website")

    # Format opening hours if available
    opening_hours = []
    if "opening_hours" in restaurant and "weekday_text" in restaurant["opening_hours"]:
        opening_hours = restaurant["opening_hours"]["weekday_text"]

    result = [
        f"\n{'=' * 80}",
        f"Name: {name}",
        f"Address: {address}",
        f"Phone: {phone}",
        f"Rating: {rating}/5 ({total_ratings} reviews)",
        f"Price: {price_level}",
        f"Website: {website}",
    ]

    if opening_hours:
        result.append("\nOpening Hours:")
        result.extend([f"- {day}" for day in opening_hours])

    result.append("=" * 80)
    return "\n".join(result)


def main():
    parser = argparse.ArgumentParser(description="Search for nearby restaurants using Google Places API")
    parser.add_argument("location", type=str, help="Location (address or lat,lng)")
    parser.add_argument(
        "--radius", "-r", type=int, default=DEFAULT_RADIUS, help=f"Search radius in meters (default: {DEFAULT_RADIUS}m)"
    )
    parser.add_argument("--keyword", "-k", type=str, default=None, help='Filter by keyword (e.g., "italian", "pizza")')
    parser.add_argument(
        "--max",
        "-m",
        type=int,
        default=DEFAULT_MAX_RESULTS,
        help=f"Maximum number of results (default: {DEFAULT_MAX_RESULTS})",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON for programmatic use")

    args = parser.parse_args()

    print(f"Searching for restaurants near: {args.location}")
    if args.keyword:
        print(f"Filtering by keyword: {args.keyword}")
    print("-" * 50)

    results = get_nearby_places(location=args.location, radius=args.radius, keyword=args.keyword, max_results=args.max)

    if not results:
        print("No restaurants found.")
        return

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for restaurant in results:
            print(format_restaurant(restaurant))


if __name__ == "__main__":
    main()
