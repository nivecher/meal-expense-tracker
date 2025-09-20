"""Tests for restaurant routes."""

import csv
import io

from flask import url_for
from werkzeug.datastructures import FileStorage


def test_list_restaurants(client, auth, test_restaurant, test_user):
    """Test listing all restaurants."""
    auth.login("testuser_1", "testpass")
    response = client.get(url_for("restaurants.list_restaurants"), follow_redirects=True)

    assert response.status_code == 200
    assert b"Restaurants" in response.data
    assert test_restaurant.name.encode() in response.data


def test_add_restaurant(client, test_user, session):
    """Test adding a new restaurant."""
    # Login the test user
    with client.session_transaction() as sess:
        sess["_user_id"] = str(test_user.id)
        sess["_fresh"] = True

    # Get the add restaurant page to get a fresh CSRF token
    response = client.get(url_for("restaurants.add_restaurant"))
    assert response.status_code == 200

    # Since we're in test mode, we can use a dummy CSRF token
    response = client.post(
        url_for("restaurants.add_restaurant"),
        data={
            "csrf_token": "dummy_csrf_token",
            "name": "New Test Restaurant",
            "type": "restaurant",  # Add required field
            "city": "Test City",
            "address": "123 Test St",
            "phone": "123-456-7890",
            "website": "http://test.com",
            "cuisine": "American",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    # The restaurant should be in the list (redirected to restaurant list page)
    assert b"New Test Restaurant" in response.data


def test_view_restaurant(client, auth, test_restaurant, test_user):
    """Test viewing a restaurant's details."""
    auth.login("testuser_1", "testpass")

    response = client.get(url_for("restaurants.restaurant_details", restaurant_id=test_restaurant.id))

    assert response.status_code == 200
    assert test_restaurant.name.encode() in response.data
    assert test_restaurant.city.encode() in response.data


def test_edit_restaurant(client, auth, test_restaurant, test_user):
    """Test editing a restaurant."""
    auth.login("testuser_1", "testpass")

    response = client.post(
        url_for("restaurants.edit_restaurant", restaurant_id=test_restaurant.id),
        data={
            "name": "Updated Name",
            "type": "restaurant",  # Add required field
            "city": test_restaurant.city,
            "address": test_restaurant.address or "",
            "phone": test_restaurant.phone or "",
            "website": test_restaurant.website or "",
            "cuisine": test_restaurant.cuisine or "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    # The restaurant should be updated (redirected to restaurant details page)
    assert b"Updated Name" in response.data


def test_delete_restaurant(client, auth, test_restaurant, test_user, session):
    """Test deleting a restaurant."""
    auth.login("testuser_1", "testpass")

    response = client.post(
        url_for("restaurants.delete_restaurant", restaurant_id=test_restaurant.id),
        follow_redirects=True,
    )

    assert response.status_code == 200
    # The restaurant should be deleted (redirected to restaurant list page)
    # We can verify this by checking that the restaurant is not in the database

    # Verify it's gone from the database
    from app.extensions import db
    from app.restaurants.models import Restaurant

    assert db.session.get(Restaurant, test_restaurant.id) is None


def test_import_restaurants_csv(client, auth, test_user, session):
    """Test importing restaurants from CSV."""
    auth.login("testuser_1", "testpass")

    # Create a test CSV file
    csv_data = [
        ["name", "city", "address", "phone", "website", "cuisine", "postal_code"],
        [
            "CSV Restaurant 1",
            "Test City",
            "123 Test St",
            "123-456-7890",
            "http://test1.com",
            "Italian",
            "12345",
        ],
        [
            "CSV Restaurant 2",
            "Test City",
            "456 Test Ave",
            "987-654-3210",
            "http://test2.com",
            "Mexican",
            "54321",
        ],
    ]

    # Create a file-like object
    file_data = io.BytesIO()
    text_wrapper = io.TextIOWrapper(file_data, encoding="utf-8")
    writer = csv.writer(text_wrapper)
    writer.writerows(csv_data)
    text_wrapper.flush()
    file_data.seek(0)

    # Create a FileStorage object
    file = FileStorage(stream=file_data, filename="test_restaurants.csv", content_type="text/csv")

    response = client.post(
        url_for("restaurants.import_restaurants"),
        data={"file": file},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    # Check that we're on the restaurant list page (where we get redirected after import)
    assert b"Restaurants" in response.data
    assert b"CSV Restaurant 1" in response.data
    assert b"CSV Restaurant 2" in response.data


def test_export_restaurants(client, test_restaurant, test_user):
    """Test exporting restaurants to CSV."""
    # Set up the session directly to simulate being logged in
    with client.session_transaction() as sess:
        sess["_user_id"] = str(test_user.id)  # Flask-Login's session key
        sess["_fresh"] = True  # Mark session as fresh

    # Make the request to export restaurants
    response = client.get(url_for("restaurants.export_restaurants"), follow_redirects=False)

    # Debug output
    print(f"Response status code: {response.status_code}")
    print(f"Response content type: {response.content_type}")
    print(f"Response headers: {response.headers}")

    # Check if we got redirected (shouldn't happen if logged in)
    if response.status_code == 302:
        print(f"Redirected to: {response.location}")
        assert False, "Unexpected redirect. User may not be properly authenticated."

    # Verify the response is a CSV file
    assert response.status_code == 200
    assert response.content_type == "text/csv; charset=utf-8"

    # Check for content disposition header
    assert "Content-Disposition" in response.headers
    assert "restaurants.csv" in response.headers["Content-Disposition"]

    # Get the response data as text
    response_text = response.get_data(as_text=True)
    print(f"CSV data first line: {response_text.splitlines()[0] if response_text else 'Empty response'}")

    # Check for CSV header (actual headers from the export)
    assert '"name","address","city","state","postal_code"' in response_text

    # Check for test restaurant data
    assert test_restaurant.name in response_text
    if test_restaurant.city:
        assert test_restaurant.city in response_text


# Test error cases
def test_view_nonexistent_restaurant(client, auth, test_user):
    """Test viewing a restaurant that doesn't exist."""
    auth.login("testuser_1", "testpass")

    response = client.get(url_for("restaurants.restaurant_details", restaurant_id=9999))

    assert response.status_code == 404


def test_edit_nonexistent_restaurant(client, auth, test_user):
    """Test editing a restaurant that doesn't exist."""
    auth.login("testuser_1", "testpass")

    response = client.post(
        url_for("restaurants.edit_restaurant", restaurant_id=9999),
        data={"name": "Test", "city": "Test"},
        follow_redirects=True,
    )

    assert response.status_code == 404


def test_unauthorized_access(client, test_restaurant):
    """Test that unauthorized users are redirected to login."""
    # Try to access protected routes without logging in
    urls = [
        (url_for("restaurants.list_restaurants"), "GET"),
        (url_for("restaurants.add_restaurant"), "GET"),
        (url_for("restaurants.add_restaurant"), "POST"),
        (
            url_for("restaurants.restaurant_details", restaurant_id=test_restaurant.id),
            "GET",
        ),
        (
            url_for("restaurants.edit_restaurant", restaurant_id=test_restaurant.id),
            "GET",
        ),
        (
            url_for("restaurants.edit_restaurant", restaurant_id=test_restaurant.id),
            "POST",
        ),
        (
            url_for("restaurants.delete_restaurant", restaurant_id=test_restaurant.id),
            "POST",
        ),
        (url_for("restaurants.import_restaurants"), "GET"),
        (url_for("restaurants.import_restaurants"), "POST"),
        (url_for("restaurants.export_restaurants"), "GET"),
        (url_for("restaurants.search_restaurants"), "GET"),
        (url_for("restaurants.search_places"), "GET"),
        (url_for("restaurants.get_place_details", place_id="test123"), "GET"),
    ]

    for url, method in urls:
        if method == "GET":
            response = client.get(url, follow_redirects=True)
        else:
            response = client.post(url, follow_redirects=True)
        # Check that we're redirected to login page
        assert response.status_code == 200
        assert b"Login" in response.data


def test_restaurant_search_page(client, auth, test_user):
    """Test the restaurant search page loads correctly."""
    auth.login("testuser_1", "testpass")

    response = client.get(url_for("restaurants.search_restaurants"))

    assert response.status_code == 200
    assert b"Search Restaurants" in response.data
    assert b"map" in response.data.lower()


def test_find_places_page(client, auth, test_user):
    """Test that the Find Places search page loads correctly."""
    auth.login("testuser_1", "testpass")

    # Test GET request to Find Places search page
    response = client.get(url_for("restaurants.find_places"))
    assert response.status_code == 200
    assert b"Find Restaurants" in response.data


def test_get_place_details_invalid_id(client, auth, test_user):
    """Test getting details for an invalid place ID."""
    auth.login("testuser_1", "testpass")

    # Test the case where no API key is configured (which is the actual test environment)
    response = client.get(url_for("restaurants.get_place_details", place_id="invalid_id"))

    assert response.status_code == 500
    assert b"Google Maps API key not configured" in response.data


def test_import_restaurants_invalid_file(client, auth, test_user):
    """Test importing restaurants with invalid file type."""
    auth.login("testuser_1", "testpass")

    # Create a test file with wrong content type
    file_data = io.BytesIO(b"This is not a CSV file")
    file = FileStorage(stream=file_data, filename="test.txt", content_type="text/plain")

    response = client.post(
        url_for("restaurants.import_restaurants"),
        data={"file": file},
        content_type="multipart/form-data",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Unsupported file type" in response.data
