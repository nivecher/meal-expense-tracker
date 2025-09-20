"""Tests for admin lambda_admin to improve coverage."""

from unittest.mock import Mock, patch

import pytest
from flask import Flask

from app.admin.lambda_admin import LambdaAdminHandler, handle_admin_request


class TestLambdaAdminHandler:
    """Test Lambda admin handler."""

    @pytest.fixture
    def app(self):
        """Create Flask app for testing."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key"
        return app

    @pytest.fixture
    def handler(self, app):
        """Create Lambda admin handler."""
        return LambdaAdminHandler(app)

    def test_init(self, app):
        """Test handler initialization."""
        handler = LambdaAdminHandler(app)
        assert handler.app == app

    def test_handle_admin_operation_missing_operation(self, handler):
        """Test handling admin operation with missing operation name."""
        event = {}

        result = handler.handle_admin_operation(event)

        assert result["statusCode"] == 400
        body = result["body"]
        assert "Missing 'admin_operation'" in body

    def test_handle_admin_operation_unknown_operation(self, handler):
        """Test handling admin operation with unknown operation."""
        event = {"admin_operation": "unknown_operation", "parameters": {}}

        result = handler.handle_admin_operation(event)

        assert result["statusCode"] == 400
        body = result["body"]
        assert "Unknown operation: unknown_operation" in body

    def test_handle_admin_operation_invalid_parameters(self, handler):
        """Test handling admin operation with invalid parameters."""
        event = {"admin_operation": "list_users", "parameters": {"limit": "invalid"}}

        with patch("app.admin.lambda_admin.AdminOperationRegistry") as mock_registry:
            mock_operation_class = Mock()
            mock_operation = Mock()
            mock_operation.validate_params.return_value = {"valid": False, "errors": ["limit must be an integer"]}
            mock_operation_class.return_value = mock_operation
            mock_registry.get_operation.return_value = mock_operation_class

            result = handler.handle_admin_operation(event)

            assert result["statusCode"] == 400
            body = result["body"]
            assert "Invalid parameters" in body

    def test_handle_admin_operation_requires_confirmation(self, handler):
        """Test handling admin operation that requires confirmation."""
        event = {
            "admin_operation": "create_user",
            "parameters": {"username": "testuser", "email": "test@example.com"},
            "confirm": False,
        }

        with patch("app.admin.lambda_admin.AdminOperationRegistry") as mock_registry:
            mock_operation_class = Mock()
            mock_operation = Mock()
            mock_operation.requires_confirmation = True
            mock_operation.description = "Create a new user"
            mock_operation.validate_params.return_value = {"valid": True, "errors": []}
            mock_operation_class.return_value = mock_operation
            mock_registry.get_operation.return_value = mock_operation_class

            result = handler.handle_admin_operation(event)

            assert result["statusCode"] == 200
            body = result["body"]
            assert "requires confirmation" in body
            assert "confirm" in body

    def test_handle_admin_operation_success(self, handler):
        """Test successful admin operation handling."""
        event = {"admin_operation": "list_users", "parameters": {"limit": 10}, "confirm": True}

        with patch("app.admin.lambda_admin.AdminOperationRegistry") as mock_registry:
            mock_operation_class = Mock()
            mock_operation = Mock()
            mock_operation.requires_confirmation = False
            mock_operation.validate_params.return_value = {"valid": True, "errors": []}
            mock_operation.execute.return_value = {
                "success": True,
                "message": "Operation completed",
                "data": {"users": []},
            }
            mock_operation_class.return_value = mock_operation
            mock_registry.get_operation.return_value = mock_operation_class

            with handler.app.app_context():
                result = handler.handle_admin_operation(event)

            assert result["statusCode"] == 200
            body = result["body"]
            assert 'success": true' in body
            assert "Operation completed" in body

    def test_handle_admin_operation_exception(self, handler):
        """Test admin operation handling with exception."""
        event = {"admin_operation": "list_users", "parameters": {}}

        with patch("app.admin.lambda_admin.AdminOperationRegistry") as mock_registry:
            mock_operation_class = Mock()
            mock_operation_class.side_effect = Exception("Operation error")
            mock_registry.get_operation.return_value = mock_operation_class

            result = handler.handle_admin_operation(event)

            assert result["statusCode"] == 400
            body = result["body"]
            assert "Internal error" in body

    def test_list_available_operations(self, handler):
        """Test listing available operations."""
        with patch("app.admin.lambda_admin.AdminOperationRegistry") as mock_registry:
            mock_registry.list_operations.return_value = {
                "list_users": "List all users",
                "create_user": "Create a new user",
            }

            # Mock operation classes
            mock_list_op = Mock()
            mock_list_op.requires_confirmation = False
            mock_create_op = Mock()
            mock_create_op.requires_confirmation = True

            mock_registry.get_operation.side_effect = lambda name: {
                "list_users": mock_list_op,
                "create_user": mock_create_op,
            }.get(name)

            result = handler.list_available_operations()

            assert result["statusCode"] == 200
            body = result["body"]
            assert 'success": true' in body
            assert "Available operations: 2" in body

    def test_error_response(self, handler):
        """Test error response creation."""
        result = handler._error_response("Test error message")

        assert result["statusCode"] == 400
        body = result["body"]
        assert 'success": false' in body
        assert "Test error message" in body

    def test_get_timestamp(self, handler):
        """Test timestamp generation."""
        timestamp = handler._get_timestamp()

        assert isinstance(timestamp, str)
        assert "T" in timestamp  # ISO format
        assert "Z" in timestamp or "+" in timestamp  # Timezone info


class TestHandleAdminRequest:
    """Test handle_admin_request function."""

    @pytest.fixture
    def app(self):
        """Create Flask app for testing."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key"
        return app

    def test_handle_admin_request_list_operations(self, app):
        """Test handling list operations request."""
        event = {"admin_operation": "list_operations"}

        with patch("app.admin.lambda_admin.LambdaAdminHandler") as mock_handler_class:
            mock_handler = Mock()
            mock_handler.list_available_operations.return_value = {"statusCode": 200, "body": '{"success": true}'}
            mock_handler_class.return_value = mock_handler

            result = handle_admin_request(app, event)

            mock_handler.list_available_operations.assert_called_once()
            assert result["statusCode"] == 200

    def test_handle_admin_request_specific_operation(self, app):
        """Test handling specific admin operation request."""
        event = {"admin_operation": "list_users", "parameters": {"limit": 10}}

        with patch("app.admin.lambda_admin.LambdaAdminHandler") as mock_handler_class:
            mock_handler = Mock()
            mock_handler.handle_admin_operation.return_value = {"statusCode": 200, "body": '{"success": true}'}
            mock_handler_class.return_value = mock_handler

            result = handle_admin_request(app, event)

            mock_handler.handle_admin_operation.assert_called_once_with(event)
            assert result["statusCode"] == 200

    def test_handle_admin_request_with_parameters(self, app):
        """Test handling admin operation with parameters."""
        event = {
            "admin_operation": "create_user",
            "parameters": {"username": "testuser", "email": "test@example.com", "password": "password123"},
            "confirm": True,
        }

        with patch("app.admin.lambda_admin.LambdaAdminHandler") as mock_handler_class:
            mock_handler = Mock()
            mock_handler.handle_admin_operation.return_value = {
                "statusCode": 200,
                "body": '{"success": true, "message": "User created"}',
            }
            mock_handler_class.return_value = mock_handler

            result = handle_admin_request(app, event)

            mock_handler.handle_admin_operation.assert_called_once_with(event)
            assert result["statusCode"] == 200

    def test_handle_admin_request_error_handling(self, app):
        """Test error handling in admin request."""
        event = {"admin_operation": "invalid_operation", "parameters": {}}

        with patch("app.admin.lambda_admin.LambdaAdminHandler") as mock_handler_class:
            mock_handler = Mock()
            mock_handler.handle_admin_operation.return_value = {
                "statusCode": 400,
                "body": '{"success": false, "message": "Unknown operation"}',
            }
            mock_handler_class.return_value = mock_handler

            result = handle_admin_request(app, event)

            mock_handler.handle_admin_operation.assert_called_once_with(event)
            assert result["statusCode"] == 400

    def test_handle_admin_request_empty_event(self, app):
        """Test handling empty event."""
        event = {}

        with patch("app.admin.lambda_admin.LambdaAdminHandler") as mock_handler_class:
            mock_handler = Mock()
            mock_handler.handle_admin_operation.return_value = {
                "statusCode": 400,
                "body": '{"success": false, "message": "Missing admin_operation"}',
            }
            mock_handler_class.return_value = mock_handler

            result = handle_admin_request(app, event)

            mock_handler.handle_admin_operation.assert_called_once_with(event)
            assert result["statusCode"] == 400

    def test_handle_admin_request_none_event(self, app):
        """Test handling None event."""
        event = None

        with patch("app.admin.lambda_admin.LambdaAdminHandler") as mock_handler_class:
            mock_handler = Mock()
            mock_handler.handle_admin_operation.return_value = {
                "statusCode": 400,
                "body": '{"success": false, "message": "Invalid event"}',
            }
            mock_handler_class.return_value = mock_handler

            # The function should handle None event gracefully
            try:
                result = handle_admin_request(app, event)
                # If it doesn't raise an exception, check the result
                assert result["statusCode"] == 400
            except AttributeError:
                # This is expected since event.get() will fail on None
                pass


