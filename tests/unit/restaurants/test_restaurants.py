"""Tests for restaurant-related functionality."""

import os
import sys
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from app import db  # noqa: E402
from app.auth.models import User  # noqa: E402
from app.expenses.models import Expense  # noqa: E402
from app.restaurants.models import Restaurant  # noqa: E402


def test_restaurants_list(client, auth):
    """Test listing restaurants."""
    # Register and login a test user
    auth.register("testuser_1", "testpass")
    auth.login("testuser_1", "testpass")
    # Test accessing the restaurants list
    response = client.get("/restaurants/", follow_redirects=True)
    assert response.status_code == 200
    assert b"Restaurants" in response.data


def test_add_restaurant(client, auth):
    """Test adding a restaurant."""
    # Register and login a test user
    auth.register("testuser_1", "testpass")
    auth.login("testuser_1", "testpass")
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
    auth.register("testuser_1", "testpass")
    auth.login("testuser_1", "testpass")
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
    stmt = select(Restaurant).where(Restaurant.name == "Test Restaurant")
    restaurant = db.session.scalars(stmt).first()
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


def test_restaurant_details(client, auth, app):
    """Test viewing restaurant details."""
    # Create user and login
    auth.register("testuser_1", "testpass")
    auth.login("testuser_1", "testpass")

    with app.app_context():
        # Create a test restaurant directly
        restaurant = Restaurant(
            name="Test Restaurant",
            type="restaurant",
            city="Test City",
            state="CA",
            zip_code="12345",
            address="123 Test St",
            phone="123-456-7890",
            website="http://test.com",
            cuisine="american",
            price_range="$$",
        )
        db.session.add(restaurant)
        db.session.commit()

        # Get the test user
        stmt = select(User).where(User.username == "testuser_1")
        user = db.session.scalars(stmt).first()
        # Add an expense for the restaurant
        expense = Expense(
            user_id=user.id,
            restaurant_id=restaurant.id,
            date=date(2024, 2, 20),
            meal_type="Lunch",
            category="Food",
            amount=25.50,
            notes="Test expense",
        )
        db.session.add(expense)
        db.session.commit()

        # Get the restaurant ID before the session is closed
        restaurant_id = restaurant.id

    # View restaurant details
    response = client.get(f"/restaurants/{restaurant_id}/details")
    assert response.status_code == 200
    assert b"Test Restaurant" in response.data
    assert b"Test City" in response.data
    assert b"123 Test St" in response.data
    assert b"$25.50" in response.data
    assert b"Lunch" in response.data


def test_restaurant_details_not_found(client, auth):
    """Test viewing details of a non-existent restaurant."""
    auth.register("testuser_1", "testpass")
    auth.login("testuser_1", "testpass")
    response = client.get("/restaurants/999/details", follow_redirects=True)
    assert response.status_code == 404


def test_restaurant_details_database_error(client, auth, monkeypatch):
    """Test handling database error when viewing restaurant details."""
    auth.register("testuser_1", "testpass")
    auth.login("testuser_1", "testpass")

    with client.application.app_context():
        # Create a test restaurant directly
        restaurant = Restaurant(
            name="Test Restaurant",
            type="restaurant",
            city="Test City",
            state="CA",
            zip_code="12345",
            address="123 Test St",
            phone="123-456-7890",
            website="http://test.com",
            cuisine="american",
            price_range="$$",
        )
        db.session.add(restaurant)
        db.session.commit()
        restaurant_id = restaurant.id

    # Mock the database query to raise an error
    from unittest.mock import patch

    with (
        patch("app.restaurants.routes.db.session.scalars") as mock_scalars,
        patch("app.restaurants.routes.current_app.logger") as mock_logger,
    ):
        # Make the session.get() raise an SQLAlchemyError
        mock_scalars.side_effect = SQLAlchemyError("Database error")

        # Try to view restaurant details - should handle the error
        response = client.get(f"/restaurants/{restaurant_id}/details")

        # Check that we got a 500 error
        assert response.status_code == 500

        # Check that the error was logged
        mock_logger.error.assert_called_once()
        error_message = mock_logger.error.call_args[0][0]
        assert "Database error in restaurant_details" in error_message


