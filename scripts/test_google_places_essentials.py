#!/usr/bin/env python3
"""Test Google Places API (New) with Essentials tier fields only.

This script tests the Google Places API using only Essentials tier fields
to verify field availability and control costs.
"""

import json
import os
from pathlib import Path
import sys
from typing import cast

from dotenv import load_dotenv
import requests

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# API configuration
BASE_URL = "https://places.googleapis.com/v1/places"
# Try GOOGLE_API_KEY first, then fallback to GOOGLE_MAPS_API_KEY
API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")

if not API_KEY:
    print("❌ Error: GOOGLE_API_KEY or GOOGLE_MAPS_API_KEY not found in .env file")
    print(f"   Checked .env file at: {env_path}")
    print("   Please add GOOGLE_API_KEY=your-api-key to .env file")
    sys.exit(1)


def parse_address_components(address_data: dict) -> dict[str, str]:
    """Parse address fields into readable individual components.

    Args:
        address_data: Dictionary containing address fields from API response

    Returns:
        Dictionary with parsed address components
    """
    parsed = {
        "street_number": "",
        "street_name": "",
        "address_line_1": "",
        "address_line_2": "",
        "city": "",
        "state": "",
        "state_code": "",
        "postal_code": "",
        "country": "",
        "country_code": "",
    }

    # Parse addressComponents if available (preferred source)
    address_components = address_data.get("addressComponents", [])
    if address_components:
        for component in address_components:
            types = component.get("types", [])
            long_name = component.get("longText", "") or component.get("longName", "")
            short_name = component.get("shortText", "") or component.get("shortName", "")

            if "street_number" in types:
                parsed["street_number"] = long_name or ""
            elif "route" in types:
                parsed["street_name"] = long_name or ""
            elif "locality" in types or "sublocality" in types:
                if not parsed["city"]:  # Prefer locality over sublocality
                    parsed["city"] = long_name or ""
            elif "administrative_area_level_1" in types:
                parsed["state"] = long_name or ""
                parsed["state_code"] = short_name or ""
            elif "postal_code" in types:
                parsed["postal_code"] = long_name or ""
            elif "country" in types:
                parsed["country"] = long_name or ""
                parsed["country_code"] = short_name or ""
            elif "premise" in types or "subpremise" in types:
                parsed["address_line_2"] = long_name or ""

    # Fallback: Parse postalAddress if addressComponents not available
    postal_address = address_data.get("postalAddress")
    if not address_components and postal_address:
        # postalAddress is a structured object with addressLines, locality, etc.
        if isinstance(postal_address, dict):
            address_lines = postal_address.get("addressLines", [])
            if address_lines and not parsed["address_line_1"]:
                parsed["address_line_1"] = address_lines[0] if len(address_lines) > 0 else ""
                if len(address_lines) > 1:
                    parsed["address_line_2"] = address_lines[1]
            if not parsed["city"]:
                parsed["city"] = postal_address.get("locality", "")
            if not parsed["state"]:
                parsed["state"] = postal_address.get("administrativeArea", "")
            if not parsed["postal_code"]:
                parsed["postal_code"] = postal_address.get("postalCode", "")
            if not parsed["country"]:
                parsed["country"] = postal_address.get("regionCode", "")
                parsed["country_code"] = postal_address.get("regionCode", "")

    # Build address_line_1 from street_number and street_name
    street_parts = [parsed["street_number"], parsed["street_name"]]
    parsed["address_line_1"] = " ".join(filter(None, street_parts)).strip()

    return parsed


def format_address_display(parsed_address: dict) -> str:
    """Format parsed address into readable display format.

    Args:
        parsed_address: Dictionary with parsed address components

    Returns:
        Formatted address string
    """
    lines = []

    if parsed_address.get("address_line_1"):
        lines.append(f"   Street: {parsed_address['address_line_1']}")
    if parsed_address.get("address_line_2"):
        lines.append(f"   Unit/Suite: {parsed_address['address_line_2']}")
    if parsed_address.get("city"):
        lines.append(f"   City: {parsed_address['city']}")
    if parsed_address.get("state"):
        state_display = parsed_address["state"]
        if parsed_address.get("state_code") and parsed_address["state_code"] != parsed_address["state"]:
            state_display += f" ({parsed_address['state_code']})"
        lines.append(f"   State: {state_display}")
    if parsed_address.get("postal_code"):
        lines.append(f"   ZIP/Postal Code: {parsed_address['postal_code']}")
    if parsed_address.get("country"):
        country_display = parsed_address["country"]
        if parsed_address.get("country_code") and parsed_address["country_code"] != parsed_address["country"]:
            country_display += f" ({parsed_address['country_code']})"
        lines.append(f"   Country: {country_display}")

    return "\n".join(lines) if lines else "   (No address components available)"


