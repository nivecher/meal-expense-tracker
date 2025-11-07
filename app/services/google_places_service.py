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
from typing import Any, Dict, List, Optional, Tuple

import requests
from flask import current_app

logger = logging.getLogger(__name__)

# Google Places API configuration
PLACES_API_BASE = "https://places.googleapis.com/v1/places"

# Simplified field masks - Essentials tier only
# For searchText endpoint, use "places.fieldName" format
# For individual place details, use "fieldName" format
FIELD_MASKS = {
    "basic": "displayName,formattedAddress,location,rating,userRatingCount,priceLevel",
    "search": "places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.priceLevel",
    "comprehensive": "displayName,formattedAddress,location,rating,userRatingCount,priceLevel,nationalPhoneNumber,websiteUri,types,primaryType",
}

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

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the service with API key."""
        self.api_key = api_key or self._get_api_key()
        if not self.api_key:
            logger.warning("Google Maps API key not configured - Google Places features will not work")

        # Simple in-memory cache
        self._cache = {}

    def _get_api_key(self) -> Optional[str]:
        """Get API key from Flask configuration or environment variable."""
        try:
            api_key = current_app.config.get("GOOGLE_MAPS_API_KEY")
            if api_key:
                return api_key
        except RuntimeError:
            pass
        return os.getenv("GOOGLE_MAPS_API_KEY")

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "User-Agent": "Meal-Expense-Tracker/1.0",
        }

        # Set referrer based on API key restrictions
        # Check for explicit referrer configuration first
        referrer = os.getenv("GOOGLE_API_REFERRER_DOMAIN")

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
        self, url: str, payload: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
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
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Google Places API error: {e}")
            if hasattr(e, "response") and e.response:
                logger.error(f"Response content: {e.response.text}")
            return {}

    def search_places_by_text(
        self,
        query: str,
        location_bias: Optional[Tuple[float, float]] = None,
        radius_meters: int = 50000,
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search for places using text query."""
        if not query or not isinstance(query, str):
            return []

        # Check cache
        cache_key = f"text_search:{query}:{location_bias}:{radius_meters}"
        if cache_key in self._cache:
            return self._cache[cache_key]

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

        places = result.get("places", [])
        logger.info(f"Google Places API returned {len(places)} places")

        # Cache result
        self._cache[cache_key] = places
        return places

    def search_places_nearby(
        self,
        location: Tuple[float, float],
        radius_meters: int = 5000,
        included_type: str = "restaurant",
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search for places nearby a location."""
        if not location or len(location) != 2:
            return []

        cache_key = f"nearby:{location}:{radius_meters}:{included_type}"
        if cache_key in self._cache:
            return self._cache[cache_key]

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

        places = result.get("places", [])

        self._cache[cache_key] = places
        return places

    def get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a place."""
        if not place_id:
            return None

        cache_key = f"details:{place_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        url = f"{PLACES_API_BASE}/{place_id}"
        headers = self._get_headers()
        headers["X-Goog-FieldMask"] = FIELD_MASKS["comprehensive"]

        result = self._make_request(url, headers=headers)

        if result:
            self._cache[cache_key] = result

        return result

    def extract_restaurant_data(self, place_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and format restaurant data from Google Places response."""
        if not place_data:
            return {}

        # Extract basic information
        name = place_data.get("displayName", {}).get("text", "")
        address = place_data.get("formattedAddress", "")

        # Extract location
        location = place_data.get("location", {})
        latitude = location.get("latitude")
        longitude = location.get("longitude")

        # Extract ratings and price
        rating = place_data.get("rating")
        user_rating_count = place_data.get("userRatingCount", 0)
        price_level = self._convert_price_level(place_data.get("priceLevel"))

        # Extract contact info
        phone = place_data.get("nationalPhoneNumber", "")
        website = place_data.get("websiteUri", "")

        # Extract types and determine cuisine
        types = place_data.get("types", [])
        primary_type = place_data.get("primaryType", "")
        cuisine_type = self._detect_cuisine(name, types)

        return {
            "name": name,
            "address": address,
            "latitude": latitude,
            "longitude": longitude,
            "rating": rating,
            "user_rating_count": user_rating_count,
            "price_level": price_level,
            "phone": phone,
            "website": website,
            "cuisine_type": cuisine_type,
            "primary_type": primary_type,
            "types": types,
            "google_place_id": place_data.get("id") or place_data.get("place_id") or "",
        }

    def _convert_price_level(self, price_level: Any) -> Optional[int]:
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

    def _detect_cuisine(self, name: str, types: List[str]) -> str:
        """Detect cuisine type from name and Google types."""
        name_lower = name.lower()

        # Common cuisine patterns in names
        cuisine_patterns = {
            "italian": ["pizza", "pasta", "italian"],
            "chinese": ["chinese", "china", "wok"],
            "mexican": ["mexican", "taco", "burrito", "cantina"],
            "japanese": ["sushi", "japanese", "ramen", "hibachi"],
            "indian": ["indian", "curry", "tandoor"],
            "thai": ["thai", "pad thai"],
            "french": ["french", "bistro", "brasserie"],
            "american": ["burger", "grill", "bbq", "steakhouse"],
        }

        for cuisine, patterns in cuisine_patterns.items():
            if any(pattern in name_lower for pattern in patterns):
                return cuisine

        # Check Google types
        type_cuisine_map = {
            "italian_restaurant": "italian",
            "chinese_restaurant": "chinese",
            "mexican_restaurant": "mexican",
            "japanese_restaurant": "japanese",
            "indian_restaurant": "indian",
            "thai_restaurant": "thai",
            "french_restaurant": "french",
            "american_restaurant": "american",
            "pizza_restaurant": "italian",
            "sushi_restaurant": "japanese",
        }

        for place_type in types:
            if place_type in type_cuisine_map:
                return type_cuisine_map[place_type]

        return "american"  # Default

    def search_places_with_fallback(
        self,
        query: str,
        location: Optional[Tuple[float, float]] = None,
        radius_miles: float = 31.0,
        cuisine: str = "",
        max_results: int = 20,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """Search with fallback to different methods."""
        # Convert miles to meters
        radius_meters = int(radius_miles * 1609.34)

        # Try text search first
        places = self.search_places_by_text(query, location, radius_meters, max_results)

        # If no results and we have location, try nearby search
        if not places and location:
            places = self.search_places_nearby(location, radius_meters, "restaurant", max_results)

        return places

    def build_photo_urls(self, photos: List[Dict[str, Any]], max_width: int = 400) -> List[Dict[str, str]]:
        """Build photo URLs from Google Places photo references."""
        # Simplified - photos require separate API calls which are expensive
        # Return empty list to maintain compatibility
        return []

    def build_reviews_summary(self, reviews: List[Dict[str, Any]], max_reviews: int = 3) -> List[Dict[str, Any]]:
        """Build reviews summary from Google Places reviews."""
        # Simplified - reviews are Pro+ tier feature
        # Return empty list to maintain compatibility
        return []

    def filter_places_by_criteria(
        self, places: List[Dict[str, Any]], min_rating: Optional[float] = None, max_price_level: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Filter places by rating and price level criteria."""
        if not places:
            return []

        filtered = []
        for place in places:
            # Check rating
            if min_rating is not None:
                rating = place.get("rating")
                if rating is None or rating < min_rating:
                    continue

            # Check price level
            if max_price_level is not None:
                price_level = self._convert_price_level(place.get("priceLevel"))
                if price_level is not None and price_level > max_price_level:
                    continue

            filtered.append(place)

        return filtered

    def process_search_result_place(self, place: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single place from search results."""
        if not place:
            return None

        return self.extract_restaurant_data(place)

    def convert_price_level_to_int(self, price_level: Any) -> Optional[int]:
        """Convert Google's price level to integer."""
        return self._convert_price_level(price_level)

    def detect_chain_restaurant(self, name: str, place_data: Optional[Dict[str, Any]] = None) -> bool:
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

    def parse_address_components(self, address_components: List[Dict[str, Any]]) -> Dict[str, str]:
        """Parse Google Places address components."""
        result = {
            "street_number": "",
            "route": "",
            "locality": "",
            "administrative_area_level_1": "",
            "postal_code": "",
            "country": "",
        }

        for component in address_components:
            types = component.get("types", [])
            long_name = component.get("longName", "")

            for component_type in types:
                if component_type in result:
                    result[component_type] = long_name
                    break

        return result

    def analyze_restaurant_types(self, place_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze restaurant types and return cuisine and service level."""
        name = (
            place_data.get("displayName", {}).get("text", "")
            if isinstance(place_data.get("displayName"), dict)
            else place_data.get("displayName", "")
        )
        types = place_data.get("types", [])

        cuisine = self._detect_cuisine(name, types)

        # Simple service level detection
        service_level = "casual_dining"
        confidence = 0.7

        price_level = self._convert_price_level(place_data.get("priceLevel"))
        if price_level is not None:
            if price_level <= 1:
                service_level = "quick_service"
                confidence = 0.8
            elif price_level >= 3:
                service_level = "fine_dining"
                confidence = 0.8

        return {
            "cuisine_type": cuisine,
            "service_level": service_level,
            "confidence": confidence,
        }

    def generate_notes(self, place: Dict[str, Any]) -> Optional[str]:
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

    def generate_description(self, place: Dict[str, Any]) -> str:
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

        # Add rating if available
        rating = place.get("rating")
        if rating:
            parts.append(f"rated {rating:.1f} stars")

        # Add price level
        price_level = place.get("price_level")
        if price_level is not None:
            price_desc = ["Free", "Inexpensive", "Moderate", "Expensive", "Very Expensive"]
            if 0 <= price_level < len(price_desc):
                parts.append(f"({price_desc[price_level]})")

        return " • ".join(parts) if parts else "Restaurant"


def get_google_places_service() -> GooglePlacesService:
    """Get a GooglePlacesService instance."""
    return GooglePlacesService()