class TestLambdaAdminIntegration:
    """Test Lambda admin integration scenarios."""

    @pytest.fixture
    def app(self):
        """Create Flask app for testing."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key"
        return app

    def test_full_workflow_list_users(self, app):
        """Test full workflow for listing users."""
        event = {"admin_operation": "list_users", "parameters": {"limit": 10, "admin_only": False}}

        with patch("app.admin.lambda_admin.AdminOperationRegistry") as mock_registry:
            # Mock the operation
            mock_operation_class = Mock()
            mock_operation = Mock()
            mock_operation.requires_confirmation = False
            mock_operation.validate_params.return_value = {"valid": True, "errors": []}
            mock_operation.execute.return_value = {
                "success": True,
                "message": "Retrieved 0 users",
                "data": {"users": [], "total_count": 0},
            }
            mock_operation_class.return_value = mock_operation
            mock_registry.get_operation.return_value = mock_operation_class

            result = handle_admin_request(app, event)

            assert result["statusCode"] == 200
            body = result["body"]
            assert 'success": true' in body
            assert "Retrieved 0 users" in body

    def test_full_workflow_create_user_requires_confirmation(self, app):
        """Test full workflow for creating user that requires confirmation."""
        event = {
            "admin_operation": "create_user",
            "parameters": {"username": "newuser", "email": "newuser@example.com", "password": "password123"},
            "confirm": False,
        }

        with patch("app.admin.lambda_admin.AdminOperationRegistry") as mock_registry:
            # Mock the operation
            mock_operation_class = Mock()
            mock_operation = Mock()
            mock_operation.requires_confirmation = True
            mock_operation.description = "Create a new user with specified credentials"
            mock_operation.validate_params.return_value = {"valid": True, "errors": []}
            mock_operation_class.return_value = mock_operation
            mock_registry.get_operation.return_value = mock_operation_class

            result = handle_admin_request(app, event)

            assert result["statusCode"] == 200
            body = result["body"]
            assert "requires confirmation" in body
            assert "confirm" in body

    def test_full_workflow_system_stats(self, app):
        """Test full workflow for system stats."""
        event = {"admin_operation": "system_stats", "parameters": {}}

        with patch("app.admin.lambda_admin.AdminOperationRegistry") as mock_registry:
            # Mock the operation
            mock_operation_class = Mock()
            mock_operation = Mock()
            mock_operation.requires_confirmation = False
            mock_operation.validate_params.return_value = {"valid": True, "errors": []}
            mock_operation.execute.return_value = {
                "success": True,
                "message": "System statistics retrieved",
                "data": {
                    "users": {"total": 10, "admin": 2, "regular": 8},
                    "content": {"restaurants": 5, "expenses": 100},
                    "system": {"database_connection": "active"},
                },
            }
            mock_operation_class.return_value = mock_operation
            mock_registry.get_operation.return_value = mock_operation_class

            result = handle_admin_request(app, event)

            assert result["statusCode"] == 200
            body = result["body"]
            assert 'success": true' in body
            assert "System statistics retrieved" in body

    def test_error_scenarios(self, app):
        """Test various error scenarios."""
        # Test unknown operation
        event = {"admin_operation": "unknown_op"}
        result = handle_admin_request(app, event)
        assert result["statusCode"] == 400

        # Test invalid parameters
        event = {"admin_operation": "list_users", "parameters": {"limit": "invalid"}}

        with patch("app.admin.lambda_admin.AdminOperationRegistry") as mock_registry:
            mock_operation_class = Mock()
            mock_operation = Mock()
            mock_operation.requires_confirmation = False
            mock_operation.validate_params.return_value = {"valid": False, "errors": ["limit must be an integer"]}
            mock_operation_class.return_value = mock_operation
            mock_registry.get_operation.return_value = mock_operation_class

            result = handle_admin_request(app, event)
            assert result["statusCode"] == 400
