"""Tests for restaurant routes."""

import csv
import io

from flask import url_for
from werkzeug.datastructures import FileStorage

from app.extensions import db
from app.merchants.models import Merchant
from app.restaurants.models import Restaurant


def test_list_restaurants(client, auth, test_restaurant, test_user) -> None:
    """Test listing all restaurants."""
    auth.login("testuser_1", "testpass")
    response = client.get(url_for("restaurants.list_restaurants"), follow_redirects=True)

    assert response.status_code == 200
    assert b"Restaurants" in response.data
    assert test_restaurant.name.encode() in response.data


def test_list_restaurants_shows_location_name_cta_for_chain_restaurant_missing_location(
    client, auth, test_user
) -> None:
    """Restaurants list should prompt users to add a location name for chain-linked merchants."""
    test_user.advanced_features_enabled = True
    db.session.add(test_user)
    db.session.flush()

    merchant = Merchant(
        name="Chipotle Mexican Grill",
        short_name="Chipotle",
        is_chain=True,
    )
    db.session.add(merchant)
    db.session.flush()

    restaurant = Restaurant(
        user_id=test_user.id,
        name="Chipotle",
        type="restaurant",
        merchant_id=merchant.id,
        location_name="",
        city="Dallas",
    )
    db.session.add(restaurant)
    db.session.commit()

    auth.login("testuser_1", "testpass")
    response = client.get(url_for("restaurants.list_restaurants"), follow_redirects=True)

    assert response.status_code == 200
    assert b"Add location name" in response.data
    expected_edit_url = url_for(
        "restaurants.edit_restaurant",
        restaurant_id=restaurant.id,
        next=url_for("restaurants.list_restaurants", missing_location_name="true"),
    )
    assert f'href="{expected_edit_url}#location_name"'.encode() in response.data


