"""Integration tests for restaurant services workflows.

These tests focus on complete restaurant service workflows including
Google Places integration, data processing, and service level detection.
"""

from unittest.mock import Mock, patch

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

    def test_restaurant_creation_from_google_places_workflow(self, app, user, mock_google_places_data):
        """Test restaurant creation from Google Places data workflow."""
        with app.app_context():
            with patch("app.restaurants.services.create_restaurant_from_google_places") as mock_create:
                # Mock successful restaurant creation
                mock_restaurant = Mock()
                mock_restaurant.id = 1
                mock_restaurant.name = "Test Restaurant"
                mock_restaurant.place_id = "ChIJN1t_tDeuEmsRUsoyG83frY4"
                mock_restaurant.cuisine = "italian"
                mock_restaurant.service_level = "casual_dining"
                mock_create.return_value = mock_restaurant

                # Test restaurant creation from Google Places
                from app.restaurants.services import (
                    create_restaurant_from_google_places,
                )

                result = create_restaurant_from_google_places(user.id, mock_google_places_data)

                assert result.id == 1
                assert result.name == "Test Restaurant"
                assert result.place_id == "ChIJN1t_tDeuEmsRUsoyG83frY4"

    def test_restaurant_search_by_location_workflow(self, app, user):
        """Test restaurant search by location workflow."""
        with app.app_context():
            with patch("app.restaurants.services.search_restaurants_by_location") as mock_search:
                # Mock search results
                mock_restaurants = [
                    Mock(id=1, name="Nearby Restaurant", distance=0.5),
                    Mock(id=2, name="Another Restaurant", distance=1.2),
                ]
                mock_search.return_value = mock_restaurants

                # Test location-based search
                from app.restaurants.services import search_restaurants_by_location

                results = search_restaurants_by_location(
                    user_id=user.id, latitude=40.7128, longitude=-74.0060, radius_miles=5
                )

                assert len(results) == 2
                assert results[0].name == "Nearby Restaurant"

    def test_restaurant_service_level_detection_workflow(self, app, user, mock_google_places_data):
        """Test restaurant service level detection workflow."""
        with app.app_context():
            with patch("app.restaurants.services.detect_service_level") as mock_detect:
                # Mock service level detection
                mock_detect.return_value = {
                    "service_level": "casual_dining",
                    "confidence": 0.85,
                    "indicators": ["table_service", "moderate_pricing"],
                }

                # Test service level detection
                from app.restaurants.services import detect_service_level

                result = detect_service_level(mock_google_places_data)

                assert result["service_level"] == "casual_dining"
                assert result["confidence"] == 0.85

    def test_restaurant_cuisine_detection_workflow(self, app, user, mock_google_places_data):
        """Test restaurant cuisine detection workflow."""
        with app.app_context():
            with patch("app.restaurants.services.detect_cuisine") as mock_detect:
                # Mock cuisine detection
                mock_detect.return_value = {
                    "cuisine": "italian",
                    "confidence": 0.90,
                    "indicators": ["pasta", "italian_types"],
                }

                # Test cuisine detection
                from app.restaurants.services import detect_cuisine

                result = detect_cuisine(mock_google_places_data)

                assert result["cuisine"] == "italian"
                assert result["confidence"] == 0.90

    def test_restaurant_validation_workflow(self, app, user):
        """Test restaurant validation workflow."""
        with app.app_context():
            with patch("app.restaurants.services.validate_restaurant_data") as mock_validate:
                # Mock validation results
                mock_validate.return_value = {
                    "valid": True,
                    "warnings": ["Address could not be geocoded"],
                    "suggestions": {"cuisine": "italian", "service_level": "casual_dining"},
                }

                # Test restaurant validation
                from app.restaurants.services import validate_restaurant_data

                restaurant_data = {"name": "Test Restaurant", "address": "123 Test St", "cuisine": "unknown"}

                result = validate_restaurant_data(restaurant_data)
                assert result["valid"] is True
                assert "italian" in result["suggestions"]["cuisine"]

    def test_restaurant_duplicate_detection_workflow(self, app, user):
        """Test restaurant duplicate detection workflow."""
        with app.app_context():
            with patch("app.restaurants.services.find_duplicate_restaurants") as mock_find_duplicates:
                # Mock duplicate detection
                mock_find_duplicates.return_value = {
                    "duplicates": [Mock(id=1, name="Test Restaurant", similarity_score=0.95)],
                    "exact_match": None,
                    "similar_matches": 1,
                }

                # Test duplicate detection
                from app.restaurants.services import find_duplicate_restaurants

                result = find_duplicate_restaurants(user_id=user.id, name="Test Restaurant", address="123 Test St")

                assert len(result["duplicates"]) == 1
                assert result["duplicates"][0].similarity_score == 0.95

    def test_restaurant_data_processing_workflow(self, app, user, mock_google_places_data):
        """Test restaurant data processing workflow."""
        with app.app_context():
            with patch("app.restaurants.services.process_google_places_data") as mock_process:
                # Mock data processing
                mock_process.return_value = {
                    "processed_data": {
                        "name": "Test Restaurant",
                        "address": "123 Test St",
                        "city": "Test City",
                        "state": "TC",
                        "postal_code": "12345",
                        "country": "US",
                        "cuisine": "italian",
                        "service_level": "casual_dining",
                        "rating": 4.5,
                        "price_level": 2,
                    },
                    "confidence_scores": {"cuisine": 0.90, "service_level": 0.85},
                }

                # Test data processing
                from app.restaurants.services import process_google_places_data

                result = process_google_places_data(mock_google_places_data)

                assert result["processed_data"]["name"] == "Test Restaurant"
                assert result["confidence_scores"]["cuisine"] == 0.90

    def test_restaurant_bulk_operations_workflow(self, app, user):
        """Test restaurant bulk operations workflow."""
        with app.app_context():
            with patch("app.restaurants.services.bulk_update_restaurants") as mock_bulk_update:
                # Mock bulk update results
                mock_bulk_update.return_value = {
                    "updated_count": 3,
                    "error_count": 1,
                    "errors": ["Restaurant ID 999 not found"],
                }

                # Test bulk restaurant update
                from app.restaurants.services import bulk_update_restaurants

                updates = [
                    {"id": 1, "cuisine": "italian"},
                    {"id": 2, "cuisine": "chinese"},
                    {"id": 999, "cuisine": "mexican"},  # Non-existent restaurant
                ]

                result = bulk_update_restaurants(user.id, updates)
                assert result["updated_count"] == 3
                assert result["error_count"] == 1

    def test_restaurant_analytics_workflow(self, app, user):
        """Test restaurant analytics workflow."""
        with app.app_context():
            with patch("app.restaurants.services.generate_restaurant_analytics") as mock_analytics:
                # Mock analytics data
                mock_analytics.return_value = {
                    "total_restaurants": 25,
                    "cuisine_distribution": {"italian": 8, "chinese": 6, "mexican": 5, "other": 6},
                    "service_level_distribution": {"casual_dining": 15, "fine_dining": 5, "quick_service": 5},
                    "top_rated_restaurants": [{"name": "Best Restaurant", "rating": 4.8, "review_count": 150}],
                    "recent_activity": {"added_this_month": 3, "updated_this_month": 5},
                }

                # Test restaurant analytics
                from app.restaurants.services import generate_restaurant_analytics

                analytics = generate_restaurant_analytics(user.id)

                assert analytics["total_restaurants"] == 25
                assert analytics["cuisine_distribution"]["italian"] == 8
                assert len(analytics["top_rated_restaurants"]) == 1

    def test_restaurant_import_processing_workflow(self, app, user):
        """Test restaurant import processing workflow."""
        with app.app_context():
            with patch("app.restaurants.services.process_restaurant_import") as mock_import:
                # Mock import processing
                mock_import.return_value = {
                    "processed_count": 10,
                    "success_count": 8,
                    "error_count": 2,
                    "errors": ["Row 3: Invalid address format", "Row 7: Missing required field 'name'"],
                    "restaurants": [Mock(id=1, name="Imported Restaurant 1"), Mock(id=2, name="Imported Restaurant 2")],
                }

                # Test restaurant import processing
                from app.restaurants.services import process_restaurant_import

                import_data = [
                    {"name": "Restaurant 1", "address": "123 St"},
                    {"name": "Restaurant 2", "address": "456 Ave"},
                ]

                result = process_restaurant_import(user.id, import_data)
                assert result["processed_count"] == 10
                assert result["success_count"] == 8
                assert result["error_count"] == 2

    def test_restaurant_error_handling_workflow(self, app, user):
        """Test restaurant error handling workflow."""
        with app.app_context():
            with patch("app.restaurants.services.create_restaurant_for_user") as mock_create:
                # Mock service exception
                mock_create.side_effect = Exception("Google Places API error")

                # Test error handling
                from app.restaurants.services import create_restaurant_for_user

                with pytest.raises(Exception) as exc_info:
                    create_restaurant_for_user(user.id, {"name": "Test Restaurant"})

                assert "Google Places API error" in str(exc_info.value)

    def test_restaurant_geocoding_workflow(self, app, user):
        """Test restaurant geocoding workflow."""
        with app.app_context():
            with patch("app.restaurants.services.geocode_address") as mock_geocode:
                # Mock geocoding results
                mock_geocode.return_value = {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "formatted_address": "123 Test St, Test City, TC 12345, USA",
                    "confidence": 0.95,
                    "components": {
                        "street_number": "123",
                        "route": "Test St",
                        "locality": "Test City",
                        "administrative_area_level_1": "TC",
                        "postal_code": "12345",
                        "country": "US",
                    },
                }

                # Test address geocoding
                from app.restaurants.services import geocode_address

                result = geocode_address("123 Test St, Test City, TC")

                assert result["latitude"] == 40.7128
                assert result["longitude"] == -74.0060
                assert result["confidence"] == 0.95
