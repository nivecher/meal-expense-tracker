"""Tests for restaurant services."""

import csv
import io
from unittest.mock import MagicMock, patch

import pytest
from flask import Response
from werkzeug.datastructures import FileStorage

from app.restaurants.models import Restaurant
from app.restaurants.services import (
    export_restaurants_to_csv,
    get_restaurant,
    import_restaurants_from_csv,
    process_restaurant_form,
)


def test_get_restaurant_success(session, test_restaurant):
    """Test getting an existing restaurant."""
    result = get_restaurant(test_restaurant.id)
    assert result == test_restaurant


def test_get_restaurant_not_found(session):
    """Test getting a non-existent restaurant."""
    with pytest.raises(Exception) as exc_info:
        get_restaurant(9999)
    assert "404" in str(exc_info.value)


def test_process_restaurant_form_success(session, test_restaurant):
    """Test processing a valid restaurant form."""

    class MockForm:
        def __init__(self):
            self.name = "Updated Name"
            self.city = "Updated City"
            self.phone = "123-456-7890"

        def __iter__(self):
            for field in ["name", "city", "phone"]:
                mock_field = MagicMock()
                mock_field.name = field
                mock_field.data = getattr(self, field, "")
                yield mock_field

    form = MockForm()
    success, message = process_restaurant_form(test_restaurant, form)

    assert success is True
    assert message == "Restaurant updated successfully"
    assert test_restaurant.name == "Updated Name"
    assert test_restaurant.city == "Updated City"
    assert test_restaurant.phone == "123-456-7890"


def test_import_restaurants_from_csv_success(session, test_user):
    """Test importing restaurants from a valid CSV file."""
    # Create a test CSV file in memory
    csv_data = [
        ["name", "city", "address", "phone", "website", "cuisine"],
        ["Test Restaurant 1", "Test City 1", "123 Test St", "111-111-1111", "http://test1.com", "Italian"],
        ["Test Restaurant 2", "Test City 2", "456 Test Ave", "222-222-2222", "http://test2.com", "Mexican"],
    ]

    # Create a file-like object
    file_data = io.StringIO()
    writer = csv.writer(file_data)
    writer.writerows(csv_data)
    file_data.seek(0)

    # Create a FileStorage object
    file = FileStorage(stream=file_data, filename="test_restaurants.csv", content_type="text/csv")

    # Call the import function
    success, message = import_restaurants_from_csv(file, test_user["user"])

    # Verify results
    assert success is True
    assert "2 restaurants imported successfully" in message

    # Verify the restaurants were created in the database
    restaurants = Restaurant.query.filter_by(user_id=test_user["id"]).all()
    assert len(restaurants) == 2
    assert {r.name for r in restaurants} == {"Test Restaurant 1", "Test Restaurant 2"}


def test_export_restaurants_to_csv(session, test_restaurant, test_user):
    """Test exporting restaurants to CSV format."""
    # Call the export function
    response = export_restaurants_to_csv(test_user["id"])

    # Verify the response
    assert isinstance(response, Response)
    assert response.mimetype == "text/csv"

    # Parse the CSV data
    csv_data = response.get_data(as_text=True)
    reader = csv.DictReader(io.StringIO(csv_data))
    rows = list(reader)

    # Verify the data
    assert len(rows) == 1  # Should have one restaurant
    assert rows[0]["name"] == test_restaurant.name
    assert rows[0]["city"] == test_restaurant.city


def test_import_restaurants_invalid_csv(session, test_user):
    """Test importing restaurants with invalid CSV data."""
    # Create invalid CSV data (missing required fields)
    csv_data = [
        ["name", "city"],  # Missing required fields
        ["Test Restaurant", "Test City"],
    ]

    # Create a file-like object
    file_data = io.StringIO()
    writer = csv.writer(file_data)
    writer.writerows(csv_data)
    file_data.seek(0)

    # Create a FileStorage object
    file = FileStorage(stream=file_data, filename="test_restaurants.csv", content_type="text/csv")

    # Call the import function and expect it to fail
    success, message = import_restaurants_from_csv(file, test_user["user"])

    # Verify results
    assert success is False
    assert "Error importing restaurants" in message


