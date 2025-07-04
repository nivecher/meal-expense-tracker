"""Tests for restaurant-related functionality."""

import os
import sys
from datetime import datetime

from sqlalchemy import select

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

    # First create a restaurant to edit
    with client.application.app_context():
        restaurant = Restaurant(
            name="Old Name",
            type="restaurant",
            address="123 Old St",
            city="Old City",
            cuisine="Italian",
        )
        db.session.add(restaurant)
        db.session.commit()
        restaurant_id = restaurant.id

    # Now edit it
    response = client.post(
        f"/restaurants/{restaurant_id}/edit",
        data={
            "name": "New Name",
            "type": "cafe",
            "address": "456 New St",
            "city": "New City",
            "cuisine": "French",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Restaurant updated successfully" in response.data

    # Verify the changes
    with client.application.app_context():
        updated = db.session.get(Restaurant, restaurant_id)
        assert updated is not None
        assert updated.name == "New Name"
        assert updated.type == "cafe"
        assert updated.address == "456 New St"
        assert updated.city == "New City"
        assert updated.cuisine == "French"


def test_restaurant_details(client, auth, app):
    """Test viewing restaurant details."""
    auth.register("testuser_1", "testpass")
    auth.login("testuser_1", "testpass")

    with app.app_context():
        # Create a restaurant
        restaurant = Restaurant(
            name="Test Restaurant",
            type="restaurant",
            address="123 Test St",
            city="Test City",
            cuisine="American",
        )
        db.session.add(restaurant)
        db.session.commit()
        restaurant_id = restaurant.id

    # View the restaurant details
    response = client.get(f"/restaurants/{restaurant_id}")
    assert response.status_code == 200
    assert b"Test Restaurant" in response.data
    assert b"Test City" in response.data


def test_restaurant_details_not_found(client, auth):
    """Test viewing details of a non-existent restaurant."""
    auth.register("testuser_1", "testpass")
    auth.login("testuser_1", "testpass")

    # Try to view a non-existent restaurant
    response = client.get("/restaurants/999999")
    assert response.status_code == 404


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
        expenses = db.session.scalars(select(Expense).where(Expense.restaurant_id == restaurant_id)).all()
        assert len(expenses) == 0

    # Try to delete the restaurant
    response = client.post(f"/restaurants/{restaurant_id}/delete", follow_redirects=True)
    assert response.status_code == 200  # After following redirect
    assert b"Restaurant and associated expenses deleted successfully." in response.data

    # Verify the restaurant is deleted
    with app.app_context():
        assert db.session.get(Restaurant, restaurant_id) is None
        # Verify no expenses exist
        expenses = db.session.scalars(select(Expense).where(Expense.restaurant_id == restaurant_id)).all()
        assert len(expenses) == 0


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
                date=datetime.strptime("2024-02-20", "%Y-%m-%d").date(),
                amount=25.50,
                category_id=1,  # Assuming 1 is the ID for 'Dining' category
                meal_type="Lunch",
                notes="Test expense 1",
                restaurant_id=restaurant_id,
                user_id=user.id,
            ),
            Expense(
                date=datetime.strptime("2024-02-21", "%Y-%m-%d").date(),
                amount=35.75,
                category_id=1,  # Assuming 1 is the ID for 'Dining' category
                meal_type="Dinner",
                notes="Test expense 2",
                restaurant_id=restaurant_id,
                user_id=user.id,
            ),
        ]
        db.session.add_all(expenses)
        db.session.commit()

        # Verify expenses were added
        expense_count = db.session.scalar(
            select(db.func.count(Expense.id)).where(Expense.restaurant_id == restaurant_id)
        )
        assert expense_count == 2

    # Try to delete the restaurant
    response = client.post(f"/restaurants/{restaurant_id}/delete", follow_redirects=True)
    assert response.status_code == 200  # After following redirect
    assert b"Restaurant and associated expenses deleted successfully." in response.data

    # Verify the restaurant is deleted
    with app.app_context():
        assert db.session.get(Restaurant, restaurant_id) is None
        # Verify all associated expenses are deleted
        expense_count = db.session.scalar(
            select(db.func.count(Expense.id)).where(Expense.restaurant_id == restaurant_id)
        )
        assert expense_count == 0
