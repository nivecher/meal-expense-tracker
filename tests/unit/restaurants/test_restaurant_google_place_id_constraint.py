"""Tests for Google Place ID uniqueness constraint in restaurants."""

from unittest.mock import MagicMock

import pytest

from app.restaurants.exceptions import (
    DuplicateGooglePlaceIdError,
    DuplicateRestaurantError,
)
from app.restaurants.models import Restaurant
from app.restaurants.services import create_restaurant, validate_restaurant_uniqueness


class TestGooglePlaceIdConstraint:
    """Test suite for Google Place ID uniqueness constraint."""

    def test_unique_google_place_id_per_user_database_constraint(self, session, test_user, test_user2) -> None:
        """Test database-level unique constraint for google_place_id per user."""
        google_place_id = "ChIJ_test_place_id_123"

        # User 1 creates restaurant with Google Place ID
        restaurant1 = Restaurant(
            user_id=test_user.id, name="Test Restaurant", city="Test City", google_place_id=google_place_id
        )
        session.add(restaurant1)
        session.commit()

        # User 2 can create restaurant with same Google Place ID (different user)
        restaurant2 = Restaurant(
            user_id=test_user2.id,
            name="Same Restaurant Different User",
            city="Test City",
            google_place_id=google_place_id,
        )
        session.add(restaurant2)
        session.commit()  # Should succeed

        # User 1 tries to create another restaurant with same Google Place ID
        restaurant3 = Restaurant(
            user_id=test_user.id, name="Duplicate Restaurant", city="Different City", google_place_id=google_place_id
        )
        session.add(restaurant3)

        # Should raise IntegrityError due to unique constraint
        with pytest.raises(Exception):  # SQLAlchemy IntegrityError
            session.commit()

        session.rollback()

    def test_null_google_place_id_allowed_multiple_times(self, session, test_user) -> None:
        """Test that multiple restaurants can have NULL google_place_id."""
        # Create multiple restaurants without Google Place ID
        restaurant1 = Restaurant(user_id=test_user.id, name="Restaurant 1", city="City 1", google_place_id=None)
        restaurant2 = Restaurant(user_id=test_user.id, name="Restaurant 2", city="City 2", google_place_id=None)

        session.add_all([restaurant1, restaurant2])
        session.commit()  # Should succeed

        assert restaurant1.id != restaurant2.id
        assert restaurant1.google_place_id is None
        assert restaurant2.google_place_id is None

    def test_validate_restaurant_uniqueness_google_place_id_duplicate(self, session, test_user) -> None:
        """Test validation function catches Google Place ID duplicates."""
        google_place_id = "ChIJ_test_validation_123"

        # Create existing restaurant
        existing = Restaurant(
            user_id=test_user.id, name="Existing Restaurant", city="Test City", google_place_id=google_place_id
        )
        session.add(existing)
        session.commit()

        # Try to validate new restaurant with same Google Place ID
        with pytest.raises(DuplicateGooglePlaceIdError) as exc_info:
            validate_restaurant_uniqueness(
                user_id=test_user.id, name="New Restaurant", city="Different City", google_place_id=google_place_id
            )

        error = exc_info.value
        assert error.google_place_id == google_place_id
        assert error.existing_restaurant.id == existing.id
        # The error message intentionally omits "Google Place ID" from user-facing text
        assert "Existing Restaurant" in error.message
        assert "Test City" in error.message

    def test_validate_restaurant_uniqueness_name_city_duplicate(self, session, test_user) -> None:
        """Test validation function catches name/city duplicates."""
        # Create existing restaurant
        existing = Restaurant(user_id=test_user.id, name="Test Restaurant", city="Test City", google_place_id=None)
        session.add(existing)
        session.commit()

        # Try to validate new restaurant with same name/city
        with pytest.raises(DuplicateRestaurantError) as exc_info:
            validate_restaurant_uniqueness(
                user_id=test_user.id, name="Test Restaurant", city="Test City", google_place_id=None
            )

        error = exc_info.value
        assert error.name == "Test Restaurant"
        assert error.city == "Test City"
        assert error.existing_restaurant.id == existing.id

    def test_validate_restaurant_uniqueness_exclude_id(self, session, test_user) -> None:
        """Test validation excludes specific restaurant ID (for updates)."""
        google_place_id = "ChIJ_test_exclude_123"

        # Create existing restaurant
        existing = Restaurant(
            user_id=test_user.id, name="Test Restaurant", city="Test City", google_place_id=google_place_id
        )
        session.add(existing)
        session.commit()

        # Validation should pass when excluding the existing restaurant's ID
        validate_restaurant_uniqueness(
            user_id=test_user.id,
            name="Test Restaurant",
            city="Test City",
            google_place_id=google_place_id,
            exclude_id=existing.id,
        )  # Should not raise

    def test_create_restaurant_with_duplicate_google_place_id(self, session, test_user) -> None:
        """Test create_restaurant function with duplicate Google Place ID."""
        google_place_id = "ChIJ_test_create_duplicate_123"

        # Create existing restaurant
        existing = Restaurant(
            user_id=test_user.id, name="Existing Restaurant", city="Test City", google_place_id=google_place_id
        )
        session.add(existing)
        session.commit()

        # Create mock form for new restaurant
        class MockForm:
            def __init__(self):
                self.name = MagicMock()
                self.name.data = "New Restaurant"
                self.city = MagicMock()
                self.city.data = "Different City"
                self.google_place_id = MagicMock()
                self.google_place_id.data = google_place_id

            def populate_obj(self, obj):
                obj.name = "New Restaurant"
                obj.city = "Different City"
                obj.google_place_id = google_place_id
                obj.type = "restaurant"
                obj.description = "Test description"
                obj.address_line_1 = "789 Test St"
                obj.state = "TS"
                obj.postal_code = "12345"
                obj.country = "Test Country"
                obj.phone = "123-456-7892"
                obj.website = "https://newtest.com"
                obj.email = "newtest@example.com"
                obj.cuisine = "Test Cuisine"
                obj.is_chain = False
                obj.rating = None
                obj.notes = "Test notes"

        form = MockForm()

        # Should raise DuplicateGooglePlaceIdError
        with pytest.raises(DuplicateGooglePlaceIdError) as exc_info:
            create_restaurant(test_user.id, form)

        error = exc_info.value
        assert error.google_place_id == google_place_id
        assert error.existing_restaurant.id == existing.id

    def test_duplicate_google_place_id_error_to_dict(self, session, test_user) -> None:
        """Test DuplicateGooglePlaceIdError to_dict method."""
        google_place_id = "ChIJ_test_to_dict_123"

        # Create restaurant for the error
        restaurant = Restaurant(
            user_id=test_user.id, name="Test Restaurant", city="Test City", google_place_id=google_place_id
        )
        session.add(restaurant)
        session.commit()

        # Create error
        error = DuplicateGooglePlaceIdError(google_place_id, restaurant)
        error_dict = error.to_dict()

        assert error_dict["code"] == "DUPLICATE_GOOGLE_PLACE_ID"
        assert error_dict["field"] == "google_place_id"
        assert error_dict["google_place_id"] == google_place_id
        assert error_dict["existing_restaurant"]["id"] == restaurant.id
        assert error_dict["existing_restaurant"]["name"] == "Test Restaurant"
        assert error_dict["existing_restaurant"]["city"] == "Test City"
        assert error_dict["existing_restaurant"]["full_name"] == "Test Restaurant - Test City"

    def test_different_users_can_have_same_google_place_id(self, session, test_user, test_user2) -> None:
        """Test that different users can have restaurants with same Google Place ID."""
        google_place_id = "ChIJ_test_different_users_123"

        # Create mock forms
        class MockForm1:
            def __init__(self):
                self.name = MagicMock()
                self.name.data = "Restaurant for User 1"
                self.city = MagicMock()
                self.city.data = "Test City"
                self.google_place_id = MagicMock()
                self.google_place_id.data = google_place_id

            def populate_obj(self, obj):
                obj.name = "Restaurant for User 1"
                obj.city = "Test City"
                obj.google_place_id = google_place_id
                obj.type = "restaurant"
                obj.description = "Test description"
                obj.address_line_1 = "123 Test St"
                obj.state = "TS"
                obj.postal_code = "12345"
                obj.country = "Test Country"
                obj.phone = "123-456-7890"
                obj.website = "https://test.com"
                obj.email = "test1@example.com"
                obj.cuisine = "Test Cuisine"
                obj.is_chain = False
                obj.rating = None
                obj.notes = "Test notes"

        class MockForm2:
            def __init__(self):
                self.name = MagicMock()
                self.name.data = "Restaurant for User 2"
                self.city = MagicMock()
                self.city.data = "Test City"
                self.google_place_id = MagicMock()
                self.google_place_id.data = google_place_id

            def populate_obj(self, obj):
                obj.name = "Restaurant for User 2"
                obj.city = "Test City"
                obj.google_place_id = google_place_id
                obj.type = "restaurant"
                obj.description = "Test description"
                obj.address_line_1 = "456 Test St"
                obj.state = "TS"
                obj.postal_code = "12345"
                obj.country = "Test Country"
                obj.phone = "123-456-7891"
                obj.website = "https://test2.com"
                obj.email = "test2@example.com"
                obj.cuisine = "Test Cuisine"
                obj.is_chain = False
                obj.rating = None
                obj.notes = "Test notes"

        form1 = MockForm1()
        form2 = MockForm2()

        # Both should succeed
        restaurant1, is_new1 = create_restaurant(test_user.id, form1)
        restaurant2, is_new2 = create_restaurant(test_user2.id, form2)

        assert is_new1 is True
        assert is_new2 is True
        assert restaurant1.google_place_id == google_place_id
        assert restaurant2.google_place_id == google_place_id
        assert restaurant1.user_id == test_user.id
        assert restaurant2.user_id == test_user2.id

    def test_validate_restaurant_uniqueness_google_place_id_priority(self, session, test_user) -> None:
        """Test that Google Place ID validation takes priority over name/city."""
        google_place_id = "ChIJ_test_priority_123"

        # Create existing restaurant with same Google Place ID but different name/city
        existing = Restaurant(
            user_id=test_user.id, name="Different Name", city="Different City", google_place_id=google_place_id
        )
        session.add(existing)
        session.commit()

        # Try to create restaurant with same Google Place ID but different name/city
        with pytest.raises(DuplicateGooglePlaceIdError) as exc_info:
            validate_restaurant_uniqueness(
                user_id=test_user.id,
                name="Completely Different Name",
                city="Completely Different City",
                google_place_id=google_place_id,
            )

            # Should raise DuplicateGooglePlaceIdError, not DuplicateRestaurantError
            error = exc_info.value
            assert isinstance(error, DuplicateGooglePlaceIdError)
            assert error.google_place_id == google_place_id
