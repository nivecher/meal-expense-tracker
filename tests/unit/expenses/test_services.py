"""Unit tests for expense services.

These tests focus on the business logic in app/expenses/services.py
without Flask context complexity, providing maximum coverage impact.
"""

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
    export_expenses_for_user,
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
            return user, user.id

    @pytest.fixture
    def restaurant(self, app, user):
        """Create test restaurant."""
        user_obj, user_id = user  # Unpack user and user_id
        with app.app_context():
            restaurant = Restaurant(name="Test Restaurant", address_line_1="123 Test St", user_id=user_id)
            db.session.add(restaurant)
            db.session.commit()
            return restaurant, restaurant.id

    @pytest.fixture
    def category(self, app, user):
        """Create test category."""
        user_obj, user_id = user  # Unpack user and user_id
        with app.app_context():
            category = Category(name="Test Category", user_id=user_id)
            db.session.add(category)
            db.session.commit()
            return category, category.id

    @pytest.fixture
    def expense(self, app, user, restaurant, category):
        """Create test expense."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        category_obj, category_id = category  # Unpack category and category_id
        with app.app_context():
            expense = Expense(
                amount=Decimal("25.50"),
                notes="Test expense",
                date=date.today(),
                restaurant_id=restaurant_id,
                category_id=category_id,
                user_id=user_id,
            )
            db.session.add(expense)
            db.session.commit()
            return expense, expense.id

    def test_create_expense_for_user(self, app, user, restaurant, category):
        """Test creating an expense for a user."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        category_obj, category_id = category  # Unpack category and category_id
        with app.app_context():
            data = {
                "amount": 30.75,
                "notes": "New expense",
                "date": date.today(),
                "restaurant_id": restaurant_id,
                "category_id": category_id,
            }

            expense = create_expense_for_user(user_id, data)

            assert expense.amount == Decimal("30.75")
            assert expense.notes == "New expense"
            assert expense.restaurant_id == restaurant_id
            assert expense.category_id == category_id
            assert expense.user_id == user_id

    def test_get_expenses_for_user(self, app, user, expense):
        """Test getting expenses for a user."""
        user_obj, user_id = user  # Unpack user and user_id
        expense_obj, expense_id = expense  # Unpack expense and expense_id
        with app.app_context():
            expenses = get_expenses_for_user(user_id)

            assert len(expenses) == 1
            assert expenses[0].amount == Decimal("25.50")
            assert expenses[0].notes == "Test expense"

    def test_get_expense_by_id_for_user(self, app, user, expense):
        """Test getting a specific expense by ID for a user."""
        user_obj, user_id = user  # Unpack user and user_id
        expense_obj, expense_id = expense  # Unpack expense and expense_id
        with app.app_context():
            found_expense = get_expense_by_id_for_user(expense_id, user_id)

            assert found_expense is not None
            assert found_expense.amount == Decimal("25.50")
            assert found_expense.notes == "Test expense"

    def test_get_expense_by_id_for_user_not_found(self, app, user):
        """Test getting a non-existent expense."""
        user_obj, user_id = user  # Unpack user and user_id
        # No expense fixture needed for this test
        with app.app_context():
            found_expense = get_expense_by_id_for_user(999, user_id)

            assert found_expense is None

    def test_update_expense_for_user(self, app, user, expense):
        """Test updating an expense for a user."""
        user_obj, user_id = user  # Unpack user and user_id
        expense_obj, expense_id = expense  # Unpack expense and expense_id
        with app.app_context():
            data = {"amount": 35.00, "notes": "Updated expense", "date": date.today()}

            updated_expense = update_expense_for_user(expense_obj, data)

            assert updated_expense.amount == Decimal("35.00")
            assert updated_expense.notes == "Updated expense"

    def test_delete_expense_for_user(self, app, user, expense):
        """Test deleting an expense for a user."""
        user_obj, user_id = user  # Unpack user and user_id
        expense_obj, expense_id = expense  # Unpack expense and expense_id
        with app.app_context():
            delete_expense_for_user(expense_obj)

            # Verify expense is deleted
            deleted_expense = get_expense_by_id_for_user(expense_id, user_id)
            assert deleted_expense is None

    def test_get_expense_filters(self, app):
        """Test getting expense filters from request."""
        # No expense fixture needed for this test
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
        user_obj, user_id = user  # Unpack user and user_id
        expense_obj, expense_id = expense  # Unpack expense and expense_id
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

            expenses, total, avg_price_per_person = get_user_expenses(user_id, filters)

            assert len(expenses) == 1
            assert expenses[0].notes == "Test expense"
            assert total == 25.50

    def test_get_user_expenses_with_search_filter(self, app, user, expense):
        """Test getting user expenses with search filter."""
        user_obj, user_id = user  # Unpack user and user_id
        expense_obj, expense_id = expense  # Unpack expense and expense_id
        with app.app_context():
            # Create another expense with different description
            expense2 = Expense(amount=Decimal("15.00"), notes="Different expense", date=date.today(), user_id=user_id)
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

            expenses, total, avg_price_per_person = get_user_expenses(user_id, filters)

            assert len(expenses) == 1
            assert expenses[0].notes == "Test expense"
            assert total == 25.50

    def test_export_expenses_to_csv(self, app, user, expense):
        """Test exporting expenses for CSV generation."""
        user_obj, user_id = user  # Unpack user and user_id
        expense_obj, expense_id = expense  # Unpack expense and expense_id
        with app.app_context():
            expenses_data = export_expenses_for_user(user_id)

            # Check that we get a list of dictionaries
            assert isinstance(expenses_data, list)
            assert len(expenses_data) == 1

            expense_data = expenses_data[0]
            assert expense_data["amount"] == 25.50
            assert expense_data["notes"] == "Test expense"

    def test_import_expenses_from_csv(self, app, user, restaurant, category):
        """Test importing expenses from CSV."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        category_obj, category_id = category  # Unpack category and category_id
        # No expense fixture needed for this test
        with app.app_context():
            # Create CSV data
            csv_data = "date,amount,notes,restaurant_name,category_name\n"
            csv_data += f"{date.today()},30.00,Imported expense,Test Restaurant,Test Category\n"

            csv_file = Mock()
            csv_file.read.return_value = csv_data.encode("utf-8")
            csv_file.seek.return_value = None
            csv_file.filename = "test.csv"

            success, result = import_expenses_from_csv(csv_file, user_id)

            assert success is True
            assert result["success_count"] == 1
            assert result["error_count"] == 0
            assert len(result["errors"]) == 0

            # Verify expense was created
            expenses = get_expenses_for_user(user_id)
            assert len(expenses) == 1
            assert expenses[0].amount == Decimal("30.00")
            assert expenses[0].notes == "Imported expense"

    def test_import_expenses_from_csv_with_errors(self, app, user):
        """Test importing expenses from CSV with validation errors."""
        user_obj, user_id = user  # Unpack user and user_id
        # No expense fixture needed for this test
        with app.app_context():
            # Create CSV data with missing required fields
            csv_data = "date,amount,notes,restaurant_name,category_name\n"
            csv_data += ",30.00,Imported expense,Test Restaurant,Test Category\n"  # Missing date

            csv_file = Mock()
            csv_file.read.return_value = csv_data.encode("utf-8")
            csv_file.seek.return_value = None
            csv_file.filename = "test.csv"

            success, result = import_expenses_from_csv(csv_file, user_id)

            assert success is False
            assert result["success_count"] == 0
            assert result["error_count"] == 1
            assert len(result["errors"]) > 0

    def test_expense_services_error_handling(self, app, user):
        """Test error handling in expense services."""
        user_obj, user_id = user  # Unpack user and user_id
        # No expense fixture needed for this test
        with app.app_context():
            # Test with invalid user ID
            expenses = get_expenses_for_user(999)
            assert len(expenses) == 0

            # Test with invalid expense ID
            expense = get_expense_by_id_for_user(999, user_id)
            assert expense is None

    def test_expense_services_edge_cases(self, app, user):
        """Test edge cases in expense services."""
        user_obj, user_id = user  # Unpack user and user_id
        # No expense fixture needed for this test
        with app.app_context():
            # Test empty expenses list
            expenses = get_expenses_for_user(user_id)
            assert expenses == []

            # Test export with no expenses
            expenses_data = export_expenses_for_user(user_id)
            assert isinstance(expenses_data, list)
            assert len(expenses_data) == 0

    def test_expense_amount_validation(self, app, user, restaurant, category):
        """Test expense amount validation."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        category_obj, category_id = category  # Unpack category and category_id
        # No expense fixture needed for this test
        with app.app_context():
            # Test positive amount
            data = {
                "amount": 25.50,
                "notes": "Valid expense",
                "date": date.today(),
                "restaurant_id": restaurant_id,
                "category_id": category_id,
            }

            expense = create_expense_for_user(user_id, data)
            assert expense.amount == Decimal("25.50")

            # Test zero amount
            data["amount"] = "0.00"
            expense = create_expense_for_user(user_id, data)
            assert expense.amount == Decimal("0.00")

    def test_expense_date_handling(self, app, user, restaurant, category):
        """Test expense date handling."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        category_obj, category_id = category  # Unpack category and category_id
        # No expense fixture needed for this test
        with app.app_context():
            # Test with different date formats
            test_date = date(2024, 1, 15)

            data = {
                "amount": 25.50,
                "notes": "Date test expense",
                "date": test_date,
                "restaurant_id": restaurant_id,
                "category_id": category_id,
            }

            expense = create_expense_for_user(user_id, data)
            assert expense.date.date() == test_date

    def test_expense_restaurant_association(self, app, user, restaurant, category):
        """Test expense restaurant association."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        category_obj, category_id = category  # Unpack category and category_id
        # No expense fixture needed for this test
        with app.app_context():
            data = {
                "amount": 25.50,
                "notes": "Restaurant test expense",
                "date": date.today(),
                "restaurant_id": restaurant_id,
                "category_id": category_id,
            }

            expense = create_expense_for_user(user_id, data)

            # Verify restaurant association
            assert expense.restaurant_id == restaurant_id
            assert expense.restaurant.name == "Test Restaurant"

    def test_expense_category_association(self, app, user, restaurant, category):
        """Test expense category association."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        category_obj, category_id = category  # Unpack category and category_id
        # No expense fixture needed for this test
        with app.app_context():
            data = {
                "amount": 25.50,
                "notes": "Category test expense",
                "date": date.today(),
                "restaurant_id": restaurant_id,
                "category_id": category_id,
            }

            expense = create_expense_for_user(user_id, data)

            # Verify category association
            assert expense.category_id == category_id
            assert expense.category.name == "Test Category"

    def test_expense_user_isolation(self, app, user, restaurant, category):
        """Test that expenses are isolated by user."""
        user_obj, user_id = user  # Unpack user and user_id
        restaurant_obj, restaurant_id = restaurant  # Unpack restaurant and restaurant_id
        category_obj, category_id = category  # Unpack category and category_id
        # No expense fixture needed for this test
        with app.app_context():
            # Create another user
            user2 = User(username="testuser2", email="test2@example.com", password_hash="hashed_password2")
            db.session.add(user2)
            db.session.commit()

            # Create expense for user1
            data = {
                "amount": 25.50,
                "notes": "User1 expense",
                "date": date.today(),
                "restaurant_id": restaurant_id,
                "category_id": category_id,
            }

            create_expense_for_user(user_id, data)

            # Create expense for user2
            data["notes"] = "User2 expense"
            expense2 = create_expense_for_user(user2.id, data)

            # Verify isolation
            user1_expenses = get_expenses_for_user(user_id)
            user2_expenses = get_expenses_for_user(user2.id)

            assert len(user1_expenses) == 1
            assert len(user2_expenses) == 1
            assert user1_expenses[0].notes == "User1 expense"
            assert user2_expenses[0].notes == "User2 expense"

            # User1 should not see user2's expense
            user1_expense = get_expense_by_id_for_user(expense2.id, user_id)
            assert user1_expense is None
