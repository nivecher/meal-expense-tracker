"""Unit tests for expense services.

These tests focus on the business logic in app/expenses/services.py
without Flask context complexity, providing maximum coverage impact.
"""

import csv
import io
from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest

from app import create_app
from app.auth.models import User
from app.expenses.models import Category, Expense
from app.expenses.services import (
    create_expense_for_user,
    delete_expense_for_user,
    export_expenses_to_csv,
    get_expense_by_id_for_user,
    get_expense_filters,
    get_expenses_for_user,
    get_user_expenses,
    import_expenses_from_csv,
    update_expense_for_user,
)
from app.extensions import db
from app.restaurants.models import Restaurant


class TestExpenseServices:
    """Test expense service functions."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        app = create_app("testing")
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["SECRET_KEY"] = "test_secret_key"

        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()

    @pytest.fixture
    def user(self, app):
        """Create test user."""
        with app.app_context():
            user = User(username="testuser", email="test@example.com", password_hash="hashed_password")
            db.session.add(user)
            db.session.commit()
            return user

    @pytest.fixture
    def restaurant(self, app, user):
        """Create test restaurant."""
        with app.app_context():
            restaurant = Restaurant(name="Test Restaurant", address="123 Test St", user_id=user.id)
            db.session.add(restaurant)
            db.session.commit()
            return restaurant

    @pytest.fixture
    def category(self, app, user):
        """Create test category."""
        with app.app_context():
            category = Category(name="Test Category", user_id=user.id)
            db.session.add(category)
            db.session.commit()
            return category

    @pytest.fixture
    def expense(self, app, user, restaurant, category):
        """Create test expense."""
        with app.app_context():
            expense = Expense(
                amount=Decimal("25.50"),
                description="Test expense",
                date=date.today(),
                restaurant_id=restaurant.id,
                category_id=category.id,
                user_id=user.id,
            )
            db.session.add(expense)
            db.session.commit()
            return expense

    def test_create_expense_for_user(self, app, user, restaurant, category):
        """Test creating an expense for a user."""
        with app.app_context():
            data = {
                "amount": "30.75",
                "description": "New expense",
                "date": date.today().isoformat(),
                "restaurant_id": restaurant.id,
                "category_id": category.id,
            }

            expense = create_expense_for_user(user.id, data)

            assert expense.amount == Decimal("30.75")
            assert expense.description == "New expense"
            assert expense.restaurant_id == restaurant.id
            assert expense.category_id == category.id
            assert expense.user_id == user.id

    def test_get_expenses_for_user(self, app, user, expense):
        """Test getting expenses for a user."""
        with app.app_context():
            expenses = get_expenses_for_user(user.id)

            assert len(expenses) == 1
            assert expenses[0].amount == Decimal("25.50")
            assert expenses[0].description == "Test expense"

    def test_get_expense_by_id_for_user(self, app, user, expense):
        """Test getting a specific expense by ID for a user."""
        with app.app_context():
            found_expense = get_expense_by_id_for_user(expense.id, user.id)

            assert found_expense is not None
            assert found_expense.amount == Decimal("25.50")
            assert found_expense.description == "Test expense"

    def test_get_expense_by_id_for_user_not_found(self, app, user):
        """Test getting a non-existent expense."""
        with app.app_context():
            found_expense = get_expense_by_id_for_user(999, user.id)

            assert found_expense is None

    def test_update_expense_for_user(self, app, user, expense):
        """Test updating an expense for a user."""
        with app.app_context():
            data = {"amount": "35.00", "description": "Updated expense", "date": date.today().isoformat()}

            updated_expense = update_expense_for_user(expense, data)

            assert updated_expense.amount == Decimal("35.00")
            assert updated_expense.description == "Updated expense"

    def test_delete_expense_for_user(self, app, user, expense):
        """Test deleting an expense for a user."""
        with app.app_context():
            delete_expense_for_user(expense)

            # Verify expense is deleted
            deleted_expense = get_expense_by_id_for_user(expense.id, user.id)
            assert deleted_expense is None

    def test_get_expense_filters(self, app):
        """Test getting expense filters from request."""
        with app.app_context():
            from flask import Flask, request

            # Create a test request context
            app = Flask(__name__)
            with app.test_request_context("/?search=lunch&meal_type=dinner&category=food"):
                filters = get_expense_filters(request)

                assert filters["search"] == "lunch"
                assert filters["meal_type"] == "dinner"
                assert filters["category"] == "food"
                assert filters["sort_by"] == "date"
                assert filters["sort_order"] == "desc"

    def test_get_user_expenses_with_filters(self, app, user, expense):
        """Test getting user expenses with filters."""
        with app.app_context():
            filters = {
                "search": "Test",
                "meal_type": "",
                "category": "",
                "start_date": "",
                "end_date": "",
                "sort_by": "date",
                "sort_order": "desc",
            }

            expenses, total = get_user_expenses(user.id, filters)

            assert len(expenses) == 1
            assert expenses[0].description == "Test expense"
            assert total == 25.50

    def test_get_user_expenses_with_search_filter(self, app, user, expense):
        """Test getting user expenses with search filter."""
        with app.app_context():
            # Create another expense with different description
            expense2 = Expense(
                amount=Decimal("15.00"), description="Different expense", date=date.today(), user_id=user.id
            )
            db.session.add(expense2)
            db.session.commit()

            filters = {
                "search": "Test",
                "meal_type": "",
                "category": "",
                "start_date": "",
                "end_date": "",
                "sort_by": "date",
                "sort_order": "desc",
            }

            expenses, total = get_user_expenses(user.id, filters)

            assert len(expenses) == 1
            assert expenses[0].description == "Test expense"
            assert total == 25.50

    def test_export_expenses_to_csv(self, app, user, expense):
        """Test exporting expenses to CSV."""
        with app.app_context():
            csv_content = export_expenses_to_csv(user.id)

            # Parse CSV content
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            rows = list(csv_reader)

            assert len(rows) == 1
            assert rows[0]["amount"] == "25.50"
            assert rows[0]["description"] == "Test expense"

    def test_import_expenses_from_csv(self, app, user, restaurant, category):
        """Test importing expenses from CSV."""
        with app.app_context():
            # Create CSV data
            csv_data = "date,amount,description,restaurant_name,category_name\n"
            csv_data += f"{date.today()},30.00,Imported expense,Test Restaurant,Test Category\n"

            csv_file = Mock()
            csv_file.stream = io.StringIO(csv_data)
            csv_file.filename = "test.csv"

            success, result = import_expenses_from_csv(csv_file, user.id)

            assert success is True
            assert result["success_count"] == 1
            assert result["error_count"] == 0
            assert len(result["errors"]) == 0

            # Verify expense was created
            expenses = get_expenses_for_user(user.id)
            assert len(expenses) == 1
            assert expenses[0].amount == Decimal("30.00")
            assert expenses[0].description == "Imported expense"

    def test_import_expenses_from_csv_with_errors(self, app, user):
        """Test importing expenses from CSV with validation errors."""
        with app.app_context():
            # Create CSV data with missing required fields
            csv_data = "date,amount,description,restaurant_name,category_name\n"
            csv_data += ",30.00,Imported expense,Test Restaurant,Test Category\n"  # Missing date

            csv_file = Mock()
            csv_file.stream = io.StringIO(csv_data)
            csv_file.filename = "test.csv"

            success, result = import_expenses_from_csv(csv_file, user.id)

            assert success is False
            assert result["success_count"] == 0
            assert result["error_count"] == 1
            assert len(result["errors"]) > 0

    def test_expense_services_error_handling(self, app, user):
        """Test error handling in expense services."""
        with app.app_context():
            # Test with invalid user ID
            expenses = get_expenses_for_user(999)
            assert len(expenses) == 0

            # Test with invalid expense ID
            expense = get_expense_by_id_for_user(999, user.id)
            assert expense is None

    def test_expense_services_edge_cases(self, app, user):
        """Test edge cases in expense services."""
        with app.app_context():
            # Test empty expenses list
            expenses = get_expenses_for_user(user.id)
            assert expenses == []

            # Test export with no expenses
            csv_content = export_expenses_to_csv(user.id)
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            rows = list(csv_reader)
            assert len(rows) == 0

    def test_expense_amount_validation(self, app, user, restaurant, category):
        """Test expense amount validation."""
        with app.app_context():
            # Test positive amount
            data = {
                "amount": "25.50",
                "description": "Valid expense",
                "date": date.today().isoformat(),
                "restaurant_id": restaurant.id,
                "category_id": category.id,
            }

            expense = create_expense_for_user(user.id, data)
            assert expense.amount == Decimal("25.50")

            # Test zero amount
            data["amount"] = "0.00"
            expense = create_expense_for_user(user.id, data)
            assert expense.amount == Decimal("0.00")

    def test_expense_date_handling(self, app, user, restaurant, category):
        """Test expense date handling."""
        with app.app_context():
            # Test with different date formats
            test_date = date(2024, 1, 15)

            data = {
                "amount": "25.50",
                "description": "Date test expense",
                "date": test_date.isoformat(),
                "restaurant_id": restaurant.id,
                "category_id": category.id,
            }

            expense = create_expense_for_user(user.id, data)
            assert expense.date == test_date

    def test_expense_restaurant_association(self, app, user, restaurant, category):
        """Test expense restaurant association."""
        with app.app_context():
            data = {
                "amount": "25.50",
                "description": "Restaurant test expense",
                "date": date.today().isoformat(),
                "restaurant_id": restaurant.id,
                "category_id": category.id,
            }

            expense = create_expense_for_user(user.id, data)

            # Verify restaurant association
            assert expense.restaurant_id == restaurant.id
            assert expense.restaurant.name == "Test Restaurant"

    def test_expense_category_association(self, app, user, restaurant, category):
        """Test expense category association."""
        with app.app_context():
            data = {
                "amount": "25.50",
                "description": "Category test expense",
                "date": date.today().isoformat(),
                "restaurant_id": restaurant.id,
                "category_id": category.id,
            }

            expense = create_expense_for_user(user.id, data)

            # Verify category association
            assert expense.category_id == category.id
            assert expense.category.name == "Test Category"

    def test_expense_user_isolation(self, app, user, restaurant, category):
        """Test that expenses are isolated by user."""
        with app.app_context():
            # Create another user
            user2 = User(username="testuser2", email="test2@example.com", password_hash="hashed_password2")
            db.session.add(user2)
            db.session.commit()

            # Create expense for user1
            data = {
                "amount": "25.50",
                "description": "User1 expense",
                "date": date.today().isoformat(),
                "restaurant_id": restaurant.id,
                "category_id": category.id,
            }

            create_expense_for_user(user.id, data)

            # Create expense for user2
            data["description"] = "User2 expense"
            expense2 = create_expense_for_user(user2.id, data)

            # Verify isolation
            user1_expenses = get_expenses_for_user(user.id)
            user2_expenses = get_expenses_for_user(user2.id)

            assert len(user1_expenses) == 1
            assert len(user2_expenses) == 1
            assert user1_expenses[0].description == "User1 expense"
            assert user2_expenses[0].description == "User2 expense"

            # User1 should not see user2's expense
            user1_expense = get_expense_by_id_for_user(expense2.id, user.id)
            assert user1_expense is None
