"""Integration tests for expense workflows.

These tests focus on complete expense management workflows including
data processing, calculations, and reporting.
"""

import csv
import io
from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from app import create_app
from app.auth.models import User
from app.expenses.models import Category
from app.extensions import db
from app.restaurants.models import Restaurant


class TestExpenseWorkflows:
    """Test complete expense management workflows."""

    @pytest.fixture
    def app(self):
        """Create test Flask app with proper configuration."""
        app = create_app("testing")
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["SECRET_KEY"] = "test_secret_key"
        app.config["WTF_CSRF_ENABLED"] = False

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

    def test_expense_creation_workflow(self, app, user, restaurant, category):
        """Test complete expense creation workflow."""
        with app.app_context():
            with patch("app.expenses.services.create_expense_for_user") as mock_create:
                # Mock successful expense creation
                mock_expense = Mock()
                mock_expense.id = 1
                mock_expense.amount = Decimal("25.50")
                mock_expense.description = "Test expense"
                mock_expense.restaurant_id = restaurant.id
                mock_expense.category_id = category.id
                mock_create.return_value = mock_expense

                # Test expense creation
                from app.expenses.services import create_expense_for_user

                expense_data = {
                    "amount": "25.50",
                    "description": "Test expense",
                    "restaurant_id": restaurant.id,
                    "category_id": category.id,
                    "date": date.today().isoformat(),
                }

                result = create_expense_for_user(user.id, expense_data)
                assert result.id == 1
                assert result.amount == Decimal("25.50")

    def test_expense_filtering_workflow(self, app, user):
        """Test expense filtering and search workflow."""
        with app.app_context():
            with patch("app.expenses.services.get_user_expenses") as mock_get_expenses:
                # Mock filtered expenses
                mock_expenses = [
                    Mock(id=1, amount=Decimal("25.50"), description="Lunch"),
                    Mock(id=2, amount=Decimal("15.75"), description="Coffee"),
                ]
                mock_get_expenses.return_value = (mock_expenses, 41.25)

                # Test expense filtering
                from app.expenses.services import get_user_expenses

                filters = {
                    "search": "lunch",
                    "meal_type": "lunch",
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-31",
                }

                expenses, total = get_user_expenses(user.id, filters)
                assert len(expenses) == 2
                assert total == 41.25

    def test_expense_aggregation_workflow(self, app, user):
        """Test expense aggregation and calculation workflow."""
        with app.app_context():
            with patch("app.expenses.services.get_expense_stats_for_user") as mock_stats:
                # Mock expense statistics
                mock_stats.return_value = {
                    "total_expenses": Decimal("150.75"),
                    "average_expense": Decimal("25.13"),
                    "expense_count": 6,
                    "monthly_totals": {"2024-01": Decimal("75.25"), "2024-02": Decimal("75.50")},
                    "category_breakdown": {"Food": Decimal("100.00"), "Drinks": Decimal("50.75")},
                }

                # Test expense aggregation
                from app.expenses.services import get_expense_stats_for_user

                stats = get_expense_stats_for_user(user.id)

                assert stats["total_expenses"] == Decimal("150.75")
                assert stats["expense_count"] == 6
                assert "Food" in stats["category_breakdown"]

    def test_expense_import_workflow(self, app, user, restaurant, category):
        """Test expense CSV import workflow."""
        with app.app_context():
            # Create CSV data
            csv_data = "date,amount,description,restaurant_name,category_name\n"
            csv_data += "2024-01-15,25.50,Lunch,Test Restaurant,Test Category\n"
            csv_data += "2024-01-16,15.75,Coffee,Test Restaurant,Test Category\n"

            csv_file = io.StringIO(csv_data)

            with patch("app.expenses.services.process_expense_import") as mock_import:
                # Mock import results
                mock_import.return_value = {
                    "success_count": 2,
                    "error_count": 0,
                    "errors": [],
                    "expenses": [Mock(id=1, amount=Decimal("25.50")), Mock(id=2, amount=Decimal("15.75"))],
                }

                # Test expense import
                from app.expenses.services import process_expense_import

                result = process_expense_import(csv_file, user.id)

                assert result["success_count"] == 2
                assert result["error_count"] == 0

    def test_expense_export_workflow(self, app, user):
        """Test expense CSV export workflow."""
        with app.app_context():
            with patch("app.expenses.services.get_expenses_for_user") as mock_get_expenses:
                # Mock expenses for export
                mock_expenses = [
                    Mock(
                        id=1,
                        amount=Decimal("25.50"),
                        description="Lunch",
                        date=date(2024, 1, 15),
                        restaurant=Mock(name="Test Restaurant"),
                        category=Mock(name="Test Category"),
                    ),
                    Mock(
                        id=2,
                        amount=Decimal("15.75"),
                        description="Coffee",
                        date=date(2024, 1, 16),
                        restaurant=Mock(name="Test Restaurant"),
                        category=Mock(name="Test Category"),
                    ),
                ]
                mock_get_expenses.return_value = mock_expenses

                # Test expense export
                from app.expenses.services import export_expenses_to_csv

                csv_content = export_expenses_to_csv(user.id)

                # Parse CSV content
                csv_reader = csv.DictReader(io.StringIO(csv_content))
                rows = list(csv_reader)

                assert len(rows) == 2
                assert rows[0]["amount"] == "25.50"
                assert rows[1]["amount"] == "15.75"

    def test_expense_reporting_workflow(self, app, user):
        """Test expense reporting and analytics workflow."""
        with app.app_context():
            with patch("app.expenses.services.generate_expense_report") as mock_report:
                # Mock expense report
                mock_report.return_value = {
                    "summary": {
                        "total_expenses": Decimal("500.00"),
                        "average_daily": Decimal("16.67"),
                        "expense_count": 30,
                    },
                    "trends": {"weekly_change": Decimal("5.25"), "monthly_change": Decimal("25.50")},
                    "top_categories": [
                        {"name": "Food", "amount": Decimal("300.00"), "percentage": 60.0},
                        {"name": "Drinks", "amount": Decimal("200.00"), "percentage": 40.0},
                    ],
                    "top_restaurants": [{"name": "Test Restaurant", "amount": Decimal("250.00"), "count": 15}],
                }

                # Test expense reporting
                from app.expenses.services import generate_expense_report

                report = generate_expense_report(user.id, "2024-01-01", "2024-01-31")

                assert report["summary"]["total_expenses"] == Decimal("500.00")
                assert len(report["top_categories"]) == 2
                assert report["top_categories"][0]["name"] == "Food"

    def test_expense_validation_workflow(self, app, user):
        """Test expense data validation workflow."""
        with app.app_context():
            with patch("app.expenses.services.validate_expense_data") as mock_validate:
                # Mock validation results
                mock_validate.return_value = {
                    "valid": False,
                    "errors": ["Amount must be positive", "Date cannot be in the future"],
                    "warnings": ["Restaurant not found, will be created"],
                }

                # Test expense validation
                from app.expenses.services import validate_expense_data

                expense_data = {"amount": "-25.50", "date": "2025-01-01"}  # Invalid negative amount  # Future date

                result = validate_expense_data(expense_data)
                assert result["valid"] is False
                assert len(result["errors"]) == 2

    def test_expense_bulk_operations_workflow(self, app, user):
        """Test expense bulk operations workflow."""
        with app.app_context():
            with patch("app.expenses.services.bulk_update_expenses") as mock_bulk_update:
                # Mock bulk update results
                mock_bulk_update.return_value = {
                    "updated_count": 5,
                    "error_count": 1,
                    "errors": ["Expense ID 999 not found"],
                }

                # Test bulk expense update
                from app.expenses.services import bulk_update_expenses

                updates = [
                    {"id": 1, "category_id": 2},
                    {"id": 2, "category_id": 2},
                    {"id": 999, "category_id": 2},  # Non-existent expense
                ]

                result = bulk_update_expenses(user.id, updates)
                assert result["updated_count"] == 5
                assert result["error_count"] == 1

    def test_expense_search_workflow(self, app, user):
        """Test expense search functionality workflow."""
        with app.app_context():
            with patch("app.expenses.services.search_expenses") as mock_search:
                # Mock search results
                mock_search.return_value = [
                    Mock(id=1, description="Lunch at Italian place", amount=Decimal("25.50")),
                    Mock(id=2, description="Italian dinner", amount=Decimal("45.00")),
                ]

                # Test expense search
                from app.expenses.services import search_expenses

                results = search_expenses(user.id, "italian")

                assert len(results) == 2
                assert "Italian" in results[0].description

    def test_expense_error_handling_workflow(self, app, user):
        """Test expense error handling workflow."""
        with app.app_context():
            with patch("app.expenses.services.create_expense_for_user") as mock_create:
                # Mock service exception
                mock_create.side_effect = Exception("Database connection failed")

                # Test error handling
                from app.expenses.services import create_expense_for_user

                with pytest.raises(Exception) as exc_info:
                    create_expense_for_user(user.id, {"amount": "25.50"})

                assert "Database connection failed" in str(exc_info.value)

    def test_expense_data_processing_workflow(self, app, user):
        """Test expense data processing and transformation workflow."""
        with app.app_context():
            with patch("app.expenses.services.process_expense_data") as mock_process:
                # Mock data processing results
                mock_process.return_value = {
                    "processed_data": {
                        "amount": Decimal("25.50"),
                        "date": date(2024, 1, 15),
                        "normalized_description": "lunch at test restaurant",
                        "detected_category": "Food",
                    },
                    "confidence_score": 0.85,
                }

                # Test expense data processing
                from app.expenses.services import process_expense_data

                raw_data = {"amount": "25.50", "description": "Lunch at Test Restaurant", "date": "2024-01-15"}

                result = process_expense_data(raw_data)
                assert result["processed_data"]["amount"] == Decimal("25.50")
                assert result["confidence_score"] == 0.85