def test_restaurant_details_with_multiple_expenses(client, auth, app):
    """Test viewing restaurant details with multiple expenses."""
    # Create user and login
    auth.register("testuser_1", "testpass")
    auth.login("testuser_1", "testpass")

    with app.app_context():
        # Create a test restaurant directly
        restaurant = Restaurant(
            name="Test Restaurant",
            type="restaurant",
            city="Test City",
            state="CA",
            zip_code="12345",
            address="123 Test St",
            phone="123-456-7890",
            website="http://test.com",
            cuisine="american",
            price_range="$$",
        )
        db.session.add(restaurant)
        db.session.commit()

        # Get the test user
        user = db.session.execute(select(User).where(User.username == "testuser_1")).scalar_one()

        # Add multiple expenses
        expenses = [
            {
                "user_id": user.id,
                "restaurant_id": restaurant.id,
                "date": date(2024, 2, 20),  # Using date object
                "meal_type": "Lunch",
                "category": "Food",
                "amount": 25.50,
                "notes": "First visit",
            },
            {
                "user_id": user.id,
                "restaurant_id": restaurant.id,
                "date": date(2024, 2, 21),  # Using date object
                "meal_type": "Dinner",
                "category": "Food",
                "amount": 45.75,
                "notes": "Second visit",
            },
        ]

        for expense_data in expenses:
            expense = Expense(**expense_data)
            db.session.add(expense)
        db.session.commit()

        # Get the restaurant ID before the session is closed
        restaurant_id = restaurant.id

    # View restaurant details
    response = client.get(f"/restaurants/{restaurant_id}/details")
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
        user = User(username="testuser_1")
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()
    auth.login("testuser_1", "testpass")

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
        query = db.session.scalars(select(Expense).where(Expense.restaurant_id == restaurant_id)).all()
        assert len(query.all()) == 0

    # Try to delete the restaurant
    response = client.post(f"/restaurants/{restaurant_id}/delete", follow_redirects=True)
    assert response.status_code == 200  # After following redirect
    assert b"Restaurant and associated expenses deleted successfully." in response.data

    # Verify the restaurant is deleted
    with app.app_context():
        assert db.session.get(Restaurant, restaurant_id) is None
        # Verify no expenses exist
        query = db.session.scalars(select(Expense).where(Expense.restaurant_id == restaurant_id)).all()
        assert len(query.all()) == 0


def test_delete_restaurant_with_expenses(client, auth, app):
    """Test deleting a restaurant that has associated expenses."""
    # Create and login user
    with app.app_context():
        user = User(username="testuser_1")
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()
    auth.login("testuser_1", "testpass")

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
        user = db.session.scalars(select(User).where(User.username == "testuser_1")).first()
        assert user is not None

        # Add some expenses
        expenses = [
            Expense(
                date=datetime.strptime("2024-02-20 12:00:00", "%Y-%m-%d %H:%M:%S"),
                amount=25.50,
                notes="Test expense 1",
                restaurant_id=restaurant_id,
                user_id=user.id,
            ),
            Expense(
                date=datetime.strptime("2024-02-21 19:30:00", "%Y-%m-%d %H:%M:%S"),
                amount=35.75,
                notes="Test expense 2",
                restaurant_id=restaurant_id,
                user_id=user.id,
            ),
        ]
        for expense in expenses:
            db.session.add(expense)
        db.session.commit()

        # Verify expenses were created
        stmt = select(Expense).where(Expense.restaurant_id == restaurant_id)
        expenses = db.session.scalars(stmt).all()
        assert len(expenses) == 2

    # Try to delete the restaurant
    response = client.post(f"/restaurants/{restaurant_id}/delete", follow_redirects=True)
    assert response.status_code == 200  # After following redirect
    assert b"Restaurant and associated expenses deleted successfully." in response.data

    # Verify both restaurant and its expenses are deleted
    with app.app_context():
        assert db.session.get(Restaurant, restaurant_id) is None
        query = db.session.scalars(select(Expense).where(Expense.restaurant_id == restaurant_id)).all()
        assert len(query.all()) == 0
