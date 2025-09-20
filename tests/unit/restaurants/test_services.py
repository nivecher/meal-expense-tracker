"""Unit tests for restaurant services.

These tests focus on the business logic in app/restaurants/services.py
without Flask context complexity, providing maximum coverage impact.
"""

import io
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import select

from app import create_app
from app.auth.models import User
from app.extensions import db
from app.restaurants.models import Restaurant
from app.restaurants.services import (
    apply_restaurant_filters,
    apply_restaurant_sorting,
    calculate_expense_stats,
    create_restaurant,
    create_restaurant_for_user,
    delete_restaurant_by_id,
    detect_service_level_from_google_data,
    export_restaurants_for_user,
    get_filter_options,
    get_restaurant_for_user,
    get_restaurants_for_user,
    get_restaurants_with_stats,
    get_unique_cities,
    get_unique_cuisines,
    get_unique_service_levels,
    import_restaurants_from_csv,
    recalculate_restaurant_statistics,
    restaurant_exists,
    search_restaurants_by_location,
    update_restaurant,
    update_restaurant_for_user,
    validate_restaurant_uniqueness,
)


class TestRestaurantServices:
    """Test restaurant service functions."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        app = create_app("testing")
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["SECRET_KEY"] = "test_secret_key"

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
    def restaurant(self, app, user):
        """Create test restaurant."""
        with app.app_context():
            restaurant = Restaurant(
                name="Test Restaurant",
                address="123 Test St",
                city="Test City",
                cuisine="italian",
                service_level="casual_dining",
                user_id=user.id,
            )
            db.session.add(restaurant)
            db.session.commit()
            return restaurant

    def test_create_restaurant_for_user(self, app, user):
        """Test creating a restaurant for a user."""
        with app.app_context():
            data = {
                "name": "New Restaurant",
                "address": "456 New St",
                "city": "New City",
                "cuisine": "chinese",
                "service_level": "casual_dining",
            }

            restaurant = create_restaurant_for_user(user.id, data)

            assert restaurant.name == "New Restaurant"
            assert restaurant.address == "456 New St"
            assert restaurant.city == "New City"
            assert restaurant.cuisine == "chinese"
            assert restaurant.service_level == "casual_dining"
            assert restaurant.user_id == user.id

    def test_get_restaurants_for_user(self, app, user, restaurant):
        """Test getting restaurants for a user."""
        with app.app_context():
            restaurants = get_restaurants_for_user(user.id)

            assert len(restaurants) == 1
            assert restaurants[0].name == "Test Restaurant"

    def test_get_restaurant_for_user(self, app, user, restaurant):
        """Test getting a specific restaurant for a user."""
        with app.app_context():
            found_restaurant = get_restaurant_for_user(restaurant.id, user.id)

            assert found_restaurant is not None
            assert found_restaurant.name == "Test Restaurant"

    def test_get_restaurant_for_user_not_found(self, app, user):
        """Test getting a non-existent restaurant."""
        with app.app_context():
            found_restaurant = get_restaurant_for_user(999, user.id)

            assert found_restaurant is None

    def test_update_restaurant_for_user(self, app, user, restaurant):
        """Test updating a restaurant for a user."""
        with app.app_context():
            data = {"name": "Updated Restaurant", "address": "789 Updated St", "cuisine": "mexican"}

            updated_restaurant = update_restaurant_for_user(restaurant, data)

            assert updated_restaurant.name == "Updated Restaurant"
            assert updated_restaurant.address == "789 Updated St"
            assert updated_restaurant.cuisine == "mexican"

    def test_delete_restaurant_by_id(self, app, user, restaurant):
        """Test deleting a restaurant by ID."""
        with app.app_context():
            success, message = delete_restaurant_by_id(restaurant.id, user.id)

            assert success is True
            assert "deleted" in message.lower()

            # Verify restaurant is deleted
            deleted_restaurant = get_restaurant_for_user(restaurant.id, user.id)
            assert deleted_restaurant is None

    def test_restaurant_exists(self, app, user, restaurant):
        """Test checking if a restaurant exists."""
        with app.app_context():
            # Test existing restaurant
            exists = restaurant_exists(user.id, "Test Restaurant", "Test City")
            assert exists is not None
            assert exists.name == "Test Restaurant"

            # Test non-existing restaurant
            not_exists = restaurant_exists(user.id, "Non-existent", "Nowhere")
            assert not_exists is None

    def test_validate_restaurant_uniqueness(self, app, user, restaurant):
        """Test restaurant uniqueness validation."""
        with app.app_context():
            # Test duplicate restaurant
            is_unique, message = validate_restaurant_uniqueness(user.id, "Test Restaurant", "Test City")
            assert is_unique is False
            assert "already exists" in message.lower()

            # Test unique restaurant
            is_unique, message = validate_restaurant_uniqueness(user.id, "Unique Restaurant", "Unique City")
            assert is_unique is True

    def test_get_unique_cuisines(self, app, user, restaurant):
        """Test getting unique cuisines for a user."""
        with app.app_context():
            # Create another restaurant with different cuisine
            restaurant2 = Restaurant(name="Chinese Restaurant", cuisine="chinese", user_id=user.id)
            db.session.add(restaurant2)
            db.session.commit()

            cuisines = get_unique_cuisines(user.id)

            assert "italian" in cuisines
            assert "chinese" in cuisines
            assert len(cuisines) == 2

    def test_get_unique_cities(self, app, user, restaurant):
        """Test getting unique cities for a user."""
        with app.app_context():
            # Create another restaurant in different city
            restaurant2 = Restaurant(name="Other Restaurant", city="Other City", user_id=user.id)
            db.session.add(restaurant2)
            db.session.commit()

            cities = get_unique_cities(user.id)

            assert "Test City" in cities
            assert "Other City" in cities
            assert len(cities) == 2

    def test_get_unique_service_levels(self, app, user, restaurant):
        """Test getting unique service levels for a user."""
        with app.app_context():
            # Create another restaurant with different service level
            restaurant2 = Restaurant(name="Fine Restaurant", service_level="fine_dining", user_id=user.id)
            db.session.add(restaurant2)
            db.session.commit()

            service_levels = get_unique_service_levels(user.id)

            assert "casual_dining" in service_levels
            assert "fine_dining" in service_levels
            assert len(service_levels) == 2

    def test_get_filter_options(self, app, user, restaurant):
        """Test getting filter options for a user."""
        with app.app_context():
            options = get_filter_options(user.id)

            assert "cuisines" in options
            assert "cities" in options
            assert "service_levels" in options
            assert "italian" in options["cuisines"]

    def test_apply_restaurant_filters(self, app, user, restaurant):
        """Test applying restaurant filters."""
        with app.app_context():
            # Create a query
            stmt = select(Restaurant).where(Restaurant.user_id == user.id)

            # Apply search filter
            filters = {"search": "Test"}
            filtered_stmt = apply_restaurant_filters(stmt, filters)

            # Execute query
            result = db.session.execute(filtered_stmt).scalars().all()
            assert len(result) == 1
            assert result[0].name == "Test Restaurant"

    def test_apply_restaurant_sorting(self, app, user, restaurant):
        """Test applying restaurant sorting."""
        with app.app_context():
            # Create another restaurant for sorting test
            restaurant2 = Restaurant(name="A Restaurant", user_id=user.id)
            db.session.add(restaurant2)
            db.session.commit()

            # Create a query
            stmt = select(Restaurant).where(Restaurant.user_id == user.id)

            # Apply sorting
            sorted_stmt = apply_restaurant_sorting(stmt, "name", "asc")

            # Execute query
            result = db.session.execute(sorted_stmt).scalars().all()
            assert len(result) == 2
            assert result[0].name == "A Restaurant"  # Alphabetically first
            assert result[1].name == "Test Restaurant"

    def test_get_restaurants_with_stats(self, app, user, restaurant):
        """Test getting restaurants with statistics."""
        with app.app_context():
            args = {"page": 1, "per_page": 10}
            restaurants, stats = get_restaurants_with_stats(user.id, args)

            assert len(restaurants) == 1
            assert restaurants[0].name == "Test Restaurant"
            assert "total_count" in stats
            assert stats["total_count"] == 1

    def test_calculate_expense_stats(self, app, user, restaurant):
        """Test calculating expense statistics for a restaurant."""
        with app.app_context():
            with patch("app.restaurants.services.db.session.execute") as mock_execute:
                # Mock expense statistics
                mock_result = Mock()
                mock_result.scalar.return_value = Decimal("150.50")
                mock_execute.return_value = mock_result

                stats = calculate_expense_stats(restaurant.id, user.id)

                assert "total_amount" in stats
                assert "expense_count" in stats
                assert "average_amount" in stats

    def test_detect_service_level_from_google_data(self, app):
        """Test detecting service level from Google Places data."""
        google_data = {"types": ["restaurant", "food", "establishment"], "price_level": 2, "rating": 4.5}

        service_level, confidence = detect_service_level_from_google_data(google_data)

        assert service_level in ["quick_service", "casual_dining", "fine_dining"]
        assert 0.0 <= confidence <= 1.0

    def test_export_restaurants_for_user(self, app, user, restaurant):
        """Test exporting restaurants for a user."""
        with app.app_context():
            export_data = export_restaurants_for_user(user.id)

            assert len(export_data) == 1
            assert export_data[0]["name"] == "Test Restaurant"
            assert export_data[0]["cuisine"] == "italian"
            assert export_data[0]["service_level"] == "casual_dining"

    def test_import_restaurants_from_csv(self, app, user):
        """Test importing restaurants from CSV."""
        with app.app_context():
            # Create CSV data
            csv_data = "name,address,city,cuisine,service_level\n"
            csv_data += "Imported Restaurant,123 Import St,Import City,italian,casual_dining\n"

            csv_file = Mock()
            csv_file.stream = io.StringIO(csv_data)
            csv_file.filename = "test.csv"

            success, result = import_restaurants_from_csv(csv_file, user.id)

            assert success is True
            assert result["success_count"] == 1
            assert result["skipped_count"] == 0
            assert len(result["errors"]) == 0

            # Verify restaurant was created
            restaurants = get_restaurants_for_user(user.id)
            assert len(restaurants) == 1
            assert restaurants[0].name == "Imported Restaurant"

    def test_import_restaurants_from_csv_with_errors(self, app, user):
        """Test importing restaurants from CSV with validation errors."""
        with app.app_context():
            # Create CSV data with missing required fields
            csv_data = "name,address,city,cuisine,service_level\n"
            csv_data += ",123 Import St,Import City,italian,casual_dining\n"  # Missing name

            csv_file = Mock()
            csv_file.stream = io.StringIO(csv_data)
            csv_file.filename = "test.csv"

            success, result = import_restaurants_from_csv(csv_file, user.id)

            assert success is False
            assert result["success_count"] == 0
            assert result["skipped_count"] == 1
            assert len(result["errors"]) > 0

    def test_search_restaurants_by_location(self, app, user, restaurant):
        """Test searching restaurants by location."""
        with app.app_context():
            # Mock restaurant with coordinates
            restaurant.latitude = 40.7128
            restaurant.longitude = -74.0060
            db.session.commit()

            results = search_restaurants_by_location(
                user_id=user.id, latitude=40.7128, longitude=-74.0060, radius_miles=5
            )

            assert len(results) == 1
            assert results[0].name == "Test Restaurant"

    def test_recalculate_restaurant_statistics(self, app, user, restaurant):
        """Test recalculating restaurant statistics."""
        with app.app_context():
            # This should not raise an exception
            recalculate_restaurant_statistics(user.id)

            # Verify the function completed successfully
            assert True  # If we get here, no exception was raised

    def test_create_restaurant_with_form(self, app, user):
        """Test creating a restaurant with form data."""
        with app.app_context():
            # Mock form data
            form = Mock()
            form.name.data = "Form Restaurant"
            form.address.data = "123 Form St"
            form.city.data = "Form City"
            form.cuisine.data = "italian"
            form.service_level.data = "casual_dining"

            restaurant, is_new = create_restaurant(user.id, form)

            assert restaurant.name == "Form Restaurant"
            assert restaurant.address == "123 Form St"
            assert restaurant.city == "Form City"
            assert restaurant.cuisine == "italian"
            assert restaurant.service_level == "casual_dining"
            assert is_new is True

    def test_update_restaurant_with_form(self, app, user, restaurant):
        """Test updating a restaurant with form data."""
        with app.app_context():
            # Mock form data
            form = Mock()
            form.name.data = "Updated Form Restaurant"
            form.address.data = "456 Updated St"
            form.cuisine.data = "chinese"

            updated_restaurant = update_restaurant(restaurant.id, user.id, form)

            assert updated_restaurant.name == "Updated Form Restaurant"
            assert updated_restaurant.address == "456 Updated St"
            assert updated_restaurant.cuisine == "chinese"

    def test_restaurant_services_error_handling(self, app, user):
        """Test error handling in restaurant services."""
        with app.app_context():
            # Test with invalid user ID
            restaurants = get_restaurants_for_user(999)
            assert len(restaurants) == 0

            # Test with invalid restaurant ID
            restaurant = get_restaurant_for_user(999, user.id)
            assert restaurant is None

            # Test deleting non-existent restaurant
            success, message = delete_restaurant_by_id(999, user.id)
            assert success is False
            assert "not found" in message.lower()

    def test_restaurant_services_edge_cases(self, app, user):
        """Test edge cases in restaurant services."""
        with app.app_context():
            # Test empty search
            cuisines = get_unique_cuisines(user.id)
            assert cuisines == []

            cities = get_unique_cities(user.id)
            assert cities == []

            service_levels = get_unique_service_levels(user.id)
            assert service_levels == []

            # Test filter options with no restaurants
            options = get_filter_options(user.id)
            assert options["cuisines"] == []
            assert options["cities"] == []
            assert options["service_levels"] == []
