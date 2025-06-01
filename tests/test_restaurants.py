from app.restaurants.models import Restaurant
from sqlalchemy.exc import SQLAlchemyError
from unittest.mock import Mock


def test_restaurants_list(client, auth):
    """Test listing restaurants."""
    auth.create_user()
    auth.login()
    response = client.get("/restaurants/")
    assert response.status_code == 200
    assert b"Restaurants" in response.data


def test_add_restaurant(client, auth):
    """Test adding a restaurant."""
    auth.create_user()
    auth.login()
    response = client.post(
        "/restaurants/add",
        data={
            "name": "Test Restaurant",
            "city": "Test City",
            "address": "123 Test St",
            "phone": "123-456-7890",
            "website": "http://test.com",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Restaurant added successfully" in response.data


def test_edit_restaurant(client, auth):
    """Test editing a restaurant."""
    auth.create_user()
    auth.login()
    # First add a restaurant
    client.post(
        "/restaurants/add",
        data={
            "name": "Test Restaurant",
            "city": "Test City",
            "address": "123 Test St",
            "phone": "123-456-7890",
            "website": "http://test.com",
        },
    )

    # Get the restaurant ID after creation
    restaurant = Restaurant.query.filter_by(name="Test Restaurant").first()
    assert restaurant is not None

    # Edit the restaurant
    response = client.post(
        f"/restaurants/{restaurant.id}/edit",
        data={
            "name": "Updated Restaurant",
            "city": "Updated City",
            "address": "456 Updated St",
            "phone": "098-765-4321",
            "website": "http://updated.com",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Restaurant updated successfully" in response.data

    # Verify changes
    response = client.get("/restaurants/", follow_redirects=True)
    assert response.status_code == 200
    assert b"Updated Restaurant" in response.data


def test_restaurant_details(client, auth):
    """Test viewing restaurant details."""
    auth.create_user()
    auth.login()
    # Add a restaurant first
    client.post(
        "/restaurants/add",
        data={
            "name": "Test Restaurant",
            "type": "restaurant",
            "city": "Test City",
            "state": "CA",
            "zip_code": "12345",
            "address": "123 Test St",
            "phone": "123-456-7890",
            "website": "http://test.com",
            "cuisine": "American",
            "price_range": "$$",
        },
    )
    # Get the restaurant ID after creation
    restaurant = Restaurant.query.filter_by(name="Test Restaurant").first()
    assert restaurant is not None

    # Add an expense for the restaurant
    client.post(
        "/expenses/add",
        data={
            "restaurant_id": restaurant.id,
            "date": "2024-02-20",
            "meal_type": "Lunch",
            "amount": "25.50",
            "notes": "Test expense",
        },
    )

    # View restaurant details
    response = client.get(f"/restaurants/{restaurant.id}/details")
    assert response.status_code == 200
    assert b"Test Restaurant" in response.data
    assert b"Test City" in response.data
    assert b"123 Test St" in response.data
    assert b"<td>$25.50</td>" in response.data
    assert b"<td>Lunch</td>" in response.data


def test_restaurant_details_not_found(client, auth):
    """Test viewing details of a non-existent restaurant."""
    auth.create_user()
    auth.login()
    response = client.get("/restaurants/999/details", follow_redirects=True)
    assert response.status_code == 404


def test_restaurant_details_database_error(client, auth, monkeypatch):
    """Test handling database error when viewing restaurant details."""
    auth.create_user()
    auth.login()
    # Add a restaurant first
    client.post(
        "/restaurants/add",
        data={
            "name": "Test Restaurant",
            "type": "restaurant",
            "city": "Test City",
            "state": "CA",
            "zip_code": "12345",
            "address": "123 Test St",
            "phone": "123-456-7890",
            "website": "http://test.com",
            "cuisine": "American",
            "price_range": "$$",
        },
    )
    # Get the restaurant ID after creation
    restaurant = Restaurant.query.filter_by(name="Test Restaurant").first()
    assert restaurant is not None

    # Simulate a database error
    monkeypatch.setattr(Restaurant, "query", Mock(side_effect=SQLAlchemyError))

    # Try to view restaurant details
    response = client.get(f"/restaurants/{restaurant.id}/details")
    assert response.status_code == 200
    assert b"Error loading restaurant details. Please try again." in response.data


def test_restaurant_details_with_multiple_expenses(client, auth):
    """Test viewing restaurant details with multiple expenses."""
    auth.create_user()
    auth.login()
    # Add a restaurant first
    client.post(
        "/restaurants/add",
        data={
            "name": "Test Restaurant",
            "type": "restaurant",
            "city": "Test City",
            "state": "CA",
            "zip_code": "12345",
            "address": "123 Test St",
            "phone": "123-456-7890",
            "website": "http://test.com",
            "cuisine": "American",
            "price_range": "$$",
        },
    )
    # Get the restaurant ID after creation
    restaurant = Restaurant.query.filter_by(name="Test Restaurant").first()
    assert restaurant is not None

    # Add multiple expenses
    expenses = [
        {
            "date": "2024-02-20",
            "meal_type": "Lunch",
            "amount": "25.50",
            "notes": "First visit",
        },
        {
            "date": "2024-02-21",
            "meal_type": "Dinner",
            "amount": "45.75",
            "notes": "Second visit",
        },
    ]

    for expense_data in expenses:
        client.post(
            "/expenses/add",
            data={
                **expense_data,
                "restaurant_id": restaurant.id,
            },
        )

    # View restaurant details
    response = client.get(f"/restaurants/{restaurant.id}/details")
    assert response.status_code == 200
    assert b"Test Restaurant" in response.data
    assert b"2024-02-20" in response.data
    assert b"$25.50" in response.data
    assert b"Lunch" in response.data
    assert b"2024-02-21" in response.data
    assert b"$45.75" in response.data
    assert b"Dinner" in response.data


def test_delete_restaurant(client, auth):
    """Test deleting a restaurant."""
    auth.create_user()
    auth.login()
    # First add a restaurant
    client.post(
        "/restaurants/add",
        data={
            "name": "Test Restaurant",
            "city": "Test City",
            "address": "123 Test St",
            "phone": "123-456-7890",
            "website": "http://test.com",
        },
    )

    # Get the restaurant ID after creation
    restaurant = Restaurant.query.filter_by(name="Test Restaurant").first()
    assert restaurant is not None

    # Delete the restaurant
    response = client.post(
        f"/restaurants/{restaurant.id}/delete", follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Restaurant deleted successfully" in response.data

    # Verify restaurant is deleted
    response = client.get("/restaurants/", follow_redirects=True)
    assert response.status_code == 200
    assert b"Test Restaurant" not in response.data
