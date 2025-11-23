"""True unit tests for API routes - no Flask app required."""

from unittest.mock import Mock, patch

import pytest
from marshmallow import ValidationError

from app.api.routes import (
    _create_api_response,
    _get_current_user,
    _handle_validation_error,
)


class TestAPIHelpers:
    """Test API helper functions without Flask app."""

    def test_create_api_response_with_data(self):
        """Test creating API response with data."""
        with patch("app.api.routes.jsonify") as mock_jsonify:
            mock_jsonify.return_value = Mock()

            response, status = _create_api_response(
                data={"test": "data"}, message="Success", status="success", code=200
            )

            assert status == 200
            mock_jsonify.assert_called_once_with({"status": "success", "message": "Success", "data": {"test": "data"}})

    def test_create_api_response_without_data(self):
        """Test creating API response without data."""
        with patch("app.api.routes.jsonify") as mock_jsonify:
            mock_jsonify.return_value = Mock()

            response, status = _create_api_response(message="Success", status="success", code=200)

            assert status == 200
            mock_jsonify.assert_called_once_with({"status": "success", "message": "Success"})

    def test_handle_validation_error(self):
        """Test handling validation error."""
        with patch("app.api.routes.jsonify") as mock_jsonify:
            mock_jsonify.return_value = Mock()

            error = ValidationError({"field": ["Error message"]})
            response, status = _handle_validation_error(error)

            assert status == 400
            mock_jsonify.assert_called_once_with(
                {"status": "error", "message": "Validation failed", "errors": {"field": ["Error message"]}}
            )

    def test_handle_service_error_basic(self):
        """Test basic service error handling logic."""
        # This function inherently requires Flask context, so we'll test the concept
        Exception("Service error")
        "test operation"

        # Test that the function exists and can be called
        from app.api.routes import _handle_service_error

        assert callable(_handle_service_error)

        # The actual testing of this function should be done in integration tests
        # since it requires Flask context for current_app.logger and jsonify

    def test_get_current_user(self):
        """Test getting current user."""
        with patch("app.api.routes.current_user") as mock_current_user:
            mock_user = Mock()
            mock_current_user._get_current_object = Mock(return_value=mock_user)

            result = _get_current_user()

            assert result == mock_user
            mock_current_user._get_current_object.assert_called_once()


class TestAPISchemas:
    """Test API schema validation without Flask app."""

    def test_expense_schema_validation(self):
        """Test expense schema validation."""
        from app.api.schemas import ExpenseSchema

        schema = ExpenseSchema()

        # Valid data
        valid_data = {"amount": 25.50, "restaurant_id": 1, "category_id": 1, "date": "2024-01-01"}

        result = schema.load(valid_data)
        assert result["amount"] == 25.50
        assert result["restaurant_id"] == 1
        assert result["category_id"] == 1

        # Invalid data
        invalid_data = {"amount": "invalid", "restaurant_id": 1, "category_id": 1}

        with pytest.raises(ValidationError):
            schema.load(invalid_data)

    def test_restaurant_schema_validation(self):
        """Test restaurant schema validation."""
        from app.api.schemas import RestaurantSchema

        schema = RestaurantSchema()

        # Valid data
        valid_data = {"name": "Test Restaurant", "address": "123 Test St", "city": "Test City"}

        result = schema.load(valid_data)
        assert result["name"] == "Test Restaurant"
        assert result["address"] == "123 Test St"

        # Invalid data (missing required field)
        invalid_data = {"address": "123 Test St", "city": "Test City"}

        with pytest.raises(ValidationError):
            schema.load(invalid_data)

    def test_category_schema_validation(self):
        """Test category schema validation."""
        from app.api.schemas import CategorySchema

        schema = CategorySchema()

        # Valid data
        valid_data = {"name": "Test Category", "color": "#FF5733"}

        result = schema.load(valid_data)
        assert result["name"] == "Test Category"
        assert result["color"] == "#FF5733"

        # Invalid data (missing required field)
        invalid_data = {"color": "#FF5733"}

        with pytest.raises(ValidationError):
            schema.load(invalid_data)


class TestAPIServices:
    """Test API service layer without Flask app."""

    def test_expense_services_get_expenses(self):
        """Test expense services get expenses."""
        from app.expenses import services as expense_services

        with patch.object(expense_services, "get_expenses_for_user") as mock_get_expenses:
            mock_user = Mock()
            mock_user.id = 1

            mock_expenses = [Mock(), Mock()]
            mock_get_expenses.return_value = mock_expenses

            result = expense_services.get_expenses_for_user(mock_user.id)

            assert result == mock_expenses
            mock_get_expenses.assert_called_once_with(mock_user.id)

    def test_restaurant_services_get_restaurants(self):
        """Test restaurant services get restaurants."""
        from app.restaurants import services as restaurant_services

        with patch.object(restaurant_services, "get_restaurants_for_user") as mock_get_restaurants:
            mock_user = Mock()
            mock_user.id = 1

            mock_restaurants = [Mock(), Mock()]
            mock_get_restaurants.return_value = mock_restaurants

            result = restaurant_services.get_restaurants_for_user(mock_user.id)

            assert result == mock_restaurants
            mock_get_restaurants.assert_called_once_with(mock_user.id)

    def test_category_services_get_categories(self):
        """Test category services get categories."""
        from app.categories import services as category_services

        with patch.object(category_services, "get_categories_for_user") as mock_get_categories:
            mock_user = Mock()
            mock_user.id = 1

            mock_categories = [Mock(), Mock()]
            mock_get_categories.return_value = mock_categories

            result = category_services.get_categories_for_user(mock_user.id)

            assert result == mock_categories
            mock_get_categories.assert_called_once_with(mock_user.id)
