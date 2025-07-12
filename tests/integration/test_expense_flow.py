from datetime import datetime, timedelta
import pytest

from app import db
from app.auth.models import User
from app.expenses.models import Category, Expense
from app.restaurants.models import Restaurant
from app.utils.messages import FlashMessages

# Helper functions


def create_test_restaurant(client, test_data=None):
    """Helper to create a test restaurant."""
    default_data = {
        "name": "Test Restaurant",
        "type": "restaurant",
        "cuisine_type": "american",
        "cuisine": "American",
        "address": "123 Test St",
        "city": "Test City",
        "state_province": "CA",
        "postal_code": "12345",
        "country": "US",
        "phone": "123-456-7890",
        "website": "http://test.com",
        "price_range": "$$",
        "description": "Test restaurant description",
        "notes": "Test notes",
        "is_chain": "false"
    }

    if test_data:
        default_data.update(test_data)

    response = client.post(
        "/restaurants/add",
        data=default_data,
        follow_redirects=True,
    )

    return response


def create_test_expense(client, restaurant_id, category_id, **kwargs):
    """Helper to create a test expense."""
    today = datetime.now().date()
    expense_data = {
        "csrf_token": "dummy_csrf_token",
        "restaurant_id": str(restaurant_id),
        "category_id": str(category_id),
        "date": today.strftime("%Y-%m-%d"),
        "meal_type": "Lunch",
        "amount": "25.50",
        "notes": "Test expense",
    }
    expense_data.update(kwargs)

    return client.post(
        "/expenses/add",
        data=expense_data,
        follow_redirects=True,
    )

# Fixtures


@pytest.fixture
def dining_category(app):
    """Create and return a Dining category."""
    with app.app_context():
        category = Category.query.filter_by(name="Dining").first()
        if not category:
            category = Category(name="Dining", description="Dining out expenses")
            db.session.add(category)
            db.session.commit()
        return category

# Test functions


def test_authentication(client, auth, test_user):
    """Test user authentication flow."""
    # Login using the auth fixture
    client = auth.login("testuser_1", "testpass")

    # Verify login by accessing a protected route
    response = client.get("/restaurants/", follow_redirects=True)
    assert response.status_code == 200, "Failed to access protected route after login"

    # Verify profile access
    profile_response = client.get("/auth/profile", follow_redirects=True)
    assert profile_response.status_code == 200, "Failed to access profile page"


def test_restaurant_creation(client, auth, test_user):
    """Test restaurant creation flow."""
    # Login
    client = auth.login("testuser_1", "testpass")

    # Access restaurant form
    response = client.get("/restaurants/add", follow_redirects=True)
    assert response.status_code == 200, "Failed to load restaurant form"

    # Create a restaurant
    response = create_test_restaurant(client)
    assert response.status_code == 200, f"Failed to create restaurant: {response.status_code}"
    assert FlashMessages.RESTAURANT_ADDED.encode() in response.data, "Success message not found"

    # Verify restaurant in database
    restaurant = Restaurant.query.filter_by(name="Test Restaurant").first()
    assert restaurant is not None, "Restaurant not found in database"
    return restaurant


def test_expense_creation(client, app, auth, test_user, dining_category):
    """Test expense creation with restaurant association."""
    # Setup: Create a restaurant first
    restaurant = test_restaurant_creation(client, auth, test_user)

    # Create an expense for the restaurant
    response = create_test_expense(
        client,
        restaurant_id=restaurant.id,
        category_id=dining_category.id
    )

    assert response.status_code == 200, f"Failed to create expense: {response.status_code}"
    assert FlashMessages.EXPENSE_ADDED.encode() in response.data, "Success message not found"

    # Verify expense in database
    expense = Expense.query.filter_by(notes="Test expense").first()
    assert expense is not None, "Expense not found in database"

    # Verify expense details
    assert expense.restaurant_id == restaurant.id
    assert expense.category_id == dining_category.id
    assert expense.user_id == test_user.id
    assert float(expense.amount) == 25.50

    return expense


def test_expense_restaurant_association(client, app, auth, test_user, dining_category):
    """Test that expense is properly associated with restaurant and user."""
    # Create test data
    restaurant = test_restaurant_creation(client, auth, test_user)
    expense = test_expense_creation(client, app, auth, test_user, dining_category)

    # Refresh objects from database
    db_user = User.query.get(test_user.id)
    restaurant = Restaurant.query.get(restaurant.id)

    # Verify user association
    assert expense in db_user.expenses, "Expense not associated with user"

    # Verify restaurant association
    assert expense in restaurant.expenses, "Expense not associated with restaurant"

    # Verify category association
    assert expense in expense.category.expenses, "Expense not associated with category"


