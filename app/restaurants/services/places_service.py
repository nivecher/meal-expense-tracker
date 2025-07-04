"""Service for handling Google Places API integration."""

from datetime import datetime
from typing import Dict, Optional, Any
import requests
from flask import current_app
from ...extensions import db
from ..models import Restaurant


class PlacesService:
    """Service for interacting with Google Places API."""

    BASE_URL = "https://maps.googleapis.com/maps/api/place"
    DETAILS_FIELDS = [
        "name",
        "formatted_address",
        "formatted_phone_number",
        "website",
        "rating",
        "price_level",
        "types",
        "opening_hours",
        "geometry/location",
        "address_components",
        "international_phone_number",
    ]

    def __init__(self, api_key: str):
        """Initialize the PlacesService with an API key.

        Args:
            api_key: Google Places API key
        """
        self.api_key = api_key
        self.session = requests.Session()

    def get_place_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a place.

        Args:
            place_id: Google Place ID

        Returns:
            Dictionary containing place details or None if not found
        """
        if not place_id:
            return None

        try:
            url = f"{self.BASE_URL}/details/json"
            params = {"place_id": place_id, "fields": ",".join(self.DETAILS_FIELDS), "key": self.api_key}

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "OK":
                current_app.logger.error("Google Places API error: %s", data.get("error_message", "Unknown error"))
                return None

            return data.get("result")

        except requests.RequestException as e:
            current_app.logger.error("Failed to fetch place details: %s", str(e))
            return None

    def sync_restaurant_from_google(self, restaurant: Restaurant) -> bool:
        """Sync restaurant data from Google Places.

        Args:
            restaurant: Restaurant instance to update

        Returns:
            bool: True if sync was successful, False otherwise
        """
        if not restaurant.google_place_id:
            return False

        place_data = self.get_place_details(restaurant.google_place_id)
        if not place_data:
            return False

        try:
            # Update basic information
            restaurant.name = place_data.get("name", restaurant.name)
            restaurant.place_name = place_data.get("name")

            # Update address components
            self._update_address_components(restaurant, place_data.get("address_components", []))

            # Update contact information
            restaurant.phone = place_data.get("formatted_phone_number") or restaurant.phone
            restaurant.website = place_data.get("website") or restaurant.website

            # Update business details
            restaurant.rating = place_data.get("rating", restaurant.rating)
            restaurant.price_range = place_data.get("price_level", restaurant.price_range)

            # Update location
            if "geometry" in place_data and "location" in place_data["geometry"]:
                loc = place_data["geometry"]["location"]
                restaurant.latitude = loc.get("lat")
                restaurant.longitude = loc.get("lng")

            # Update cuisine from types
            if "types" in place_data:
                restaurant.type = self._get_best_type_match(place_data["types"])

            restaurant.last_synced_at = datetime.utcnow()

            db.session.commit()
            return True

        except Exception as e:
            db.session.rollback()
            current_app.logger.error("Failed to sync restaurant data: %s", str(e))
            return False

    @staticmethod
    def _update_address_components(restaurant: Restaurant, components: list) -> None:
        """Update restaurant address fields from Google address components."""
        for component in components:
            types = component.get("types", [])
            long_name = component.get("long_name", "")
            short_name = component.get("short_name", "")

            if "street_number" in types:
                restaurant.address = long_name
            elif "route" in types:
                if restaurant.address:
                    restaurant.address += f" {long_name}"
                else:
                    restaurant.address = long_name
            elif "locality" in types:
                restaurant.city = long_name
            elif "administrative_area_level_1" in types:
                restaurant.state = short_name
            elif "postal_code" in types:
                restaurant.postal_code = long_name
            elif "country" in types:
                restaurant.country = long_name

    @staticmethod
    def _get_best_type_match(types: list) -> Optional[str]:
        """Get the most relevant type from Google Places types."""
        # Map Google types to our types
        type_mapping = {
            "restaurant": "restaurant",
            "cafe": "cafe",
            "bar": "bar",
            "bakery": "bakery",
            "meal_takeaway": "takeout",
            "meal_delivery": "delivery",
        }

        # Check for exact matches first
        for t in types:
            if t in type_mapping:
                return type_mapping[t]

        # Check for partial matches
        for t in types:
            for key, value in type_mapping.items():
                if key in t:
                    return value

        return None
