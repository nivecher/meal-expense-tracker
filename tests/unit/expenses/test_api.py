"""Test cases for the Expense API endpoints."""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict

import pytest

# from flask import Flask
from flask.testing import FlaskClient
from flask_sqlalchemy import SQLAlchemy

from app import create_app
from app.auth.models import User
from app.expenses.models import Category, Expense
from app.extensions import db as _db
from app.restaurants.models import Restaurant

# Type aliases
TestData = Dict[str, Any]


@pytest.fixture(scope="function")
def app():
    """Create and configure a new app instance for testing."""
    app = create_app("testing")
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "connect_args": {"check_same_thread": False},
        "echo": False,
    }

    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture(scope="function")
def db(app):
    """Database session with rollback after each test."""
    with app.app_context():
        _db.session.begin_nested()
        yield _db
        _db.session.rollback()
        _db.session.remove()


@pytest.fixture(scope="function")
def test_user(db):
    """Create a test user."""
    import uuid

    unique_id = str(uuid.uuid4())[:8]
    user = User(username=f"testuser_{unique_id}", email=f"test_{unique_id}@example.com", is_active=True)
    user.set_password("testpass123")
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture(scope="function")
def test_category(db, test_user):
    """Create a test category."""
    category = Category(name="Test Category", user_id=test_user.id, description="Test Description", color="#000000")
    db.session.add(category)
    db.session.commit()
    return category


@pytest.fixture(scope="function")
def test_restaurant(db, test_user):
    """Create a test restaurant."""
    restaurant = Restaurant(
        name="Test Restaurant",
        type="restaurant",  # Add required field
        user_id=test_user.id,
        address="123 Test St",
        city="Test City",
        state="TS",
        postal_code="12345",
        country="Test Country",
    )
    db.session.add(restaurant)
    db.session.commit()
    return restaurant


@pytest.fixture(scope="function")
def auth_headers(client, test_user):
    """Get authentication headers for the test user."""
    # Use session-based authentication for testing
    with client.session_transaction() as sess:
        sess["_fresh"] = True
        sess["_user_id"] = str(test_user.id)
    return {}