def test_import_restaurants_duplicate_restaurant(session, test_restaurant, test_user):
    """Test importing a restaurant that already exists."""
    # Create CSV data with a duplicate restaurant (same name and city)
    csv_data = [
        ["name", "city", "address", "phone", "website", "cuisine"],
        [test_restaurant.name, test_restaurant.city, "123 Test St", "111-111-1111", "http://test.com", "Test"],
    ]

    # Create a file-like object
    file_data = io.StringIO()
    writer = csv.writer(file_data)
    writer.writerows(csv_data)
    file_data.seek(0)

    # Create a FileStorage object
    file = FileStorage(stream=file_data, filename="test_restaurants.csv", content_type="text/csv")

    # Call the import function
    success, message = import_restaurants_from_csv(file, test_user["user"])

    # Verify results - should skip the duplicate
    assert success is True
    assert "1 restaurants imported successfully" in message
    assert "1 restaurants skipped (already exist)" in message


def test_process_restaurant_form_invalid_data():
    """Test processing a restaurant form with invalid data."""

    class MockForm:
        def __init__(self):
            self.name = ""  # Invalid: empty name
            self.city = "Test City"

        def __iter__(self):
            for field in ["name", "city"]:
                mock_field = MagicMock()
                mock_field.name = field
                mock_field.data = getattr(self, field, "")
                yield mock_field

    class MockRestaurant:
        def __init__(self):
            self.name = ""
            self.city = ""

    form = MockForm()
    restaurant = MockRestaurant()

    success, message = process_restaurant_form(restaurant, form)

    assert success is False
    assert "Name is required" in message


def test_export_restaurants_no_restaurants(session, test_user):
    """Test exporting when user has no restaurants."""
    # Delete any existing restaurants for the test user
    Restaurant.query.filter_by(user_id=test_user["id"]).delete()
    session.commit()

    # Call the export function
    response = export_restaurants_to_csv(test_user["id"])

    # Verify the response
    assert isinstance(response, Response)
    assert response.mimetype == "text/csv"

    # Parse the CSV data
    csv_data = response.get_data(as_text=True)
    reader = csv.DictReader(io.StringIO(csv_data))
    rows = list(reader)

    # Should only have the header row
    assert len(rows) == 0


def test_import_restaurants_missing_columns(session, test_user):
    """Test importing a CSV with missing required columns."""
    # Create CSV data with missing required columns
    csv_data = [
        ["name", "city"],  # Missing required columns
        ["Test Restaurant", "Test City"],
    ]

    # Create a file-like object
    file_data = io.StringIO()
    writer = csv.writer(file_data)
    writer.writerows(csv_data)
    file_data.seek(0)

    # Create a FileStorage object
    file = FileStorage(stream=file_data, filename="test_restaurants.csv", content_type="text/csv")

    # Call the import function
    success, message = import_restaurants_from_csv(file, test_user["user"])

    # Verify results
    assert success is False
    assert "Missing required columns" in message


def test_process_restaurant_form_sql_error(session, test_restaurant):
    """Test handling SQL errors during form processing."""

    class MockForm:
        def __init__(self):
            self.name = "Test Restaurant"
            self.city = "Test City"

        def __iter__(self):
            for field in ["name", "city"]:
                mock_field = MagicMock()
                mock_field.name = field
                mock_field.data = getattr(self, field, "")
                yield mock_field

    # Mock the session to raise an exception on commit
    with patch("app.restaurants.services.db.session.commit") as mock_commit:
        mock_commit.side_effect = Exception("Database error")

        form = MockForm()
        success, message = process_restaurant_form(test_restaurant, form)

        assert success is False
        assert "Error saving restaurant" in message
