"""
Unit tests for consolidated expense filtering functionality.

This module tests the expense filtering logic that was consolidated from
app/main/services/__init__.py into app/expenses/services.py to eliminate
code duplication.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest

from app.expenses.services import (
    apply_filters,
    apply_sorting,
    get_expense_filters,
    get_main_filter_options,
    get_user_expenses,
)


class TestGetExpenseFilters:
    """Test the get_expense_filters function that extracts filter parameters from requests."""

    def test_get_expense_filters_with_search_param(self) -> None:
        """Test filter extraction with 'search' parameter."""
        mock_request = Mock()
        mock_request.args.get.side_effect = lambda key, default="": {
            "search": "coffee",
            "q": "",
            "meal_type": "breakfast",
            "category": "dining",
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
            "sort": "amount",
            "order": "asc",
        }.get(key, default)

        filters = get_expense_filters(mock_request)

        assert filters["search"] == "coffee"
        assert filters["meal_type"] == "breakfast"
        assert filters["category"] == "dining"
        assert filters["start_date"] == "2025-01-01"
        assert filters["end_date"] == "2025-01-31"
        assert filters["sort_by"] == "amount"
        assert filters["sort_order"] == "asc"

    def test_get_expense_filters_with_q_param(self) -> None:
        """Test filter extraction with 'q' parameter (legacy support)."""
        mock_request = Mock()
        mock_request.args.get.side_effect = lambda key, default="": {
            "search": "",
            "q": "pizza",
            "meal_type": "",
            "category": "",
            "start_date": "",
            "end_date": "",
            "sort": "date",
            "order": "desc",
        }.get(key, default)

        filters = get_expense_filters(mock_request)

        assert filters["search"] == "pizza"
        assert filters["sort_by"] == "date"
        assert filters["sort_order"] == "desc"

    def test_get_expense_filters_with_defaults(self) -> None:
        """Test filter extraction with default values."""
        mock_request = Mock()
        mock_request.args.get.side_effect = lambda key, default="": default

        filters = get_expense_filters(mock_request)

        assert filters["search"] == ""
        assert filters["meal_type"] == ""
        assert filters["category"] == ""
        assert filters["start_date"] == ""
        assert filters["end_date"] == ""
        assert filters["sort_by"] == "date"
        assert filters["sort_order"] == "desc"

    def test_get_expense_filters_prioritizes_search_over_q(self) -> None:
        """Test that 'search' parameter takes priority over 'q' parameter."""
        mock_request = Mock()
        mock_request.args.get.side_effect = lambda key, default="": {
            "search": "primary",
            "q": "secondary",
        }.get(key, default)

        filters = get_expense_filters(mock_request)

        assert filters["search"] == "primary"


class TestGetUserExpenses:
    """Test the get_user_expenses function that retrieves filtered expenses."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session for testing."""
        return Mock()

    @pytest.fixture
    def sample_expenses(self):
        """Create sample expense objects for testing."""
        expenses = []
        for i in range(3):
            expense = Mock()
            expense.id = i + 1
            expense.amount = Decimal(f"{10 + i}.00")
            expense.date = date(2025, 1, i + 1)
            expense.meal_type = "lunch" if i % 2 == 0 else "dinner"
            expense.notes = f"Test expense {i + 1}"
            expense.user_id = 1
            expenses.append(expense)
        return expenses

    def test_get_user_expenses_basic_functionality(self, mock_db_session, sample_expenses) -> None:
        """Test basic expense retrieval with filters."""
        # This test would require more complex mocking of SQLAlchemy
        # For now, we'll test the function structure

        # Note: Full testing would require database setup or extensive mocking
        # This serves as a structure test
        assert callable(get_user_expenses)
        # Test that the function has a return annotation (format may vary by Python version)
        assert "return" in get_user_expenses.__annotations__


class TestGetMainFilterOptions:
    """Test the get_main_filter_options function."""

    def test_get_main_filter_options_structure(self) -> None:
        """Test that the function has correct structure and return type."""
        assert callable(get_main_filter_options)
        # Note: Full testing would require database setup
        # This ensures the function exists and is callable