class TestExpenseAPI:
    """Test cases for the Expense API endpoints."""

    def test_create_expense(
        self, client: FlaskClient, test_restaurant: Restaurant, test_category: Category, auth_headers: Dict[str, str]
    ) -> None:
        """Test creating a new expense."""
        expense_data = {
            "amount": "25.50",
            "notes": "Test expense",
            "date": date.today().isoformat(),
            "restaurant_id": test_restaurant.id,
            "category_id": test_category.id,
        }

        response = client.post(
            "/api/v1/expenses",
            json=expense_data,
            headers=auth_headers,
        )

        assert response.status_code == 201, f"Unexpected status code: {response.status_code}"
        response_data = response.get_json()
        assert "data" in response_data
        data = response_data["data"]
        assert "id" in data
        assert data["amount"] == "25.50"
        assert data["notes"] == "Test expense"
        assert data["restaurant_id"] == test_restaurant.id
        assert data["category_id"] == test_category.id

    def test_create_expense_invalid_data(self, client: FlaskClient, auth_headers: Dict[str, str]) -> None:
        """Test creating an expense with invalid data."""
        response = client.post(
            "/api/v1/expenses",
            json={"amount": "not_a_number"},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "Not a valid number" in response.get_json().get("errors", {}).get("amount", [""])[0]

    def test_get_expenses(
        self,
        client: FlaskClient,
        db: SQLAlchemy,
        test_user: User,
        test_restaurant: Restaurant,
        test_category: Category,
        auth_headers: Dict[str, str],
    ) -> None:
        """Test retrieving all expenses for the current user."""
        # Create a test expense
        expense = Expense(
            amount=30.00,
            date=datetime.now(timezone.utc),
            notes="Dinner at Test Restaurant",  # Use 'notes' instead of 'description'
            category_id=test_category.id,
            restaurant_id=test_restaurant.id,
            user_id=test_user.id,
        )
        db.session.add(expense)
        db.session.commit()

        response = client.get("/api/v1/expenses", headers=auth_headers)
        assert response.status_code == 200
        response_data = response.get_json()
        assert "data" in response_data
        data = response_data["data"]
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["notes"] == "Dinner at Test Restaurant"

    def test_get_expense(
        self,
        client: FlaskClient,
        db: SQLAlchemy,
        test_user: User,
        test_restaurant: Restaurant,
        test_category: Category,
        auth_headers: Dict[str, str],
    ) -> None:
        """Test retrieving a single expense."""
        # Create an expense
        expense = Expense(
            amount=10.99,
            date=date(2025, 7, 12),
            user_id=test_user.id,
            restaurant_id=test_restaurant.id,
            category_id=test_category.id,
            notes="Test expense",  # Use 'notes' instead of 'description'
            meal_type="lunch",
        )
        db.session.add(expense)
        db.session.commit()

        response = client.get(f"/api/v1/expenses/{expense.id}", headers=auth_headers)
        assert response.status_code == 200
        response_data = response.get_json()
        assert "data" in response_data
        data = response_data["data"]
        assert data["amount"] == "10.99"
        assert data["notes"] == "Test expense"

    def test_update_expense(
        self,
        client: FlaskClient,
        db: SQLAlchemy,
        test_user: User,
        test_restaurant: Restaurant,
        test_category: Category,
        auth_headers: Dict[str, str],
    ) -> None:
        """Test updating an expense."""
        # Create an expense
        expense = Expense(
            amount=10.99,
            date=date(2025, 7, 12),
            user_id=test_user.id,
            restaurant_id=test_restaurant.id,
            category_id=test_category.id,
            notes="Original note",  # Use 'notes' instead of 'description'
            meal_type="lunch",
        )
        db.session.add(expense)
        db.session.commit()

        update_data = {
            "amount": 12.99,
            "date": "2025-07-13",
            "restaurant_id": test_restaurant.id,
            "category_id": test_category.id,
            "notes": "Updated note",  # Use 'notes' instead of 'description'
            "meal_type": "dinner",
        }

        response = client.put(
            f"/api/v1/expenses/{expense.id}",
            json=update_data,
            headers=auth_headers,
        )
        assert response.status_code == 200
        response_data = response.get_json()
        assert "data" in response_data
        data = response_data["data"]
        assert data["amount"] == "12.99"
        assert data["notes"] == "Updated note"
        assert data["meal_type"] == "dinner"

    def test_delete_expense(
        self,
        client: FlaskClient,
        db: SQLAlchemy,
        test_user: User,
        test_restaurant: Restaurant,
        test_category: Category,
        auth_headers: Dict[str, str],
    ) -> None:
        """Test deleting an expense."""
        # Create a test expense
        expense = Expense(
            amount=Decimal("8.50"),
            date=datetime.now(timezone.utc),
            notes="Test expense to delete",
            meal_type="lunch",
            category_id=test_category.id,
            restaurant_id=test_restaurant.id,
            user_id=test_user.id,
        )
        db.session.add(expense)
        db.session.commit()

        # Delete the expense
        response = client.delete(
            f"/api/v1/expenses/{expense.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify it's gone
        response = client.get(
            f"/api/v1/expenses/{expense.id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_unauthorized_access(self, client: FlaskClient) -> None:
        """Test that unauthorized access is rejected."""
        endpoints = [
            ("/api/v1/expenses", "GET"),
            ("/api/v1/expenses/1", "GET"),
            ("/api/v1/expenses", "POST"),
            ("/api/v1/expenses/1", "PUT"),
            ("/api/v1/expenses/1", "DELETE"),
        ]

        for endpoint, method in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})
            elif method == "PUT":
                response = client.put(endpoint, json={})
            elif method == "DELETE":
                response = client.delete(endpoint)

            # Should be unauthorized (401) or method not allowed (405)
            assert response.status_code in (
                401,
                405,
            ), f"Unexpected status code for {method} {endpoint}: {response.status_code}"

    def test_access_other_user_expense(
        self,
        client: FlaskClient,
        db: SQLAlchemy,
        test_user: User,
        test_restaurant: Restaurant,
        test_category: Category,
        auth_headers: Dict[str, str],
    ) -> None:
        """Test that users cannot access expenses belonging to other users."""
        # Create a second user
        other_user = User(username="otheruser", email="other@example.com", is_active=True)
        other_user.set_password("otherpassword")
        db.session.add(other_user)
        db.session.commit()

        # Create an expense for the other user
        other_expense = Expense(
            amount=Decimal("100.00"),
            date=datetime.now(timezone.utc),
            notes="Other user's expense",
            meal_type="dinner",
            category_id=test_category.id,
            restaurant_id=test_restaurant.id,
            user_id=other_user.id,
        )
        db.session.add(other_expense)
        db.session.commit()

        # Try to access the other user's expense
        response = client.get(
            f"/api/v1/expenses/{other_expense.id}",
            headers=auth_headers,
        )
        assert response.status_code == 404, "Should not be able to access another user's expense"
