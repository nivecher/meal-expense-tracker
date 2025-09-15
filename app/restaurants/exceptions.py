"""Custom exceptions for restaurant operations."""

from typing import Optional

from app.restaurants.models import Restaurant


class RestaurantValidationError(Exception):
    """Base exception for restaurant validation errors."""

    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


class DuplicateGooglePlaceIdError(RestaurantValidationError):
    """Raised when attempting to create a restaurant with a duplicate Google Place ID."""

    def __init__(self, google_place_id: str, existing_restaurant: Restaurant):
        self.google_place_id = google_place_id
        self.existing_restaurant = existing_restaurant

        # Create message that clearly identifies the real conflict (Google Place ID)
        location_str = (
            f"{existing_restaurant.city}, {existing_restaurant.state}"
            if existing_restaurant.city and existing_restaurant.state
            else existing_restaurant.city or "unknown location"
        )
        # Keep user-facing text clean: emphasize name and location, omit Google ID
        message = f"A restaurant already exists: '{existing_restaurant.name}' — {location_str}"

        super().__init__(message, field="google_place_id")

    def to_dict(self) -> dict:
        """Convert exception to dictionary for API responses."""
        return {
            "code": "DUPLICATE_GOOGLE_PLACE_ID",
            "message": self.message,
            "field": self.field,
            "google_place_id": self.google_place_id,
            "existing_restaurant": {
                "id": self.existing_restaurant.id,
                "name": self.existing_restaurant.name,
                "city": self.existing_restaurant.city,
                "full_name": self.existing_restaurant.full_name,
            },
        }


class DuplicateRestaurantError(RestaurantValidationError):
    """Raised when attempting to create a restaurant that already exists by name/city."""

    def __init__(self, name: str, city: Optional[str], existing_restaurant: Restaurant):
        self.name = name
        self.city = city
        self.existing_restaurant = existing_restaurant

        # Create user-friendly message with restaurant name and location
        location_str = (
            f"{existing_restaurant.city}, {existing_restaurant.state}"
            if existing_restaurant.city and existing_restaurant.state
            else existing_restaurant.city or "unknown location"
        )
        message = f"A restaurant named '{name}' in {location_str} already exists"

        super().__init__(message, field="name")

    def to_dict(self) -> dict:
        """Convert exception to dictionary for API responses."""
        return {
            "code": "DUPLICATE_RESTAURANT",
            "message": self.message,
            "field": self.field,
            "name": self.name,
            "city": self.city,
            "existing_restaurant": {
                "id": self.existing_restaurant.id,
                "name": self.existing_restaurant.name,
                "city": self.existing_restaurant.city,
                "full_name": self.existing_restaurant.full_name,
            },
        }


class RestaurantNotFoundError(Exception):
    """Raised when a requested restaurant is not found."""

    def __init__(self, restaurant_id: Optional[int] = None, google_place_id: Optional[str] = None):
        self.restaurant_id = restaurant_id
        self.google_place_id = google_place_id

        if restaurant_id:
            message = f"Restaurant with ID {restaurant_id} not found"
        elif google_place_id:
            message = f"Restaurant with Google Place ID '{google_place_id}' not found"
        else:
            message = "Restaurant not found"

        super().__init__(message)
