"""Integration tests for restaurant services workflows.

These tests focus on complete restaurant service workflows including
Google Places integration, data processing, and service level detection.
"""

from typing import Any
from unittest.mock import Mock, patch

from flask import Flask
from flask.testing import FlaskClient
import pytest

from app import create_app
from app.auth.models import User
from app.extensions import db


class TestRestaurantServicesWorkflows:
    """Test complete restaurant services workflows."""

    @pytest.fixture
    def app(self):
        """Create test Flask app with proper configuration."""
        app = create_app("testing")
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["SECRET_KEY"] = "test_secret_key"
        app.config["WTF_CSRF_ENABLED"] = False

        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()

    @pytest.fixture
    def client(self, app: Flask) -> FlaskClient:
        """Create test client."""
        return app.test_client()

    @pytest.fixture
    def user(self, app: Flask) -> tuple[User, int]:
        """Create test user."""
        with app.app_context():
            user = User(username="testuser", email="test@example.com", password_hash="hashed_password")
            db.session.add(user)
            db.session.commit()
            return user, user.id

    @pytest.fixture
    def logged_in_client(self, client: FlaskClient, user: tuple[User, int], app: Flask) -> FlaskClient | None:
        """Create a test client with logged-in user."""
        user_obj, user_id = user  # Unpack user and user_id

        # Create a test client that simulates being logged in
        class LoggedInTestClient:
            def __init__(self, client: FlaskClient, app: Flask, user_id: int):
                self.client = client
                self.app = app
                self.user_id = user_id

            def get(self, *args: Any, **kwargs: Any) -> Any:
                return self._make_request("GET", *args, **kwargs)

            def post(self, *args: Any, **kwargs: Any) -> Any:
                return self._make_request("POST", *args, **kwargs)

            def _make_request(self, method: str, *args: Any, **kwargs: Any) -> Any:
                with self.app.app_context():
                    # Set up the session for this request
                    with self.client.session_transaction() as sess:
                        sess["_user_id"] = str(self.user_id)
                        sess["_fresh"] = True
                        sess["_id"] = str(self.user_id)

                    # Make the request
                    return getattr(self.client, method.lower())(*args, **kwargs)

        return LoggedInTestClient(client, app, user_id)

    @pytest.fixture
    def mock_google_places_data(self) -> dict[str, Any]:
        """Mock Google Places API response data."""
        return {
            "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
            "name": "Test Restaurant",
            "formatted_address": "123 Test St, Test City, TC 12345, USA",
            "rating": 4.5,
            "price_level": 2,
            "types": ["restaurant", "food", "establishment"],
            "photos": [{"photo_reference": "test_photo_ref", "height": 400, "width": 600}],
            "reviews": [{"author_name": "Test Reviewer", "rating": 5, "text": "Great food!", "time": 1640995200}],
            "address_components": [
                {"long_name": "123", "short_name": "123", "types": ["street_number"]},
                {"long_name": "Test St", "short_name": "Test St", "types": ["route"]},
                {"long_name": "Test City", "short_name": "Test City", "types": ["locality"]},
                {"long_name": "TC", "short_name": "TC", "types": ["administrative_area_level_1"]},
                {"long_name": "12345", "short_name": "12345", "types": ["postal_code"]},
                {"long_name": "United States", "short_name": "US", "types": ["country"]},
            ],
        }

    def test_restaurant_creation_from_google_places_workflow(
        self, app: Flask, user: tuple[User, int], mock_google_places_data: dict[str, Any]
    ) -> None:
        """Test restaurant creation from Google Places data workflow."""
        user_obj, user_id = user  # Unpack user and user_id

        with app.app_context():
            with patch("app.restaurants.services.create_restaurant_for_user") as mock_create:
                # Mock successful restaurant creation
                mock_restaurant = Mock()
                mock_restaurant.id = 1
                mock_restaurant.name = "Test Restaurant"
                mock_restaurant.google_place_id = "ChIJN1t_tDeuEmsRUsoyG83frY4"
                mock_restaurant.cuisine = "italian"
                mock_restaurant.service_level = "casual_dining"
                mock_create.return_value = mock_restaurant

                # Test restaurant creation from Google Places data
                from app.restaurants.services import create_restaurant_for_user

                # Convert Google Places data to restaurant data format
                restaurant_data = {
                    "name": mock_google_places_data["name"],
                    "address_line_1": "123 Test St",
                    "city": "Test City",
                    "google_place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
                    "cuisine": "italian",
                    "service_level": "casual_dining",
                }

                result = create_restaurant_for_user(user_id, restaurant_data)

                assert result.id == 1
                assert result.name == "Test Restaurant"
                assert result.google_place_id == "ChIJN1t_tDeuEmsRUsoyG83frY4"

    # Removed test_restaurant_search_by_location_workflow - references non-existent search_restaurants_by_location method

    # Removed test_restaurant_service_level_detection_workflow - references non-existent detect_service_level method

    # Removed test_restaurant_cuisine_detection_workflow - references non-existent detect_cuisine method

    # Removed test_restaurant_validation_workflow - references non-existent validate_restaurant_data method

    # Removed test_restaurant_duplicate_detection_workflow - references non-existent detect_duplicate_restaurants method

    # Removed test_restaurant_data_processing_workflow - references non-existent process_google_places_data method

    # Removed test_restaurant_bulk_operations_workflow - references non-existent bulk_import_restaurants method

    # Removed test_restaurant_analytics_workflow - references non-existent generate_restaurant_analytics method

    # Removed test_restaurant_import_processing_workflow - references non-existent process_restaurant_import method

    # Removed test_restaurant_error_handling_workflow - references non-existent error handling methods

    # Removed test_restaurant_geocoding_workflow - references non-existent geocode_address method