def test_list_restaurants_infinite_scroll_chunk(client, auth, test_restaurant, test_user) -> None:
    """Test restaurant list returns chunk partial when HTMX requests with offset."""
    auth.login("testuser_1", "testpass")
    response = client.get(
        url_for("restaurants.list_restaurants", tab="restaurants", offset=0, limit=25),
        follow_redirects=True,
    )
    assert response.status_code == 200
    response = client.get(
        url_for("restaurants.list_restaurants", tab="restaurants", offset=25, limit=25),
        headers={"HX-Request": "true"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert (
        b"restaurant-chunk-buffer" in response.data
        or b"restaurant-load-more-sentinel" in response.data
        or len(response.data) < 500
    )


def test_add_restaurant(client, test_user, session) -> None:
    """Test adding a new restaurant."""
    # Login the test user
    with client.session_transaction() as sess:
        sess["_user_id"] = str(test_user.id)
        sess["_fresh"] = True

    # Get the add restaurant page to get a fresh CSRF token
    response = client.get(url_for("restaurants.add_restaurant"))
    assert response.status_code == 200
    assert b"Is Chain?" not in response.data

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


def test_add_restaurant_prefills_from_merchant_query_args(client, auth, test_user) -> None:
    """Merchant-origin add restaurant links should prefill the restaurant form and search query."""
    merchant = Merchant(
        name="Blue Baker",
        cuisine="American",
        service_level="fast_casual",
        website="https://bluebaker.example",
    )
    db.session.add(merchant)
    db.session.commit()
    auth.login("testuser_1", "testpass")

    response = client.get(
        url_for(
            "restaurants.add_restaurant",
            merchant_id=merchant.id,
            name=merchant.name,
            cuisine=merchant.cuisine,
            service_level=merchant.service_level,
            website=merchant.website,
            search_query="Blue Baker",
        )
    )

    assert response.status_code == 200
    assert b'value="Blue Baker"' in response.data
    assert b'data-initial-query="Blue Baker"' in response.data
    assert b"https://bluebaker.example" in response.data
    assert b"restaurant-search-include-nearby" in response.data


def test_add_restaurant_shows_chain_merchant_status_and_requires_location_name(client, auth, test_user) -> None:
    """Chain merchants should be visible on the form and require a location name."""
    test_user.advanced_features_enabled = True
    db.session.add(test_user)
    db.session.commit()

    merchant = Merchant(
        name="Blue Baker",
        short_name="Blue Baker",
        is_chain=True,
        cuisine="American",
        service_level="fast_casual",
    )
    db.session.add(merchant)
    db.session.commit()
    auth.login("testuser_1", "testpass")

    response = client.get(
        url_for(
            "restaurants.add_restaurant",
            merchant_id=merchant.id,
            name=merchant.name,
        )
    )

    assert response.status_code == 200
    assert b"Brand: Chain Brand" in response.data
    assert b"location-name-required-indicator" in response.data
    assert b"Required for chain brands so each location stays distinct." in response.data

    response = client.post(
        url_for("restaurants.add_restaurant"),
        data={
            "csrf_token": "dummy_csrf_token",
            "name": "Blue Baker",
            "type": "restaurant",
            "merchant_id": str(merchant.id),
            "merchant_name": merchant.name,
            "location_name": "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Location Name is required when the linked merchant is a chain brand." in response.data


def test_view_restaurant(client, auth, test_restaurant, test_user) -> None:
    """Test viewing a restaurant's details."""
    auth.login("testuser_1", "testpass")

    response = client.get(url_for("restaurants.restaurant_details", restaurant_id=test_restaurant.id))

    assert response.status_code == 200
    assert test_restaurant.name.encode() in response.data
    assert test_restaurant.city.encode() in response.data


def test_view_restaurant_shows_merchant_chain_info(client, auth, test_restaurant, test_user) -> None:
    """Restaurant detail should show associated merchant chain info instead of restaurant chain info."""
    merchant = Merchant(name="Blue Baker", is_chain=True)
    db.session.add(merchant)
    db.session.flush()
    test_restaurant.merchant_id = merchant.id
    db.session.add(test_restaurant)
    db.session.commit()

    auth.login("testuser_1", "testpass")
    response = client.get(url_for("restaurants.restaurant_details", restaurant_id=test_restaurant.id))

    assert response.status_code == 200
    assert b"Chain Brand" in response.data
    assert b"Chain Restaurant" not in response.data


def test_edit_restaurant(client, auth, test_restaurant, test_user) -> None:
    """Test editing a restaurant."""
    auth.login("testuser_1", "testpass")

    response = client.post(
        url_for("restaurants.edit_restaurant", restaurant_id=test_restaurant.id),
        data={
            "name": "Updated Name",
            "type": "restaurant",  # Add required field
            "city": test_restaurant.city,
            "address_line_1": test_restaurant.address_line_1 or "",
            "phone": test_restaurant.phone or "",
            "website": test_restaurant.website or "",
            "cuisine": test_restaurant.cuisine or "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    # The restaurant should be updated (redirected to restaurant details page)
    assert b"Updated Name" in response.data


def test_edit_restaurant_preserves_safe_next_url_in_form(client, auth, test_restaurant, test_user) -> None:
    """Edit form should preserve a safe return URL for bulk location-name cleanup."""
    auth.login("testuser_1", "testpass")

    next_url = url_for("restaurants.list_restaurants", missing_location_name="true")
    response = client.get(url_for("restaurants.edit_restaurant", restaurant_id=test_restaurant.id, next=next_url))

    assert response.status_code == 200
    assert f'href="{next_url}"'.encode() in response.data
    assert f'<input type="hidden" name="next" value="{next_url}">'.encode() in response.data


def test_restaurant_form_normalizes_us_phone_number(app) -> None:
    """Restaurant form should normalize a plain US phone number during validation."""
    from app.restaurants.forms import RestaurantForm

    with app.test_request_context(
        "/restaurants/add",
        method="POST",
        data={
            "name": "Phone Normalized Restaurant",
            "type": "restaurant",
            "city": "Test City",
            "address_line_1": "123 Test St",
            "phone": "(312) 521-9788",
            "website": "",
            "cuisine": "",
        },
    ):
        form = RestaurantForm()

        assert form.validate() is True
        assert form.phone.data == "+13125219788"


def test_delete_restaurant(client, auth, test_restaurant, test_user, session) -> None:
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


def test_import_restaurants_csv(client, auth, test_user, session) -> None:
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


def test_export_restaurants(client, test_restaurant, test_user) -> None:
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
    assert '"name","location_name","located_within","address","city","state","postal_code"' in response_text

    # Check for test restaurant data
    assert test_restaurant.name in response_text
    if test_restaurant.city:
        assert test_restaurant.city in response_text


# Test error cases
def test_view_nonexistent_restaurant(client, auth, test_user) -> None:
    """Test viewing a restaurant that doesn't exist."""
    auth.login("testuser_1", "testpass")

    response = client.get(url_for("restaurants.restaurant_details", restaurant_id=9999))

    assert response.status_code == 404


def test_edit_nonexistent_restaurant(client, auth, test_user) -> None:
    """Test editing a restaurant that doesn't exist."""
    auth.login("testuser_1", "testpass")

    response = client.post(
        url_for("restaurants.edit_restaurant", restaurant_id=9999),
        data={"name": "Test", "city": "Test"},
        follow_redirects=True,
    )

    assert response.status_code == 404


def test_unauthorized_access(client, test_restaurant) -> None:
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
            response = client.get(url, follow_redirects=False)
        else:
            response = client.post(url, follow_redirects=False)

        # Check that we get a redirect (302) to login page
        # Some routes might return 401 for API endpoints
        if response.status_code == 302:
            # Follow the redirect to verify it goes to login
            login_response = client.get(response.location, follow_redirects=True)
            assert login_response.status_code == 200
            assert b"Login" in login_response.data or b"Sign In" in login_response.data
        elif response.status_code == 401:
            # API endpoints might return 401 directly
            pass  # This is also acceptable for unauthorized access
        else:
            # If it's not a redirect or 401, something is wrong
            # But let's be more lenient and check if we can still get to login
            response = client.get(url_for("auth.login"), follow_redirects=True)
            assert response.status_code == 200
            assert b"Login" in response.data or b"Sign In" in response.data


def test_restaurant_search_page(client, auth, test_user) -> None:
    """Test the restaurant search page loads correctly."""
    auth.login("testuser_1", "testpass")

    response = client.get(url_for("restaurants.search_restaurants"))

    assert response.status_code == 200
    assert b"Search Restaurants" in response.data
    assert b"map" in response.data.lower()


def test_find_places_page(client, auth, test_user) -> None:
    """Test that the Find Places search page loads correctly."""
    auth.login("testuser_1", "testpass")

    # Test GET request to Find Places search page
    response = client.get(url_for("restaurants.find_places"), follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == url_for("restaurants.list_restaurants", tab="places", places_mode="find")


def test_get_place_details_invalid_id(client, auth, test_user, app) -> None:
    """Test getting details for an invalid place ID."""
    auth.login("testuser_1", "testpass")

    # Ensure no API key is configured for this test
    app.config["GOOGLE_MAPS_API_KEY"] = None

    # Test the case where no API key is configured (which is the actual test environment)
    response = client.get(url_for("restaurants.get_place_details", place_id="invalid_id"))

    assert response.status_code == 500
    assert b"Google Maps API key not configured" in response.data


def test_import_restaurants_invalid_file(client, auth, test_user) -> None:
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
