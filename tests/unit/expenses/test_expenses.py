"""Tests for expense-related functionality."""

import os
import sys

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from app import db  # noqa: E402
from app.expenses.models import Expense  # noqa: E402


def test_expenses_list(client, auth):
    """Test expenses list page."""
    auth.create_user()
    auth.login()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Meal Expenses" in response.data


def test_add_expense(client, auth):
    """Test adding an expense."""
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

    # Add an expense
    response = client.post(
        "/expenses/add",
        data={
            "restaurant_id": 1,
            "date": "2024-02-20",
            "meal_type": "Lunch",
            "amount": "25.50",
            "notes": "Test expense",
        },
    )
    assert response.status_code == 302  # Redirect after successful add
    response = client.get("/")
    assert b"Expense added successfully!" in response.data
    assert b"25.50" in response.data


def test_edit_expense(client, auth, app):
    """Test editing an expense."""
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

    # Add an expense
    client.post(
        "/expenses/add",
        data={
            "restaurant_id": 1,
            "date": "2024-02-20",
            "meal_type": "Lunch",
            "amount": "25.50",
            "notes": "Test expense",
        },
    )

    # Test GET request to edit page
    response = client.get("/expenses/1/edit")
    assert response.status_code == 200
    assert b"Edit Expense" in response.data
    assert b"Test expense" in response.data

    # Edit the expense
    response = client.post(
        "/expenses/1/edit",
        data={
            "restaurant_id": 1,
            "date": "2024-02-21",
            "meal_type": "Dinner",
            "amount": "35.50",
            "notes": "Updated expense",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Expense updated successfully!" in response.data
    assert b"35.50" in response.data
    # Check the database for updated notes and amount
    with app.app_context():
        expense = db.session.get(Expense, 1)
        assert expense.notes == "Updated expense"
        assert expense.amount == 35.50


def test_edit_expense_unauthorized(client, auth, app):
    """Test editing an expense without permission."""
    # Create first user and add an expense
    auth.create_user()
    auth.login()
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
    client.post(
        "/expenses/add",
        data={
            "restaurant_id": 1,
            "date": "2024-02-20",
            "meal_type": "Lunch",
            "amount": "25.50",
            "notes": "Test expense",
        },
    )
    # Log out and register/login as a different user
    auth.logout()
    auth.create_user(username="otheruser", password="otherpass")
    auth.login(username="otheruser", password="otherpass")
    response = client.post(
        "/expenses/1/edit",
        data={
            "restaurant_id": 1,
            "date": "2024-02-21",
            "meal_type": "Dinner",
            "amount": "35.50",
            "notes": "Malicious update",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"You do not have permission to edit this expense." in response.data
    assert b"Meal Expenses" in response.data
    with app.app_context():
        expense = db.session.get(Expense, 1)
        assert expense.notes == "Test expense"
        assert expense.amount == 25.50


def test_edit_expense_not_found(client, auth):
    """Test editing a non-existent expense."""
    auth.create_user()
    auth.login()
    response = client.get("/expenses/999/edit", follow_redirects=True)
    assert response.status_code == 404


def test_edit_expense_invalid_data(client, auth):
    """Test editing an expense with invalid data."""
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

    # Add an expense
    client.post(
        "/expenses/add",
        data={
            "restaurant_id": 1,
            "date": "2024-02-20",
            "meal_type": "Lunch",
            "amount": "25.50",
            "notes": "Test expense",
        },
    )

    # Try to edit with invalid data
    response = client.post(
        "/expenses/1/edit",
        data={
            "restaurant_id": 1,
            "date": "invalid-date",  # Invalid date
            "meal_type": "Lunch",
            "amount": "not-a-number",  # Invalid amount
            "notes": "Updated expense",
        },
    )
    assert response.status_code == 400  # Should be 400 Bad Request
    assert b"Invalid date format." in response.data or b"Invalid amount format." in response.data


def test_delete_expense(client, auth):
    """Test deleting an expense."""
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

    # Add an expense
    client.post(
        "/expenses/add",
        data={
            "restaurant_id": 1,
            "date": "2024-02-20",
            "meal_type": "Lunch",
            "amount": "25.50",
            "notes": "Test expense",
        },
    )

    # Delete the expense
    response = client.post("/expenses/1/delete", follow_redirects=True)
    assert response.status_code == 200
    assert b"Expense deleted successfully!" in response.data


def test_expense_filters(client, auth):
    """Test expense filtering."""
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

    # Add expenses with different meal types
    client.post(
        "/expenses/add",
        data={
            "restaurant_id": 1,
            "date": "2024-02-20",
            "meal_type": "Lunch",
            "amount": "25.50",
            "notes": "Today's lunch",
        },
    )

    client.post(
        "/expenses/add",
        data={
            "restaurant_id": 1,
            "date": "2024-02-20",
            "meal_type": "Dinner",
            "amount": "35.50",
            "notes": "Today's dinner",
        },
    )

    # Test filtering by meal type
    response = client.get("/?meal_type=Lunch")
    assert response.status_code == 200
    assert b"25.50" in response.data
    assert b"35.50" not in response.data

    # Test filtering by date
    response = client.get("/?start_date=2024-02-20")
    assert response.status_code == 200
    assert b"25.50" in response.data
    assert b"35.50" in response.data


def test_add_expense_with_restaurant_type(client, auth):
    """Test adding an expense with automatic category based on restaurant type."""
    auth.create_user()
    auth.login()
    # Add a cafe
    client.post(
        "/restaurants/add",
        data={
            "name": "Test Cafe",
            "type": "cafe",
            "city": "Test City",
            "state": "CA",
            "zip_code": "12345",
            "address": "123 Test St",
            "phone": "123-456-7890",
            "website": "http://test.com",
            "cuisine": "Coffee",
            "price_range": "$",
        },
    )

    # Add an expense
    response = client.post(
        "/expenses/add",
        data={
            "restaurant_id": 1,
            "date": "2024-02-20",
            "meal_type": "Breakfast",
            "amount": "5.50",
            "notes": "Morning coffee",
        },
    )
    assert response.status_code == 302  # Redirect after successful add
    response = client.get("/")
    assert b"Expense added successfully!" in response.data
    assert b"5.50" in response.data
    assert b"Coffee" in response.data  # Category should be automatically set to Coffee
