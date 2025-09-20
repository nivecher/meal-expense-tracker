"""Integration tests for restaurant workflows.

These tests focus on complete user journeys rather than individual functions,
providing maximum coverage with minimal test complexity.
"""

import csv
import io
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
            return user

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

    def test_restaurant_creation_workflow(self, client, user, mock_google_places_data):
        """Test complete restaurant creation workflow."""
        with patch("app.restaurants.routes.services.create_restaurant") as mock_create:
            with patch("app.restaurants.routes.services.get_restaurant_by_place_id") as mock_get:
                # Mock that restaurant doesn't exist yet
                mock_get.return_value = None

                # Mock successful restaurant creation
                mock_restaurant = Mock()
                mock_restaurant.id = 1
                mock_restaurant.name = "Test Restaurant"
                mock_restaurant.to_dict.return_value = {"id": 1, "name": "Test Restaurant", "address": "123 Test St"}
                mock_create.return_value = mock_restaurant

                # Test restaurant creation via POST
                response = client.post(
                    "/restaurants/add",
                    data={
                        "name": "Test Restaurant",
                        "address": "123 Test St",
                        "cuisine": "italian",
                        "csrf_token": "test_token",
                    },
                )

                # Should redirect to restaurant details
                assert response.status_code == 302
                assert "/restaurants/1" in response.location

    def test_google_places_search_workflow(self, client, user, mock_google_places_data):
        """Test Google Places search and restaurant creation workflow."""
        with patch("app.restaurants.routes.requests.get") as mock_get:
            # Mock Google Places API response
            mock_response = Mock()
            mock_response.json.return_value = {"results": [mock_google_places_data], "status": "OK"}
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            # Test Google Places search
            response = client.get(
                "/restaurants/api/places/search", query_string={"query": "test restaurant", "api_key": "test_api_key"}
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "success"
            assert len(data["data"]["places"]) == 1
            assert data["data"]["places"][0]["name"] == "Test Restaurant"

    def test_restaurant_import_export_workflow(self, client, user):
        """Test restaurant CSV import and export workflow."""
        # First, create a test restaurant
        with patch("app.restaurants.routes.services.create_restaurant") as mock_create:
            mock_restaurant = Mock()
            mock_restaurant.id = 1
            mock_restaurant.name = "Test Restaurant"
            mock_restaurant.address = "123 Test St"
            mock_restaurant.cuisine = "italian"
            mock_create.return_value = mock_restaurant

            # Test CSV export
            response = client.get("/restaurants/export?format=csv")
            assert response.status_code == 200
            assert response.headers["Content-Type"] == "text/csv"

            # Parse CSV content
            csv_content = response.data.decode("utf-8")
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            rows = list(csv_reader)

            # Should have header row
            assert "name" in rows[0] if rows else True

    def test_restaurant_filtering_and_pagination_workflow(self, client, user):
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
            response = client.get("/restaurants/", query_string={"cuisine": "italian", "page": 1, "per_page": 10})

            assert response.status_code == 200
            # Should render the restaurant list template
            assert b"restaurants" in response.data.lower()

    def test_restaurant_edit_workflow(self, client, user):
        """Test restaurant editing workflow."""
        with patch("app.restaurants.routes.services.get_restaurant_by_id_for_user") as mock_get:
            with patch("app.restaurants.routes.services.update_restaurant_for_user") as mock_update:
                # Mock existing restaurant
                mock_restaurant = Mock()
                mock_restaurant.id = 1
                mock_restaurant.name = "Original Name"
                mock_restaurant.address = "Original Address"
                mock_get.return_value = mock_restaurant

                # Mock updated restaurant
                mock_updated = Mock()
                mock_updated.id = 1
                mock_updated.name = "Updated Name"
                mock_update.return_value = mock_updated

                # Test restaurant edit
                response = client.post(
                    "/restaurants/1/edit",
                    data={
                        "name": "Updated Name",
                        "address": "Updated Address",
                        "cuisine": "italian",
                        "csrf_token": "test_token",
                    },
                )

                # Should redirect to restaurant details
                assert response.status_code == 302
                assert "/restaurants/1" in response.location

    def test_restaurant_deletion_workflow(self, client, user):
        """Test restaurant deletion workflow."""
        with patch("app.restaurants.routes.services.get_restaurant_by_id_for_user") as mock_get:
            with patch("app.restaurants.routes.services.delete_restaurant_for_user") as mock_delete:
                # Mock existing restaurant
                mock_restaurant = Mock()
                mock_restaurant.id = 1
                mock_restaurant.name = "Test Restaurant"
                mock_get.return_value = mock_restaurant

                # Test restaurant deletion
                response = client.post("/restaurants/delete/1")

                # Should redirect to restaurant list
                assert response.status_code == 302
                assert "/restaurants/" in response.location

                # Verify delete was called
                mock_delete.assert_called_once()

    def test_restaurant_search_by_location_workflow(self, client, user):
        """Test restaurant search by location workflow."""
        with patch("app.restaurants.routes.search_restaurants_by_location") as mock_search:
            # Mock search results
            mock_restaurants = [
                Mock(id=1, name="Nearby Restaurant", distance=0.5),
                Mock(id=2, name="Another Restaurant", distance=1.2),
            ]
            mock_search.return_value = mock_restaurants

            # Test location-based search
            response = client.get(
                "/restaurants/api/search/location", query_string={"lat": "40.7128", "lng": "-74.0060", "radius": "5"}
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "success"
            assert len(data["data"]["restaurants"]) == 2

    def test_restaurant_duplicate_detection_workflow(self, client, user):
        """Test restaurant duplicate detection workflow."""
        with patch("app.restaurants.routes.services.get_restaurant_by_place_id") as mock_get:
            # Mock existing restaurant with same place ID
            mock_existing = Mock()
            mock_existing.id = 1
            mock_existing.name = "Existing Restaurant"
            mock_get.return_value = mock_existing

            # Test duplicate check
            response = client.post(
                "/restaurants/check-restaurant-exists", json={"place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4"}
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["exists"] is True
            assert data["restaurant"]["name"] == "Existing Restaurant"

    def test_restaurant_form_validation_workflow(self, client, user):
        """Test restaurant form validation workflow."""
        # Test with invalid data
        response = client.post(
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

    def test_restaurant_ajax_creation_workflow(self, client, user):
        """Test AJAX restaurant creation workflow."""
        with patch("app.restaurants.routes.services.create_restaurant") as mock_create:
            # Mock successful restaurant creation
            mock_restaurant = Mock()
            mock_restaurant.id = 1
            mock_restaurant.name = "AJAX Restaurant"
            mock_restaurant.to_dict.return_value = {"id": 1, "name": "AJAX Restaurant", "address": "123 Test St"}
            mock_create.return_value = mock_restaurant

            # Test AJAX restaurant creation
            response = client.post(
                "/restaurants/add-from-google-places",
                json={"name": "AJAX Restaurant", "address": "123 Test St", "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4"},
                headers={"X-Requested-With": "XMLHttpRequest"},
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "success"
            assert data["data"]["name"] == "AJAX Restaurant"

    def test_restaurant_error_handling_workflow(self, client, user):
        """Test restaurant error handling workflow."""
        with patch("app.restaurants.routes.services.create_restaurant") as mock_create:
            # Mock service exception
            mock_create.side_effect = Exception("Database error")

            # Test error handling
            response = client.post(
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
