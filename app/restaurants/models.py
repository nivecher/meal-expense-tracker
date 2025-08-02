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
        latitude: Geographic latitude
        longitude: Geographic longitude
        phone: Contact phone number
        website: Restaurant website URL
        email: Contact email
        price_range: Price range (1-5)
        cuisine: Type of cuisine
        is_chain: Whether it's a chain restaurant
        rating: Average rating (1-5)
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
        {"comment": "Restaurants where expenses were incurred"},
    )

    # Basic Information
    name: Mapped[str] = db.Column(db.String(100), nullable=False, comment="Name of the restaurant")
    type: Mapped[Optional[str]] = db.Column(db.String(50), comment="Type of cuisine or restaurant style")
    description: Mapped[Optional[str]] = db.Column(db.Text, comment="Detailed description of the restaurant")

    # Location Information
    address: Mapped[Optional[str]] = db.Column(db.String(200), comment="Street address")
    city: Mapped[Optional[str]] = db.Column(db.String(100), comment="City")
    state: Mapped[Optional[str]] = db.Column(db.String(100), comment="State/Province")
    postal_code: Mapped[Optional[str]] = db.Column(db.String(20), comment="ZIP/Postal code")
    country: Mapped[Optional[str]] = db.Column(db.String(100), comment="Country")
    latitude: Mapped[Optional[float]] = db.Column(db.Float, comment="Geographic latitude")
    longitude: Mapped[Optional[float]] = db.Column(db.Float, comment="Geographic longitude")

    # Contact Information
    phone: Mapped[Optional[str]] = db.Column(db.String(20), comment="Contact phone number")
    website: Mapped[Optional[str]] = db.Column(db.String(200), comment="Restaurant website URL")
    email: Mapped[Optional[str]] = db.Column(db.String(100), comment="Contact email")
    google_place_id: Mapped[Optional[str]] = db.Column(
        db.String(255), index=True, comment="Google Place ID for the restaurant"
    )

    # Business Details
    price_range: Mapped[Optional[int]] = db.Column(db.SmallInteger, comment="Price range (1-5)")
    cuisine: Mapped[Optional[str]] = db.Column(db.String(100), index=True, comment="Type of cuisine")
    is_chain: Mapped[bool] = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
        comment="Whether it's a chain restaurant",
    )
    rating: Mapped[Optional[float]] = db.Column(db.Float, comment="Average rating (1-5)")
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
    user: Mapped["User"] = relationship("User", back_populates="restaurants", lazy="joined")
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
    def full_address(self) -> Optional[str]:
        """Return the restaurant's full address as a formatted string.

        Returns:
            Optional[str]: Formatted address string or None if no address components
        """
        parts: List[str] = []
        if self.address:
            parts.append(self.address)
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.postal_code:
            parts.append(self.postal_code)
        if self.country:
            parts.append(self.country)
        return ", ".join(parts) if parts else None

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

        Returns:
            Optional[str]: Google Maps URL or None if no location data is available
        """
        if self.google_place_id:
            return f"https://www.google.com/maps/place/?q=place_id:{self.google_place_id}"
        elif self.latitude is not None and self.longitude is not None:
            return f"https://www.google.com/maps/search/?api=1&query={self.latitude},{self.longitude}"
        else:
            search_query = self.google_search
            if search_query:
                return f"https://www.google.com/maps/search/?api=1&query={search_query}"
        return None

    def _update_address_components(self, address_components: list[dict]) -> None:
        """Update address-related fields from Google Places address components.

        Args:
            address_components: List of address component dictionaries from Google Places
        """
        for component in address_components:
            types = component.get("types", [])
            component_type_handlers = {
                "street_number": lambda c: self._update_street_address(c, "long_name", prepend=True),
                "route": lambda c: self._update_street_address(c, "long_name"),
                "locality": lambda c: setattr(self, "city", c.get("long_name", self.city)),
                "administrative_area_level_1": lambda c: setattr(self, "state", c.get("short_name", self.state)),
                "postal_code": lambda c: setattr(self, "postal_code", c.get("long_name", self.postal_code)),
                "country": lambda c: setattr(self, "country", c.get("long_name", self.country)),
            }

            for address_type, handler in component_type_handlers.items():
                if address_type in types:
                    handler(component)
                    break

    def _update_street_address(self, component: dict, name_attr: str, prepend: bool = False) -> None:
        """Update the street address component.

        Args:
            component: Address component dictionary
            name_attr: Attribute name to get from component ('short_name' or 'long_name')
            prepend: Whether to prepend (True) or append (False) the component to existing address
        """
        value = component.get(name_attr, "")
        if not value:
            return

        if prepend:
            self.address = f"{value} {self.address or ''}".strip()
        else:
            self.address = f"{self.address or ''} {value}".strip()

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
        if "geometry" in place_data and "location" in place_data["geometry"]:
            location = place_data["geometry"]["location"]
            self.latitude = location.get("lat", self.latitude)
            self.longitude = location.get("lng", self.longitude)

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
                    'price_level': int (0-4),
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
                'price_level': 2,
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

            # Update address components if available
            if "address_components" in place_data:
                self._update_address_components(place_data["address_components"])

            # Update from formatted address if available and no address was set
            if "formatted_address" in place_data and not self.address:
                self.address = place_data["formatted_address"]

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
        # Business status
        if "business_status" in place_data:
            self.business_status = place_data["business_status"]

        # Price level (convert Google's 0-4 to our 1-5 scale)
        price_level = place_data.get("price_level")
        if price_level is not None:
            self.price_range = min(5, max(1, price_level + 1))

        # Rating
        if "rating" in place_data:
            self.rating = place_data["rating"]

        # Website (as fallback if not set in _update_contact_info)
        if not self.website and "website" in place_data:
            self.website = place_data["website"]

        # Store raw place data for reference
        if hasattr(self, "place_data"):
            self.place_data = place_data

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation of the restaurant.

        Returns:
            Dict containing the restaurant data
        """
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "address": self.address,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "latitude": float(self.latitude) if self.latitude is not None else None,
            "longitude": float(self.longitude) if self.longitude is not None else None,
            "phone": self.phone,
            "website": self.website,
            "email": self.email,
            "price_range": self.price_range,
            "cuisine": self.cuisine,
            "is_chain": self.is_chain,
            "rating": self.rating,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def __repr__(self) -> str:
        return f"<Restaurant {self.name}>"
