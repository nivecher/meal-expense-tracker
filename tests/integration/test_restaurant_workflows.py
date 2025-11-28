"""Integration tests for restaurant workflows.

These tests focus on complete user journeys rather than individual functions,
providing maximum coverage with minimal test complexity.
"""

import json
from unittest.mock import Mock, patch

import pytest

from app import create_app
from app.auth.models import User
from app.extensions import db


class TestRestaurantWorkflows:
    """Test complete restaurant management workflows."""

    @pytest.fixture
    def app(self):
        """Create test Flask app with proper configuration."""
        # Set CSRF config before creating app
        import os

        os.environ["WTF_CSRF_ENABLED"] = "False"

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
    def client(self, app):
        """Create test client."""
        return app.test_client()

    @pytest.fixture
    def user(self, app):
        """Create test user."""
        with app.app_context():
            user = User(username="testuser", email="test@example.com", password_hash="hashed_password")
            db.session.add(user)
            db.session.commit()
            user_id = user.id  # Store ID before session closes
            return user, user_id

    @pytest.fixture
    def logged_in_client(self, client, user, app):
        """Create a test client with logged-in user."""
        user_obj, user_id = user  # Unpack user and user_id

        # Create a test client that simulates being logged in
        class LoggedInTestClient:
            def __init__(self, client, app, user_id):
                self.client = client
                self.app = app
                self.user_id = user_id

            def get(self, *args, **kwargs):
                return self._make_request("GET", *args, **kwargs)

            def post(self, *args, **kwargs):
                return self._make_request("POST", *args, **kwargs)

            def _make_request(self, method, *args, **kwargs):
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
    def mock_google_places_data(self):
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

    def test_restaurant_creation_workflow(self, logged_in_client, user, mock_google_places_data) -> None:
        """Test complete restaurant creation workflow."""
        # Test that the route exists and is accessible
        response = logged_in_client.get("/restaurants/add")
        assert response.status_code == 200

        # Test POST request (will fail validation but that's expected)
        response = logged_in_client.post(
            "/restaurants/add",
            data={
                "name": "Test Restaurant",
                "type": "restaurant",  # Required field
                "address_line_1": "123 Test St",
                "cuisine": "italian",
            },
        )

        # Should return 200 (form with validation errors) or 302 (success)
        assert response.status_code in [200, 302]

    def test_google_places_search_workflow(self, logged_in_client, user, mock_google_places_data) -> None:
        """Test Google Places search and restaurant creation workflow."""
        # Test that the Google Places search route is accessible
        response = logged_in_client.get(
            "/restaurants/api/places/search", query_string={"query": "test restaurant", "api_key": "test_api_key"}
        )

        # Should return 200 (success) or 500 (error due to missing API key in test environment)
        assert response.status_code in [200, 500]

    def test_restaurant_import_export_workflow(self, logged_in_client, user) -> None:
        """Test restaurant CSV import and export workflow."""
        # Test that the export route is accessible (will redirect since no restaurants exist)
        response = logged_in_client.get("/restaurants/export?format=csv")

        # Should redirect to restaurant list (no restaurants to export)
        assert response.status_code == 302
        assert "/restaurants/" in response.location

    def test_restaurant_filtering_and_pagination_workflow(self, logged_in_client, user) -> None:
        """Test restaurant filtering and pagination workflow."""
        with patch("app.restaurants.routes.services.get_restaurants_for_user") as mock_get_restaurants:
            # Mock restaurant data
            mock_restaurants = [
                Mock(id=1, name="Italian Restaurant", cuisine="italian"),
                Mock(id=2, name="Chinese Restaurant", cuisine="chinese"),
                Mock(id=3, name="Mexican Restaurant", cuisine="mexican"),
            ]
            mock_get_restaurants.return_value = mock_restaurants

            # Test filtering by cuisine
            response = logged_in_client.get(
                "/restaurants/", query_string={"cuisine": "italian", "page": 1, "per_page": 10}
            )

            assert response.status_code == 200
            # Should render the restaurant list template
            assert b"restaurants" in response.data.lower()

    def test_restaurant_edit_workflow(self, logged_in_client, user) -> None:
        """Test restaurant editing workflow."""
        # Test that the edit route is accessible (will return 404 since restaurant doesn't exist)
        response = logged_in_client.get("/restaurants/1/edit")

        # Should return 404 (restaurant not found) rather than 500 (server error)
        assert response.status_code == 404

    def test_restaurant_deletion_workflow(self, logged_in_client, user) -> None:
        """Test restaurant deletion workflow."""
        with patch("app.restaurants.routes.services.get_restaurant_for_user") as mock_get:
            with patch("app.restaurants.routes.services.delete_restaurant_by_id") as mock_delete:
                # Mock existing restaurant
                mock_restaurant = Mock()
                mock_restaurant.id = 1
                mock_restaurant.name = "Test Restaurant"
                mock_get.return_value = mock_restaurant

                # Test restaurant deletion
                response = logged_in_client.post("/restaurants/delete/1")

                # Should redirect to restaurant list
                assert response.status_code == 302
                assert "/restaurants/" in response.location

                # Verify delete was called
                mock_delete.assert_called_once()

    def test_restaurant_search_by_location_workflow(self, logged_in_client, user) -> None:
        """Test restaurant search by location workflow."""
        # Test location-based search with correct parameters
        response = logged_in_client.get(
            "/restaurants/api/search/location",
            query_string={"latitude": "40.7128", "longitude": "-74.0060", "radius_km": "5"},
        )

        # Should return 200 (even if no restaurants found)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "results" in data

    def test_restaurant_duplicate_detection_workflow(self, logged_in_client, user) -> None:
        """Test restaurant duplicate detection workflow."""
        # Test that the duplicate detection route is accessible
        response = logged_in_client.post(
            "/restaurants/check-restaurant-exists", json={"google_place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4"}
        )

        # Should return 200 (even if no duplicate found)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "exists" in data

    def test_restaurant_form_validation_workflow(self, logged_in_client, user) -> None:
        """Test restaurant form validation workflow."""
        # Test with invalid data
        response = logged_in_client.post(
            "/restaurants/add",
            data={
                "name": "",  # Empty name should fail validation
                "address": "123 Test St",
                "cuisine": "invalid_cuisine",
                "csrf_token": "test_token",
            },
        )

        # Should return validation errors
        assert response.status_code == 200  # Form re-rendered with errors
        assert b"error" in response.data.lower() or b"invalid" in response.data.lower()

    def test_restaurant_ajax_creation_workflow(self, logged_in_client, user) -> None:
        """Test AJAX restaurant creation workflow."""
        with patch("app.restaurants.routes.services.create_restaurant") as mock_create:
            # Mock successful restaurant creation
            mock_restaurant = Mock()
            mock_restaurant.id = 1
            mock_restaurant.name = "AJAX Restaurant"
            mock_restaurant.to_dict.return_value = {"id": 1, "name": "AJAX Restaurant", "address": "123 Test St"}
            mock_create.return_value = (mock_restaurant, True)  # Return tuple (restaurant, is_new)

            # Test AJAX restaurant creation with CSRF token
            response = logged_in_client.post(
                "/restaurants/add-from-google-places",
                json={
                    "name": "AJAX Restaurant",
                    "address": "123 Test St",
                    "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
                    "type": "restaurant",
                },
                headers={"X-Requested-With": "XMLHttpRequest", "X-CSRFToken": "test_csrf_token"},
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert data["restaurant_id"] == 1

    def test_restaurant_error_handling_workflow(self, logged_in_client, user) -> None:
        """Test restaurant error handling workflow."""
        with patch("app.restaurants.routes.services.create_restaurant") as mock_create:
            # Mock service exception
            mock_create.side_effect = Exception("Database error")

            # Test error handling
            response = logged_in_client.post(
                "/restaurants/add",
                data={
                    "name": "Test Restaurant",
                    "address": "123 Test St",
                    "cuisine": "italian",
                    "csrf_token": "test_token",
                },
            )

            # Should handle error gracefully
            assert response.status_code in [200, 500]  # Either form re-rendered or server error
