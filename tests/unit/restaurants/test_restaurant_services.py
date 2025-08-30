"""Tests for restaurant services."""

import io
from unittest.mock import patch

import pytest
from werkzeug.datastructures import FileStorage

from app.restaurants.services import create_restaurant
from app.restaurants.services import get_restaurant_for_user as get_restaurant
from app.restaurants.services import import_restaurants_from_csv


def test_get_restaurant_success(session, test_restaurant):
    """Test getting an existing restaurant."""
    restaurant = get_restaurant(test_restaurant.id, test_restaurant.user_id)
    assert restaurant is not None
    assert restaurant.id == test_restaurant.id


def test_get_restaurant_not_found(session):
    """Test getting a non-existent restaurant."""
    with pytest.raises(Exception) as exc_info:
        get_restaurant(9999, 1)
    assert "404" in str(exc_info.value)


def test_create_restaurant_success(session, test_user):
    """Test creating a new restaurant."""

    # Create a mock form with required fields
    class MockForm:
        def populate_obj(self, obj):
            # Set all required fields on the restaurant object
            obj.name = "New Test Restaurant"
            obj.type = "restaurant"
            obj.description = "Test description"
            obj.address = "123 Test St"
            obj.city = "Test City"
            obj.state = "TS"
            obj.postal_code = "12345"
            obj.country = "Test Country"
            obj.phone = "123-456-7890"
            obj.website = "https://test.com"
            obj.email = "test@example.com"
            obj.cuisine = "Test Cuisine"

    form_mock = MockForm()

    # Call the create_restaurant function
    restaurant = create_restaurant(user_id=test_user.id, form=form_mock)

    # Verify the restaurant was created with the correct data
    assert restaurant is not None
    assert restaurant.name == "New Test Restaurant"
    assert restaurant.type == "restaurant"
    assert restaurant.description == "Test description"
    assert restaurant.address == "123 Test St"
    assert restaurant.city == "Test City"
    assert restaurant.state == "TS"
    assert restaurant.postal_code == "12345"
    assert restaurant.country == "Test Country"
    assert restaurant.phone == "123-456-7890"
    assert restaurant.website == "https://test.com"
    assert restaurant.email == "test@example.com"
    assert restaurant.cuisine == "Test Cuisine"
    assert restaurant.user_id == test_user.id


def test_import_restaurants_from_csv_success(session, test_user):
    """Test importing restaurants from a valid CSV file."""
    with patch("app.restaurants.services.services._process_csv_file") as mock_process_csv:
        # Mock the CSV processing to return test data
        mock_process_csv.return_value = (
            True,
            None,
            [
                {
                    "name": "Test Restaurant 1",
                    "cuisine": "Italian",
                    "address": "123 Main St",
                    "city": "Test City",
                    "state": "TS",
                    "zip": "12345",
                    "phone": "123-456-7890",
                    "website": "https://example1.com",
                }
            ],
        )

        # Create a test CSV file
        csv_data = """Name,Cuisine,Address,City,State,Zip,Phone,Website
Test Restaurant 1,Italian,123 Main St,Test City,TS,12345,123-456-7890,https://example1.com
"""
        file = FileStorage(
            stream=io.BytesIO(csv_data.encode("utf-8")),
            filename="test_restaurants.csv",
            content_type="text/csv",
        )

        # Import restaurants
        success, message = import_restaurants_from_csv(file, test_user.id)

        # Check results
        assert success is True
        assert "1 restaurants imported successfully" in message


def test_import_restaurants_invalid_csv(session, test_user):
    """Test importing restaurants with invalid CSV data."""
    with patch("app.restaurants.services.services._process_csv_file") as mock_process_csv:
        # Mock the CSV processing to return an error
        mock_process_csv.return_value = (False, "Missing required fields", None)

        # Create invalid CSV data (missing required fields)
        csv_data = """Name,City
Test Restaurant 1,Test City
"""
        file = FileStorage(
            stream=io.BytesIO(csv_data.encode("utf-8")),
            filename="test_restaurants.csv",
            content_type="text/csv",
        )

        # Import restaurants
        success, message = import_restaurants_from_csv(file, test_user.id)

        # Check results
        assert success is False
        assert "Missing required fields" in message


def test_import_restaurants_missing_columns(session, test_user):
    """Test importing a CSV with missing required columns."""
    with patch("app.restaurants.services.services._process_csv_file") as mock_process_csv:
        # Mock the CSV processing to return an error
        mock_process_csv.return_value = (
            False,
            "Missing required columns: cuisine",
            None,
        )

        # Create CSV data with missing required columns
        csv_data = """Name,Address,City,State,Zip,Phone,Website
Test Restaurant 1,123 Main St,Test City,TS,12345,123-456-7890,https://example1.com
"""
        file = FileStorage(
            stream=io.BytesIO(csv_data.encode("utf-8")),
            filename="test_restaurants.csv",
            content_type="text/csv",
        )

        # Import restaurants
        success, message = import_restaurants_from_csv(file, test_user.id)

        # Check results
        assert success is False
        assert "Missing required columns" in message


def test_import_restaurants_duplicate_restaurant(session, test_restaurant, test_user):
    """Test importing a restaurant that already exists."""
    with (
        patch("app.restaurants.services.services._process_csv_file") as mock_process_csv,
        patch("app.restaurants.services.services._import_restaurants_from_reader") as mock_import,
    ):

        # Mock the CSV processing to return test data
        mock_process_csv.return_value = (
            True,
            None,
            [
                {
                    "name": test_restaurant.name,
                    "cuisine": "Test Cuisine",
                    "address": "123 Main St",
                    "city": test_restaurant.city,
                    "state": "TS",
                    "zip": "12345",
                    "phone": "123-456-7890",
                    "website": "https://example.com",
                }
            ],
        )

        # Mock the import to return 0 successes (duplicate)
        mock_import.return_value = (
            0,
            [f"Restaurant '{test_restaurant.name}' already exists"],
        )

        # Create a test CSV file
        csv_data = f"""Name,Cuisine,Address,City,State,Zip,Phone,Website
{test_restaurant.name},Test Cuisine,123 Main St,{test_restaurant.city},TS,12345,123-456-7890,https://example.com
"""
        file = FileStorage(
            stream=io.BytesIO(csv_data.encode("utf-8")),
            filename="test_restaurants.csv",
            content_type="text/csv",
        )

        # Import restaurants
        success, message = import_restaurants_from_csv(file, test_user.id)

        # Check results - should indicate duplicate was skipped
        assert success is True
        assert "0 restaurants imported successfully" in message
