"""Unit tests for restaurant services.

These tests focus on the business logic in app/restaurants/services.py
without Flask context complexity, providing maximum coverage impact.
"""

from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import select

from app import create_app
from app.auth.models import User
from app.extensions import db
from app.restaurants.exceptions import DuplicateRestaurantError
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
            return user, user.id

    @pytest.fixture
    def restaurant(self, app, user):
        """Create test restaurant."""
        user_obj, user_id = user  # Unpack user and user_id
        with app.app_context():
            restaurant = Restaurant(
                name="Test Restaurant",
                address_line_1="123 Test St",
                city="Test City",
                cuisine="italian",
                service_level="casual_dining",
                type="restaurant",  # Add required field
                user_id=user_id,
            )
            db.session.add(restaurant)
            db.session.commit()
            return restaurant, restaurant.id

    def test_create_restaurant_for_user(self, app, user):
        """Test creating a restaurant for a user."""
        user_obj, user_id = user  # Unpack user and user_id
        with app.app_context():
            data = {
                "name": "New Restaurant",
                "address_line_1": "456 New St",
                "city": "New City",
                "cuisine": "chinese",
                "service_level": "casual_dining",
            }

            restaurant = create_restaurant_for_user(user_id, data)

            assert restaurant.name == "New Restaurant"
            assert restaurant.address_line_1 == "456 New St"
            assert restaurant.city == "New City"
            assert restaurant.cuisine == "chinese"
            assert restaurant.service_level == "casual_dining"
            assert restaurant.user_id == user_id

    def test_get_restaurants_for_user(self, app, user, restaurant):
        """Test getting restaurants for a user."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        with app.app_context():
            restaurants = get_restaurants_for_user(user_id)

            assert len(restaurants) == 1
            assert restaurants[0].name == "Test Restaurant"

    def test_get_restaurant_for_user(self, app, user, restaurant):
        """Test getting a specific restaurant for a user."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        with app.app_context():
            found_restaurant = get_restaurant_for_user(restaurant_id, user_id)

            assert found_restaurant is not None
            assert found_restaurant.name == "Test Restaurant"

    def test_get_restaurant_for_user_not_found(self, app, user):
        """Test getting a non-existent restaurant."""
        user_obj, user_id = user  # Unpack user and user_id
        with app.app_context():
            found_restaurant = get_restaurant_for_user(999, user_id)

            assert found_restaurant is None

    def test_update_restaurant_for_user(self, app, user, restaurant):
        """Test updating a restaurant for a user."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        with app.app_context():
            data = {"name": "Updated Restaurant", "address_line_1": "789 Updated St", "cuisine": "mexican"}

            updated_restaurant = update_restaurant_for_user(restaurant_obj, data)

            assert updated_restaurant.name == "Updated Restaurant"
            assert updated_restaurant.address_line_1 == "789 Updated St"
            assert updated_restaurant.cuisine == "mexican"

    def test_delete_restaurant_by_id(self, app, user, restaurant):
        """Test deleting a restaurant by ID."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        with app.app_context():
            success, message = delete_restaurant_by_id(restaurant_id, user_id)

            assert success is True
            assert "deleted" in message.lower()

            # Verify restaurant is deleted
            deleted_restaurant = get_restaurant_for_user(restaurant_id, user_id)
            assert deleted_restaurant is None

    def test_restaurant_exists(self, app, user, restaurant):
        """Test checking if a restaurant exists."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        with app.app_context():
            # Test existing restaurant
            exists = restaurant_exists(user_id, "Test Restaurant", "Test City")
            assert exists is not None
            assert exists.name == "Test Restaurant"

            # Test non-existing restaurant
            not_exists = restaurant_exists(user_id, "Non-existent", "Nowhere")
            assert not_exists is None

    def test_validate_restaurant_uniqueness(self, app, user, restaurant):
        """Test restaurant uniqueness validation."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        with app.app_context():
            # Test duplicate restaurant - should raise exception
            with pytest.raises(DuplicateRestaurantError) as exc_info:
                validate_restaurant_uniqueness(user_id, "Test Restaurant", "Test City")
            assert "already exists" in str(exc_info.value).lower()

            # Test unique restaurant - should not raise exception
            validate_restaurant_uniqueness(user_id, "Unique Restaurant", "Unique City")  # Should not raise

    def test_get_unique_cuisines(self, app, user, restaurant):
        """Test getting unique cuisines for a user."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        with app.app_context():
            # Create another restaurant with different cuisine
            restaurant2 = Restaurant(name="Chinese Restaurant", cuisine="chinese", user_id=user_id)
            db.session.add(restaurant2)
            db.session.commit()

            cuisines = get_unique_cuisines(user_id)

            assert "italian" in cuisines
            assert "chinese" in cuisines
            assert len(cuisines) == 2

    def test_get_unique_cities(self, app, user, restaurant):
        """Test getting unique cities for a user."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        with app.app_context():
            # Create another restaurant in different city
            restaurant2 = Restaurant(name="Other Restaurant", city="Other City", user_id=user_id)
            db.session.add(restaurant2)
            db.session.commit()

            cities = get_unique_cities(user_id)

            assert "Test City" in cities
            assert "Other City" in cities
            assert len(cities) == 2

    def test_get_unique_service_levels(self, app, user, restaurant):
        """Test getting unique service levels for a user."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        with app.app_context():
            # Create another restaurant with different service level
            restaurant2 = Restaurant(name="Fine Restaurant", service_level="fine_dining", user_id=user_id)
            db.session.add(restaurant2)
            db.session.commit()

            service_levels = get_unique_service_levels(user_id)

            assert "casual_dining" in service_levels
            assert "fine_dining" in service_levels
            assert len(service_levels) == 2

    def test_get_filter_options(self, app, user, restaurant):
        """Test getting filter options for a user."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        with app.app_context():
            options = get_filter_options(user_id)

            assert "cuisines" in options
            assert "cities" in options
            assert "service_levels" in options
            assert "italian" in options["cuisines"]

    def test_apply_restaurant_filters(self, app, user, restaurant):
        """Test applying restaurant filters."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        with app.app_context():
            # Create a query
            stmt = select(Restaurant).where(Restaurant.user_id == user_id)

            # Apply search filter
            filters = {
                "search": "Test",
                "cuisine": "",
                "service_level": "",
                "city": "",
                "is_chain": "",
                "rating_min": "",
                "rating_max": "",
            }
            filtered_stmt = apply_restaurant_filters(stmt, filters)

            # Execute query
            result = db.session.execute(filtered_stmt).scalars().all()
            assert len(result) == 1
            assert result[0].name == "Test Restaurant"

    def test_apply_restaurant_sorting(self, app, user, restaurant):
        """Test applying restaurant sorting."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        with app.app_context():
            # Create another restaurant for sorting test
            restaurant2 = Restaurant(name="A Restaurant", user_id=user_id)
            db.session.add(restaurant2)
            db.session.commit()

            # Create a query
            stmt = select(Restaurant).where(Restaurant.user_id == user_id)

            # Apply sorting
            sorted_stmt = apply_restaurant_sorting(stmt, "name", "asc")

            # Execute query
            result = db.session.execute(sorted_stmt).scalars().all()
            assert len(result) == 2
            assert result[0].name == "A Restaurant"  # Alphabetically first
            assert result[1].name == "Test Restaurant"

    def test_get_restaurants_with_stats(self, app, user, restaurant):
        """Test getting restaurants with statistics."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        with app.app_context():
            args = {"page": 1, "per_page": 10}
            restaurants, stats = get_restaurants_with_stats(user_id, args)

            assert len(restaurants) == 1
            assert restaurants[0]["name"] == "Test Restaurant"
            assert "total_restaurants" in stats
            assert stats["total_restaurants"] == 1

    def test_calculate_expense_stats(self, app, user, restaurant):
        """Test calculating expense statistics for a restaurant."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        with app.app_context():
            with patch("app.restaurants.services.db.session.execute") as mock_execute:
                # Mock expense statistics result
                mock_stats = Mock()
                mock_stats.visit_count = 3
                mock_stats.total_amount = Decimal("150.50")
                mock_stats.last_visit = None
                mock_execute.return_value.first.return_value = mock_stats

                stats = calculate_expense_stats(restaurant_id, user_id)

                assert "total_amount" in stats
                assert "visit_count" in stats
                assert "avg_per_visit" in stats

    def test_detect_service_level_from_google_data(self, app):
        """Test detecting service level from Google Places data."""
        google_data = {"types": ["restaurant", "food", "establishment"], "price_level": 2, "rating": 4.5}

        with patch("app.services.google_places_service.get_google_places_service") as mock_get_service:
            mock_service = Mock()
            mock_service.detect_service_level_from_data.return_value = ("casual_dining", 0.8)
            mock_get_service.return_value = mock_service

            service_level, confidence = detect_service_level_from_google_data(google_data)

            assert service_level in ["quick_service", "casual_dining", "fine_dining"]
            assert 0.0 <= confidence <= 1.0

    def test_export_restaurants_for_user(self, app, user, restaurant):
        """Test exporting restaurants for a user."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        with app.app_context():
            export_data = export_restaurants_for_user(user_id)

            assert len(export_data) == 1
            assert export_data[0]["name"] == "Test Restaurant"
            assert export_data[0]["cuisine"] == "italian"
            assert export_data[0]["service_level"] == "casual_dining"

    def test_import_restaurants_from_csv(self, app, user):
        """Test importing restaurants from CSV."""
        user_obj, user_id = user  # Unpack user and user_id
        with app.app_context():
            # Create CSV data
            csv_data = "name,address,city,cuisine,service_level\n"
            csv_data += "Imported Restaurant,123 Import St,Import City,italian,casual_dining\n"

            csv_file = Mock()
            csv_file.stream.read.return_value.decode.return_value = csv_data
            csv_file.filename = "test.csv"

            success, result = import_restaurants_from_csv(csv_file, user_id)

            assert success is True
            assert result["success_count"] == 1
            assert result["skipped_count"] == 0
            assert len(result["errors"]) == 0

            # Verify restaurant was created
            restaurants = get_restaurants_for_user(user_id)
            assert len(restaurants) == 1
            assert restaurants[0].name == "Imported Restaurant"

    def test_import_restaurants_from_csv_with_errors(self, app, user):
        """Test importing restaurants from CSV with validation errors."""
        user_obj, user_id = user  # Unpack user and user_id
        with app.app_context():
            # Create CSV data with missing required fields
            csv_data = "name,address,city,cuisine,service_level\n"
            csv_data += ",123 Import St,Import City,italian,casual_dining\n"  # Missing name

            csv_file = Mock()
            csv_file.stream.read.return_value.decode.return_value = csv_data
            csv_file.filename = "test.csv"

            success, result = import_restaurants_from_csv(csv_file, user_id)

            assert success is False  # Import fails due to validation errors
            assert result["success_count"] == 0
            assert result["skipped_count"] == 0
            assert result["error_count"] == 1
            assert len(result["errors"]) > 0
            assert "Name is required" in result["errors"][0]

    def test_search_restaurants_by_location(self, app, user):
        """Test searching restaurants by location."""
        user_obj, user_id = user  # Unpack user and user_id
        with app.app_context():
            # Create restaurant with coordinates directly in this context
            restaurant = Restaurant(
                name="Test Restaurant",
                address_line_1="123 Test St",
                city="Test City",
                cuisine="italian",
                service_level="casual_dining",
                type="restaurant",
                user_id=user_id,
                latitude=40.7128,
                longitude=-74.0060,
            )
            db.session.add(restaurant)
            db.session.commit()

            results = search_restaurants_by_location(
                user_id=user_id, latitude=40.7128, longitude=-74.0060, radius_km=8.0
            )

            assert len(results) == 1
            assert results[0]["name"] == "Test Restaurant"

    def test_recalculate_restaurant_statistics(self, app, user, restaurant):
        """Test recalculating restaurant statistics."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        with app.app_context():
            # This should not raise an exception
            recalculate_restaurant_statistics(user_id)

            # Verify the function completed successfully
            assert True  # If we get here, no exception was raised

    def test_create_restaurant_with_form(self, app, user):
        """Test creating a restaurant with form data."""
        user_obj, user_id = user  # Unpack user and user_id
        with app.app_context():
            # Mock form data with proper structure for populate_obj
            form = Mock()
            form.name.data = "Form Restaurant"
            form.address_line_1.data = "123 Form St"
            form.city.data = "Form City"
            form.cuisine.data = "italian"
            form.service_level.data = "casual_dining"
            form.google_place_id.data = ""  # Empty string instead of Mock

            # Mock populate_obj to set attributes directly
            def mock_populate_obj(obj):
                obj.name = form.name.data
                obj.address_line_1 = form.address_line_1.data
                obj.city = form.city.data
                obj.cuisine = form.cuisine.data
                obj.service_level = form.service_level.data
                obj.google_place_id = form.google_place_id.data
                obj.type = "restaurant"  # Add required field

            form.populate_obj = mock_populate_obj

            restaurant, is_new = create_restaurant(user_id, form)

            assert restaurant.name == "Form Restaurant"
            assert restaurant.address_line_1 == "123 Form St"
            assert restaurant.city == "Form City"
            assert restaurant.cuisine == "Italian"
            assert restaurant.service_level == "casual_dining"
            assert is_new is True

    def test_update_restaurant_with_form(self, app, user, restaurant):
        """Test updating a restaurant with form data."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        with app.app_context():
            # Mock form data with proper field structure
            form = Mock()
            form.name.data = "Updated Form Restaurant"
            form.address_line_1.data = "456 Updated St"
            form.cuisine.data = "chinese"

            # Mock form iteration to return field objects for all fields
            field_mocks = []
            for field_name in ["name", "address_line_1", "cuisine"]:
                field_mock = Mock()
                field_mock.name = field_name
                field_mock.data = getattr(form, field_name).data
                field_mocks.append(field_mock)

            form.__iter__ = Mock(return_value=iter(field_mocks))

            updated_restaurant = update_restaurant(restaurant_id, user_id, form)

            assert updated_restaurant.name == "Updated Form Restaurant"
            assert updated_restaurant.address_line_1 == "456 Updated St"
            assert updated_restaurant.cuisine == "Chinese"

    def test_restaurant_services_error_handling(self, app, user):
        """Test error handling in restaurant services."""
        user_obj, user_id = user  # Unpack user and user_id
        with app.app_context():
            # Test with invalid user ID
            restaurants = get_restaurants_for_user(999)
            assert len(restaurants) == 0

            # Test with invalid restaurant ID
            restaurant = get_restaurant_for_user(999, user_id)
            assert restaurant is None

            # Test deleting non-existent restaurant
            success, message = delete_restaurant_by_id(999, user_id)
            assert success is False
            assert "not found" in message.lower()

    def test_restaurant_services_edge_cases(self, app, user):
        """Test edge cases in restaurant services."""
        user_obj, user_id = user  # Unpack user and user_id
        with app.app_context():
            # Test empty search
            cuisines = get_unique_cuisines(user_id)
            assert cuisines == []

            cities = get_unique_cities(user_id)
            assert cities == []

            service_levels = get_unique_service_levels(user_id)
            assert service_levels == []

            # Test filter options with no restaurants
            options = get_filter_options(user_id)
            assert options["cuisines"] == []
            assert options["cities"] == []
            assert options["service_levels"] == []
