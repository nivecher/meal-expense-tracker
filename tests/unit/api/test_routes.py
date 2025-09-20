"""Tests for API routes module."""

from unittest.mock import Mock, patch

import pytest
from flask import Flask
from marshmallow import ValidationError

from app.api.routes import (
    _create_api_response,
    _get_current_user,
    _handle_service_error,
    _handle_validation_error,
    check_restaurant_exists,
    create_category,
    create_expense,
    create_restaurant,
    delete_category,
    delete_expense,
    get_categories,
    get_category,
    get_cuisines,
    get_expense,
    get_expenses,
    get_restaurant,
    get_restaurants,
    health_check,
    update_category,
    update_expense,
    validate_restaurant,
    version_info,
)


class TestAPIRoutes:
    """Test API routes functions."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.static_folder = "/tmp/static"
        return app

    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = Mock()
        user.id = 1
        user.username = "testuser"
        return user

    @pytest.fixture
    def mock_expense(self):
        """Create mock expense."""
        expense = Mock()
        expense.id = 1
        expense.amount = 25.50
        expense.description = "Test expense"
        return expense

    @pytest.fixture
    def mock_restaurant(self):
        """Create mock restaurant."""
        restaurant = Mock()
        restaurant.id = 1
        restaurant.name = "Test Restaurant"
        restaurant.city = "Test City"
        return restaurant

    @pytest.fixture
    def mock_category(self):
        """Create mock category."""
        category = Mock()
        category.id = 1
        category.name = "Test Category"
        category.color = "#FF5733"
        return category

    def test_get_current_user(self, app, mock_user):
        """Test getting current user."""
        with app.test_request_context():
            with patch("app.api.routes.current_user") as mock_current_user:
                mock_current_user._get_current_object.return_value = mock_user
                result = _get_current_user()
                assert result == mock_user

    def test_create_api_response_with_data(self, app):
        """Test creating API response with data."""
        with app.app_context():
            response, status = _create_api_response(
                data={"test": "data"}, message="Test message", status="success", code=200
            )
            assert status == 200
            assert response.json["status"] == "success"
            assert response.json["message"] == "Test message"
            assert response.json["data"]["test"] == "data"

    def test_create_api_response_without_data(self, app):
        """Test creating API response without data."""
        with app.app_context():
            response, status = _create_api_response(message="Test message", status="error", code=400)
            assert status == 400
            assert response.json["status"] == "error"
            assert response.json["message"] == "Test message"
            assert "data" not in response.json

    def test_handle_validation_error(self, app):
        """Test handling validation error."""
        error = ValidationError({"field": ["Error message"]})
        response, status = _handle_validation_error(error)
        assert status == 400
        assert response.json["status"] == "error"
        assert response.json["message"] == "Validation failed"
        assert "errors" in response.json

    def test_handle_service_error(self, app):
        """Test handling service error."""
        error = Exception("Service error")
        with app.app_context():
            with patch("app.api.routes.current_app") as mock_app:
                response, status = _handle_service_error(error, "test operation")
                assert status == 500
                assert response.json["status"] == "error"
                assert "Failed to test operation" in response.json["message"]
                mock_app.logger.error.assert_called_once()

    def test_health_check(self, app):
        """Test health check endpoint."""
        with app.test_request_context():
            response = health_check()
            assert response.json["status"] == "healthy"

    def test_version_info(self, app):
        """Test version info endpoint."""
        with app.test_request_context():
            with patch("app.api.routes.__version__", "1.0.0"):
                response, status = version_info()
                assert status == 200
                assert response.json["status"] == "success"
                assert response.json["data"]["version"] == "1.0.0"

    def test_get_cuisines_success(self, app):
        """Test getting cuisines successfully."""
        with app.test_request_context():
            with patch("app.api.routes.current_app") as mock_app:
                mock_app.static_folder = "/tmp/static"
                with patch("app.api.routes.os.path.join") as mock_join:
                    with patch("app.api.routes.open") as mock_open:
                        with patch("app.api.routes.json.load") as mock_load:
                            mock_join.return_value = "/tmp/static/data/cuisines.json"
                            mock_load.return_value = {"cuisines": ["American", "Chinese"]}
                            mock_open.return_value.__enter__.return_value = Mock()

                            response, status = get_cuisines()
                            assert status == 200
                            assert response.json["status"] == "success"
                            assert "cuisines" in response.json["data"]

    def test_get_cuisines_error(self, app):
        """Test getting cuisines with error."""
        with app.test_request_context():
            with patch("app.api.routes.current_app") as mock_app:
                mock_app.static_folder = "/tmp/static"
                with patch("app.api.routes.os.path.join", side_effect=Exception("File not found")):
                    with patch("app.api.routes.current_app") as mock_app:
                        response, status = get_cuisines()
                        assert status == 500
                        assert response.json["status"] == "error"

    def test_get_expenses_success(self, app, mock_user, mock_expense):
        """Test getting expenses successfully."""
        with app.test_request_context():
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.expense_services") as mock_services:
                    with patch("app.api.routes.expenses_schema") as mock_schema:
                        mock_services.get_expenses_for_user.return_value = [mock_expense]
                        mock_schema.dump.return_value = [{"id": 1, "amount": 25.50}]

                        response, status = get_expenses()
                        assert status == 200
                        assert response.json["status"] == "success"
                        mock_services.get_expenses_for_user.assert_called_once_with(1)

    def test_get_expenses_error(self, app, mock_user):
        """Test getting expenses with error."""
        with app.test_request_context():
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.expense_services") as mock_services:
                    mock_services.get_expenses_for_user.side_effect = Exception("Database error")

                    response, status = get_expenses()
                    assert status == 500
                    assert response.json["status"] == "error"

    def test_create_expense_success(self, app, mock_user, mock_expense):
        """Test creating expense successfully."""
        with app.test_request_context(
            "/expenses",
            method="POST",
            json={"amount": 25.50, "description": "Test expense"},
            headers={"X-CSRFToken": "test-token"},
        ):
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.expense_services") as mock_services:
                    with patch("app.api.routes.expense_schema") as mock_schema:
                        mock_schema.load.return_value = {"amount": 25.50, "description": "Test expense"}
                        mock_services.create_expense_for_user.return_value = mock_expense
                        mock_schema.dump.return_value = {"id": 1, "amount": 25.50}

                        response, status = create_expense()
                        assert status == 201
                        assert response.json["status"] == "success"
                        mock_services.create_expense_for_user.assert_called_once()

    def test_create_expense_validation_error(self, app, mock_user):
        """Test creating expense with validation error."""
        with app.test_request_context(
            "/expenses",
            method="POST",
            json={"amount": "invalid"},
            headers={"X-CSRFToken": "test-token"},
        ):
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.expense_schema") as mock_schema:
                    mock_schema.load.side_effect = ValidationError({"amount": ["Invalid amount"]})

                    response, status = create_expense()
                    assert status == 400
                    assert response.json["status"] == "error"

    def test_get_expense_success(self, app, mock_user, mock_expense):
        """Test getting single expense successfully."""
        with app.test_request_context():
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.expense_services") as mock_services:
                    with patch("app.api.routes.expense_schema") as mock_schema:
                        mock_services.get_expense_by_id_for_user.return_value = mock_expense
                        mock_schema.dump.return_value = {"id": 1, "amount": 25.50}

                        response, status = get_expense(1)
                        assert status == 200
                        assert response.json["status"] == "success"

    def test_get_expense_not_found(self, app, mock_user):
        """Test getting expense that doesn't exist."""
        with app.test_request_context():
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.expense_services") as mock_services:
                    mock_services.get_expense_by_id_for_user.return_value = None

                    response, status = get_expense(999)
                    assert status == 404
                    assert response.json["status"] == "error"

    def test_update_expense_success(self, app, mock_user, mock_expense):
        """Test updating expense successfully."""
        with app.test_request_context(
            "/expenses/1",
            method="PUT",
            json={"amount": 30.00, "description": "Updated expense"},
            headers={"X-CSRFToken": "test-token"},
        ):
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.expense_services") as mock_services:
                    with patch("app.api.routes.expense_schema") as mock_schema:
                        mock_services.get_expense_by_id_for_user.return_value = mock_expense
                        mock_schema.load.return_value = {"amount": 30.00, "description": "Updated expense"}
                        mock_services.update_expense_for_user.return_value = mock_expense
                        mock_schema.dump.return_value = {"id": 1, "amount": 30.00}

                        response, status = update_expense(1)
                        assert status == 200
                        assert response.json["status"] == "success"

    def test_update_expense_not_found(self, app, mock_user):
        """Test updating expense that doesn't exist."""
        with app.test_request_context(
            "/expenses/999",
            method="PUT",
            json={"amount": 30.00},
            headers={"X-CSRFToken": "test-token"},
        ):
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.expense_services") as mock_services:
                    mock_services.get_expense_by_id_for_user.return_value = None

                    response, status = update_expense(999)
                    assert status == 404
                    assert response.json["status"] == "error"

    def test_delete_expense_success(self, app, mock_user, mock_expense):
        """Test deleting expense successfully."""
        with app.test_request_context(
            "/expenses/1",
            method="DELETE",
            headers={"X-CSRFToken": "test-token"},
        ):
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.expense_services") as mock_services:
                    mock_services.get_expense_by_id_for_user.return_value = mock_expense

                    response, status = delete_expense(1)
                    assert status == 204
                    assert response.json["status"] == "success"
                    mock_services.delete_expense_for_user.assert_called_once_with(mock_expense)

    def test_delete_expense_not_found(self, app, mock_user):
        """Test deleting expense that doesn't exist."""
        with app.test_request_context(
            "/expenses/999",
            method="DELETE",
            headers={"X-CSRFToken": "test-token"},
        ):
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.expense_services") as mock_services:
                    mock_services.get_expense_by_id_for_user.return_value = None

                    response, status = delete_expense(999)
                    assert status == 404
                    assert response.json["status"] == "error"

    def test_get_restaurants_success(self, app, mock_user, mock_restaurant):
        """Test getting restaurants successfully."""
        with app.test_request_context():
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.restaurant_services") as mock_services:
                    with patch("app.api.routes.restaurants_schema") as mock_schema:
                        mock_services.get_restaurants_for_user.return_value = [mock_restaurant]
                        mock_schema.dump.return_value = [{"id": 1, "name": "Test Restaurant"}]

                        response, status = get_restaurants()
                        assert status == 200
                        assert response.json["status"] == "success"
                        mock_services.get_restaurants_for_user.assert_called_once_with(1)

    def test_create_restaurant_success(self, app, mock_user, mock_restaurant):
        """Test creating restaurant successfully."""
        with app.test_request_context(
            "/restaurants",
            method="POST",
            json={"name": "Test Restaurant", "city": "Test City"},
            headers={"X-CSRFToken": "test-token"},
        ):
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.restaurant_services") as mock_services:
                    with patch("app.api.routes.restaurant_schema") as mock_schema:
                        mock_schema.load.return_value = {"name": "Test Restaurant", "city": "Test City"}
                        mock_services.create_restaurant_for_user.return_value = mock_restaurant
                        mock_schema.dump.return_value = {"id": 1, "name": "Test Restaurant"}

                        response, status = create_restaurant()
                        assert status == 201
                        assert response.json["status"] == "success"
                        mock_services.create_restaurant_for_user.assert_called_once()

    def test_get_restaurant_success(self, app, mock_user, mock_restaurant):
        """Test getting single restaurant successfully."""
        with app.test_request_context():
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.restaurant_services") as mock_services:
                    with patch("app.api.routes.restaurant_schema") as mock_schema:
                        mock_services.get_restaurant_for_user.return_value = mock_restaurant
                        mock_schema.dump.return_value = {"id": 1, "name": "Test Restaurant"}

                        response, status = get_restaurant(1)
                        assert status == 200
                        assert response.json["status"] == "success"

    def test_get_restaurant_not_found(self, app, mock_user):
        """Test getting restaurant that doesn't exist."""
        with app.test_request_context():
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.restaurant_services") as mock_services:
                    mock_services.get_restaurant_for_user.return_value = None

                    response, status = get_restaurant(999)
                    assert status == 404
                    assert response.json["status"] == "error"

    def test_check_restaurant_exists_with_place_id(self, app, mock_user, mock_restaurant):
        """Test checking restaurant exists with place ID."""
        with app.test_request_context("/restaurants/check?place_id=test_place_id"):
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.Restaurant") as mock_restaurant_model:
                    mock_query = Mock()
                    mock_query.filter_by.return_value.first.return_value = mock_restaurant
                    mock_restaurant_model.query = mock_query

                    response, status = check_restaurant_exists()
                    assert status == 200
                    assert response.json["status"] == "success"
                    assert response.json["data"]["exists"] is True
                    assert response.json["data"]["restaurant_id"] == 1

    def test_check_restaurant_exists_missing_place_id(self, app, mock_user):
        """Test checking restaurant exists without place ID."""
        with app.test_request_context("/restaurants/check"):
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                response, status = check_restaurant_exists()
                assert status == 400
                assert response.json["status"] == "error"

    def test_validate_restaurant_success(self, app, mock_user):
        """Test validating restaurant successfully."""
        with app.test_request_context(
            "/restaurants/validate",
            method="POST",
            json={"name": "Test Restaurant", "address": "123 Test St"},
            headers={"X-CSRFToken": "test-token"},
        ):
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                response, status = validate_restaurant()
                assert status == 200
                assert response.json["status"] == "success"
                assert response.json["data"]["valid"] is True

    def test_validate_restaurant_missing_name(self, app, mock_user):
        """Test validating restaurant with missing name."""
        with app.test_request_context(
            "/restaurants/validate",
            method="POST",
            json={"address": "123 Test St"},
            headers={"X-CSRFToken": "test-token"},
        ):
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                response, status = validate_restaurant()
                assert status == 400
                assert response.json["status"] == "error"

    def test_validate_restaurant_missing_address(self, app, mock_user):
        """Test validating restaurant with missing address."""
        with app.test_request_context(
            "/restaurants/validate",
            method="POST",
            json={"name": "Test Restaurant"},
            headers={"X-CSRFToken": "test-token"},
        ):
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                response, status = validate_restaurant()
                assert status == 400
                assert response.json["status"] == "error"

    def test_validate_restaurant_no_data(self, app, mock_user):
        """Test validating restaurant with no data."""
        with app.test_request_context(
            "/restaurants/validate",
            method="POST",
            json=None,
            headers={"X-CSRFToken": "test-token"},
        ):
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                response, status = validate_restaurant()
                assert status == 400
                assert response.json["status"] == "error"

    def test_get_categories_success(self, app, mock_user, mock_category):
        """Test getting categories successfully."""
        with app.test_request_context():
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.category_services") as mock_services:
                    with patch("app.api.routes.categories_schema") as mock_schema:
                        mock_services.get_categories_for_user.return_value = [mock_category]
                        mock_schema.dump.return_value = [{"id": 1, "name": "Test Category"}]

                        response, status = get_categories()
                        assert status == 200
                        assert response.json["status"] == "success"
                        mock_services.get_categories_for_user.assert_called_once_with(1)

    def test_create_category_success(self, app, mock_user, mock_category):
        """Test creating category successfully."""
        with app.test_request_context(
            "/categories",
            method="POST",
            json={"name": "Test Category", "color": "#FF5733"},
            headers={"X-CSRFToken": "test-token"},
        ):
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.category_services") as mock_services:
                    with patch("app.api.routes.category_schema") as mock_schema:
                        mock_schema.load.return_value = {"name": "Test Category", "color": "#FF5733"}
                        mock_services.create_category_for_user.return_value = mock_category
                        mock_schema.dump.return_value = {"id": 1, "name": "Test Category"}

                        response, status = create_category()
                        assert status == 201
                        assert response.json["status"] == "success"
                        mock_services.create_category_for_user.assert_called_once()

    def test_get_category_success(self, app, mock_user, mock_category):
        """Test getting single category successfully."""
        with app.test_request_context():
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.category_services") as mock_services:
                    with patch("app.api.routes.category_schema") as mock_schema:
                        mock_services.get_category_by_id_for_user.return_value = mock_category
                        mock_schema.dump.return_value = {"id": 1, "name": "Test Category"}

                        response, status = get_category(1)
                        assert status == 200
                        assert response.json["status"] == "success"

    def test_get_category_not_found(self, app, mock_user):
        """Test getting category that doesn't exist."""
        with app.test_request_context():
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.category_services") as mock_services:
                    mock_services.get_category_by_id_for_user.return_value = None

                    response, status = get_category(999)
                    assert status == 404
                    assert response.json["status"] == "error"

    def test_update_category_success(self, app, mock_user, mock_category):
        """Test updating category successfully."""
        with app.test_request_context(
            "/categories/1",
            method="PUT",
            json={"name": "Updated Category", "color": "#00FF00"},
            headers={"X-CSRFToken": "test-token"},
        ):
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.category_services") as mock_services:
                    with patch("app.api.routes.category_schema") as mock_schema:
                        mock_services.get_category_by_id_for_user.return_value = mock_category
                        mock_schema.load.return_value = {"name": "Updated Category", "color": "#00FF00"}
                        mock_services.update_category_for_user.return_value = mock_category
                        mock_schema.dump.return_value = {"id": 1, "name": "Updated Category"}

                        response, status = update_category(1)
                        assert status == 200
                        assert response.json["status"] == "success"

    def test_delete_category_success(self, app, mock_user, mock_category):
        """Test deleting category successfully."""
        with app.test_request_context(
            "/categories/1",
            method="DELETE",
            headers={"X-CSRFToken": "test-token"},
        ):
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.category_services") as mock_services:
                    mock_services.get_category_by_id_for_user.return_value = mock_category

                    response, status = delete_category(1)
                    assert status == 204
                    assert response.json["status"] == "success"
                    mock_services.delete_category_for_user.assert_called_once_with(mock_category)

    def test_delete_category_not_found(self, app, mock_user):
        """Test deleting category that doesn't exist."""
        with app.test_request_context(
            "/categories/999",
            method="DELETE",
            headers={"X-CSRFToken": "test-token"},
        ):
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.category_services") as mock_services:
                    mock_services.get_category_by_id_for_user.return_value = None

                    response, status = delete_category(999)
                    assert status == 404
                    assert response.json["status"] == "error"

    def test_create_api_response_defaults(self, app):
        """Test creating API response with default values."""
        with app.app_context():
            response, status = _create_api_response()
            assert status == 200
            assert response.json["status"] == "success"
            assert response.json["message"] == "Success"

    def test_handle_service_error_with_logging(self, app):
        """Test handling service error with proper logging."""
        error = Exception("Test error")
        with app.app_context():
            with patch("app.api.routes.current_app") as mock_app:
                response, status = _handle_service_error(error, "test operation")
                assert status == 500
                mock_app.logger.error.assert_called_once()
                assert "Error in test operation" in mock_app.logger.error.call_args[0][0]

    def test_validate_restaurant_exception(self, app, mock_user):
        """Test validating restaurant with exception."""
        with app.test_request_context(
            "/restaurants/validate",
            method="POST",
            json={"name": "Test Restaurant", "address": "123 Test St"},
            headers={"X-CSRFToken": "test-token"},
        ):
            with patch("app.api.routes._get_current_user", return_value=mock_user):
                with patch("app.api.routes.request.get_json", side_effect=Exception("JSON error")):
                    with patch("app.api.routes.current_app") as mock_app:
                        response, status = validate_restaurant()
                        assert status == 500
                        assert response.json["status"] == "error"
                        mock_app.logger.error.assert_called_once()
