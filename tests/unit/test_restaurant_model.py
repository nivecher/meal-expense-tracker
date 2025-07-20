"""Unit tests for the Restaurant model."""

import pytest

from app import create_app
from app.extensions import db
from app.restaurants.models import Restaurant


@pytest.fixture(scope="module")
def app():
    """Create and configure a new app instance for testing."""
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


class TestRestaurantModel:
    """Test cases for the Restaurant model."""

    def test_update_from_google_places_complete_data(self, app):
        """Test updating a restaurant with complete Google Places data."""
        with app.app_context():
            # Create test restaurant
            restaurant = Restaurant(name="Test Restaurant")
            db.session.add(restaurant)
            db.session.commit()

            # Mock Google Places data
            place_data = {
                "place_id": "test123",
                "name": "Updated Name",
                "formatted_address": "123 Main St, City, ST 12345, USA",
                "address_components": [
                    {"types": ["street_number"], "long_name": "123"},
                    {"types": ["route"], "long_name": "Main St"},
                    {"types": ["locality"], "long_name": "City"},
                    {"types": ["administrative_area_level_1"], "short_name": "ST"},
                    {"types": ["postal_code"], "long_name": "12345"},
                    {"types": ["country"], "long_name": "United States"},
                ],
                "formatted_phone_number": "+1 (123) 456-7890",
                "international_phone_number": "+11234567890",
                "website": "https://example.com",
                "geometry": {"location": {"lat": 40.7128, "lng": -74.0060}},
                "business_status": "OPERATIONAL",
                "price_level": 2,
                "rating": 4.5,
                "url": "https://maps.google.com/?cid=1234567890",
            }

            # Update restaurant
            restaurant.update_from_google_places(place_data)
            db.session.commit()

            # Verify updates
            assert restaurant.google_place_id == "test123"
            assert restaurant.name == "Updated Name"
            assert "123 Main St" in restaurant.address
            assert restaurant.city == "City"
            assert restaurant.state == "ST"
            assert restaurant.postal_code == "12345"
            assert restaurant.country == "United States"
            assert restaurant.phone == "+1 (123) 456-7890"
            assert restaurant.website == "https://example.com"
            assert restaurant.latitude == 40.7128
            assert restaurant.longitude == -74.0060
            assert restaurant.business_status == "OPERATIONAL"
            assert restaurant.price_range == 3  # 2 + 1
            assert restaurant.rating == 4.5

    def test_update_from_google_places_partial_data(self, app):
        """Test updating a restaurant with partial Google Places data."""
        with app.app_context():
            # Create test restaurant with existing data
            restaurant = Restaurant(name="Existing Name", address="456 Oak St", city="Old City", phone="+1987654321")
            db.session.add(restaurant)
            db.session.commit()

            # Partial update with only some fields
            place_data = {"place_id": "partial123", "name": "New Name", "formatted_phone_number": "+1122334455"}

            restaurant.update_from_google_places(place_data)
            db.session.commit()

            # Verify only specified fields were updated
            assert restaurant.google_place_id == "partial123"
            assert restaurant.name == "New Name"
            assert restaurant.phone == "+1122334455"
            # These should remain unchanged
            assert restaurant.address == "456 Oak St"
            assert restaurant.city == "Old City"

    def test_update_from_google_places_invalid_data(self, app):
        """Test updating with invalid or empty data."""
        with app.app_context():
            restaurant = Restaurant(name="Test")
            db.session.add(restaurant)
            db.session.commit()

            # Test with None
            restaurant.update_from_google_places(None)
            assert restaurant.name == "Test"  # Should remain unchanged

            # Test with empty dict
            restaurant.update_from_google_places({})
            assert restaurant.name == "Test"  # Should remain unchanged

            # Test with invalid type
            restaurant.update_from_google_places("not a dict")
            assert restaurant.name == "Test"  # Should remain unchanged

    def test_google_maps_url(self, app):
        """Test generating Google Maps URL."""
        with app.app_context():
            # Test with place ID
            restaurant = Restaurant(google_place_id="test123")
            assert "place_id=test123" in restaurant.google_maps_url

            # Test with address
            restaurant = Restaurant(address="123 Main St", city="Test City", state="TS", country="Testland")
            url = restaurant.google_maps_url
            assert "123+Main+St" in url
            assert "Test+City" in url
            assert "TS" in url
            assert "Testland" in url

            # Test with insufficient data
            restaurant = Restaurant()
            assert restaurant.google_maps_url is None

    def test_update_address_components(self, app):
        """Test the _update_address_components method."""
        with app.app_context():
            restaurant = Restaurant()
            address_components = [
                {"types": ["street_number"], "long_name": "123"},
                {"types": ["route"], "long_name": "Main St"},
                {"types": ["locality"], "long_name": "Test City"},
                {"types": ["administrative_area_level_1"], "short_name": "TS"},
                {"types": ["postal_code"], "long_name": "12345"},
                {"types": ["country"], "long_name": "Testland"},
            ]

            restaurant._update_address_components(address_components)

            assert restaurant.address == "123 Main St"
            assert restaurant.city == "Test City"
            assert restaurant.state == "TS"
            assert restaurant.postal_code == "12345"
            assert restaurant.country == "Testland"

    def test_update_contact_info(self, app):
        """Test the _update_contact_info method."""
        with app.app_context():
            restaurant = Restaurant()
            place_data = {
                "formatted_phone_number": "+1 (123) 456-7890",
                "international_phone_number": "+11234567890",
                "website": "https://example.com",
            }

            restaurant._update_contact_info(place_data)

            assert restaurant.phone == "+1 (123) 456-7890"
            assert restaurant.website == "https://example.com"

            # Test with only international number
            restaurant.phone = None
            place_data.pop("formatted_phone_number")
            restaurant._update_contact_info(place_data)
            assert restaurant.phone == "+11234567890"

    def test_update_location_data(self, app):
        """Test the _update_location_data method."""
        with app.app_context():
            restaurant = Restaurant()
            place_data = {"geometry": {"location": {"lat": 40.7128, "lng": -74.0060}}}

            restaurant._update_location_data(place_data)

            assert restaurant.latitude == 40.7128
            assert restaurant.longitude == -74.0060

            # Test with missing location data
            restaurant.latitude = None
            restaurant.longitude = None
            restaurant._update_location_data({})
            assert restaurant.latitude is None
            assert restaurant.longitude is None
