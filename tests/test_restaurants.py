from app.restaurants.models import Restaurant
from app import db
from sqlalchemy.exc import SQLAlchemyError
from unittest.mock import Mock
from app.expenses.models import Expense
from datetime import datetime
from app.auth.models import User


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
            "cuisine": "American",
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
            "cuisine": "American",
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
            "cuisine": "Italian",
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


def test_delete_restaurant_without_expenses(client, auth, app):
    """Test deleting a restaurant that has no expenses."""
    # Create and login user
    with app.app_context():
        user = User(username="testuser")
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()
    auth.login()

    # Create a restaurant first
    restaurant = Restaurant(
        name="Test Restaurant",
        type="restaurant",
        address="123 Test St",
        city="Test City",
        cuisine="American",
    )
    with app.app_context():
        db.session.add(restaurant)
        db.session.commit()
        restaurant_id = restaurant.id

        # Verify no expenses exist
        query = db.session.query(Expense).filter_by(restaurant_id=restaurant_id)
        assert len(query.all()) == 0

    # Try to delete the restaurant
    response = client.post(
        f"/restaurants/{restaurant_id}/delete", follow_redirects=True
    )
    assert response.status_code == 200  # After following redirect
    assert b"Restaurant and associated expenses deleted successfully." in response.data

    # Verify the restaurant is deleted
    with app.app_context():
        assert db.session.get(Restaurant, restaurant_id) is None
        # Verify no expenses exist
        query = db.session.query(Expense).filter_by(restaurant_id=restaurant_id)
        assert len(query.all()) == 0


def test_delete_restaurant_with_expenses(client, auth, app):
    """Test deleting a restaurant that has associated expenses."""
    # Create and login user
    with app.app_context():
        user = User(username="testuser")
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()
    auth.login()

    # Create a restaurant first
    restaurant = Restaurant(
        name="Test Restaurant",
        type="restaurant",
        address="123 Test St",
        city="Test City",
        cuisine="American",
    )
    with app.app_context():
        db.session.add(restaurant)
        db.session.commit()
        restaurant_id = restaurant.id

        # Get the current user
        user = User.query.filter_by(username="testuser").first()
        assert user is not None

        # Add some expenses
        expenses = [
            Expense(
                date=datetime.strptime("2024-02-20", "%Y-%m-%d").date(),
                amount=25.50,
                category="Dining",
                meal_type="Lunch",
                notes="Test expense 1",
                restaurant_id=restaurant_id,
                user_id=user.id,
            ),
            Expense(
                date=datetime.strptime("2024-02-21", "%Y-%m-%d").date(),
                amount=35.75,
                category="Dining",
                meal_type="Dinner",
                notes="Test expense 2",
                restaurant_id=restaurant_id,
                user_id=user.id,
            ),
        ]
        for expense in expenses:
            db.session.add(expense)
        db.session.commit()

        # Verify expenses were created
        query = db.session.query(Expense).filter_by(restaurant_id=restaurant_id)
        assert len(query.all()) == 2

    # Try to delete the restaurant
    response = client.post(
        f"/restaurants/{restaurant_id}/delete", follow_redirects=True
    )
    assert response.status_code == 200  # After following redirect
    assert b"Restaurant and associated expenses deleted successfully." in response.data

    # Verify both restaurant and its expenses are deleted
    with app.app_context():
        assert db.session.get(Restaurant, restaurant_id) is None
        query = db.session.query(Expense).filter_by(restaurant_id=restaurant_id)
        assert len(query.all()) == 0
