"""Unit tests for expense services.

These tests focus on the business logic in app/expenses/services.py
without Flask context complexity, providing maximum coverage impact.
"""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock

import pytest

from app import create_app
from app.auth.models import User
from app.expenses.models import Category, Expense, ExpenseTag, Tag
from app.expenses.services import (
    apply_expense_import_review,
    build_expense_import_review,
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

    def test_create_expense_for_user(self, app, user, restaurant, category) -> None:
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

    def test_get_expenses_for_user(self, app, user, expense) -> None:
        """Test getting expenses for a user."""
        user_obj, user_id = user  # Unpack user and user_id
        expense_obj, expense_id = expense  # Unpack expense and expense_id
        with app.app_context():
            expenses = get_expenses_for_user(user_id)

            assert len(expenses) == 1
            assert expenses[0].amount == Decimal("25.50")
            assert expenses[0].notes == "Test expense"

    def test_get_expense_by_id_for_user(self, app, user, expense) -> None:
        """Test getting a specific expense by ID for a user."""
        user_obj, user_id = user  # Unpack user and user_id
        expense_obj, expense_id = expense  # Unpack expense and expense_id
        with app.app_context():
            found_expense = get_expense_by_id_for_user(expense_id, user_id)

            assert found_expense is not None
            assert found_expense.amount == Decimal("25.50")
            assert found_expense.notes == "Test expense"

    def test_get_expense_by_id_for_user_not_found(self, app, user) -> None:
        """Test getting a non-existent expense."""
        user_obj, user_id = user  # Unpack user and user_id
        # No expense fixture needed for this test
        with app.app_context():
            found_expense = get_expense_by_id_for_user(999, user_id)

            assert found_expense is None

    def test_update_expense_for_user(self, app, user, expense) -> None:
        """Test updating an expense for a user."""
        user_obj, user_id = user  # Unpack user and user_id
        expense_obj, expense_id = expense  # Unpack expense and expense_id
        with app.app_context():
            data = {"amount": 35.00, "notes": "Updated expense", "date": date.today()}

            updated_expense = update_expense_for_user(expense_obj, data)

            assert updated_expense.amount == Decimal("35.00")
            assert updated_expense.notes == "Updated expense"

    def test_delete_expense_for_user(self, app, user, expense) -> None:
        """Test deleting an expense for a user."""
        user_obj, user_id = user  # Unpack user and user_id
        expense_obj, expense_id = expense  # Unpack expense and expense_id
        with app.app_context():
            delete_expense_for_user(expense_obj)

            # Verify expense is deleted
            deleted_expense = get_expense_by_id_for_user(expense_id, user_id)
            assert deleted_expense is None

    def test_get_expense_filters(self, app) -> None:
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

    def test_get_user_expenses_with_filters(self, app, user, expense) -> None:
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

    def test_get_user_expenses_with_search_filter(self, app, user, expense) -> None:
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

    def test_export_expenses_to_csv(self, app, user, expense) -> None:
        """Test exporting expenses for CSV generation."""
        user_obj, user_id = user  # Unpack user and user_id
        expense_obj, expense_id = expense  # Unpack expense and expense_id
        with app.app_context():
            stored_expense = db.session.get(Expense, expense_id)
            assert stored_expense is not None
            assert stored_expense.restaurant is not None
            stored_expense.restaurant.location_name = "Wylie"
            db.session.add(stored_expense.restaurant)
            db.session.commit()

            expenses_data = export_expenses_for_user(user_id)

            # Check that we get a list of dictionaries
            assert isinstance(expenses_data, list)
            assert len(expenses_data) == 1

            expense_data = expenses_data[0]
            assert expense_data["amount"] == 25.50
            assert expense_data["notes"] == "Test expense"
            assert expense_data["restaurant_name"] == "Test Restaurant - Wylie"

    def test_export_expenses_preserves_tag_order(self, app, user, expense) -> None:
        """Export should preserve the order tags were added to the expense."""
        user_obj, user_id = user
        expense_obj, expense_id = expense

        with app.app_context():
            first_tag = Tag(name="Zeta", user_id=user_id)
            second_tag = Tag(name="Alpha", user_id=user_id)
            db.session.add_all([first_tag, second_tag])
            db.session.commit()

            db.session.add(ExpenseTag(expense_id=expense_id, tag_id=first_tag.id, added_by=user_id))
            db.session.commit()
            db.session.add(ExpenseTag(expense_id=expense_id, tag_id=second_tag.id, added_by=user_id))
            db.session.commit()

            expenses_data = export_expenses_for_user(user_id, [expense_id])

            assert len(expenses_data) == 1
            assert expenses_data[0]["tags"] == "Zeta, Alpha"

    def test_import_expenses_from_csv(self, app, user, restaurant, category) -> None:
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

    def test_import_expenses_from_csv_with_errors(self, app, user) -> None:
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

    def test_build_expense_import_review_for_simplifi(self, app, user, restaurant) -> None:
        """Test building review rows for a Simplifi-style import file."""
        user_obj, user_id = user
        restaurant_obj, restaurant_id = restaurant

        with app.app_context():
            stored_restaurant = db.session.get(Restaurant, restaurant_id)
            assert stored_restaurant is not None
            stored_restaurant.name = "Chick-fil-A"
            stored_restaurant.location_name = "Wylie"
            db.session.add(
                Expense(
                    amount=Decimal("25.00"),
                    notes="Existing duplicate candidate",
                    date=datetime.strptime("2026-03-03", "%Y-%m-%d"),
                    restaurant_id=restaurant_id,
                    user_id=user_id,
                )
            )
            db.session.commit()

            csv_data = "Date,Payee,Category,Amount,Tags,Notes,Exclusion\n"
            csv_data += "6-Mar-26,Chick-fil-A - Wylie,Dining & Drinks:Fast Food,-25.00,Pam; Morgan,Test note,yes\n"

            csv_file = Mock()
            csv_file.read.return_value = csv_data.encode("utf-8")
            csv_file.seek.return_value = None
            csv_file.filename = "simplifi.csv"

            success, result = build_expense_import_review(csv_file, user_id)

            assert success is True
            assert result["total_rows"] == 1
            row = result["review_rows"][0]
            assert row["import_source_type"] == "simplifi"
            assert row["parsed_visit_date"] == ""
            assert row["parsed_cleared_date"] == "2026-03-06"
            assert row["parsed_date"] == "2026-03-06"
            assert row["parsed_time_display"] == ""
            assert row["amount"] == "25.00"
            assert row["category_name"] == "Fast Food"
            assert row["tags"] == "Pam, Morgan"
            assert row["default_decision"] == "skip"
            assert len(row["duplicate_candidates"]) == 1
            assert row["duplicate_candidates"][0]["time_display"] == "00:00 UTC"
            comparison = row["duplicate_candidates"][0]["comparison"]
            assert comparison["change_count"] == 4
            assert {change["field"] for change in comparison["changes"]} == {
                "Cleared Date",
                "Expense category",
                "Notes",
                "Tags",
            }
            assert row["restaurant_candidates"][0]["display_name"] == "Chick-fil-A - Wylie"
            assert row["tag_count"] == 2
            assert row["tag_new_count"] == 2

    def test_build_expense_import_review_accepts_simplifi_default_date_format(self, app, user) -> None:
        """Test Simplifi import review supports month-name dates like 'Jan 1, 2025'."""
        user_obj, user_id = user

        with app.app_context():
            csv_data = "Date,Payee,Category,Amount,Tags,Notes,Exclusion\n"
            csv_data += '"Jan 1, 2025",Coffee Shop,Dining & Drinks:Coffee,-5.75,,,no\n'

            csv_file = Mock()
            csv_file.read.return_value = csv_data.encode("utf-8")
            csv_file.seek.return_value = None
            csv_file.filename = "simplifi-default-date.csv"

            success, result = build_expense_import_review(csv_file, user_id)

            assert success is True
            assert result["total_rows"] == 1
            row = result["review_rows"][0]
            assert row["import_source_type"] == "simplifi"
            assert row["parsed_date"] == "2025-01-01"
            assert row["parsed_cleared_date"] == "2025-01-01"
            assert row["amount"] == "5.75"
            assert row["default_decision"] == "skip"
            assert row["error_messages"] == []

    def test_build_expense_import_review_warns_when_cleared_date_is_far_after_visit_date(
        self, app, user, restaurant
    ) -> None:
        """Test Simplifi review warns when cleared date is more than three days after visit date."""
        user_obj, user_id = user
        restaurant_obj, restaurant_id = restaurant

        with app.app_context():
            existing_expense = Expense(
                amount=Decimal("25.00"),
                notes="Existing duplicate candidate",
                date=datetime.strptime("2026-03-01", "%Y-%m-%d"),
                restaurant_id=restaurant_id,
                user_id=user_id,
            )
            db.session.add(existing_expense)
            db.session.commit()

            csv_data = "Date,Payee,Category,Amount,Exclusion\n"
            csv_data += "6-Mar-26,Test Restaurant,Dining & Drinks:Fast Food,-25.00,no\n"

            csv_file = Mock()
            csv_file.read.return_value = csv_data.encode("utf-8")
            csv_file.seek.return_value = None
            csv_file.filename = "simplifi-warning.csv"

            success, result = build_expense_import_review(csv_file, user_id)

            assert success is True
            row = result["review_rows"][0]
            assert row["warning_messages"] == [
                f"Expense #{existing_expense.id}: Cleared date 2026-03-06 is 5 days after visit date 2026-03-01."
            ]

    def test_build_expense_import_review_ignores_blank_rows_and_auto_matches_single_address_only_match(
        self, app, user
    ) -> None:
        """Test that a single suggested address-only match is auto-selected."""
        user_obj, user_id = user

        with app.app_context():
            restaurant = Restaurant(
                name="The Atrium Cafe",
                address_line_1="123 Main St Wylie TX",
                user_id=user_id,
            )
            db.session.add(restaurant)
            db.session.commit()

            csv_data = "Date,Payee,Address,Category,Amount,Tags,Notes\n"
            csv_data += ",,,,,,\n"
            csv_data += (
                "5-Mar-26,Unknown Payee,123 Main St Wylie TX,Dining & Drinks:Restaurants,-17.59,Morgan,Address match\n"
            )

            csv_file = Mock()
            csv_file.read.return_value = csv_data.encode("utf-8")
            csv_file.seek.return_value = None
            csv_file.filename = "simplifi-address.csv"

            success, result = build_expense_import_review(csv_file, user_id)

            assert success is True
            assert result["total_rows"] == 1
            row = result["review_rows"][0]
            assert row["restaurant_candidates"][0]["display_name"] == "The Atrium Cafe"
            assert row["restaurant_candidates"][0]["match_basis"] == "exact address"
            assert row["suggested_restaurant_id"] == restaurant.id
            assert row["restaurant_requires_confirmation"] is False
            assert row["default_decision"] == "match"

    def test_build_expense_import_review_auto_matches_exact_display_name_and_address(self, app, user) -> None:
        """Test that an exact display-name and address match is auto-selected."""
        user_obj, user_id = user

        with app.app_context():
            restaurant = Restaurant(
                name="The Atrium Cafe",
                location_name="Downtown",
                address_line_1="123 Main St",
                city="Wylie",
                state="TX",
                postal_code="75098",
                user_id=user_id,
            )
            db.session.add(restaurant)
            db.session.commit()

            csv_data = "Date,Payee,Address,Category,Amount\n"
            csv_data += (
                "5-Mar-26,The Atrium Cafe - Downtown,123 Main St Wylie TX 75098,Dining & Drinks:Restaurants,-17.59\n"
            )

            csv_file = Mock()
            csv_file.read.return_value = csv_data.encode("utf-8")
            csv_file.seek.return_value = None
            csv_file.filename = "simplifi-display-address.csv"

            success, result = build_expense_import_review(csv_file, user_id)

            assert success is True
            row = result["review_rows"][0]
            assert row["restaurant_candidates"][0]["display_name"] == "The Atrium Cafe - Downtown"
            assert row["restaurant_candidates"][0]["match_basis"] == "exact display name + address"
            assert row["suggested_restaurant_id"] == restaurant.id
            assert row["restaurant_requires_confirmation"] is False
            assert row["default_decision"] == "match"

    def test_build_expense_import_review_picks_unique_exact_display_name_match_over_partial_match(
        self, app, user
    ) -> None:
        """Test that a unique exact display-name match is auto-selected over looser matches."""
        user_obj, user_id = user

        with app.app_context():
            broad_restaurant = Restaurant(name="Wingstop", user_id=user_id)
            exact_restaurant = Restaurant(name="Wingstop", location_name="Wylie", user_id=user_id)
            db.session.add(broad_restaurant)
            db.session.add(exact_restaurant)
            db.session.commit()

            csv_data = "Date,Payee,Category,Amount\n"
            csv_data += "7-Mar-26,Wingstop - Wylie,Dining & Drinks:Fast Food,-37.75\n"

            csv_file = Mock()
            csv_file.read.return_value = csv_data.encode("utf-8")
            csv_file.seek.return_value = None
            csv_file.filename = "simplifi-full-payee.csv"

            success, result = build_expense_import_review(csv_file, user_id)

            assert success is True
            row = result["review_rows"][0]
            assert row["restaurant_candidates"][0]["display_name"] == "Wingstop - Wylie"
            assert row["restaurant_candidates"][0]["match_basis"] == "exact display name"
            assert len(row["restaurant_candidates"]) == 2
            assert row["suggested_restaurant_id"] == exact_restaurant.id
            assert row["restaurant_requires_confirmation"] is False

    def test_build_expense_import_review_auto_matches_single_partial_name_match_without_address(
        self, app, user
    ) -> None:
        """Test that a single suggested partial-name match is auto-selected."""
        user_obj, user_id = user

        with app.app_context():
            restaurant = Restaurant(name="Woodbridge Golf Club", user_id=user_id)
            db.session.add(restaurant)
            db.session.commit()

            csv_data = "Date,Payee,Category,Amount\n"
            csv_data += "6-Mar-26,Woodbridge Golf Course,Dining & Drinks:Restaurants,-104.33\n"

            csv_file = Mock()
            csv_file.read.return_value = csv_data.encode("utf-8")
            csv_file.seek.return_value = None
            csv_file.filename = "woodbridge.csv"

            success, result = build_expense_import_review(csv_file, user_id)

            assert success is True
            row = result["review_rows"][0]
            assert row["restaurant_candidates"][0]["display_name"] == "Woodbridge Golf Club"
            assert row["restaurant_candidates"][0]["match_basis"] in {"partial name", "shared prefix"}
            assert row["suggested_restaurant_id"] == restaurant.id
            assert row["restaurant_requires_confirmation"] is False
            assert row["expense_default_action"] == "create"

    def test_build_expense_import_review_requires_confirmation_for_multiple_restaurant_matches(self, app, user) -> None:
        """Test that multiple exact display-name matches require explicit confirmation."""
        user_obj, user_id = user

        with app.app_context():
            db.session.add(Restaurant(name="Wingstop", location_name="Wylie", user_id=user_id))
            db.session.add(Restaurant(name="Wingstop", location_name="Wylie", user_id=user_id))
            db.session.commit()

            csv_data = "Date,Payee,Category,Amount\n"
            csv_data += "7-Mar-26,Wingstop - Wylie,Dining & Drinks:Fast Food,-37.75\n"

            csv_file = Mock()
            csv_file.read.return_value = csv_data.encode("utf-8")
            csv_file.seek.return_value = None
            csv_file.filename = "simplifi-multiple-exact.csv"

            success, result = build_expense_import_review(csv_file, user_id)

            assert success is True
            row = result["review_rows"][0]
            assert len(row["restaurant_candidates"]) == 2
            assert row["restaurant_requires_confirmation"] is True
            assert row["suggested_restaurant_id"] is None
            assert row["expense_default_action"] == "skip"

    def test_apply_expense_import_review_requires_matched_restaurant(self, app, user, restaurant, category) -> None:
        """Test applying reviewed import decisions with matched restaurants."""
        user_obj, user_id = user
        restaurant_obj, restaurant_id = restaurant
        category_obj, category_id = category

        with app.app_context():
            review_rows = [
                {
                    "row_number": 1,
                    "import_source_type": "standard",
                    "parsed_visit_date": "2026-03-06",
                    "amount": "31.05",
                    "category_name": "Test Category",
                    "notes": "Reviewed row",
                    "tags": "Morgan, Pam",
                    "restaurant_name": "Test Restaurant",
                    "error_messages": [],
                    "default_decision": "match",
                },
                {
                    "row_number": 2,
                    "import_source_type": "standard",
                    "parsed_visit_date": "2026-03-07",
                    "amount": "18.15",
                    "category_name": "Test Category",
                    "notes": "Matched row",
                    "tags": "",
                    "restaurant_name": "Test Restaurant",
                    "error_messages": [],
                    "default_decision": "match",
                },
            ]

            result = apply_expense_import_review(
                review_rows,
                {
                    "decision_1": "match",
                    "restaurant_id_1": str(restaurant_id),
                    "decision_2": "match",
                    "restaurant_id_2": str(restaurant_id),
                },
                user_id,
            )

            assert result["success"] is True
            assert result["imported_count"] == 2
            expenses = get_expenses_for_user(user_id)
            assert len(expenses) == 2
            assert all(expense.restaurant_id == restaurant_id for expense in expenses)

    def test_apply_expense_import_review_rejects_unmatched_restaurant(self, app, user) -> None:
        """Test import review cannot apply changes when restaurant is unresolved."""
        user_obj, user_id = user

        with app.app_context():
            review_rows = [
                {
                    "row_number": 1,
                    "import_source_type": "standard",
                    "parsed_visit_date": "2026-03-06",
                    "amount": "31.05",
                    "category_name": "Test Category",
                    "notes": "Reviewed row",
                    "tags": "",
                    "restaurant_name": "Unknown Place",
                    "error_messages": [],
                    "default_decision": "skip",
                }
            ]

            result = apply_expense_import_review(
                review_rows,
                {
                    "decision_1": "match",
                    "expense_action_1": "create",
                    "restaurant_action_1": "match",
                    "restaurant_id_1": "",
                },
                user_id,
            )

            assert result["success"] is False
            assert result["errors"] == ["Row 1: Select a restaurant match before applying expense changes."]

    def test_apply_expense_import_review_updates_existing_expense(self, app, user, restaurant) -> None:
        """Test updating an existing expense from an import review row."""
        user_obj, user_id = user
        restaurant_obj, restaurant_id = restaurant

        with app.app_context():
            old_category = Category(name="Old Category", user_id=user_id)
            new_category = Category(name="Fast Food", user_id=user_id)
            db.session.add_all([old_category, new_category])
            db.session.commit()

            existing_expense = Expense(
                amount=Decimal("25.00"),
                notes="Old note",
                date=datetime.fromisoformat("2026-03-03T16:30:00+00:00"),
                restaurant_id=restaurant_id,
                category_id=old_category.id,
                meal_type="dinner",
                order_type="dine-in",
                party_size=4,
                user_id=user_id,
            )
            db.session.add(existing_expense)
            db.session.commit()

            old_tag = Tag(name="OldTag", user_id=user_id)
            db.session.add(old_tag)
            db.session.commit()
            db.session.add(ExpenseTag(expense_id=existing_expense.id, tag_id=old_tag.id, added_by=user_id))
            db.session.commit()

            review_rows = [
                {
                    "row_number": 1,
                    "import_source_type": "standard",
                    "parsed_visit_date": "2026-03-06",
                    "parsed_visit_datetime_utc": "2026-03-06T00:00:00+00:00",
                    "has_explicit_time": False,
                    "amount": "25.00",
                    "category_name": "Fast Food",
                    "notes": "Updated from import",
                    "tags": "Pam, Morgan",
                    "meal_type": "lunch",
                    "order_type": "takeout",
                    "party_size": "2",
                    "restaurant_name": "Test Restaurant",
                    "duplicate_candidates": [{"id": existing_expense.id}],
                    "duplicate_candidates_by_restaurant": {str(restaurant_id): [{"id": existing_expense.id}]},
                    "error_messages": [],
                    "default_decision": "skip",
                }
            ]

            result = apply_expense_import_review(
                review_rows,
                {
                    "decision_1": "update",
                    "restaurant_id_1": str(restaurant_id),
                    "update_expense_id_1": str(existing_expense.id),
                },
                user_id,
            )

            assert result["success"] is True
            assert result["imported_count"] == 0
            assert result["updated_count"] == 1

            db.session.refresh(existing_expense)
            assert existing_expense.date.isoformat() == "2026-03-06T16:30:00"
            assert existing_expense.amount == Decimal("25.00")
            assert existing_expense.category_id == new_category.id
            assert existing_expense.notes == "Updated from import"
            assert existing_expense.meal_type == "lunch"
            assert existing_expense.order_type == "takeout"
            assert existing_expense.party_size == 2
            assert [tag.name for tag in existing_expense.tags] == ["Pam", "Morgan"]

    def test_apply_expense_import_review_updates_existing_expense_cleared_date_for_simplifi(
        self, app, user, restaurant
    ) -> None:
        """Test Simplifi review updates cleared date without overwriting visit date."""
        user_obj, user_id = user
        restaurant_obj, restaurant_id = restaurant

        with app.app_context():
            existing_expense = Expense(
                amount=Decimal("25.00"),
                notes="Old note",
                date=datetime.fromisoformat("2026-03-03T16:30:00+00:00"),
                restaurant_id=restaurant_id,
                user_id=user_id,
            )
            db.session.add(existing_expense)
            db.session.commit()

            review_rows = [
                {
                    "row_number": 1,
                    "import_source_type": "simplifi",
                    "parsed_cleared_date": "2026-03-06",
                    "amount": "25.00",
                    "notes": "Updated from import",
                    "tags": "",
                    "restaurant_name": "Test Restaurant",
                    "duplicate_candidates": [{"id": existing_expense.id}],
                    "duplicate_candidates_by_restaurant": {str(restaurant_id): [{"id": existing_expense.id}]},
                    "error_messages": [],
                    "default_decision": "skip",
                }
            ]

            result = apply_expense_import_review(
                review_rows,
                {
                    "decision_1": "update",
                    "restaurant_id_1": str(restaurant_id),
                    "update_expense_id_1": str(existing_expense.id),
                },
                user_id,
            )

            assert result["success"] is True
            db.session.refresh(existing_expense)
            assert existing_expense.date.isoformat() == "2026-03-03T16:30:00"
            assert existing_expense.cleared_date.isoformat() == "2026-03-06"

    def test_expense_services_error_handling(self, app, user) -> None:
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

    def test_expense_services_edge_cases(self, app, user) -> None:
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

    def test_expense_amount_validation(self, app, user, restaurant, category) -> None:
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

    def test_expense_date_handling(self, app, user, restaurant, category) -> None:
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

    def test_expense_restaurant_association(self, app, user, restaurant, category) -> None:
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
            assert expense.restaurant is not None
            assert expense.restaurant.name == "Test Restaurant"

    def test_expense_category_association(self, app, user, restaurant, category) -> None:
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
            assert expense.category is not None
            assert expense.category.name == "Test Category"

    def test_expense_user_isolation(self, app, user, restaurant, category) -> None:
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
