"""Tests for restaurant-related functionality."""

# Standard library imports
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

# Third-party imports
import pytest
from flask import current_app as app
from flask import url_for
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.auth.models import User
from app.expenses.models import Category, Expense

# Local application imports
from app.extensions import db
from app.restaurants.models import Restaurant


@pytest.fixture
def test_user():
    user = User(username="testuser", email="test@example.com")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def test_restaurant():
    restaurant = Restaurant(
        name="Test Restaurant",
        city="Test City",
        address="123 Test St",
        phone="123-456-7890",
        website="http://test.com",
        cuisine="American",
        email="test@example.com",
        type="restaurant",
        price_range="$$",
        country="United States",
    )
    db.session.add(restaurant)
    db.session.commit()
    return restaurant


@pytest.fixture
def test_category():
    category = Category(name="Dining", description="Dining out expenses", user_id=1)
    db.session.add(category)
    db.session.commit()
    return category


def test_restaurants_list(client, auth, test_user, test_restaurant):
    """Test listing restaurants."""
    # Login the test user
    auth.login(test_user.username, "testpass")

    # Test accessing the restaurants list
    with app.test_request_context():
        url = url_for("restaurants.list_restaurants")
        response = client.get(url, follow_redirects=True)

        assert response.status_code == 200
        assert b"Restaurants" in response.data
        assert test_restaurant.name.encode() in response.data


