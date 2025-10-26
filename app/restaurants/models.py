from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from flask import current_app
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, relationship

from app.extensions import db
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.auth.models import User
    from app.expenses.models import Expense


class Restaurant(BaseModel):
    """Restaurant model for tracking dining locations.

    Attributes:
        name: Name of the restaurant
        type: Type of cuisine or restaurant style
        description: Detailed description
        address: Street address
        city: City
        state: State/Province
        postal_code: ZIP/Postal code
        country: Country

        phone: Contact phone number
        website: Restaurant website URL
        email: Contact email
        cuisine: Type of cuisine
        is_chain: Whether it's a chain restaurant
        rating: User's personal rating (1.0-5.0)
        notes: Additional notes
    """

    __tablename__ = "restaurant"

    __table_args__ = (
        UniqueConstraint(
            "name",
            "city",
            "user_id",
            name="uix_restaurant_name_city_user",
            comment="Ensure unique restaurant per user by name and city",
        ),
        UniqueConstraint(
            "user_id",
            "google_place_id",
            name="uix_restaurant_google_place_id_user",
            comment="Ensure unique Google Place ID per user (excludes NULL values)",
        ),
        {"comment": "Restaurants where expenses were incurred"},
    )

    # Basic Information
    name: Mapped[str] = db.Column(db.String(100), nullable=False, comment="Name of the restaurant")
    type: Mapped[Optional[str]] = db.Column(db.String(50), comment="Type of cuisine or restaurant style")
    located_within: Mapped[Optional[str]] = db.Column(
        db.String(100), comment="Location within (e.g., mall, airport, hotel)"
    )
    description: Mapped[Optional[str]] = db.Column(db.Text, comment="Detailed description of the restaurant")

    # Location Information
    address_line_1: Mapped[Optional[str]] = db.Column(db.String(200), comment="Primary street address")
    address_line_2: Mapped[Optional[str]] = db.Column(
        db.String(200), comment="Secondary address (apartment/suite/unit)"
    )
    city: Mapped[Optional[str]] = db.Column(db.String(100), comment="City")
    state: Mapped[Optional[str]] = db.Column(db.String(100), comment="State/Province")
    postal_code: Mapped[Optional[str]] = db.Column(db.String(20), comment="ZIP/Postal code")
    country: Mapped[Optional[str]] = db.Column(db.String(100), comment="Country")

    # Contact Information
    phone: Mapped[Optional[str]] = db.Column(db.String(20), comment="Contact phone number")
    website: Mapped[Optional[str]] = db.Column(db.String(500), comment="Restaurant website URL")
    email: Mapped[Optional[str]] = db.Column(db.String(100), comment="Contact email")
    google_place_id: Mapped[Optional[str]] = db.Column(
        db.String(255), index=True, comment="Google Place ID for the restaurant"
    )

    # Business Details - User Customizable
    cuisine: Mapped[Optional[str]] = db.Column(db.String(100), index=True, comment="Type of cuisine")
    service_level: Mapped[Optional[str]] = db.Column(
        db.String(50),
        index=True,
        comment="Service level (fine_dining, casual_dining, fast_casual, quick_service)",
    )
    is_chain: Mapped[bool] = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
        comment="Whether it's a chain restaurant",
    )
    rating: Mapped[Optional[float]] = db.Column(db.Float, comment="User's personal rating (1.0-5.0)")
    price_level: Mapped[Optional[int]] = db.Column(
        db.Integer,
        comment="Price level from Google Places (0=Free, 1=$1-10, 2=$11-30, 3=$31-60, 4=$61+)",
    )
    primary_type: Mapped[Optional[str]] = db.Column(
        db.String(100),
        comment="Primary business type from Google Places API (e.g., restaurant, cafe, bar)",
    )
    latitude: Mapped[Optional[float]] = db.Column(db.Float, comment="Restaurant latitude coordinate")
    longitude: Mapped[Optional[float]] = db.Column(db.Float, comment="Restaurant longitude coordinate")
    notes: Mapped[Optional[str]] = db.Column(db.Text, comment="Additional notes")

    # Foreign Keys
    user_id: Mapped[int] = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the user who added this restaurant",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="restaurants", lazy="select")
    expenses: Mapped[List["Expense"]] = relationship(
        "Expense",
        back_populates="restaurant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def full_name(self) -> str:
        """Return the restaurant's full name including city if available.

        Returns:
            str: The restaurant name with city if available
        """
        if not self.city or not self.city.strip():
            return self.name
        return f"{self.name} - {self.city}"

    @property
    def address(self) -> Optional[str]:
        """Return the combined address lines (address_line_1 + address_line_2).

        Returns:
            Optional[str]: Combined address lines or None if no address components
        """
        parts: List[str] = []
        if self.address_line_1:
            parts.append(self.address_line_1)
        if self.address_line_2:
            parts.append(self.address_line_2)
        return ", ".join(parts) if parts else None

    @property
    def full_address(self) -> Optional[str]:
        """Return the restaurant's full address as a formatted string using US Standard format.

        Returns:
            Optional[str]: Formatted address string or None if no address components
        """
        parts: List[str] = []

        # Combine address lines with space (US Standard)
        address_lines = []
        if self.address_line_1:
            address_lines.append(self.address_line_1)
        if self.address_line_2:
            address_lines.append(self.address_line_2)
        if address_lines:
            parts.append(" ".join(address_lines))

        # Combine city and state with comma (US Standard)
        city_state = []
        if self.city:
            city_state.append(self.city)
        if self.state:
            city_state.append(self.state)
        if city_state:
            parts.append(", ".join(city_state))

        # Add postal code
        if self.postal_code:
            parts.append(self.postal_code)

        # Only add country if it's not United States (avoid redundancy for US addresses)
        if self.country and self.country.lower() not in ["united states", "usa", "us"]:
            parts.append(self.country)

        return " ".join(parts) if parts else None

    @property
    def google_search(self) -> Optional[str]:
        """Return a string suitable for a Google Maps search.

        Returns:
            Optional[str]: Search string for Google Maps or None if no location data
        """
        if not self.name:
            return None

        search_terms = [self.name]
        if self.city:
            search_terms.append(self.city)
        if self.state:
            search_terms.append(self.state)

        return ", ".join(search_terms)

    def get_google_maps_url(self) -> Optional[str]:
        """Return a Google Maps URL for this restaurant.

        Uses the best available method in order of preference (all API token-free):
        1. Google Maps URLs API with place_id (recommended format)
        2. Coordinate-based URL if coordinates are available
        3. Search-based URL with restaurant name and address

        Returns:
            Optional[str]: Google Maps URL or None if no location data is available
        """
        from urllib.parse import quote_plus

        # First preference: Use the improved place_id format with restaurant name
        if self.google_place_id:
            # Use the recommended Google Maps URLs API format with both query and place_id
            # This provides the most reliable link without API token usage
            restaurant_name = quote_plus(self.name)
            return f"https://www.google.com/maps/search/?api=1&query={restaurant_name}&query_place_id={self.google_place_id}"

        # Second preference: Use coordinates if available (would need to be stored or fetched)
        # Note: Coordinates would need to be added to the model or fetched dynamically
        # if hasattr(self, 'latitude') and hasattr(self, 'longitude') and self.latitude and self.longitude:
        #     return f"https://www.google.com/maps/search/?api=1&query={self.latitude},{self.longitude}"

        # Third preference: Use search-based URL with detailed address
        search_query = self._build_optimized_search_query()
        if search_query:
            return f"https://www.google.com/maps/search/?api=1&query={search_query}"

        return None

    def _build_optimized_search_query(self) -> Optional[str]:
        """Build an optimized search query for Google Maps.

        Creates a comprehensive search string that includes restaurant name, address,
        and location details to maximize the chance of finding the correct place.

        Returns:
            Optional[str]: URL-encoded search query or None if insufficient data
        """
        from urllib.parse import quote_plus

        search_parts = []

        # Always include restaurant name
        if self.name:
            search_parts.append(self.name)

        # Add address details in order of specificity
        if self.address_line_1:
            search_parts.append(self.address_line_1)
        elif self.city:
            # If no street address, at least include city
            search_parts.append(self.city)

        # Add city if not already included in address
        if self.city and self.address_line_1 and self.city.lower() not in self.address_line_1.lower():
            search_parts.append(self.city)

        # Add state for better disambiguation
        if self.state:
            search_parts.append(self.state)

        # Add postal code for precision
        if self.postal_code:
            search_parts.append(self.postal_code)

        # Join parts and URL encode
        if search_parts:
            search_query = ", ".join(search_parts)
            return quote_plus(search_query)

        return None

    def _update_contact_info(self, place_data: dict) -> None:
        """Update contact information from Google Places data.

        Args:
            place_data: Raw Google Places API response data
        """
        self.phone = place_data.get("formatted_phone_number", self.phone)
        self.website = place_data.get("website", self.website)

        # Update from international_phone_number if available
        if not self.phone and "international_phone_number" in place_data:
            self.phone = place_data["international_phone_number"]

    def _update_location_data(self, place_data: dict) -> None:
        """Update geographic location data.

        Args:
            place_data: Raw Google Places API response data
        """
        # Coordinates no longer stored - would be looked up dynamically from Google Places API

    def update_from_google_places(self, place_data: dict) -> None:
        """Update restaurant data from Google Places API response.

        Args:
            place_data: Dictionary containing Google Places API response data with structure:
                {
                    'place_id': str,
                    'name': str,
                    'formatted_address': str,
                    'address_components': List[Dict],
                    'formatted_phone_number': str,
                    'international_phone_number': str,
                    'website': str,
                    'geometry': {'location': {'lat': float, 'lng': float}},
                    'business_status': str,

                    'rating': float,
                    'opening_hours': dict,
                    'photos': list,
                    'url': str
                }

        Example:
            place_data = {
                'place_id': 'ChIJN1t_tDeuEmsRUsoyG83frY4',
                'name': 'Google',
                'formatted_address': '1600 Amphitheatre Pkwy, Mountain View, CA 94043, USA',
                'address_components': [...],
                'formatted_phone_number': '(650) 253-0000',
                'website': 'https://about.google/',
                'geometry': {'location': {'lat': 37.422, 'lng': -122.084}},
                'business_status': 'OPERATIONAL',

                'rating': 4.5
            }
        """
        if not place_data or not isinstance(place_data, dict):
            current_app.logger.warning("Invalid place_data provided to update_from_google_places")
            return

        try:
            # Update basic information
            self.google_place_id = place_data.get("place_id", self.google_place_id)
            self.name = place_data.get("name", self.name)

            # Update address components using centralized service
            if "addressComponents" in place_data:
                from app.services.google_places_service import get_google_places_service

                places_service = get_google_places_service()

                # Parse address components using centralized service
                address_data = places_service.parse_address_components(place_data["addressComponents"])

                # Update address fields with standardized field names
                self.address_line_1 = address_data.get("address_line_1", self.address_line_1)
                self.address_line_2 = address_data.get("address_line_2", self.address_line_2)
                self.city = address_data.get("city", self.city)
                self.state = address_data.get("state", self.state)
                self.postal_code = address_data.get("postal_code", self.postal_code)
                self.country = address_data.get("country", self.country)

            # Update from formatted address if available and no address was set
            if "formatted_address" in place_data and not self.address_line_1:
                self.address_line_1 = place_data["formatted_address"]

            # Update contact information
            self._update_contact_info(place_data)

            # Update location data (includes geometry)
            self._update_location_data(place_data)

            # Update additional fields
            self._update_additional_fields(place_data)

        except Exception as e:
            current_app.logger.error(f"Error updating restaurant from Google Places: {str(e)}")
            raise

    def _update_additional_fields(self, place_data: dict) -> None:
        """Update additional fields from Google Places data.

        Args:
            place_data: Raw Google Places API response data
        """
        # Note: business_status is time-sensitive and not stored permanently
        # Note: rating is now user's personal rating, not from Google Places

        self._update_price_level(place_data)
        self._update_primary_type(place_data)
        self._update_coordinates(place_data)
        self._update_website_fallback(place_data)
        self._update_service_level_and_cuisine(place_data)
        self._store_raw_place_data(place_data)

    def _update_price_level(self, place_data: dict) -> None:
        """Update price level from Google Places data.

        Args:
            place_data: Raw Google Places API response data
        """
        if "price_level" in place_data:
            self.price_level = place_data["price_level"]
        elif "priceLevel" in place_data:
            self.price_level = self._convert_price_level(place_data["priceLevel"])

    def _convert_price_level(self, price_level: Any) -> int:
        """Convert price level to integer format using centralized service.

        Args:
            price_level: Price level value from Google Places API

        Returns:
            int: Converted price level (0-4)
        """
        from app.services.google_places_service import get_google_places_service

        places_service = get_google_places_service()
        converted = places_service.convert_price_level_to_int(price_level)
        return converted if converted is not None else 0

    def _update_primary_type(self, place_data: dict) -> None:
        """Update primary type from Google Places data.

        Args:
            place_data: Raw Google Places API response data
        """
        if "primary_type" in place_data:
            self.primary_type = place_data["primary_type"]
        elif "primaryType" in place_data:
            self.primary_type = place_data["primaryType"]

    def _update_coordinates(self, place_data: dict) -> None:
        """Update coordinates from Google Places data.

        Args:
            place_data: Raw Google Places API response data
        """
        # Try legacy API geometry format first
        if "geometry" in place_data and place_data["geometry"]:
            self._update_coordinates_from_geometry(place_data["geometry"])
        # Try new API location format
        elif "location" in place_data and place_data["location"]:
            self._update_coordinates_from_location(place_data["location"])

    def _update_coordinates_from_geometry(self, geometry: dict) -> None:
        """Update coordinates from legacy API geometry format.

        Args:
            geometry: Geometry data from Google Places API
        """
        if "location" in geometry:
            location = geometry["location"]
            if "lat" in location:
                self.latitude = location["lat"]
            if "lng" in location:
                self.longitude = location["lng"]

    def _update_coordinates_from_location(self, location: dict) -> None:
        """Update coordinates from new API location format.

        Args:
            location: Location data from Google Places API
        """
        if "latitude" in location:
            self.latitude = location["latitude"]
        if "longitude" in location:
            self.longitude = location["longitude"]

    def _update_website_fallback(self, place_data: dict) -> None:
        """Update website as fallback if not already set.

        Args:
            place_data: Raw Google Places API response data
        """
        if not self.website and "website" in place_data:
            self.website = place_data["website"]

    def _store_raw_place_data(self, place_data: dict) -> None:
        """Store raw place data for reference.

        Args:
            place_data: Raw Google Places API response data
        """
        if hasattr(self, "place_data"):
            self.place_data = place_data

    def _update_service_level_and_cuisine(self, place_data: dict) -> None:
        """Update service level and cuisine from Google Places data.

        Args:
            place_data: Raw Google Places API response data
        """
        try:
            from flask import current_app

            from app.services.google_places_service import get_google_places_service

            # Get types from place data
            types = place_data.get("types", [])
            if not types:
                current_app.logger.info("No types found in place data, skipping classification")
                return

            # Use centralized service for restaurant type analysis
            places_service = get_google_places_service()
            cuisine, service_level = places_service.analyze_restaurant_types(types, place_data)

            # Update the restaurant fields if we detected values
            if cuisine:
                self.cuisine = cuisine
                current_app.logger.info(f"Updated cuisine to: {cuisine}")

            if service_level:
                self.service_level = service_level
                current_app.logger.info(f"Updated service level to: {service_level}")

        except Exception as e:
            current_app.logger.error(f"Error updating service level and cuisine: {str(e)}")
            # Don't raise - this is not critical enough to fail the entire update

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation of the restaurant.

        Returns:
            Dict containing the restaurant data
        """
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "located_within": self.located_within,
            "description": self.description,
            "address_line_1": self.address_line_1,
            "address_line_2": self.address_line_2,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "phone": self.phone,
            "website": self.website,
            "email": self.email,
            "cuisine": self.cuisine,
            "service_level": self.service_level,
            "is_chain": self.is_chain,
            "rating": self.rating,
            "price_level": self.price_level,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<Restaurant {self.name}>"