class TestApplyFilters:
    """Test the apply_filters function that modifies SQLAlchemy statements."""

    def test_apply_filters_with_search(self) -> None:
        """Test applying search filters to a statement."""
        # Create a mock statement
        mock_stmt = Mock()
        mock_stmt.join.return_value = mock_stmt
        mock_stmt.where.return_value = mock_stmt

        filters = {
            "search": "coffee",
            "meal_type": "",
            "category": "",
            "start_date": "",
            "end_date": "",
        }

        filtered_stmt = apply_filters(mock_stmt, filters)

        # Verify that joins were called for restaurant and category
        assert mock_stmt.join.call_count == 2
        # Verify that where was called for search
        assert mock_stmt.where.call_count >= 1
        # Verify the function returns a statement
        assert filtered_stmt is not None

    def test_apply_filters_with_meal_type(self) -> None:
        """Test applying meal type filters."""
        mock_stmt = Mock()
        mock_stmt.join.return_value = mock_stmt
        mock_stmt.where.return_value = mock_stmt

        filters = {
            "search": "",
            "meal_type": "lunch",
            "category": "",
            "start_date": "",
            "end_date": "",
        }

        apply_filters(mock_stmt, filters)

        # Verify joins were called
        assert mock_stmt.join.call_count == 2
        # Verify where was called for meal_type
        assert mock_stmt.where.call_count >= 1

    def test_apply_filters_with_date_range(self) -> None:
        """Test applying date range filters."""
        mock_stmt = Mock()
        mock_stmt.join.return_value = mock_stmt
        mock_stmt.where.return_value = mock_stmt

        filters = {
            "search": "",
            "meal_type": "",
            "category": "",
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
        }

        apply_filters(mock_stmt, filters)

        # Verify joins were called
        assert mock_stmt.join.call_count == 2
        # Verify where was called for date filters
        assert mock_stmt.where.call_count >= 2

    def test_apply_filters_with_invalid_dates(self) -> None:
        """Test that invalid dates don't break the filtering."""
        mock_stmt = Mock()
        mock_stmt.join.return_value = mock_stmt
        mock_stmt.where.return_value = mock_stmt

        filters = {
            "search": "",
            "meal_type": "",
            "category": "",
            "start_date": "invalid-date",
            "end_date": "also-invalid",
        }

        # This should not raise an exception
        apply_filters(mock_stmt, filters)

        # Verify joins were still called
        assert mock_stmt.join.call_count == 2


class TestApplySorting:
    """Test the apply_sorting function."""

    def test_apply_sorting_by_date_desc(self) -> None:
        """Test sorting by date in descending order."""
        mock_stmt = Mock()
        mock_field = Mock()
        mock_field.desc.return_value = "date_desc"
        mock_stmt.order_by.return_value = mock_stmt

        # Mock Expense.date
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr("app.expenses.services.Expense.date", mock_field)

            apply_sorting(mock_stmt, "date", "desc")

            # Verify desc() was called on the field
            mock_field.desc.assert_called_once()
            # Verify order_by was called
            mock_stmt.order_by.assert_called_once()

    def test_apply_sorting_by_amount_asc(self) -> None:
        """Test sorting by amount in ascending order."""
        mock_stmt = Mock()
        mock_field = Mock()
        mock_field.asc.return_value = "amount_asc"
        mock_stmt.order_by.return_value = mock_stmt

        with pytest.MonkeyPatch().context() as mp:
            mp.setattr("app.expenses.services.Expense.amount", mock_field)

            apply_sorting(mock_stmt, "amount", "asc")

            # Verify asc() was called on the field
            mock_field.asc.assert_called_once()
            # Verify order_by was called
            mock_stmt.order_by.assert_called_once()

    def test_apply_sorting_by_restaurant(self) -> None:
        """Test sorting by restaurant name."""
        mock_stmt = Mock()
        mock_stmt.order_by.return_value = mock_stmt

        apply_sorting(mock_stmt, "restaurant", "desc")

        # Verify order_by was called
        mock_stmt.order_by.assert_called_once()

    def test_apply_sorting_unknown_field(self) -> None:
        """Test sorting by unknown field returns unchanged statement."""
        mock_stmt = Mock()

        result = apply_sorting(mock_stmt, "unknown_field", "desc")

        # Should return the original statement unchanged
        assert result == mock_stmt


class TestConsolidationIntegrity:
    """Test that the consolidation maintains all original functionality."""

    def test_all_functions_exist(self) -> None:
        """Test that all expected functions exist in the consolidated module."""
        from app.expenses import services

        # Functions that were moved from main.services
        assert hasattr(services, "get_expense_filters")
        assert hasattr(services, "get_user_expenses")
        assert hasattr(services, "get_main_filter_options")  # Renamed from get_filter_options
        assert hasattr(services, "apply_filters")
        assert hasattr(services, "apply_sorting")

        # Original expense services functions should still exist
        assert hasattr(services, "get_filter_options")  # The enhanced version
        assert hasattr(services, "create_expense")
        assert hasattr(services, "update_expense")
        assert hasattr(services, "delete_expense")

    def test_function_signatures_match_expected(self) -> None:
        """Test that function signatures match expectations."""
        import inspect

        from app.expenses import services

        # Test get_expense_filters signature
        sig = inspect.signature(services.get_expense_filters)
        assert len(sig.parameters) == 1
        assert "request" in sig.parameters

        # Test get_user_expenses signature
        sig = inspect.signature(services.get_user_expenses)
        assert len(sig.parameters) == 2
        assert "user_id" in sig.parameters
        assert "filters" in sig.parameters

        # Test get_main_filter_options signature
        sig = inspect.signature(services.get_main_filter_options)
        assert len(sig.parameters) == 1
        assert "user_id" in sig.parameters
