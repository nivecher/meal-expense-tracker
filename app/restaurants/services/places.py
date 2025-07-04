"""Service for interacting with Google Places API."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import requests
from flask import current_app
from werkzeug.exceptions import BadRequest, ServiceUnavailable

from app.utils.ssm import get_parameter_from_env


class PlacesService:
    """Service class for Google Places API interactions."""

    def __init__(self, api_key: str):
        """Initialize the PlacesService with an API key.

        Args:
            api_key: Google Places API key
        """
        self.api_key = api_key
        self.base_url = "https://maps.googleapis.com/maps/api/place"
        self.search_cache: Dict[str, dict] = {}

    def search_places(
        self,
        lat: float,
        lng: float,
        radius: int = 1000,
        keyword: Optional[str] = None,
        page_token: Optional[str] = None,
    ) -> Dict[str, Union[List[Dict], str]]:
        """Search for places using Google Places API.

        Args:
            lat: Latitude of the search location
            lng: Longitude of the search location
            radius: Search radius in meters (max 50000)
            keyword: Optional search term
            page_token: Token for pagination

        Returns:
            Dictionary containing search results or error message

        Raises:
            BadRequest: If required parameters are missing or invalid
            ServiceUnavailable: If there's an error with the API request
        """
        if not all([lat, lng]):
            raise BadRequest("Latitude and longitude are required")

        cache_key = f"search_{lat}_{lng}_{radius}_{keyword}_{page_token}"
        cached_data = self.search_cache.get(cache_key)

        if cached_data and cached_data["expires"] > datetime.now():
            return cached_data["data"]

        params = {
            "location": f"{lat},{lng}",
            "radius": min(radius, 50000),
            "key": self.api_key,
            "type": "restaurant",
        }

        if keyword:
            params["keyword"] = keyword
        if page_token:
            params["pagetoken"] = page_token

        try:
            response = requests.get(f"{self.base_url}/nearbysearch/json", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("status") not in ("OK", "ZERO_RESULTS"):
                current_app.logger.error("Google Places API error: %s", data.get("error_message", "Unknown error"))
                return {"error": data.get("error_message", "Error searching places")}

            # Cache successful responses
            self.search_cache[cache_key] = {
                "data": data.get("results", []),
                "expires": datetime.now() + timedelta(minutes=30),
            }

            return data.get("results", [])

        except requests.RequestException as e:
            current_app.logger.error("Places API request failed: %s", str(e))
            raise ServiceUnavailable("Failed to connect to places service")

    def get_place_details(self, place_id: str) -> Dict:
        """Get detailed information about a specific place.

        Args:
            place_id: Google Place ID

        Returns:
            Dictionary containing place details

        Raises:
            BadRequest: If place_id is not provided
            ServiceUnavailable: If there's an error with the API request
        """
        if not place_id:
            raise BadRequest("Place ID is required")

        cache_key = f"place_details_{place_id}"
        cached_data = self.search_cache.get(cache_key)

        if cached_data and cached_data["expires"] > datetime.now():
            return cached_data["data"]

        fields = [
            "name",
            "formatted_address",
            "formatted_phone_number",
            "opening_hours",
            "website",
            "price_level",
            "rating",
            "user_ratings_total",
            "photos",
            "geometry",
        ]

        try:
            response = requests.get(
                f"{self.base_url}/details/json",
                params={"place_id": place_id, "fields": ",".join(fields), "key": self.api_key},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "OK":
                current_app.logger.error("Google Places API error: %s", data.get("error_message", "Unknown error"))
                return {"error": data.get("error_message", "Error fetching place details")}

            # Cache successful responses for longer (24 hours)
            self.search_cache[cache_key] = {
                "data": data.get("result", {}),
                "expires": datetime.now() + timedelta(hours=24),
            }

            return data.get("result", {})

        except requests.RequestException as e:
            current_app.logger.error("Places API details request failed: %s", str(e))
            raise ServiceUnavailable("Failed to fetch place details")


def init_places_service(app) -> PlacesService:
    """Initialize and return a PlacesService instance.

    Args:
        app: Flask application instance

    Returns:
        Configured PlacesService instance

    Raises:
        ValueError: If the Google Maps API key is not configured
    """
    try:
        # Get the API key from environment variable or SSM
        api_key = get_parameter_from_env("GOOGLE_MAPS_API_KEY", default=app.config.get("GOOGLE_MAPS_API_KEY", ""))

        if not api_key:
            app.logger.warning("Google Maps API key not configured")
            # Return a service instance with an empty key - calls will fail with a clear error
            return PlacesService("")

        return PlacesService(api_key)
    except Exception as e:
        app.logger.error("Failed to initialize PlacesService: %s", str(e))
        # In production, we might want to return a dummy service that fails gracefully
        if app.config.get("FLASK_ENV") == "production":
            return PlacesService("")
        raise