def test_add_restaurant(client, auth, test_user):
    """Test adding a restaurant."""
    # Login the test user
    auth.login(test_user.username, "testpass")

    with app.test_request_context():
        url = url_for("restaurants.add_restaurant")
        test_email = f"test-{uuid.uuid4().hex[:8]}@example.com"

        response = client.post(
            url,
            data={
                "name": "Test Restaurant",
                "city": "Test City",
                "address": "123 Test St",
                "phone": "123-456-7890",
                "website": "http://test.com",
                "cuisine": "American",
                "email": test_email,
                "type": "restaurant",
                "price_range": "$$",
                "country": "United States",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Restaurant added successfully" in response.data

        # Verify the restaurant was created
        restaurant = Restaurant.query.filter_by(email=test_email).first()
        assert restaurant is not None
        assert restaurant.name == "Test Restaurant"


def test_edit_restaurant(client, auth, test_user, test_restaurant):
    """Test editing a restaurant."""
    # Login the test user
    auth.login(test_user.username, "testpass")

    with app.test_request_context():
        url = url_for("restaurants.edit_restaurant", restaurant_id=test_restaurant.id)

        # Test editing the restaurant
        response = client.post(
            url,
            data={
                "name": "Updated Test Restaurant",
                "city": test_restaurant.city,
                "address": test_restaurant.address,
                "phone": test_restaurant.phone,
                "website": test_restaurant.website,
                "cuisine": test_restaurant.cuisine,
                "email": test_restaurant.email,
                "type": test_restaurant.type,
                "price_range": test_restaurant.price_range,
                "country": test_restaurant.country,
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Restaurant updated successfully" in response.data

        # Verify the restaurant was updated
        updated_restaurant = Restaurant.query.get(test_restaurant.id)
        assert updated_restaurant.name == "Updated Test Restaurant"


def test_restaurant_details(client, auth, test_user, test_restaurant):
    """Test viewing restaurant details."""
    # Login the test user
    auth.login(test_user.username, "testpass")
    restaurant_id = test_restaurant.id

    # Test viewing the restaurant details
    with app.test_request_context():
        url = url_for("restaurants.restaurant_detail", restaurant_id=restaurant_id)
        response = client.get(url, follow_redirects=True)

        assert response.status_code == 200
        assert test_restaurant.name.encode() in response.data
        assert test_restaurant.address.encode() in response.data
        assert test_restaurant.city.encode() in response.data
        assert test_restaurant.cuisine.encode() in response.data


def test_restaurant_details_not_found(client, auth, test_user):
    """Test viewing a non-existent restaurant."""
    # Login the test user
    auth.login(test_user.username, "testpass")

    with app.test_request_context():
        non_existent_id = 999999
        url = url_for("restaurants.restaurant_detail", restaurant_id=non_existent_id)
        response = client.get(url, follow_redirects=True)

        assert response.status_code == 404
        assert b"Restaurant not found" in response.data


def test_restaurant_details_database_error(client, auth, test_user, test_restaurant, monkeypatch):
    """Test error handling when there's a database error."""
    auth.login(test_user.username, "testpass")

    # Mock the database query to raise an error
    def mock_query_error(*args, **kwargs):
        raise SQLAlchemyError("Database error")

    with patch("app.restaurants.routes.db.session.scalars", side_effect=mock_query_error):
        with app.test_request_context():
            url = url_for("restaurants.restaurant_detail", restaurant_id=test_restaurant.id)
            response = client.get(url, follow_redirects=True)

    assert response.status_code == 500
    assert b"An error occurred while retrieving restaurant details" in response.data


def test_restaurant_details_with_expenses(client, auth, test_user, test_restaurant, test_category):
    """Test viewing a restaurant with associated expenses."""
    # Login the test user
    auth.login(test_user.username, "testpass")

    with app.test_request_context():
        # Create test expenses
        expense1 = Expense(
            amount=Decimal("25.50"),
            notes="Test expense 1",
            date=datetime.now(timezone.utc),
            user_id=test_user.id,
            restaurant_id=test_restaurant.id,
            category_id=test_category.id,
            meal_type="dinner",
        )
        expense2 = Expense(
            amount=Decimal("15.75"),
            notes="Test expense 2",
            date=datetime.now(timezone.utc),
            user_id=test_user.id,
            restaurant_id=test_restaurant.id,
            category_id=test_category.id,
            meal_type="lunch",
        )
        db.session.add_all([expense1, expense2])
        db.session.commit()

        # Test viewing the restaurant details
        url = url_for("restaurants.restaurant_detail", restaurant_id=test_restaurant.id)
        response = client.get(url, follow_redirects=True)

        assert response.status_code == 200
        assert test_restaurant.name.encode() in response.data
        assert b"25.50" in response.data
        assert b"15.75" in response.data


def test_delete_restaurant_with_expenses(client, auth, test_user, test_restaurant, test_category):
    """Test deleting a restaurant with associated expenses."""
    # Login the test user
    auth.login(test_user.username, "testpass")

    with app.test_request_context():
        # Add an expense to the test restaurant
        expense = Expense(
            amount=Decimal("25.99"),
            notes="Test expense",
            date=datetime.now(timezone.utc),
            user_id=test_user.id,
            restaurant_id=test_restaurant.id,
            category_id=test_category.id,
            meal_type="dinner",
        )
        db.session.add(expense)
        db.session.commit()

        # Test deleting the restaurant (should fail)
        url = url_for("restaurants.delete_restaurant", restaurant_id=test_restaurant.id)
        response = client.post(url, follow_redirects=True)

        assert response.status_code == 400
        assert b"Cannot delete restaurant with associated expenses" in response.data

        # Verify the restaurant was not deleted
        not_deleted = Restaurant.query.get(test_restaurant.id)
        assert not_deleted is not None

        # Test viewing the restaurant details
        url = url_for("restaurants.restaurant_detail", restaurant_id=test_restaurant.id)
        response = client.get(url, follow_redirects=True)

        assert response.status_code == 200
        assert test_restaurant.name.encode() in response.data


def test_delete_restaurant_without_expenses(client, auth, test_user, test_restaurant):
    """Test deleting a restaurant without any associated expenses."""
    # Login the test user
    auth.login(test_user.username, "testpass")

    with app.test_request_context():
        url = url_for("restaurants.delete_restaurant", restaurant_id=test_restaurant.id)

        # Test deleting the restaurant
        response = client.post(url, follow_redirects=True)

        assert response.status_code == 200
        assert b"Restaurant deleted successfully" in response.data

        # Verify the restaurant was deleted
        deleted = Restaurant.query.get(test_restaurant.id)
        assert deleted is None
        # Verify no expenses exist
        expenses = db.session.scalars(select(Expense).where(Expense.restaurant_id == test_restaurant.id)).all()
        assert len(expenses) == 0


def test_delete_restaurant_with_expenses_db(app, client, auth, test_user, test_restaurant):
    """Test deleting a restaurant that has associated expenses (DB version)."""
    # Login the test user
    auth.login(test_user.username, "testpass")
    restaurant_id = test_restaurant.id

    # Get or create a category for the test user
    with app.app_context():
        category = Category.query.filter_by(name="Dining", user_id=test_user.id).first()
        if not category:
            category = Category(name="Dining", description="Dining out expenses", user_id=test_user.id)
            db.session.add(category)
            db.session.commit()

        # Create test expenses
        expenses = [
            Expense(
                date=datetime.strptime("2024-02-20", "%Y-%m-%d").date(),
                amount=25.50,
                category_id=category.id,
                meal_type="Lunch",
                notes="Test expense 1",
                restaurant_id=restaurant_id,
                user_id=test_user.id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            Expense(
                date=datetime.strptime("2024-02-21", "%Y-%m-%d").date(),
                amount=35.75,
                category_id=category.id,
                meal_type="Dinner",
                notes="Test expense 2",
                restaurant_id=restaurant_id,
                user_id=test_user.id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
        ]
        db.session.add_all(expenses)
        db.session.commit()

        # Verify expenses were created
        expense_count = db.session.scalar(
            select(db.func.count(Expense.id)).where(Expense.restaurant_id == restaurant_id)
        )
        assert expense_count == 2, "Should have 2 test expenses"

    # Delete the restaurant
    response = client.post(f"/restaurants/{restaurant_id}/delete", follow_redirects=True)
    assert response.status_code == 200, "Should redirect after deletion"
    assert b"Restaurant and associated expenses deleted successfully." in response.data, "Should show success message"

    # Verify the restaurant and expenses are deleted
    with app.app_context():
        # Verify the restaurant is deleted
        assert db.session.get(Restaurant, restaurant_id) is None, "Restaurant should be deleted"

        # Verify all associated expenses are deleted
        expense_count = db.session.scalar(
            select(db.func.count(Expense.id)).where(Expense.restaurant_id == restaurant_id)
        )
        assert expense_count == 0, "All expenses should be deleted"