def make_request(method: str, url: str, field_mask: str, payload: dict | None = None) -> dict:
    """Make a request to Google Places API with Essentials tier fields."""
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": field_mask,
    }

    # Add Referer header if configured (helps with API key restrictions)
    # For server-side requests, try to use configured referrer or default
    referrer = os.getenv("GOOGLE_API_REFERRER_DOMAIN")
    if referrer:
        headers["Referer"] = f"https://{referrer}"
    else:
        # Default to localhost for development
        headers["Referer"] = "https://localhost:5000"

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        else:
            response = requests.post(url, headers=headers, json=payload, timeout=10)

        response.raise_for_status()
        return cast(dict[str, object], response.json())
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"Response: {json.dumps(error_data, indent=2)}")

                # Provide helpful guidance for common errors
                if e.response.status_code == 403:
                    error_msg = str(error_data)
                    if "referer" in error_msg.lower() or "referrer" in error_msg.lower():
                        print("\n💡 Tip: Your API key has referrer restrictions.")
                        print("   For server-side requests, you have two options:")
                        print("   1. Remove referrer restrictions from your API key in Google Cloud Console")
                        print("   2. Add IP address restrictions instead (recommended for server-side)")
                        print(f"   3. Add '{referrer or 'localhost:5000'}' to allowed referrers")
            except Exception:
                print(f"Response: {e.response.text}")
        return {}


def test_place_details() -> None:
    """Test Place Details endpoint with Essentials tier fields."""
    print("📍 Test 1: Place Details (Essentials tier fields)")
    field_mask = "id,formattedAddress,location,addressComponents,postalAddress,name,shortFormattedAddress,viewport"
    print(f"Field mask: {field_mask}")
    print()

    # Example restaurant place IDs in Texas (well-known chains)
    # Using popular Texas restaurants for better test relevance
    # Note: Place IDs may need to be looked up via search - these are examples
    test_restaurants = [
        ("ChIJh0G8J1YZRIYRR8IQgY2xC7k", "Whataburger - Austin, TX"),
        ("ChIJu8f9K1YZRIYRw_cJ_wM9h2s", "Rudy's Country Store & Bar-B-Q - Austin, TX"),
        ("ChIJlQ0Zt1QZRIYRJgYE8LZqVH4", "Franklin Barbecue - Austin, TX"),
    ]

    # Try the first restaurant
    # If place ID lookup fails, use a text search first to find valid place IDs
    place_id, restaurant_name = test_restaurants[0]
    print(f"Testing with: {restaurant_name}")
    print(f"Place ID: {place_id}")
    print("(Note: If this place doesn't exist, the API will return an error)")
    print("      You can find valid place IDs by running the text search test first.")
    print()

    url = f"{BASE_URL}/{place_id}"

    result = make_request("GET", url, field_mask)

    if result and "error" not in result:
        print("✅ Success! Response includes:")
        if "id" in result:
            print(f"   - ID: {result.get('id')}")
        if "name" in result:
            print(f"   - Name: {result.get('name')}")
        if "formattedAddress" in result:
            print(f"   - Formatted Address: {result.get('formattedAddress')}")
        if "shortFormattedAddress" in result:
            print(f"   - Short Formatted Address: {result.get('shortFormattedAddress')}")
        if "postalAddress" in result:
            print(f"   - Postal Address: {result.get('postalAddress')}")
        if "addressComponents" in result or "postalAddress" in result:
            print("   - Parsed Address Components:")
            parsed_addr = parse_address_components(result)
            print(format_address_display(parsed_addr))
        if "location" in result:
            loc = result.get("location", {})
            print(f"   - Location: {loc.get('latitude')}, {loc.get('longitude')}")
        if "viewport" in result:
            viewport = result.get("viewport", {})
            print(f"   - Viewport: {viewport}")
        print()
        print("Full response:")
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result, indent=2))
    print()
    print("---")
    print()


