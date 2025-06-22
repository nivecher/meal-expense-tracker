from app.expenses.models import Expense
from app.restaurants.models import Restaurant
from app.auth.models import User
from datetime import datetime, timedelta
from app import db


def test_expense_creation_with_restaurant(client, app, auth):
    """Test the complete flow of creating a restaurant and adding an expense."""
    # Create and login a user
    with app.app_context():
        user = User(username="testuser")
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()

    auth.login()

    # Create a restaurant
    response = client.post(
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
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Restaurant added successfully!" in response.data

    # Add an expense for the restaurant
    today = datetime.now().date()
    response = client.post(
        "/expenses/add",
        data={
            "restaurant_id": 1,
            "date": today.strftime("%Y-%m-%d"),
            "meal_type": "Lunch",
            "amount": "25.50",
            "notes": "Test expense",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Expense added successfully!" in response.data

    # Verify the expense was created with correct restaurant association
    with app.app_context():
        session = db.session

        # Use Session.get() instead of Query.get()
        expense = session.get(Expense, 1)
        assert expense is not None
        assert expense.amount == 25.50
        assert expense.notes == "Test expense"
        assert expense.restaurant_id == 1
        assert expense.category == "Dining"  # Should be set based on restaurant type

        restaurant = session.get(Restaurant, 1)
        assert restaurant is not None
        assert restaurant.name == "Test Restaurant"


def test_expense_editing_with_restaurant(client, app, auth):
    """Test editing an expense and verifying restaurant association."""
    # Create and login a user
    with app.app_context():
        user = User(username="testuser")
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()

    auth.login()

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
    assert b"Expense updated successfully!" in response.data

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


def test_expense_deletion_with_restaurant(client, app, auth):
    """Test deleting an expense and verifying restaurant data remains."""
    # Create and login a user
    with app.app_context():
        user = User(username="testuser")
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()

    auth.login()

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
    assert b"Expense deleted successfully!" in response.data

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


def test_expense_export(client, app, auth):
    """Test exporting expenses to CSV."""
    # Create and login a user
    with app.app_context():
        user = User(username="testuser")
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()

    auth.login()

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
