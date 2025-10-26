"""Google Places API service for consistent API usage across the application.

This module provides a centralized service for interacting with the new Google Places API (2024+),
ensuring consistent field masks, error handling, and data extraction patterns.

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

from app.services.simple_cache import get_simple_cache

logger = logging.getLogger(__name__)

# Google Places New API configuration
NEW_PLACES_API_BASE = "https://places.googleapis.com/v1/places"

# Field masks for different data categories
FIELD_MASKS = {
    "basic": "displayName,formattedAddress,location,rating,userRatingCount,priceLevel",
    "address": "displayName,formattedAddress,addressComponents",
    "contact": "displayName,formattedAddress,nationalPhoneNumber,websiteUri,editorialSummary",
    "services": "displayName,paymentOptions,accessibilityOptions,parkingOptions,restroom,outdoorSeating",
    "food": "displayName,servesBreakfast,servesLunch,servesDinner,servesBeer,servesWine,servesBrunch,servesVegetarianFood",
    "comprehensive": "displayName,formattedAddress,nationalPhoneNumber,websiteUri,location,rating,userRatingCount,priceLevel,editorialSummary,paymentOptions,accessibilityOptions,parkingOptions,restroom,outdoorSeating,servesBreakfast,servesLunch,servesDinner,servesBeer,servesWine,servesBrunch,servesVegetarianFood,delivery,dineIn,takeout,reservable,businessStatus,primaryType,types,addressComponents,regularOpeningHours,currentOpeningHours,plusCode,photos,reviews,generativeSummary,liveMusic,menuForChildren,servesCocktails,servesDessert,servesCoffee,goodForChildren,allowsDogs,goodForGroups,goodForWatchingSports",
    "search": "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.priceLevel,places.primaryType,places.types,places.photos",
    "all": "*",  # Get all available fields
}

# Food business types for restaurant searches (Google Places API New supported types only)
FOOD_BUSINESS_TYPES = [
    "restaurant",
    "meal_takeaway",
    "meal_delivery",
    "bakery",
    "bar",
    "cafe",
    "fast_food_restaurant",
    "ice_cream_shop",
    "sandwich_shop",
    "seafood_restaurant",
    "steak_house",
    "sushi_restaurant",
]


class GooglePlacesService:
    """Service for interacting with the new Google Places API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the service with API key.

        Args:
            api_key: Google Maps API key. If None, will try to get from Flask config.
        """
        self.api_key = api_key or self._get_api_key()
        # Allow empty API key for testing/development - just log a warning
        if not self.api_key:
            logger.warning("Google Maps API key not configured - Google Places features will not work")

        # Initialize cache for API response caching
        self.cache = get_simple_cache()

    def _get_api_key(self) -> Optional[str]:
        """Get API key from Flask configuration or environment variable."""
        try:
            # Try Flask configuration first
            api_key = current_app.config.get("GOOGLE_MAPS_API_KEY")
            if api_key:
                return api_key
        except RuntimeError:
            # Outside Flask app context, fall back to environment variable
            pass

        # Fallback to environment variable
        return os.getenv("GOOGLE_MAPS_API_KEY")

    def _get_base_headers(self) -> Dict[str, str]:
        """Get base headers for Google Places API requests."""
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
        }

        # Always add referrer header if SERVER_NAME is configured (for API key restrictions)
        # Use environment variable if set, otherwise use Flask config
        referrer_domain = os.getenv("GOOGLE_API_REFERRER_DOMAIN")
        if not referrer_domain:
            try:
                referrer_domain = current_app.config.get("SERVER_NAME", "localhost:5000")
            except RuntimeError:
                # Outside Flask context, use default
                referrer_domain = "localhost:5000"

        if referrer_domain:
            headers["Referer"] = f"https://{referrer_domain}"

        return headers

    # Refactor _make_request to reduce complexity
    def _make_request(
        self, url: str, headers: Dict[str, str], payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        self._validate_request_params(url, headers, payload)  # Extracted validation
        if self.api_key == "dummy_key_for_testing":
            return {}
        try:
            if payload:
                response = requests.post(url, headers=headers, json=payload, timeout=10)
            else:
                response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error in request: {e}")
            raise

    def _validate_request_params(self, url, headers, payload):
        if not url or not isinstance(url, str):
            raise ValueError(f"Invalid URL: {url}")
        if not headers or not isinstance(headers, dict):
            raise ValueError(f"Invalid headers: {headers}")
        if payload is not None and not isinstance(payload, dict):
            raise ValueError(f"Invalid payload: {payload}")
        if not url.startswith("https://"):
            raise ValueError(f"URL must use HTTPS: {url}")

    def search_places_by_text(
        self,
        query: str,
        location_bias: Optional[Tuple[float, float]] = None,
        radius_meters: int = 50000,
        max_results: int = 20,
        included_type: str = "restaurant",
    ) -> List[Dict[str, Any]]:
        """Search for places using text query with type validation."""
        # Type validation
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"query must be a non-empty string, got: {type(query)} {repr(query)}")
        if location_bias is not None and (not isinstance(location_bias, tuple) or len(location_bias) != 2):
            raise ValueError(f"location_bias must be a tuple of (lat, lng), got: {type(location_bias)} {location_bias}")
        if not isinstance(radius_meters, int) or radius_meters <= 0:
            raise ValueError(f"radius_meters must be a positive integer, got: {type(radius_meters)} {radius_meters}")
        if not isinstance(max_results, int) or max_results <= 0:
            raise ValueError(f"max_results must be a positive integer, got: {type(max_results)} {max_results}")
        if not isinstance(included_type, str):
            raise ValueError(f"included_type must be a string, got: {type(included_type)} {included_type}")

        """Search for places using text query.

        Args:
            query: Search query text
            location_bias: Optional (latitude, longitude) for location bias
            radius_meters: Search radius in meters (max 50000)
            max_results: Maximum number of results to return
            included_type: Type of place to search for

        Returns:
            List of place data dictionaries
        """
        url = f"{NEW_PLACES_API_BASE}:searchText"

        headers = self._get_base_headers()
        headers["X-Goog-FieldMask"] = FIELD_MASKS["search"]

        payload = {
            "textQuery": query,
            "maxResultCount": min(max_results, 20),  # API limit
        }

        # Note: includedType is not supported for searchText API
        # Use searchNearby for type-specific searches

        # Add location restriction if provided (stronger than bias for better location-based results)
        if location_bias:
            lat, lng = location_bias
            # Use locationBias for searchText API (not locationRestriction)
            payload["locationBias"] = {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": min(radius_meters, 50000),  # API limit
                }
            }

        # Check cache for this search
        cached_result = self.cache.get_search_results(query, location_bias, radius_meters)

        if cached_result:
            logger.debug(f"Cache hit for search: {query}")
            return cached_result[:max_results]

        logger.debug(f"Searching places with query: {query}")
        logger.debug(f"Request URL: {url}")
        logger.debug(f"Request headers: {headers}")
        logger.debug(f"Request payload: {payload}")
        data = self._make_request(url, headers, payload)

        places = data.get("places", [])[:max_results]

        # Cache the result (without location bias for reuse)
        self.cache.cache_search_results(query, location_bias, radius_meters, places)

        return places

    def search_places_nearby(
        self,
        location: Tuple[float, float],
        radius_meters: int = 5000,
        included_types: Optional[List[str]] = None,
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search for places near a specific location with type validation."""
        # Type validation
        if not isinstance(location, tuple) or len(location) != 2:
            raise ValueError(f"location must be a tuple of (lat, lng), got: {type(location)} {location}")
        if not isinstance(radius_meters, int) or radius_meters <= 0:
            raise ValueError(f"radius_meters must be a positive integer, got: {type(radius_meters)} {radius_meters}")
        if included_types is not None and not isinstance(included_types, list):
            raise ValueError(f"included_types must be a list or None, got: {type(included_types)} {included_types}")
        if not isinstance(max_results, int) or max_results <= 0:
            raise ValueError(f"max_results must be a positive integer, got: {type(max_results)} {max_results}")

        """Search for places near a specific location.

        Args:
            location: (latitude, longitude) tuple
            radius_meters: Search radius in meters (max 50000)
            included_types: List of place types to include
            max_results: Maximum number of results to return

        Returns:
            List of place data dictionaries
        """
        url = f"{NEW_PLACES_API_BASE}:searchNearby"

        headers = self._get_base_headers()
        headers["X-Goog-FieldMask"] = FIELD_MASKS["search"]

        lat, lng = location
        payload = {
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": min(radius_meters, 50000),  # API limit
                }
            },
            "includedTypes": included_types or FOOD_BUSINESS_TYPES,
            "maxResultCount": min(max_results, 20),  # API limit
        }

        # Check cache for this nearby search
        cached_result = self.cache.get_search_results(f"nearby:{lat},{lng}", None, radius_meters)

        if cached_result:
            logger.debug(f"Cache hit for nearby search: {lat}, {lng}")
            return cached_result[:max_results]

        logger.debug(f"Searching places nearby location: {lat}, {lng}")
        data = self._make_request(url, headers, payload)

        places = data.get("places", [])[:max_results]

        # Cache the result
        self.cache.cache_search_results(f"nearby:{lat},{lng}", None, radius_meters, places)

        return places

    def get_place_details(self, place_id: str, field_mask: str = "comprehensive") -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific place with type validation."""
        # Type validation
        if not isinstance(place_id, str) or not place_id.strip():
            raise ValueError(f"place_id must be a non-empty string, got: {type(place_id)} {repr(place_id)}")
        if not isinstance(field_mask, str):
            raise ValueError(f"field_mask must be a string, got: {type(field_mask)} {field_mask}")
        if field_mask not in FIELD_MASKS and field_mask != "all":
            raise ValueError(f"field_mask must be one of {list(FIELD_MASKS.keys())} or 'all', got: {field_mask}")

        """Get detailed information for a specific place.

        Args:
            place_id: Google Place ID
            field_mask: Field mask to specify which data to retrieve

        Returns:
            Place details dictionary or None if not found
        """
        url = f"{NEW_PLACES_API_BASE}/{place_id}"

        # Get field mask from predefined options or use as-is
        field_mask_value = FIELD_MASKS.get(field_mask, field_mask) if field_mask != "all" else "*"

        headers = self._get_base_headers()
        headers["X-Goog-FieldMask"] = field_mask_value

        # Check cache first
        cached_result = self.cache.get_place_details(place_id)

        if cached_result:
            logger.debug(f"Cache hit for place details: {place_id}")
            return cached_result

        logger.debug(f"Getting place details for ID: {place_id}")

        try:
            data = self._make_request(url, headers)

            # Cache the result if successful
            if data:
                self.cache.cache_place_details(place_id, data)

            return data if data else None
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get place details for {place_id}: {e}")
            return None

    def find_place_matches(
        self,
        name: str,
        address: Optional[str] = None,
        location_bias: Optional[Tuple[float, float]] = None,
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """Find Google Place ID matches for a restaurant.

        Args:
            name: Restaurant name
            address: Optional restaurant address
            location_bias: Optional (latitude, longitude) for location bias

        Returns:
            Tuple of (exact_match_place_id, all_matches_list)
        """
        # Build search query
        search_query = name
        if address:
            search_query += f" {address}"

        # Search for places
        places = self.search_places_by_text(search_query, location_bias=location_bias, max_results=10)

        if not places:
            return None, []

        # Look for exact name matches
        exact_matches = []
        for place in places:
            place_name = self._extract_place_name(place)
            if place_name and place_name.lower() == name.lower():
                exact_matches.append(place)

        # Return single exact match if found
        if len(exact_matches) == 1:
            return exact_matches[0].get("id"), exact_matches

        # Return all matches for manual selection
        return None, places

    def _extract_place_name(self, place: Dict[str, Any]) -> str:
        """Extract place name from API response.

        Args:
            place: Place data from API

        Returns:
            Place name string
        """
        display_name = place.get("displayName", {})
        if isinstance(display_name, dict):
            return display_name.get("text", "")
        return str(display_name) if display_name else ""

    def extract_restaurant_data(self, place_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract restaurant-specific data from place details.

        Args:
            place_data: Place details from API

        Returns:
            Dictionary with extracted restaurant data
        """
        # Extract basic information
        name_obj = place_data.get("displayName", {})
        name = name_obj.get("text") if isinstance(name_obj, dict) else str(name_obj) if name_obj else ""

        # Extract standardized address components
        address_data = self.parse_address_components(place_data.get("addressComponents", []))

        # Extract location
        location = place_data.get("location", {})
        latitude = location.get("latitude") if location else None
        longitude = location.get("longitude") if location else None

        return {
            "name": name,
            "formatted_address": place_data.get("formattedAddress", ""),
            "address_line_1": address_data.get("address_line_1", ""),
            "address_line_2": address_data.get("address_line_2", ""),
            "city": address_data.get("city", ""),
            "state": address_data.get("state", ""),
            "state_long": address_data.get("state_long", ""),
            "state_short": address_data.get("state_short", ""),
            "postal_code": address_data.get("postal_code", ""),
            "country": address_data.get("country", ""),
            # Legacy field for backward compatibility
            "street_address": address_data.get("address_line_1", ""),
            "latitude": latitude,
            "longitude": longitude,
            "rating": place_data.get("rating"),
            "user_rating_count": place_data.get("userRatingCount"),
            "price_level": place_data.get("priceLevel"),
            "phone_number": place_data.get("nationalPhoneNumber"),
            "website": place_data.get("websiteUri"),
            "business_status": place_data.get("businessStatus"),
            "primary_type": place_data.get("primaryType"),
            "types": place_data.get("types", []),
            "editorial_summary": place_data.get("editorialSummary"),
            "payment_options": place_data.get("paymentOptions", {}),
            "accessibility_options": place_data.get("accessibilityOptions", {}),
            "parking_options": place_data.get("parkingOptions", {}),
            "serves_breakfast": place_data.get("servesBreakfast"),
            "serves_lunch": place_data.get("servesLunch"),
            "serves_dinner": place_data.get("servesDinner"),
            "serves_beer": place_data.get("servesBeer"),
            "serves_wine": place_data.get("servesWine"),
            "serves_brunch": place_data.get("servesBrunch"),
            "serves_vegetarian_food": place_data.get("servesVegetarianFood"),
            "delivery": place_data.get("delivery"),
            "dine_in": place_data.get("dineIn"),
            "takeout": place_data.get("takeout"),
            "reservable": place_data.get("reservable"),
            "restroom": place_data.get("restroom"),
            "outdoor_seating": place_data.get("outdoorSeating"),
        }

    def detect_service_level_from_data(self, place_data: Dict[str, Any]) -> Tuple[str, float]:
        """Detect service level from Google Places data with type validation."""
        if not isinstance(place_data, dict):
            raise ValueError(f"place_data must be a dictionary, got: {type(place_data)} {place_data}")

        """Detect service level from Google Places data.

        Args:
            place_data: Place data from API

        Returns:
            Tuple of (service_level, confidence_score)
        """
        logger.debug("Detecting service level from Google Places data")

        # Get price level and convert to integer
        price_level = self.convert_price_level_to_int(place_data.get("priceLevel"))
        logger.debug(f"Price level: {place_data.get('priceLevel')} -> {price_level}")

        # Get types
        types = place_data.get("types", [])
        types_lower = [t.lower() for t in types] if types else []
        logger.debug(f"Types: {types_lower}")

        # Check for quick service first
        quick_service_result = self._detect_quick_service(types_lower)
        if quick_service_result:
            return quick_service_result

        # Check for sit-down restaurants
        sit_down_result = self._detect_sit_down_restaurant(types_lower, price_level)
        if sit_down_result:
            return sit_down_result

        # Fallback to price-based detection
        return self._detect_service_level_by_price(price_level)

    def _detect_quick_service(self, types_lower: List[str]) -> Optional[Tuple[str, float]]:
        """Detect quick service establishments."""
        quick_service_types = [
            "fast_food_restaurant",
            "fast_food",
            "food_truck",
            "snack_bar",
            "takeout",
            "dessert_shop",
            "ice_cream_shop",
            "bakery",
            "cafe",
            "coffee_shop",
            # Store types that are inherently quick service
            "convenience_store",
            "grocery_store",
            "supermarket",
            "gas_station",
        ]
        if any(t in types_lower for t in quick_service_types):
            logger.debug("Quick service type detected - quick_service")
            return "quick_service", 0.8
        return None

    def _detect_sit_down_restaurant(
        self, types_lower: List[str], price_level: Optional[int]
    ) -> Optional[Tuple[str, float]]:
        """Detect sit-down restaurants and determine service level."""
        # First, exclude stores - they should be quick service, not sit-down
        store_types = ["convenience_store", "grocery_store", "supermarket", "gas_station"]
        if any(t in types_lower for t in store_types):
            logger.debug("Store type detected - not a sit-down restaurant")
            return None

        sit_down_types = [
            "restaurant",
            "mexican_restaurant",
            "italian_restaurant",
            "chinese_restaurant",
            "american_restaurant",
            "steak_house",
            "seafood_restaurant",
            "indian_restaurant",
            "thai_restaurant",
            "japanese_restaurant",
            "korean_restaurant",
            "mediterranean_restaurant",
        ]

        if not any(t in types_lower for t in sit_down_types):
            return None

        # For sit-down restaurants, use price level as secondary factor
        if price_level is not None:
            if price_level <= 1:
                service_level = "casual_dining"  # Affordable sit-down = casual dining
                confidence = 0.7
            elif price_level == 2:
                service_level = "casual_dining"
                confidence = 0.8
            elif price_level == 3:
                service_level = "casual_dining"
                confidence = 0.8
            else:  # price_level >= 4
                service_level = "fine_dining"
                confidence = 0.9

            logger.debug(
                f"Sit-down restaurant with price level {price_level}: {service_level} (confidence: {confidence})"
            )
            return service_level, confidence
        else:
            # No price level, default to casual dining for sit-down restaurants
            logger.debug("Sit-down restaurant without price level - defaulting to casual_dining")
            return "casual_dining", 0.6

    def _detect_service_level_by_price(self, price_level: Optional[int]) -> Tuple[str, float]:
        """Fallback: detect service level by price only."""
        if price_level is not None:
            if price_level <= 1:
                service_level = "quick_service"
                confidence = 0.6  # Lower confidence since we don't have clear type indicators
            elif price_level == 2:
                service_level = "casual_dining"
                confidence = 0.6
            elif price_level == 3:
                service_level = "casual_dining"
                confidence = 0.7
            else:
                service_level = "fine_dining"
                confidence = 0.8

            logger.debug(f"Fallback: price level {price_level} -> {service_level} (confidence: {confidence})")
            return service_level, confidence

        # Default fallback
        logger.debug("No clear indicators found - defaulting to casual_dining")
        return "casual_dining", 0.3

    def build_photo_urls(self, photos: List[Dict[str, Any]], max_width: int = 400) -> List[Dict[str, str]]:
        """Build photo URLs from Google Places New API photo objects with type validation."""
        if not isinstance(photos, list):
            raise ValueError(f"photos must be a list, got: {type(photos)} {photos}")
        if not isinstance(max_width, int) or max_width <= 0:
            raise ValueError(f"max_width must be a positive integer, got: {type(max_width)} {max_width}")

        """Build photo URLs from Google Places New API photo objects.

        Args:
            photos: List of photo objects from Google Places New API
            max_width: Maximum width for photo URLs

        Returns:
            List of photo dictionaries with URLs
        """
        photo_list = []
        logger.debug(f"Processing {len(photos) if photos else 0} photos")

        if photos:
            for photo in photos[:3]:  # Limit to first 3 photos
                # New API provides direct photo URIs in the 'name' field
                photo_uri = photo.get("name")
                logger.debug(f"Photo data: {photo}")

                if photo_uri:
                    # For the new API, the 'name' field contains the resource name
                    # Format: places/{place_id}/photos/{photo_id}/media
                    # We need to convert this to a proper HTTP URL
                    photo_url = (
                        f"https://places.googleapis.com/v1/{photo_uri}/media?maxWidthPx={max_width}&key={self.api_key}"
                    )

                    photo_list.append(
                        {
                            "photo_reference": (photo_uri.split("/")[-2] if "/" in photo_uri else photo_uri),
                            "url": photo_url,
                        }
                    )
                else:
                    # Handle legacy API format with photo_reference only
                    photo_ref = photo.get("photo_reference")
                    if photo_ref:
                        # For legacy API, construct URL using photo reference
                        photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth={max_width}&photoreference={photo_ref}&key={self.api_key}"

                        photo_list.append(
                            {
                                "photo_reference": photo_ref,
                                "url": photo_url,
                            }
                        )

                        logger.debug(f"Using Places API photo URI: {photo_url}")
                    else:
                        logger.warning(f"No photo URI found in photo data: {photo}")

        logger.debug(f"Built {len(photo_list)} photo URLs")
        return photo_list

    def build_reviews_summary(self, reviews: List[Dict[str, Any]], max_reviews: int = 3) -> List[Dict[str, Any]]:
        """Build reviews summary from Google Places reviews.

        Args:
            reviews: List of review objects from Google Places API
            max_reviews: Maximum number of reviews to include

        Returns:
            List of review summaries
        """
        reviews_list = []
        if reviews:
            for review in reviews[:max_reviews]:
                text = review.get("text", "")
                truncated_text = text[:200] + "..." if len(text) > 200 else text
                reviews_list.append(
                    {
                        "author_name": review.get("authorAttribution", {}).get("displayName", "Anonymous"),
                        "rating": review.get("rating", 0),
                        "text": truncated_text,
                        "time": review.get("publishTime", ""),
                    }
                )
        return reviews_list

    def search_places_with_fallback(
        self,
        query: str,
        location: Optional[Tuple[float, float]] = None,
        radius_miles: float = 25.0,
        cuisine: Optional[str] = None,
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search places with intelligent fallback logic.

        Args:
            query: Search query text
            location: Optional (latitude, longitude) for location bias
            radius_miles: Search radius in miles
            cuisine: Optional cuisine type to add to query
            max_results: Maximum number of results to return

        Returns:
            List of place data dictionaries
        """
        # Build search query
        search_query = query
        if cuisine:
            search_query += f" {cuisine} restaurant"

        # Convert miles to meters
        radius_meters = int(radius_miles * 1609.34)

        # Try text search first if we have a meaningful query
        if search_query and search_query.strip() and search_query.strip() != "restaurants":
            places = self.search_places_by_text(
                search_query,
                location_bias=location,
                radius_meters=radius_meters,
                max_results=max_results,
            )
            if places:
                return places

        # Fallback to nearby search if we have location (more accurate location-based results)
        # Use only restaurant-specific types to avoid getting supermarkets like Walmart
        if location:
            restaurant_types = [
                "restaurant",
                "fast_food_restaurant",
                "cafe",
                "bar",
                "bakery",
                "meal_takeaway",
                "meal_delivery",
            ]
            places = self.search_places_nearby(
                location, radius_meters=radius_meters, included_types=restaurant_types, max_results=max_results
            )
            if places:
                return places

        # Final fallback: more specific restaurant text search with location restriction
        return self.search_places_by_text(
            "restaurant",
            location_bias=location,
            radius_meters=radius_meters,
            max_results=max_results,
        )

    def _is_non_restaurant_business(self, name: str) -> bool:
        """Check if a business name indicates it's not a restaurant.

        Args:
            name: Business name to check

        Returns:
            True if the business should be filtered out as non-restaurant
        """
        if not name:
            return False

        name_lower = name.lower().strip()

        # Common big box stores and supermarkets that have food sections but aren't restaurants
        non_restaurant_keywords = [
            "walmart",
            "target",
            "costco",
            "sam's club",
            "sams club",
            "kroger",
            "safeway",
            "whole foods",
            "trader joe's",
            "trader joes",
            "aldi",
            "lidl",
            "publix",
            "meijer",
            "heinen's",
            "giant eagle",
            "stop & shop",
            "stop and shop",
            "shoprite",
            "wegmans",
            "harris teeter",
            "food lion",
            "winco",
            "winco foods",
            "save mart",
            "ralphs",
            "vons",
            "pavilions",
            "stater bros",
            "smart & final",
            "smart and final",
            "fresh & easy",
            "fresh and easy",
            "sprouts farmers market",
            "sprouts",
            "natural grocers",
            "earth fare",
            "fresh thyme",
            "lucky",
            "ruler foods",
            "food 4 less",
            "foods co",
            "el super",
            "northgate market",
            "fiesta mart",
            "fiesta",
            "carniceria",
            "vallarta",
            "superior",
            "el rancho",
            "fiesta foods",
            "supermercado",
            "grocery outlet",
            "grocery",
            "market",
            "foods",
            "food store",
            "convenience store",
            "gas station",
            "fuel station",
            "department store",
            "discount store",
            "big box",
            "superstore",
            "hypermarket",
            "warehouse club",
        ]

        # Check for exact matches or partial matches
        for keyword in non_restaurant_keywords:
            if keyword in name_lower:
                logger.debug(f"Business '{name}' filtered out due to keyword '{keyword}'")
                return True

        return False

    def process_search_result_place(self, place: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single search result place into standardized format.

        Args:
            place: Place data from search results

        Returns:
            Processed place data or None if invalid
        """
        try:
            # Extract basic information
            place_id = place.get("id")
            if not place_id:
                return None

            # Extract name
            display_name = place.get("displayName", {})
            name = (
                display_name.get("text")
                if isinstance(display_name, dict)
                else str(display_name) if display_name else ""
            )

            # Filter out non-restaurant businesses like Walmart, Target, etc.
            if self._is_non_restaurant_business(name):
                logger.debug(f"Filtering out non-restaurant business: {name}")
                return None

            # Extract location
            location = place.get("location", {})
            latitude = location.get("latitude") if location else None
            longitude = location.get("longitude") if location else None

            # Extract rating and price level
            rating = place.get("rating")
            price_level = place.get("priceLevel")

            # Extract address
            formatted_address = place.get("formattedAddress", "")

            # Extract types
            types = place.get("types", [])
            primary_type = place.get("primaryType", "")

            return {
                "place_id": place_id,
                "name": name,
                "formatted_address": formatted_address,
                "latitude": latitude,
                "longitude": longitude,
                "rating": rating,
                "price_level": price_level,
                "types": types,
                "primary_type": primary_type,
                "user_rating_total": place.get("userRatingCount", 0),
            }

        except Exception as e:
            logger.error(f"Error processing place data: {e}")
            return None

    def filter_places_by_criteria(
        self,
        places: List[Dict[str, Any]],
        min_rating: Optional[float] = None,
        max_price_level: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Filter places by rating and price level criteria.

        Args:
            places: List of place data dictionaries
            min_rating: Minimum rating to include
            max_price_level: Maximum price level to include

        Returns:
            Filtered list of places
        """
        filtered_places = []

        for place in places:
            # Check rating filter
            if min_rating is not None:
                place_rating = place.get("rating")
                if place_rating is None or place_rating < min_rating:
                    continue

            # Check price level filter
            if max_price_level is not None:
                place_price_level = place.get("price_level")
                if place_price_level is not None and place_price_level > max_price_level:
                    continue

            filtered_places.append(place)

        return filtered_places

    def parse_address_components(self, address_components: List[Dict[str, Any]]) -> Dict[str, str]:
        """Parse Google Places address components into our standardized address structure.

        This is the SINGLE place where Google Places API address data is mapped to our structure.

        Args:
            address_components: List of address component dictionaries from Google Places API

        Returns:
            Dictionary with standardized address fields:
            - address_line_1: Street number + route name
            - address_line_2: Apartment/suite number (subpremise)
            - city: City name
            - state: State abbreviation or name
            - postal_code: ZIP/postal code
            - country: Country name
        """
        # Initialize our standardized address structure
        address_data = {
            "address_line_1": "",
            "address_line_2": "",
            "city": "",
            "state": "",
            "postal_code": "",
            "country": "",
        }

        logger.debug(f"Parsing Google Places address components: {len(address_components)} components")

        # Extract components
        street_number, route, subpremise = self._extract_street_components(address_components)

        # Parse location components
        self._parse_location_components(address_components, address_data)

        # Build final address
        self._build_final_address(address_data, street_number, route, subpremise)

        logger.debug(f"Final standardized address: {address_data}")
        return address_data

    def _extract_street_components(self, address_components: List[Dict[str, Any]]) -> Tuple[str, str, str]:
        """Extract street number, route, and subpremise from components."""
        street_number = ""
        route = ""
        subpremise = ""

        for component in address_components:
            types = component.get("types", [])
            long_text = component.get("longText", "").strip()

            # Street number (premise, street_number, or first component with no types)
            if any(t in ["street_number", "premise"] for t in types):
                street_number = long_text
                logger.debug(f"Found street number: '{street_number}'")
            elif not types and not street_number and long_text and any(c.isdigit() for c in long_text):
                # First component with no types that contains numbers is likely street number
                street_number = long_text
                logger.debug(f"Using first component as street number: '{street_number}'")

            # Route (street name)
            elif any(t in ["route", "street_address"] for t in types):
                route = long_text
                logger.debug(f"Found route: '{route}'")

            # Subpremise (apartment/suite number)
            elif "subpremise" in types:
                subpremise = long_text
                logger.debug(f"Found subpremise: '{subpremise}'")

        return street_number, route, subpremise

    def _parse_location_components(
        self, address_components: List[Dict[str, Any]], address_data: Dict[str, str]
    ) -> None:
        """Parse city, state, postal code, and country from components."""
        for component in address_components:
            types = component.get("types", [])
            long_text = component.get("longText", "").strip()
            short_text = component.get("shortText", "").strip()

            logger.debug(f"Processing: types={types}, longText='{long_text}', shortText='{short_text}'")

            # City
            if any(t in ["locality", "sublocality", "sublocality_level_1"] for t in types):
                address_data["city"] = long_text
                logger.debug(f"Found city: '{address_data['city']}'")

            # State (store both short and long forms for comparison)
            elif "administrative_area_level_1" in types:
                address_data["state"] = short_text or long_text
                address_data["state_long"] = long_text  # Store full name too
                address_data["state_short"] = short_text  # Store abbreviation too
                logger.debug(f"Found state: '{address_data['state']}' (long: '{long_text}', short: '{short_text}')")

            # Postal code
            elif "postal_code" in types:
                address_data["postal_code"] = long_text
                logger.debug(f"Found postal_code: '{address_data['postal_code']}'")

            # Country
            elif "country" in types:
                address_data["country"] = long_text
                logger.debug(f"Found country: '{address_data['country']}'")

    def _build_final_address(
        self, address_data: Dict[str, str], street_number: str, route: str, subpremise: str
    ) -> None:
        """Build the final address fields."""
        # Build address_line_1 (street number + route)
        if street_number and route:
            address_data["address_line_1"] = f"{street_number} {route}"
        elif street_number:
            address_data["address_line_1"] = street_number
        elif route:
            address_data["address_line_1"] = route

        # Set address_line_2 (subpremise with proper formatting)
        if subpremise:
            logger.debug(f"Processing subpremise: '{subpremise}'")
            stripped_subpremise = subpremise.strip()
            logger.debug(f"Stripped subpremise: '{stripped_subpremise}'")

            # Remove # prefix if it exists (Google Places sometimes includes it)
            if stripped_subpremise.startswith("#"):
                stripped_subpremise = stripped_subpremise[1:].strip()
                logger.debug(f"Removed # prefix: '{stripped_subpremise}'")
            # Check if subpremise is purely numeric (e.g., "100") vs text (e.g., "Suite 120")
            if stripped_subpremise.isdigit():
                # Only add # prefix for purely numeric values
                address_data["address_line_2"] = f"#{stripped_subpremise}"
                logger.debug(f"Set numeric address_line_2: '{address_data['address_line_2']}'")
            else:
                # Keep text values as-is (e.g., "Suite 120", "Apt B", etc.)
                address_data["address_line_2"] = stripped_subpremise
                logger.debug(f"Set text address_line_2: '{address_data['address_line_2']}'")

    def analyze_restaurant_types(
        self, types: List[str], place_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[str], str]:
        """Analyze Google Places types and service options to determine cuisine and service level.

        Args:
            types: List of place types from Google Places
            place_data: Optional place data for additional context

        Returns:
            Tuple of (cuisine, service_level)
        """
        logger.debug(f"Analyzing restaurant types: {types}")
        logger.debug(f"Place data keys: {list(place_data.keys()) if place_data else 'None'}")
        if place_data and "editorialSummary" in place_data:
            logger.debug(f"Editorial summary: {place_data['editorialSummary']}")

        types_lower = [t.lower() for t in types]
        logger.debug(f"Types lower: {types_lower}")

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
            logger.debug(f"Primary type: {primary_type}")

        # Detect cuisine from types, primary type, description, and name
        cuisine = self._detect_cuisine_from_types(types_lower, restaurant_name, place_data, primary_type)

        if not cuisine:
            logger.debug("No cuisine detected from types, will try name-based detection")

        # Detect service level
        service_level, confidence = self.detect_service_level_from_data(place_data or {})

        return cuisine, service_level

    def _detect_cuisine_from_name(self, name: str) -> Optional[str]:
        """Detect cuisine from restaurant name using pattern matching."""
        if not name:
            return None

        name_lower = name.lower()

        # Cuisine patterns for name-based detection
        cuisine_patterns = {
            "japanese": [
                "sushi",
                "ramen",
                "teriyaki",
                "tempura",
                "japanese",
                "tokyo",
                "osaka",
                "hibachi",
                "sashimi",
                "miso",
                "wasabi",
            ],
            "chinese": [
                "chinese",
                "panda",
                "dragon",
                "wok",
                "dim sum",
                "peking",
                "canton",
                "mandarin",
                "szechuan",
                "hunan",
                "kung pao",
            ],
            "italian": [
                "pizza",
                "pasta",
                "italian",
                "roma",
                "mario",
                "luigi",
                "trattoria",
                "ristorante",
                "bella",
                "bella vista",
                "bella vita",
            ],
            "mexican": [
                "mexican",
                "taco",
                "burrito",
                "enchilada",
                "quesadilla",
                "el",
                "la",
                "casa",
                "cantina",
                "fiesta",
                "margarita",
            ],
            "indian": [
                "indian",
                "curry",
                "tandoor",
                "masala",
                "biryani",
                "tikka",
                "naan",
                "samosa",
                "dal",
                "biryani",
            ],
            "thai": [
                "thai",
                "pad thai",
                "tom yum",
                "green curry",
                "red curry",
                "massaman",
                "satay",
                "pho",
                "vietnamese",
            ],
            "korean": [
                "korean",
                "korean bbq",
                "bulgogi",
                "kimchi",
                "bibimbap",
                "korean grill",
                "seoul",
            ],
            "american": [
                "grill",
                "diner",
                "cafe",
                "bistro",
                "steakhouse",
                "bbq",
                "barbecue",
                "burger",
                "sandwich",
                "deli",
                "buffalo wild wings",
                "bww",
                "wings",
                "sports bar",
                "applebee",
                "chili",
                "tgi friday",
                "olive garden",
                "red lobster",
                "outback",
                "texas roadhouse",
                "hooters",
                "denny",
                "ihop",
                "waffle house",
                "cracker barrel",
            ],
            "french": [
                "french",
                "bistro",
                "brasserie",
                "cafe",
                "creperie",
                "boulangerie",
                "patisserie",
            ],
            "greek": [
                "greek",
                "gyro",
                "souvlaki",
                "mediterranean",
                "olive",
                "acropolis",
                "parthenon",
            ],
            "middle eastern": [
                "middle eastern",
                "persian",
                "iranian",
                "lebanese",
                "turkish",
                "kebab",
                "falafel",
                "hummus",
            ],
            "seafood": [
                "seafood",
                "fish",
                "lobster",
                "crab",
                "shrimp",
                "oyster",
                "clam",
                "salmon",
                "tuna",
                "cod",
            ],
            "steakhouse": [
                "steak",
                "steakhouse",
                "chop",
                "cut",
                "prime",
                "rib",
                "beef",
                "cattle",
                "ranch",
            ],
            "pizza": [
                "pizza",
                "pizzeria",
                "slice",
                "pie",
                "domino",
                "papa",
                "little caesar",
                "pizza hut",
            ],
            "fast food": [
                "mcdonald",
                "burger king",
                "wendy",
                "kfc",
                "taco bell",
                "subway",
                "pizza hut",
                "domino",
            ],
        }

        # Check each cuisine pattern
        for cuisine, patterns in cuisine_patterns.items():
            for pattern in patterns:
                if pattern in name_lower:
                    return cuisine.title()

        return None

    def _detect_cuisine_from_types(
        self,
        types_lower: List[str],
        restaurant_name: str,
        place_data: Optional[Dict[str, Any]],
        primary_type: str,
    ) -> Optional[str]:
        """Detect cuisine from Google Places types and other data.

        Args:
            types_lower: Lowercase list of place types
            restaurant_name: Restaurant name
            place_data: Optional place data
            primary_type: Primary type from Google Places

        Returns:
            Detected cuisine or None
        """
        # PRIORITY LOGIC: If "restaurant" type is present, prioritize restaurant-specific cuisines
        if "restaurant" in types_lower:
            logger.debug("Restaurant type found - prioritizing restaurant-specific cuisine detection")
            return self._detect_restaurant_cuisine(types_lower, restaurant_name, primary_type)

        # If no "restaurant" type, check other types
        return self._detect_non_restaurant_cuisine(types_lower, restaurant_name, primary_type)

    def _detect_restaurant_cuisine(
        self, types_lower: List[str], restaurant_name: str, primary_type: str
    ) -> Optional[str]:
        """Detect cuisine when restaurant type is present."""
        cuisine_mapping = self._get_cuisine_mapping()

        # Check for exact restaurant type matches first
        for place_type in types_lower:
            if place_type in cuisine_mapping:
                logger.debug(f"Detected cuisine from restaurant type '{place_type}': {cuisine_mapping[place_type]}")
                return cuisine_mapping[place_type]

        # Check primary type if it's restaurant-related
        if primary_type and primary_type.lower() in cuisine_mapping:
            logger.debug(
                f"Detected cuisine from primary restaurant type '{primary_type}': {cuisine_mapping[primary_type.lower()]}"
            )
            return cuisine_mapping[primary_type.lower()]

        # For chain restaurants, use name-based detection
        if restaurant_name:
            detected_cuisine = self._detect_cuisine_from_name(restaurant_name)
            if detected_cuisine:
                logger.debug(f"Detected cuisine from restaurant name '{restaurant_name}': {detected_cuisine}")
                return detected_cuisine

        # Default to American for generic restaurants
        logger.debug("Restaurant type found but no specific cuisine detected - defaulting to American")
        return "American"

    def _detect_non_restaurant_cuisine(
        self, types_lower: List[str], restaurant_name: str, primary_type: str
    ) -> Optional[str]:
        """Detect cuisine when no restaurant type is present."""
        cuisine_mapping = self._get_cuisine_mapping()

        # Check for exact type matches
        for place_type in types_lower:
            if place_type in cuisine_mapping:
                logger.debug(f"Detected cuisine from type '{place_type}': {cuisine_mapping[place_type]}")
                return cuisine_mapping[place_type]

        # Check primary type
        if primary_type and primary_type.lower() in cuisine_mapping:
            logger.debug(
                f"Detected cuisine from primary type '{primary_type}': {cuisine_mapping[primary_type.lower()]}"
            )
            return cuisine_mapping[primary_type.lower()]

        # Check for partial matches
        for place_type in types_lower:
            for cuisine_type, cuisine_name in cuisine_mapping.items():
                if cuisine_type in place_type or place_type in cuisine_type:
                    logger.debug(f"Detected cuisine from partial type match '{place_type}': {cuisine_name}")
                    return cuisine_name

        # Try name-based detection as fallback
        if restaurant_name:
            detected_cuisine = self._detect_cuisine_from_name(restaurant_name)
            if detected_cuisine:
                logger.debug(f"Detected cuisine from name '{restaurant_name}': {detected_cuisine}")
                return detected_cuisine

        logger.debug("No cuisine detected from types or name")
        return None

    def _get_cuisine_mapping(self) -> Dict[str, str]:
        """Get cuisine mapping dictionary."""
        return {
            # Reduced and sorted to only Google Places new API supported types (as of 2024)
            "afghan_restaurant": "Afghan",
            "african_restaurant": "African",
            "american_restaurant": "American",
            "argentine_restaurant": "Argentine",
            "asian_restaurant": "Asian",
            "australian_restaurant": "Australian",
            "austrian_restaurant": "Austrian",
            "bangladeshi_restaurant": "Bangladeshi",
            "barbecue_restaurant": "Barbecue",
            "brazilian_restaurant": "Brazilian",
            "breakfast_restaurant": "Breakfast",
            "british_restaurant": "British",
            "cafe": "Cafe",
            "cajun_creole_restaurant": "Cajun/Creole",
            "caribbean_restaurant": "Caribbean",
            "chinese_restaurant": "Chinese",
            "colombian_restaurant": "Colombian",
            "cuban_restaurant": "Cuban",
            "dessert_restaurant": "Dessert",
            "diner": "Diner",
            "ethiopian_restaurant": "Ethiopian",
            "fast_food_restaurant": "Fast Food",
            "filipino_restaurant": "Filipino",
            "french_restaurant": "French",
            "german_restaurant": "German",
            "greek_restaurant": "Greek",
            "hawaiian_restaurant": "Hawaiian",
            "hungarian_restaurant": "Hungarian",
            "indian_restaurant": "Indian",
            "indonesian_restaurant": "Indonesian",
            "irish_restaurant": "Irish",
            "italian_restaurant": "Italian",
            "japanese_restaurant": "Japanese",
            "jewish_restaurant": "Jewish",
            "korean_restaurant": "Korean",
            "lebanese_restaurant": "Lebanese",
            "malaysian_restaurant": "Malaysian",
            "mediterranean_restaurant": "Mediterranean",
            "mexican_restaurant": "Mexican",
            "middle_eastern_restaurant": "Middle Eastern",
            "moroccan_restaurant": "Moroccan",
            "nepalese_restaurant": "Nepalese",
            "pakistani_restaurant": "Pakistani",
            "peruvian_restaurant": "Peruvian",
            "pizza_restaurant": "Pizza",
            "polish_restaurant": "Polish",
            "portuguese_restaurant": "Portuguese",
            "russian_restaurant": "Russian",
            "seafood_restaurant": "Seafood",
            "singaporean_restaurant": "Singaporean",
            "spanish_restaurant": "Spanish",
            "steak_house": "Steakhouse",
            "sushi_restaurant": "Sushi",
            "swiss_restaurant": "Swiss",
            "taiwanese_restaurant": "Taiwanese",
            "thai_restaurant": "Thai",
            "turkish_restaurant": "Turkish",
            "vegan_restaurant": "Vegan",
            "vegetarian_restaurant": "Vegetarian",
            "vietnamese_restaurant": "Vietnamese",
        }

    def convert_price_level_to_int(self, price_level: Any) -> Optional[int]:
        """Convert Google Places price level to integer (handles both old and new API formats).

        Args:
            price_level: Price level value from Google Places API

        Returns:
            Integer price level (0-4) or None if invalid
        """
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

    def get_specific_cuisine_types(self) -> Dict[str, str]:
        """Get mapping of specific Google Places cuisine types to formatted names.

        Returns:
            Dictionary mapping Google Places types to cuisine names
        """
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

    def matches_cuisine_pattern(self, name_lower: str, pattern: str) -> bool:
        """Return True when pattern matches as a whole word; for multi-word patterns,
        fallback to substring. Prevents false matches like 'bar' in 'barbecue'.

        Args:
            name_lower: Restaurant name in lowercase
            pattern: Pattern to match

        Returns:
            True if pattern matches
        """
        import re

        tokenized = not any(ch.isspace() for ch in pattern)
        if tokenized and pattern.isalpha():
            return re.search(rf"\b{re.escape(pattern)}\b", name_lower) is not None
        return pattern in name_lower

    def detect_chain_restaurant(self, name: str, place_data: Optional[Dict[str, Any]] = None) -> bool:
        """Detect if restaurant is likely a chain using multiple detection methods.

        Args:
            name: Restaurant name
            place_data: Optional Google Places data

        Returns:
            True if restaurant is likely a chain
        """
        logger.debug(f"Detecting chain status for: {name}")

        # Method 1: Known chain names (highest priority)
        is_chain = self._detect_chain_from_known_names(name)
        if is_chain is not None:
            logger.debug(f"Chain detected from known names: {is_chain}")
            return is_chain

        # Method 2: Description-based detection (secondary)
        if place_data and "editorial_summary" in place_data and place_data["editorial_summary"]:
            editorial_text = (
                place_data["editorial_summary"].get("overview", "")
                if isinstance(place_data["editorial_summary"], dict)
                else str(place_data["editorial_summary"])
            )
            if editorial_text:
                is_chain = self._detect_chain_from_description(editorial_text)
                if is_chain is not None:
                    logger.debug(f"Chain detected from description: {is_chain}")
                    return is_chain

        # Method 3: Name pattern analysis (tertiary)
        is_chain = self._detect_chain_from_name_patterns(name)
        if is_chain is not None:
            logger.debug(f"Chain detected from name patterns: {is_chain}")
            return is_chain

        # Method 4: Corporate indicators (quaternary)
        is_chain = self._detect_chain_from_corporate_indicators(name, place_data)
        if is_chain is not None:
            logger.debug(f"Chain detected from corporate indicators: {is_chain}")
            return is_chain

        # Default: assume not a chain (conservative approach)
        logger.debug("No clear chain indicators found, defaulting to False")
        return False

    def _detect_chain_from_known_names(self, name: str) -> Optional[bool]:
        """Detect chain status from known chain restaurant names.

        Args:
            name: Restaurant name

        Returns:
            True if chain, False if not, None if unknown
        """
        name_clean = name.lower().strip()

        # Remove common suffixes and clean up
        suffixes_to_remove = ["'s", "'s restaurant", " restaurant", " - ", " location", " store"]
        for suffix in suffixes_to_remove:
            if name_clean.endswith(suffix):
                name_clean = name_clean[: -len(suffix)].strip()

        # Known chain restaurants (case-insensitive)
        known_chains = {
            # Fast Food Chains
            "mcdonalds",
            "mcdonald's",
            "burger king",
            "wendy's",
            "wendys",
            "taco bell",
            "kfc",
            "kentucky fried chicken",
            "subway",
            "pizza hut",
            "domino's",
            "dominos",
            "papa john's",
            "papa johns",
            "little caesars",
            "arbys",
            "arby's",
            "chick-fil-a",
            "chick fil a",
            "popeyes",
            "popeye's",
            "sonic",
            "sonic drive-in",
            "jack in the box",
            "jack in the box",
            "white castle",
            "in-n-out",
            "in n out",
            "five guys",
            "five guys burgers",
            # Coffee Chains
            "starbucks",
            "dunkin' donuts",
            "dunkin donuts",
            "tim hortons",
            "tim horton's",
            "peet's coffee",
            "peets coffee",
            "caribou coffee",
            "the coffee bean",
            # Casual Dining Chains
            "applebee's",
            "applebees",
            "chili's",
            "chilis",
            "tgi friday's",
            "tgi fridays",
            "olive garden",
            "red lobster",
            "outback steakhouse",
            "texas roadhouse",
            "buffalo wild wings",
            "bww",
            "hooters",
            "denny's",
            "dennys",
            "ihop",
            "international house of pancakes",
            "waffle house",
            "cracker barrel",
            "bob evans",
            "perkins",
            "village inn",
            "friendly's",
            "friendlys",
            # Sandwich Chains
            "jimmy john's",
            "jimmy johns",
            "potbelly",
            "potbelly sandwich works",
            "firehouse subs",
            "jersey mike's",
            "jersey mikes",
            "quiznos",
            # Mexican Chains
            "chipotle",
            "qdoba",
            "moe's southwest grill",
            "moes",
            "taco cabana",
            "el pollo loco",
            "del taco",
            "baja fresh",
            # Asian Chains
            "panda express",
            "pf chang's",
            "pf changs",
            "pei wei",
            "benihana",
            # Pizza Chains (already listed above but being explicit)
            "papa murphy's",
            "papa murphys",
            "marco's pizza",
            "marco pizza",
            # Ice Cream Chains
            "baskin robbins",
            "cold stone creamery",
            "dairy queen",
            "dq",
            "ben & jerry's",
            "ben and jerry's",
            "haagen-dazs",
            "haagen dazs",
            # Bakery Chains
            "panera bread",
            "panera",
            "einstein bros",
            "einstein brothers",
            "cinnabon",
            "mrs. fields",
            "mrs fields",
            "great american cookies",
            # Other Popular Chains
            "hardee's",
            "hardees",
            "carl's jr",
            "carls jr",
            "long john silver's",
            "long john silvers",
            "a&w",
            "a & w",
            "steak 'n shake",
            "steak n shake",
            "culver's",
            "culvers",
            "whataburger",
            "shack shack",
            "shake shack",
            "the habit",
            "habit burger",
            "yard house",
            "bjs",
            "b.j.'s",
            "red robin",
            "fuddruckers",
            "fuddrucker's",
            "ruby tuesday",
            "twin peaks",
            "hooter's",
            "hooters",
            "tilted kilt",
            "bikinis",
            "tilted kilt pub & eatery",
            "hooters restaurant",
            "twin peaks restaurant",
        }

        # Check exact matches first
        if name_clean in known_chains:
            logger.debug(f"Found exact match in known chains: {name_clean}")
            return True

        # Check partial matches (for names with locations)
        for chain_name in known_chains:
            if chain_name in name_clean or name_clean in chain_name:
                logger.debug(f"Found partial match in known chains: {name_clean} matches {chain_name}")
                return True

        return None

    def _detect_chain_from_description(self, description: str) -> Optional[bool]:
        """Detect chain status from Google Places editorial summary.

        Args:
            description: Editorial summary text

        Returns:
            True if chain, False if not, None if unknown
        """
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
                logger.debug(f"Found anti-chain keyword: {keyword}")
                return False

        # Check for chain indicators
        for keyword in chain_keywords:
            if keyword in description_lower:
                logger.debug(f"Found chain keyword: {keyword}")
                return True

        return None

    def _detect_chain_from_name_patterns(self, name: str) -> Optional[bool]:
        """Detect chain status from restaurant name patterns.

        Args:
            name: Restaurant name

        Returns:
            True if chain, False if not, None if unknown
        """
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
                logger.debug(f"Found trademark indicator: {indicator}")
                return True

        # Check for corporate patterns (moderate chain indicator)
        import re

        for pattern in corporate_patterns:
            if re.search(pattern, name_lower):
                logger.debug(f"Found corporate pattern: {pattern}")
                return True

        return None

    def _detect_chain_from_corporate_indicators(
        self, name: str, place_data: Optional[Dict[str, Any]]
    ) -> Optional[bool]:
        """Detect chain status from corporate/Google Places indicators.

        Args:
            name: Restaurant name
            place_data: Optional Google Places data

        Returns:
            True if chain, False if not, None if unknown
        """
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
                    logger.debug(f"Found corporate website indicator: {indicator}")
                    return True

        # Check for multiple location indicators in name
        location_indicators = ["location", "branch", "store", "unit"]
        name_lower = name.lower()
        for indicator in location_indicators:
            if indicator in name_lower:
                logger.debug(f"Found location indicator: {indicator}")
                return True

        return None

    def format_primary_type_for_display(self, primary_type: str) -> Optional[str]:
        """Format a Google Places primary type for display.

        Converts snake_case to Title Case for user-friendly display.
        Returns None for empty input.
        """
        if not primary_type:
            return None

        # Replace underscores with spaces and title case
        return primary_type.replace("_", " ").title()

    def generate_description(self, place: Dict[str, Any]) -> str:
        """Generate a comprehensive description from Google Places data.

        Args:
            place: Google Places data

        Returns:
            Generated description string with extensive Google Places information
        """
        parts = []

        # Add summary information
        self._add_summary_info(place, parts)

        # Add comprehensive Google Places information
        google_info = []
        self._add_rating_info(place, google_info)
        self._add_price_level_info(place, google_info)
        self._add_business_status_info(place, google_info)
        self._add_type_info(place, google_info)
        self._add_service_options_info(place, google_info)
        self._add_amenities_info(place, google_info)
        self._add_payment_info(place, google_info)

        # Combine all information
        if google_info:
            parts.append(" | ".join(google_info))

        # Add formatted address if available
        if place.get("formattedAddress"):
            parts.append(f"📍 {place.get('formattedAddress')}")

        return " | ".join(parts) if parts else "Restaurant from Google Places"

    def _add_summary_info(self, place: Dict[str, Any], parts: list) -> None:
        """Add editorial and generative summary information."""
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

    def _add_rating_info(self, place: Dict[str, Any], google_info: list) -> None:
        """Add rating information to google_info."""
        if place.get("rating"):
            rating = place.get("rating")
            user_ratings_total = place.get("userRatingCount") or place.get("user_ratings_total")
            if user_ratings_total:
                google_info.append(f"⭐ {rating}/5 ({user_ratings_total:,} reviews)")
            else:
                google_info.append(f"⭐ {rating}/5")

    def _add_price_level_info(self, place: Dict[str, Any], google_info: list) -> None:
        """Add price level information to google_info."""
        price_level = place.get("priceLevel")
        if price_level is not None:
            price_level_int = self.convert_price_level_to_int(price_level)
            if price_level_int is not None:
                price_levels = {
                    0: "Free",
                    1: "$ (Inexpensive)",
                    2: "$$ (Moderate)",
                    3: "$$$ (Expensive)",
                    4: "$$$$ (Very Expensive)",
                }
                google_info.append(f"💰 {price_levels.get(price_level_int, 'Unknown')}")
            else:
                google_info.append(f"💰 Price Level: {price_level}")

    def _add_business_status_info(self, place: Dict[str, Any], google_info: list) -> None:
        """Add business status information to google_info."""
        business_status = place.get("businessStatus")
        if business_status and business_status != "OPERATIONAL":
            status_emoji = {"CLOSED_TEMPORARILY": "⏸️", "CLOSED_PERMANENTLY": "❌"}
            google_info.append(f"{status_emoji.get(business_status, '📊')} {business_status.replace('_', ' ').title()}")

    def _add_type_info(self, place: Dict[str, Any], google_info: list) -> None:
        """Add type and category information to google_info."""
        # Primary type
        primary_type = place.get("primaryType")
        if primary_type:
            google_info.append(f"🏷️ {primary_type.replace('_', ' ').title()}")

        # Types/Categories
        types = place.get("types", [])
        if types:
            # Filter out generic types and show interesting ones
            interesting_types = [
                t.replace("_", " ").title()
                for t in types
                if t not in ["establishment", "food", "point_of_interest", "place_of_interest"]
            ]
            if interesting_types:
                # Limit to top 3 most interesting types
                google_info.append(f"📂 {', '.join(interesting_types[:3])}")

    def _add_service_options_info(self, place: Dict[str, Any], google_info: list) -> None:
        """Add service options information to google_info."""
        service_options = []
        if place.get("takeout"):
            service_options.append("Takeout")
        if place.get("delivery"):
            service_options.append("Delivery")
        if place.get("dineIn"):
            service_options.append("Dine-in")
        if place.get("reservable"):
            service_options.append("Reservations")
        if place.get("servesBreakfast"):
            service_options.append("Breakfast")
        if place.get("servesLunch"):
            service_options.append("Lunch")
        if place.get("servesDinner"):
            service_options.append("Dinner")
        if place.get("servesBrunch"):
            service_options.append("Brunch")
        if service_options:
            google_info.append(f"🍽️ {', '.join(service_options[:4])}")

    def _add_amenities_info(self, place: Dict[str, Any], google_info: list) -> None:
        """Add amenities information to google_info."""
        amenities = []
        if place.get("wheelchairAccessibleEntrance"):
            amenities.append("♿ Wheelchair Accessible")
        if place.get("outdoorSeating"):
            amenities.append("🌳 Outdoor Seating")
        if place.get("liveMusic"):
            amenities.append("🎵 Live Music")
        if place.get("goodForChildren"):
            amenities.append("👶 Family Friendly")
        if place.get("allowsDogs"):
            amenities.append("🐕 Dog Friendly")
        if amenities:
            google_info.append(f"🏪 {', '.join(amenities[:3])}")

    def _add_payment_info(self, place: Dict[str, Any], google_info: list) -> None:
        """Add payment options information to google_info."""
        payment_options = place.get("paymentOptions", {})
        if payment_options:
            payment_types = []
            if payment_options.get("acceptsCreditCards"):
                payment_types.append("💳 Credit Cards")
            if payment_options.get("acceptsDebitCards"):
                payment_types.append("💳 Debit Cards")
            if payment_options.get("acceptsCashOnly"):
                payment_types.append("💵 Cash Only")
            if payment_types:
                google_info.append(f"💳 {', '.join(payment_types)}")

    def generate_notes(self, place: Dict[str, Any]) -> Optional[str]:
        """Generate notes from Google Places data.

        Args:
            place: Google Places data

        Returns:
            Generated notes string or None
        """
        notes = []

        if place.get("price_level"):
            price_levels = {1: "Budget-friendly", 2: "Moderate pricing", 3: "Upscale", 4: "Premium"}
            notes.append(price_levels.get(place.get("price_level"), ""))

        return " | ".join(notes) if notes else None

    def _check_rate_limit(self):
        """Placeholder for rate limit enforcement."""
        # In a real application, you would track API calls and raise an exception
        # if a rate limit is exceeded. For now, it just returns False.
        return False


def get_google_places_service() -> GooglePlacesService:
    """Get a Google Places service instance.

    Returns:
        GooglePlacesService instance
    """
    return GooglePlacesService()
