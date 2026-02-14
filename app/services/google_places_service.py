"""Simplified Google Places API service for consistent API usage across the application.

This module provides a streamlined service for interacting with the Google Places API,
focusing on essential functionality while maintaining all current features.

Following TIGER principles:
- Testing: Pure functions with clear interfaces
- Interfaces: Simple parameter validation and consistent returns
- Generality: Reusable service patterns
- Examples: Clear usage documentation
- Refactoring: Single responsibility per method
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple, cast

from flask import current_app
import requests

from app.utils.address_utils import normalize_country_to_iso2, normalize_state_to_usps

logger = logging.getLogger(__name__)

# Google Places API configuration
PLACES_API_BASE = "https://places.googleapis.com/v1/places"

# Field masks with tier documentation for cost tracking
# For searchText endpoint, use "places.fieldName" format
# For individual place details, use "fieldName" format
# Based on: https://developers.google.com/maps/documentation/places/web-service/data-fields
#
# FIELD TIERS (for cost tracking):
# ESSENTIALS: id, formattedAddress, location, addressComponents (Place Details only), types (Place Details only), viewport (Place Details only)
# PRO: displayName, primaryType, businessStatus, types (for Search), addressComponents (for Search), viewport (for Search), websiteUri, userRatingCount
# ENTERPRISE: rating, nationalPhoneNumber
# NOTE: Some fields have different tiers depending on endpoint (Place Details vs Search)
FIELD_MASKS = {
    # Basic mask - Essentials only (id, formattedAddress, location)
    # TIER: All Essentials
    "basic": "id,formattedAddress,location",
    # Search mask - includes Pro tier fields needed for restaurant matching
    # TIER: ESSENTIALS + PRO (places.id, formattedAddress, location, displayName, primaryType, types)
    "search": "places.id,places.formattedAddress,places.location,places.displayName,places.primaryType,places.businessStatus,places.types",
    # Place Details: address, name, cuisine, phone, website. One request per selection (no extra calls).
    # websiteUri = Pro (same tier as displayName). nationalPhoneNumber = Enterprise (request bills at Enterprise).
    "place_details": (
        "id,formattedAddress,location,addressComponents,postalAddress,addressDescriptor,"
        "displayName,primaryType,types,websiteUri,nationalPhoneNumber"
    ),
    # Legacy comprehensive - kept for CLI/validation if needed
    "comprehensive": (
        "id,formattedAddress,location,addressComponents,displayName,primaryType,businessStatus,"
        "types,rating,nationalPhoneNumber,websiteUri,userRatingCount,viewport"
    ),
    # Same as place_details so CLI validate gets phone, website, and address lines
    "cli_validation": (
        "id,formattedAddress,location,addressComponents,postalAddress,addressDescriptor,"
        "displayName,primaryType,types,websiteUri,nationalPhoneNumber"
    ),
}

# Unit/suite suffix patterns for splitting combined address lines (postalAddress fallback)
_ADDRESS_LINE2_SUFFIX_RE = re.compile(r"\s+((?:#|Suite|Unit|Apt\.?|Ste\.?|Bldg\.?|RM\.?)\s*\S+)\s*$")


def _has_address_street_or_locality(components: list[dict[str, Any]]) -> bool:
    """Return True if addressComponents has street or locality data for parsing."""
    street_or_locality = {"street_number", "route", "locality"}
    for comp in components:
        types_list = comp.get("types", [])
        if street_or_locality & set(types_list):
            return True
    return False


# Food business types for restaurant searches
FOOD_TYPES = [
    "restaurant",
    "meal_takeaway",
    "meal_delivery",
    "bakery",
    "bar",
    "cafe",
    "fast_food_restaurant",
    "ice_cream_shop",
    "sandwich_shop",
]


class GooglePlacesService:
    """Simplified service for Google Places API interactions."""

    def __init__(self, api_key: str | None = None):
        """Initialize the service with API key."""
        self.api_key = api_key or self._get_api_key()
        if not self.api_key:
            logger.warning("Google Maps API key not configured - Google Places features will not work")

        # Simple in-memory cache
        self._cache: dict[str, Any] = {}

    def _get_api_key(self) -> str | None:
        """Get API key from Flask configuration or environment variable."""
        try:
            api_key = current_app.config.get("GOOGLE_MAPS_API_KEY")
            if api_key:
                return str(api_key) if api_key else None
        except RuntimeError:
            pass
        env_key = os.getenv("GOOGLE_MAPS_API_KEY")
        return str(env_key) if env_key else None

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        api_key_str = str(self.api_key) if self.api_key else ""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key_str,
            "User-Agent": "Meal-Expense-Tracker/1.0",
        }

        # Set referrer based on API key restrictions
        # Check for explicit referrer configuration first
        referrer: str | None = os.getenv("GOOGLE_API_REFERRER_DOMAIN")

        if not referrer:
            # Try to get from Flask config
            try:
                referrer = current_app.config.get("GOOGLE_API_REFERRER_DOMAIN")
            except RuntimeError:
                pass

        if not referrer:
            # Default to a common development domain that API keys often allow
            # This can be overridden with GOOGLE_API_REFERRER_DOMAIN environment variable
            referrer = "localhost:5000"

        if referrer:
            headers["Referer"] = f"https://{referrer}"

        return headers

    def _make_request(
        self, url: str, payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Make API request with error handling."""
        if not self.api_key or self.api_key == "dummy_key_for_testing":
            logger.warning("Google Places API key not configured or using dummy key")
            return {}

        if headers is None:
            headers = self._get_headers()

        try:
            if payload:
                logger.debug(f"Making POST request to {url} with payload: {payload}")
                response = requests.post(url, headers=headers, json=payload, timeout=10)
            else:
                logger.debug(f"Making GET request to {url}")
                response = requests.get(url, headers=headers, timeout=10)

            logger.debug(f"Response status: {response.status_code}")

            # Handle specific error cases
            if response.status_code == 403:
                error_data = response.json() if response.content else {}
                if "referer" in str(error_data).lower() and "blocked" in str(error_data).lower():
                    logger.warning(
                        "Google Places API key has referrer restrictions. "
                        "Please update your API key in Google Cloud Console to allow requests from your domain."
                    )
                    logger.warning(
                        "For development: Add 'localhost:5000' to allowed referrers, or remove referrer restrictions."
                    )
                    return {"error": "API_KEY_REFERRER_RESTRICTED"}
                else:
                    logger.error(f"API access forbidden: {response.text}")

            if response.status_code != 200:
                logger.error(f"API request failed: {response.status_code} - {response.text}")

            response.raise_for_status()
            result = response.json()
            return cast(dict[str, Any], result)
        except requests.exceptions.RequestException as e:
            logger.error(f"Google Places API error: {e}")
            if hasattr(e, "response") and e.response:
                logger.error(f"Response content: {e.response.text}")
            return {}

    def search_places_by_text(
        self,
        query: str,
        location_bias: tuple[float, float] | None = None,
        radius_meters: int = 50000,
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        """Search for places using text query."""
        if not query or not isinstance(query, str):
            return []

        # Check cache
        cache_key = f"text_search:{query}:{location_bias}:{radius_meters}"
        if cache_key in self._cache:
            return cast(list[dict[str, Any]], self._cache[cache_key])

        url = f"{PLACES_API_BASE}:searchText"
        headers = self._get_headers()
        headers["X-Goog-FieldMask"] = FIELD_MASKS["search"]

        payload = {
            "textQuery": query,
            "maxResultCount": min(max_results, 20),
        }

        if location_bias:
            lat, lng = location_bias
            payload["locationBias"] = {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": min(radius_meters, 50000),
                }
            }

        result = self._make_request(url, payload, headers)

        # Handle API key referrer restrictions gracefully
        if result.get("error") == "API_KEY_REFERRER_RESTRICTED":
            logger.info("Google Places API search skipped due to referrer restrictions")
            return []

        places = cast(list[dict[str, Any]], result.get("places", []))
        logger.info(f"Google Places API returned {len(places)} places")

        # Cache result
        self._cache[cache_key] = places
        return places

    def search_places_nearby(
        self,
        location: tuple[float, float],
        radius_meters: int = 5000,
        included_type: str = "restaurant",
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        """Search for places nearby a location."""
        cache_key = f"nearby:{location}:{radius_meters}:{included_type}"
        if cache_key in self._cache:
            return cast(list[dict[str, Any]], self._cache[cache_key])

        url = f"{PLACES_API_BASE}:searchNearby"
        headers = self._get_headers()
        headers["X-Goog-FieldMask"] = FIELD_MASKS["search"]

        lat, lng = location
        payload = {
            "includedTypes": [included_type],
            "maxResultCount": min(max_results, 20),
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": min(radius_meters, 50000),
                }
            },
        }

        result = self._make_request(url, payload, headers)

        # Handle API key referrer restrictions gracefully
        if result.get("error") == "API_KEY_REFERRER_RESTRICTED":
            logger.info("Google Places API nearby search skipped due to referrer restrictions")
            return []

        places = cast(list[dict[str, Any]], result.get("places", []))

        self._cache[cache_key] = places
        return places

    def get_place_details(self, place_id: str, field_mask: str | None = None) -> dict[str, Any] | None:
        """Get detailed information about a place.

        Args:
            place_id: Google Place ID
            field_mask: Optional field mask string. If not provided, uses "place_details" mask.
                       Use "cli_validation" for CLI operations to minimize costs.

        Returns:
            Place data dictionary or None if not found
        """
        if not place_id:
            return None

        mask = field_mask or FIELD_MASKS["place_details"]

        # Use field mask in cache key to avoid cache collisions
        cache_key = f"details:{place_id}:{mask}"
        if cache_key in self._cache:
            logger.debug(f"Cache hit for place details: {place_id}")
            return cast(dict[str, Any] | None, self._cache[cache_key])

        url = f"{PLACES_API_BASE}/{place_id}"
        headers = self._get_headers()
        headers["X-Goog-FieldMask"] = mask

        result = self._make_request(url, headers=headers)

        if result:
            self._cache[cache_key] = result

        return result

    def extract_restaurant_data(self, place_data: dict[str, Any]) -> dict[str, Any]:
        """Extract and format restaurant data from Google Places response.

        Extracts all fields with tier annotations for cost tracking.
        """
        if not place_data:
            return {}

        # ESSENTIALS TIER: Extract basic information
        address = place_data.get("formattedAddress", "")

        # PRO TIER: Extract displayName for restaurant names
        name = place_data.get("displayName", {}).get("text", "") if place_data.get("displayName") else ""

        # ESSENTIALS TIER: Extract location
        location = place_data.get("location", {})
        latitude = location.get("latitude")
        longitude = location.get("longitude")

        # Address: prefer addressComponents for proper line 1/2 split (street vs unit/suite)
        # postalAddress often combines them in addressLines[0], e.g. "499 S State Hwy #200"
        address_components = place_data.get("addressComponents", [])
        postal_address = place_data.get("postalAddress")
        if address_components and _has_address_street_or_locality(address_components):
            parsed_address = self.parse_address_components(address_components)
        elif isinstance(postal_address, dict) and postal_address.get("addressLines"):
            parsed_address = self._parse_postal_address_with_line_split(postal_address)
        elif postal_address:
            parsed_address = self.parse_postal_address(postal_address)
        else:
            parsed_address = self.parse_formatted_address(address)

        located_within = self.extract_located_within(place_data)

        # ENTERPRISE TIER: Extract rating
        rating = place_data.get("rating")

        # ENTERPRISE TIER: Extract phone number
        phone = place_data.get("nationalPhoneNumber", "")

        # PRO TIER: Extract types and primaryType for categorization
        # Preserve Google's order; ensure primary_type is first (it is always in types when present)
        types: list[str] = list(place_data.get("types", []))
        primary_type = place_data.get("primaryType", "")
        if primary_type and types:
            types = [primary_type] + [t for t in types if t != primary_type]

        # PRO TIER: Extract business status
        business_status = place_data.get("businessStatus", "")

        # PRO TIER: Extract website (strip UTM/attribution params for canonical URL)
        from app.utils.url_utils import strip_url_query_params

        website = place_data.get("websiteUri", "")
        if website:
            website = strip_url_query_params(website) or website

        # PRO TIER: Extract user rating count
        user_rating_count = place_data.get("userRatingCount")

        # PRO TIER: Extract price level (may be deprecated in new API)
        price_level = place_data.get("priceLevel")

        # Detect cuisine from name and types
        cuisine_type = self._detect_cuisine(name, types) if name else "Unknown"

        return {
            "name": name,
            "formatted_address": address,
            "address_line_1": parsed_address.get("address_line_1", ""),
            "address_line_2": parsed_address.get("address_line_2", ""),
            "city": parsed_address.get("city", ""),
            "state": parsed_address.get("state", ""),
            "state_long": parsed_address.get("state_long", ""),
            "state_short": parsed_address.get("state_short", ""),
            "postal_code": parsed_address.get("postal_code", ""),
            "country": normalize_country_to_iso2(parsed_address.get("country", "")),
            "located_within": located_within,
            "latitude": latitude,
            "longitude": longitude,
            "rating": rating,
            "phone_number": phone,
            "website": website,
            "cuisine_type": cuisine_type,
            "primary_type": primary_type,
            "types": types,
            "business_status": business_status,
            "user_rating_count": user_rating_count,
            "price_level": price_level,
            "google_place_id": place_data.get("id") or place_data.get("place_id") or "",
        }

    def _convert_price_level(self, price_level: Any) -> int | None:
        """Convert Google's price level to integer."""
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

    def _detect_cuisine(self, name: str, types: list[str]) -> str:
        """Detect cuisine type from name and Google types."""
        name_lower = name.lower()

        # Common cuisine patterns in names (return capitalized names to match form validation)
        cuisine_patterns = {
            "Italian": ["pizza", "pasta", "italian"],
            "Chinese": ["chinese", "china", "wok"],
            "Mexican": ["mexican", "taco", "burrito", "cantina"],
            "Japanese": ["sushi", "japanese", "ramen", "hibachi"],
            "Indian": ["indian", "curry", "tandoor"],
            "Thai": ["thai", "pad thai"],
            "French": ["french", "bistro", "brasserie"],
            "Greek": ["greek", "gyro", "souvlaki", "mediterranean"],
            "Lebanese": ["lebanese", "lebanon", "shawarma", "hummus"],
            "American": ["burger", "grill", "bbq", "steakhouse"],
        }

        for cuisine, patterns in cuisine_patterns.items():
            if any(pattern in name_lower for pattern in patterns):
                return cuisine

        # Check Google types (return capitalized names to match form validation)
        type_cuisine_map = {
            "italian_restaurant": "Italian",
            "chinese_restaurant": "Chinese",
            "mexican_restaurant": "Mexican",
            "japanese_restaurant": "Japanese",
            "indian_restaurant": "Indian",
            "thai_restaurant": "Thai",
            "french_restaurant": "French",
            "greek_restaurant": "Greek",
            "lebanese_restaurant": "Lebanese",
            "mediterranean_restaurant": "Greek",
            "middle_eastern_restaurant": "Lebanese",
            "american_restaurant": "American",
            "pizza_restaurant": "Italian",
            "sushi_restaurant": "Japanese",
        }

        for place_type in types:
            if place_type in type_cuisine_map:
                return type_cuisine_map[place_type]

        return "American"  # Default (capitalized to match form validation)

    def search_places_with_fallback(
        self,
        query: str,
        location: tuple[float, float] | None = None,
        radius_miles: float = 31.0,
        cuisine: str = "",
        max_results: int = 20,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Search with fallback to different methods."""
        # Convert miles to meters
        radius_meters = int(radius_miles * 1609.34)

        # Try text search first
        places = self.search_places_by_text(query, location, radius_meters, max_results)

        # If no results and we have location, try nearby search
        if not places and location:
            places = self.search_places_nearby(location, radius_meters, "restaurant", max_results)

        return places

    def build_photo_urls(
        self, photos: list[dict[str, Any]], api_key: str | None = None, max_width: int = 400
    ) -> list[dict[str, str]]:
        """Build photo URLs from Google Places photo references."""
        # Simplified - photos require separate API calls which are expensive
        # Return empty list to maintain compatibility
        return []

    def build_reviews_summary(self, reviews: list[dict[str, Any]], max_reviews: int = 3) -> list[dict[str, Any]]:
        """Build reviews summary from Google Places reviews."""
        # Simplified - reviews are Pro+ tier feature
        # Return empty list to maintain compatibility
        return []

    def filter_places_by_criteria(
        self, places: list[dict[str, Any]], min_rating: float | None = None, max_price_level: int | None = None
    ) -> list[dict[str, Any]]:
        """Filter places by rating and price level criteria.

        ENTERPRISE TIER: Uses rating field
        PRO TIER: Uses priceLevel field (may be deprecated in new API)
        """
        if not places:
            return []

        filtered = []
        for place in places:
            # ENTERPRISE TIER: Check rating
            if min_rating is not None:
                rating = place.get("rating")
                if rating is None or rating < min_rating:
                    continue

            # PRO TIER: Check price level (may be deprecated)
            if max_price_level is not None:
                price_level = place.get("priceLevel")
                if price_level is not None and price_level > max_price_level:
                    continue

            filtered.append(place)

        return filtered

    def process_search_result_place(self, place: dict[str, Any]) -> dict[str, Any] | None:
        """Process a single place from search results."""
        if not place:
            return None

        return self.extract_restaurant_data(place)

    def convert_price_level_to_int(self, price_level: Any) -> int | None:
        """Convert Google's price level to integer."""
        return self._convert_price_level(price_level)

    def detect_chain_restaurant(self, name: str, place_data: dict[str, Any] | None = None) -> bool:
        """Detect if restaurant is likely a chain."""
        if not name:
            return False

        name_lower = name.lower()

        # Common chain indicators
        chain_patterns = [
            "mcdonald",
            "burger king",
            "subway",
            "starbucks",
            "kfc",
            "pizza hut",
            "domino",
            "taco bell",
            "wendy",
            "chipotle",
            "panera",
            "olive garden",
            "applebee",
            "chili",
            "outback",
            "red lobster",
            "ihop",
            "denny",
        ]

        return any(pattern in name_lower for pattern in chain_patterns)

    def parse_address_components(self, address_components: list[dict[str, Any]]) -> dict[str, str]:
        """Parse Google Places address components (Places API New: longText/shortText)."""
        raw_components: dict[str, Any] = {
            "street_number": "",
            "route": "",
            "locality": "",
            "postal_code": "",
            "country": "",
        }
        state_long_name = ""
        state_short_name = ""
        # Line 2: premise, subpremise, sublocality, floor (e.g. suite, building, airport terminal)
        line_2_parts: list[str] = []

        for component in address_components:
            types = component.get("types", [])
            # Places API New uses longText/shortText
            long_text = component.get("longText") or component.get("longName")
            short_text = component.get("shortText") or component.get("shortName")
            long_name_str = str(long_text).strip() if long_text else ""
            short_name_str = str(short_text).strip() if short_text else ""

            for component_type in types:
                if component_type == "administrative_area_level_1":
                    state_long_name = long_name_str
                    state_short_name = short_name_str
                    break
                if component_type in raw_components:
                    raw_components[component_type] = long_name_str
                    break
                if component_type in (
                    "premise",
                    "subpremise",
                    "sublocality",
                    "sublocality_level_1",
                    "floor",
                ):
                    if long_name_str and long_name_str not in line_2_parts:
                        line_2_parts.append(long_name_str)
                    break

        street_number = raw_components.get("street_number", "")
        route = raw_components.get("route", "")
        if street_number and route:
            address_line_1 = f"{street_number} {route}"
        elif route:
            address_line_1 = route
        elif street_number:
            address_line_1 = street_number
        else:
            address_line_1 = ""

        address_line_2 = ", ".join(line_2_parts).strip()

        return {
            "address_line_1": address_line_1.strip(),
            "address_line_2": address_line_2,
            "city": raw_components.get("locality", ""),
            "state": state_short_name or state_long_name,
            "state_long": state_long_name,
            "state_short": state_short_name,
            "postal_code": raw_components.get("postal_code", ""),
            "country": raw_components.get("country", ""),
        }

    def parse_postal_address(self, postal_address: dict[str, Any] | None) -> dict[str, str]:
        """Parse postalAddress (Essentials tier) into same structure as parse_address_components."""
        result = self._get_empty_address_result()
        if not postal_address or not isinstance(postal_address, dict):
            return result

        address_lines = postal_address.get("addressLines", [])
        if isinstance(address_lines, list) and len(address_lines) > 0:
            result["address_line_1"] = str(address_lines[0]).strip() if address_lines[0] else ""
        if isinstance(address_lines, list) and len(address_lines) > 1 and address_lines[1]:
            result["address_line_2"] = str(address_lines[1]).strip()

        locality = postal_address.get("locality")
        if locality:
            result["city"] = str(locality).strip()
        administrative_area = postal_address.get("administrativeArea")
        if administrative_area:
            raw_state = str(administrative_area).strip()
            state_abbr = normalize_state_to_usps(raw_state)
            result["state"] = state_abbr
            result["state_long"] = raw_state
            result["state_short"] = state_abbr
        postal_code = postal_address.get("postalCode")
        if postal_code:
            result["postal_code"] = str(postal_code).strip()
        region_code = postal_address.get("regionCode")
        if region_code:
            result["country"] = str(region_code).strip()

        return result

    def _parse_postal_address_with_line_split(self, postal_address: dict[str, Any]) -> dict[str, str]:
        """Parse postalAddress, splitting combined line 1+2 when unit/suite is at end (e.g. '499 S State Hwy #200')."""
        result = self.parse_postal_address(postal_address)
        line1 = result.get("address_line_1", "")
        line2 = result.get("address_line_2", "")
        if line1 and not line2:
            match = _ADDRESS_LINE2_SUFFIX_RE.search(line1)
            if match:
                unit_part = match.group(1).strip()
                street_part = line1[: match.start()].strip()
                if street_part:
                    result["address_line_1"] = street_part
                    result["address_line_2"] = unit_part
        return result

    def extract_located_within(self, place_data: dict[str, Any]) -> str:
        """Extract located_within from addressDescriptor or addressComponents (Essentials)."""
        if not place_data:
            return ""

        # addressDescriptor: landmarks/areas (e.g. "inside Mall of America")
        address_descriptor = place_data.get("addressDescriptor")
        if isinstance(address_descriptor, dict) and address_descriptor:
            text = address_descriptor.get("text") or address_descriptor.get("description")
            if text and isinstance(text, str):
                return str(text.strip())
        if isinstance(address_descriptor, str) and address_descriptor.strip():
            return str(address_descriptor.strip())

        # Fallback: sublocality or premise from addressComponents
        components = place_data.get("addressComponents", [])
        if not components:
            return ""

        parts: list[str] = []
        for component in components:
            types = component.get("types", [])
            if not any(t in types for t in ("sublocality", "sublocality_level_1", "premise")):
                continue
            long_text = component.get("longText") or component.get("longName")
            if long_text and str(long_text).strip():
                parts.append(str(long_text).strip())
        return ", ".join(parts) if parts else ""

    def parse_formatted_address(self, formatted_address: str) -> dict[str, str]:
        """Parse a formatted address string into structured components.

        This is a fallback method when detailed addressComponents are not available.
        """
        if not formatted_address or not isinstance(formatted_address, str):
            return self._get_empty_address_result()

        # Clean up the address
        address = formatted_address.strip()
        parts = [part.strip() for part in address.split(",") if part.strip()]

        result = self._get_empty_address_result()

        if len(parts) >= 4:
            self._parse_four_part_address(parts, result)
        elif len(parts) == 3:
            self._parse_three_part_address(parts, result)
        elif len(parts) == 2:
            self._parse_two_part_address(parts, result)
        elif len(parts) == 1:
            self._parse_one_part_address(parts, result)

        return result

    def _get_empty_address_result(self) -> dict[str, str]:
        """Get an empty address result dictionary."""
        return {
            "address_line_1": "",
            "address_line_2": "",
            "city": "",
            "state": "",
            "state_long": "",
            "state_short": "",
            "postal_code": "",
            "country": "",
        }

    def _parse_four_part_address(self, parts: list[str], result: dict[str, str]) -> None:
        """Parse address with 4+ parts: Street, City, State ZIP, Country."""
        result["country"] = parts[-1]
        result["city"] = parts[-3]

        # Parse state and ZIP from the second-to-last part
        state_zip_part = parts[-2]
        self._extract_state_and_zip(state_zip_part, result)

        # Everything before city is the street address
        street_parts = parts[:-3]
        result["address_line_1"] = ", ".join(street_parts)

    def _parse_three_part_address(self, parts: list[str], result: dict[str, str]) -> None:
        """Parse address with 3 parts: Street, City, State ZIP."""
        result["address_line_1"] = parts[0]
        result["city"] = parts[1]

        # Parse state and ZIP from the last part
        state_zip_part = parts[2]
        self._extract_state_and_zip(state_zip_part, result)

    def _parse_two_part_address(self, parts: list[str], result: dict[str, str]) -> None:
        """Parse address with 2 parts: Street, City State ZIP."""
        result["address_line_1"] = parts[0]
        location_part = parts[1]

        if "," in location_part:
            self._parse_city_comma_state_zip(location_part, result)
        else:
            self._parse_city_state_zip(location_part, result)

    def _parse_one_part_address(self, parts: list[str], result: dict[str, str]) -> None:
        """Parse address with 1 part: Street only."""
        result["address_line_1"] = parts[0]

    def _parse_city_comma_state_zip(self, location_part: str, result: dict[str, str]) -> None:
        """Parse 'City, State ZIP' format."""
        city_state_parts = [p.strip() for p in location_part.split(",")]
        if len(city_state_parts) >= 1:
            result["city"] = city_state_parts[0]
        if len(city_state_parts) >= 2:
            self._extract_state_and_zip(city_state_parts[1], result)

    def _parse_city_state_zip(self, location_part: str, result: dict[str, str]) -> None:
        """Parse 'City State ZIP' format (no comma)."""
        # Look for ZIP code first
        zip_match = re.search(r"\b(\d{5}(-\d{4})?|\w\d\w\s*\d\w\d)\b", location_part)
        if zip_match:
            result["postal_code"] = zip_match.group(1)
            location_part = location_part.replace(zip_match.group(0), "").strip()

        # Look for state abbreviation
        state_match = re.search(r"\b([A-Z]{2}|\w+)\b", location_part)
        if state_match:
            result["state"] = state_match.group(1)
            # Remove state to get city
            location_part = location_part.replace(state_match.group(0), "").strip()
            result["city"] = location_part
        else:
            # No clear state, treat as city
            result["city"] = location_part

    def _extract_state_and_zip(self, state_zip_part: str, result: dict[str, str]) -> None:
        """Extract state and ZIP code from a combined string."""
        zip_match = re.search(r"\b(\d{5}(-\d{4})?|\w\d\w\s*\d\w\d)\b", state_zip_part)
        if zip_match:
            result["postal_code"] = zip_match.group(1)
            # Remove ZIP to get state
            state_part = state_zip_part.replace(zip_match.group(0), "").strip()
            if state_part:
                result["state"] = state_part

    def analyze_restaurant_types(self, place_data: dict[str, Any]) -> dict[str, Any]:
        """Analyze restaurant types and return cuisine and service level.

        Uses PRO TIER fields: displayName, types, primaryType
        """
        # PRO TIER: Extract displayName for name-based cuisine detection
        name = (
            place_data.get("displayName", {}).get("text", "")
            if isinstance(place_data.get("displayName"), dict)
            else place_data.get("displayName", "")
        )

        # PRO TIER: Extract types for cuisine and service level detection
        types = place_data.get("types", [])

        cuisine = self._detect_cuisine(name, types)

        # PRO TIER: Use service level detection with primaryType and types
        service_level, confidence = self.detect_service_level_from_data(place_data)

        return {
            "cuisine_type": cuisine,
            "service_level": service_level,
            "confidence": confidence,
        }

    def generate_notes(self, place: dict[str, Any]) -> str | None:
        """Generate notes from Google Places data."""
        if not place:
            return None

        notes = []

        # Add business status if available
        business_status = place.get("businessStatus")
        if business_status and business_status != "OPERATIONAL":
            notes.append(f"Status: {business_status}")

        # Add service options
        service_options = []
        if place.get("takeout"):
            service_options.append("Takeout")
        if place.get("delivery"):
            service_options.append("Delivery")
        if place.get("dineIn"):
            service_options.append("Dine-in")

        if service_options:
            notes.append(f"Services: {', '.join(service_options)}")

        return " • ".join(notes) if notes else None

    def generate_description(self, place: dict[str, Any]) -> str:
        """Generate a description for a restaurant."""
        if not place:
            return ""

        parts = []

        # Add cuisine type
        cuisine = place.get("cuisine_type", "")
        if cuisine and cuisine != "american":
            parts.append(f"{cuisine.title()} restaurant")
        else:
            parts.append("Restaurant")

        # ENTERPRISE TIER: Add rating if available
        rating = place.get("rating")
        if rating:
            parts.append(f"rated {rating:.1f} stars")

        # PRO TIER: Price level removed from description (may be deprecated in new API)

        return " • ".join(parts) if parts else "Restaurant"

    def detect_service_level_from_data(self, place_data: dict[str, Any]) -> tuple[str, float]:
        """Detect service level from Google Places data.

        Uses PRO TIER fields: primaryType and types for classification.
        Uses ENTERPRISE TIER field: rating (if available) for confidence scoring.

        Args:
            place_data: Place data from Google Places API

        Returns:
            Tuple of (service_level, confidence_score)
        """
        from app.utils.service_level_detector import ServiceLevel, detect_service_level_from_google_places

        # PRO TIER: Use types and primaryType for classification
        if not place_data:
            return "unknown", 0.0

        # Use the service level detector utility which handles types and primaryType
        service_level = detect_service_level_from_google_places(place_data)
        service_level_str = service_level.value if isinstance(service_level, ServiceLevel) else str(service_level)

        # Calculate confidence based on available data
        # PRO TIER: primaryType and types increase confidence
        confidence = 0.5  # Base confidence

        primary_type = place_data.get("primaryType")
        types = place_data.get("types", [])

        if primary_type:
            confidence += 0.2
        if types:
            confidence += 0.2

        # ENTERPRISE TIER: rating available for additional confidence
        rating = place_data.get("rating")
        if rating is not None:
            confidence += 0.1

        # Cap confidence at 1.0
        confidence = min(confidence, 1.0)

        return service_level_str, confidence

    def format_primary_type_for_display(self, primary_type: str) -> str | None:
        """Format primary type for display.

        Args:
            primary_type: Raw primary type from Google Places

        Returns:
            Formatted display string or None if input is empty
        """
        if not primary_type:
            return None

        # Convert snake_case to Title Case
        formatted = primary_type.replace("_", " ").title()

        # Handle special cases
        replacements = {
            "Fast Food Restaurant": "Fast Food Restaurant",
            "Meal Takeaway": "Takeaway",
            "Meal Delivery": "Delivery",
        }

        return replacements.get(formatted, formatted)


def get_google_places_service() -> GooglePlacesService:
    """Get a GooglePlacesService instance."""
    return GooglePlacesService()