def test_text_search() -> None:
    """Test Text Search endpoint with Essentials tier fields."""
    print("🔍 Test 2: Text Search (Essentials tier fields)")
    field_mask = (
        "places.id,places.formattedAddress,places.location,"
        "places.postalAddress,places.addressComponents,"
        "places.name,places.shortFormattedAddress,places.viewport"
    )
    print(f"Field mask: {field_mask}")
    print()

    # Search for well-known restaurant chains in Texas
    search_query = "Texas BBQ restaurant Austin"
    print(f"Searching for: {search_query}")
    print()

    url = f"{BASE_URL}:searchText"
    payload = {
        "textQuery": search_query,
        "maxResultCount": 3,
    }

    result = make_request("POST", url, field_mask, payload)

    if result and "places" in result and not result.get("error"):
        places = result.get("places", [])
        print(f"✅ Success! Found {len(places)} result(s):")
        for idx, place in enumerate(places, 1):
            print(f"\n   {idx}. Place ID: {place.get('id', 'N/A')}")
            if "name" in place:
                print(f"      Name: {place.get('name')}")
            if "formattedAddress" in place:
                print(f"      Formatted Address: {place.get('formattedAddress')}")
            if "shortFormattedAddress" in place:
                print(f"      Short Address: {place.get('shortFormattedAddress')}")
            if "addressComponents" in place or "postalAddress" in place:
                parsed_addr = parse_address_components(place)
                addr_lines = format_address_display(parsed_addr).split("\n")
                for line in addr_lines:
                    if line.strip():
                        print(f"      {line}")
            if "location" in place:
                loc = place.get("location", {})
                print(f"      Location: {loc.get('latitude')}, {loc.get('longitude')}")
        print()
        print("Full response:")
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result, indent=2))
    print()
    print("---")
    print()


def test_nearby_search() -> None:
    """Test Nearby Search endpoint with Essentials tier fields."""
    print("🗺️  Test 3: Nearby Search (Essentials tier fields)")
    field_mask = (
        "places.id,places.formattedAddress,places.location,"
        "places.postalAddress,places.addressComponents,"
        "places.name,places.shortFormattedAddress,places.viewport"
    )
    print(f"Field mask: {field_mask}")
    print()

    # Search for restaurants near downtown Austin, Texas
    location_name = "Downtown Austin, Texas"
    latitude = 30.2672
    longitude = -97.7431
    radius_meters = 2000  # 2km radius - plenty of restaurants in Austin

    print(f"Searching for restaurants near: {location_name}")
    print(f"Location: {latitude}, {longitude}")
    print(f"Radius: {radius_meters}m")
    print()

    url = f"{BASE_URL}:searchNearby"
    payload = {
        "includedTypes": ["restaurant"],
        "maxResultCount": 5,  # Get more results for better examples
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
                "radius": radius_meters,
            },
        },
    }

    result = make_request("POST", url, field_mask, payload)

    if result and "places" in result and not result.get("error"):
        places = result.get("places", [])
        print(f"✅ Success! Found {len(places)} restaurant(s) nearby:")
        for idx, place in enumerate(places, 1):
            print(f"\n   {idx}. Place ID: {place.get('id', 'N/A')}")
            if "name" in place:
                print(f"      Name: {place.get('name')}")
            if "formattedAddress" in place:
                print(f"      Formatted Address: {place.get('formattedAddress')}")
            if "shortFormattedAddress" in place:
                print(f"      Short Address: {place.get('shortFormattedAddress')}")
            if "addressComponents" in place or "postalAddress" in place:
                parsed_addr = parse_address_components(place)
                addr_lines = format_address_display(parsed_addr).split("\n")
                for line in addr_lines:
                    if line.strip():
                        print(f"      {line}")
            if "location" in place:
                loc = place.get("location", {})
                print(f"      Location: {loc.get('latitude')}, {loc.get('longitude')}")
        print()
        print("Full response:")
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(result, indent=2))
    print()


def main() -> None:
    """Run all tests."""
    print("🧪 Testing Google Places API (New) - Essentials Tier Fields Only")
    print("=" * 66)
    print()
    # Show partial API key for verification (first 10 and last 4 chars)
    # API_KEY is guaranteed to be non-None due to sys.exit(1) check above
    api_key = API_KEY
    assert api_key is not None, "API_KEY should be set"
    if len(api_key) > 14:
        masked_key = f"{api_key[:10]}...{api_key[-4:]}"
    else:
        masked_key = f"{api_key[:4]}...{len(api_key)} chars"
    print(f"API Key loaded from .env: {masked_key}")

    # Check for referrer configuration
    referrer = os.getenv("GOOGLE_API_REFERRER_DOMAIN", "localhost:5000")
    print(f"Referrer header: https://{referrer}")
    print()
    print("ℹ️  Note: If you get 403 errors about referrer restrictions:")
    print("   - For server-side requests, use IP address restrictions instead")
    print("   - Or add your server's domain to allowed referrers")
    print("   - Or remove referrer restrictions from API key")
    print()

    test_place_details()
    test_text_search()
    test_nearby_search()

    print("✅ Tests complete!")
    print()
    print("All requests included these fields:")
    print("  - id")
    print("  - name")
    print("  - formattedAddress, shortFormattedAddress")
    print("  - postalAddress")
    print("  - location")
    print("  - viewport")
    print("  - addressComponents (Place Details only)")
    print()
    print("⚠️  Note: Some fields may not be Essentials tier - verify pricing tiers")
    print("   in Google Cloud Console billing reports.")


if __name__ == "__main__":
    main()