def test_invalid_expense_creation(client, app, auth, test_user, dining_category):
    """Test expense creation with invalid data."""
    # Login
    client = auth.login("testuser_1", "testpass")

    # Try to create an expense with invalid data
    response = create_test_expense(
        client,
        restaurant_id=999,  # Non-existent restaurant
        category_id=dining_category.id,
        date="invalid-date",
        amount="0"
    )

    assert response.status_code == 200, "Expected 200 for form validation error"
    assert b"error" in response.data.lower(), "Expected error message not found"
    assert b"Amount must be greater than 0" in response.data


def test_expense_editing_with_restaurant(client, app, auth, test_user):
    """Test editing an expense and verifying restaurant association."""
    # Login the test user
    auth.login("testuser_1", "testpass")

    # Create a restaurant
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
    today = datetime.now().date()
    client.post(
        "/expenses/add",
        data={
            "restaurant_id": 1,
            "date": today.strftime("%Y-%m-%d"),
            "meal_type": "Lunch",
            "amount": "25.50",
            "notes": "Test expense",
        },
    )

    # Edit the expense
    tomorrow = today + timedelta(days=1)
    response = client.post(
        "/expenses/1/edit",
        data={
            "restaurant_id": 1,
            "date": tomorrow.strftime("%Y-%m-%d"),
            "meal_type": "Dinner",
            "amount": "35.50",
            "notes": "Updated expense",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert FlashMessages.EXPENSE_UPDATED.encode() in response.data

    # Verify the expense was updated correctly
    with app.app_context():
        # Get the current SQLAlchemy session
        session = db.session

        # Use Session.get() instead of Query.get()
        expense = session.get(Expense, 1)
        assert expense is not None
        assert expense.amount == 35.50
        assert expense.notes == "Updated expense"
        assert expense.meal_type == "Dinner"
        assert expense.date == tomorrow
        assert expense.restaurant_id == 1
        assert expense.category == "Dining"  # Should maintain category based on restaurant type


def test_expense_deletion_with_restaurant(client, app, auth, test_user):
    """Test deleting an expense and verifying restaurant data remains."""
    # Login the test user
    auth.login("testuser_1", "testpass")

    # Create a restaurant
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
    today = datetime.now().date()
    client.post(
        "/expenses/add",
        data={
            "restaurant_id": 1,
            "date": today.strftime("%Y-%m-%d"),
            "meal_type": "Lunch",
            "amount": "25.50",
            "notes": "Test expense",
        },
    )

    # Delete the expense
    response = client.post(
        "/expenses/1/delete",
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert FlashMessages.EXPENSE_DELETED.encode() in response.data

    # Verify the expense was deleted but restaurant remains
    with app.app_context():
        # Get the current SQLAlchemy session
        session = db.session

        # Use Session.get() instead of Query.get()
        expense = session.get(Expense, 1)
        assert expense is None

        restaurant = session.get(Restaurant, 1)
        assert restaurant is not None
        assert restaurant.name == "Test Restaurant"


def test_expense_export(client, app, auth, test_user):
    """Test exporting expenses to CSV."""
    # Login the test user
    auth.login("testuser_1", "testpass")

    # Create a restaurant
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
    today = datetime.now().date()
    client.post(
        "/expenses/add",
        data={
            "restaurant_id": 1,
            "date": today.strftime("%Y-%m-%d"),
            "meal_type": "Lunch",
            "amount": "25.50",
            "notes": "Test expense",
        },
    )

    # Export expenses
    response = client.get("/expenses/export")
    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    content_disposition = response.headers["Content-Disposition"]
    assert "attachment; filename=expenses.csv" in content_disposition

    # Verify CSV content
    csv_data = response.data.decode("utf-8").split("\n")
    assert len(csv_data) >= 2  # Header + at least one row
    header = "Date,Restaurant,Meal Type,Amount,Notes," "Restaurant Type,Cuisine,Price Range,Location"
    assert header in csv_data[0]
    assert "Test Restaurant" in csv_data[1]
    assert "Lunch" in csv_data[1]
    assert "$25.50" in csv_data[1]
    assert "Test City, CA" in csv_data[1]
