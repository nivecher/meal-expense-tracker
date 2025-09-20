"""Tests for extensions module."""

import os
from unittest.mock import Mock, patch

import pytest
from flask import Flask
from flask_wtf.csrf import CSRFError

from app.extensions import (
    _configure_csrf_handlers,
    _log_session_config,
    _test_dynamodb_connection,
    _test_dynamodb_permissions,
    _validate_dynamodb_session_config,
    _validate_required_configs,
    _validate_table_name_format,
    init_app,
    load_user,
    unauthorized,
)


class TestExtensionsModule:
    """Test extensions module functions."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key"
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        return app

    @pytest.fixture
    def mock_table(self):
        """Create mock DynamoDB table."""
        table = Mock()
        table.table_status = "ACTIVE"
        table.scan.return_value = {"Items": []}
        return table

    def test_log_session_config_dynamodb(self, app):
        """Test logging DynamoDB session configuration."""
        app.config.update(
            {
                "SESSION_TYPE": "dynamodb",
                "SESSION_DYNAMODB_TABLE": "test-table",
                "SESSION_DYNAMODB_REGION": "us-east-1",
                "SESSION_DYNAMODB_ENDPOINT_URL": "http://localhost:8000",
                "SESSION_KEY_PREFIX": "test-prefix",
            }
        )

        with patch.object(app.logger, "info") as mock_info:
            _log_session_config(app)

            assert mock_info.call_count >= 2
            calls = [call[0][0] for call in mock_info.call_args_list]
            assert any("Session backend: dynamodb" in call for call in calls)
            assert any("Table: test-table" in call for call in calls)

    def test_log_session_config_dynamodb_no_endpoint(self, app):
        """Test logging DynamoDB session configuration without endpoint."""
        app.config.update(
            {"SESSION_TYPE": "dynamodb", "SESSION_DYNAMODB_TABLE": "test-table", "SESSION_DYNAMODB_REGION": "us-east-1"}
        )

        with patch.object(app.logger, "info") as mock_info:
            _log_session_config(app)

            calls = [call[0][0] for call in mock_info.call_args_list]
            assert any("Endpoint: AWS default" in call for call in calls)

    def test_log_session_config_signed_cookies(self, app):
        """Test logging signed cookies session configuration."""
        app.config.update(
            {"SESSION_COOKIE_NAME": "test-session", "SESSION_COOKIE_SECURE": True, "PERMANENT_SESSION_LIFETIME": 7200}
        )

        with patch.object(app.logger, "info") as mock_info:
            _log_session_config(app)

            calls = [call[0][0] for call in mock_info.call_args_list]
            assert any("Session backend: signed-cookies" in call for call in calls)
            assert any("Cookie name: test-session" in call for call in calls)
            assert any("Cookie secure: True" in call for call in calls)
            assert any("Session lifetime: 7200 seconds" in call for call in calls)

    def test_log_session_config_other_type(self, app):
        """Test logging other session type configuration."""
        app.config["SESSION_TYPE"] = "redis"

        with patch.object(app.logger, "info") as mock_info:
            _log_session_config(app)

            calls = [call[0][0] for call in mock_info.call_args_list]
            assert any("Session backend: redis" in call for call in calls)

    def test_validate_dynamodb_session_config_success(self, app, mock_table):
        """Test successful DynamoDB session configuration validation."""
        app.config.update(
            {
                "SESSION_TYPE": "dynamodb",
                "SESSION_DYNAMODB_TABLE": "test-table",
                "SESSION_DYNAMODB_REGION": "us-east-1",
                "SESSION_DYNAMODB": Mock(),
            }
        )

        with patch("app.extensions._validate_required_configs") as mock_validate_required:
            with patch("app.extensions._validate_table_name_format") as mock_validate_table:
                with patch("app.extensions._test_dynamodb_connection") as mock_test_connection:
                    with patch.object(app.logger, "info") as mock_info:
                        mock_validate_table.return_value = "test-table"

                        _validate_dynamodb_session_config(app)

                        mock_validate_required.assert_called_once_with(app)
                        mock_validate_table.assert_called_once_with(app)
                        mock_test_connection.assert_called_once_with(app, "test-table")
                        mock_info.assert_called_with("DynamoDB session configuration validated successfully")

    def test_validate_dynamodb_session_config_not_dynamodb(self, app):
        """Test DynamoDB session configuration validation when not using DynamoDB."""
        app.config["SESSION_TYPE"] = "redis"

        with patch("app.extensions._validate_required_configs") as mock_validate_required:
            with patch("app.extensions._validate_table_name_format") as mock_validate_table:
                with patch("app.extensions._test_dynamodb_connection") as mock_test_connection:
                    _validate_dynamodb_session_config(app)

                    mock_validate_required.assert_not_called()
                    mock_validate_table.assert_not_called()
                    mock_test_connection.assert_not_called()

    def test_validate_required_configs_success(self, app):
        """Test successful validation of required DynamoDB configurations."""
        app.config.update({"SESSION_DYNAMODB_TABLE": "test-table", "SESSION_DYNAMODB_REGION": "us-east-1"})

        with patch.object(app.logger, "error") as mock_error:
            _validate_required_configs(app)
            mock_error.assert_not_called()

    def test_validate_required_configs_missing_table(self, app):
        """Test validation with missing table configuration."""
        app.config["SESSION_DYNAMODB_REGION"] = "us-east-1"

        with patch.object(app.logger, "error") as mock_error:
            with pytest.raises(ValueError, match="Missing required DynamoDB session configuration"):
                _validate_required_configs(app)

            mock_error.assert_called_once()

    def test_validate_required_configs_missing_region(self, app):
        """Test validation with missing region configuration."""
        app.config["SESSION_DYNAMODB_TABLE"] = "test-table"

        with patch.object(app.logger, "error") as mock_error:
            with pytest.raises(ValueError, match="Missing required DynamoDB session configuration"):
                _validate_required_configs(app)

            mock_error.assert_called_once()

    def test_validate_required_configs_missing_both(self, app):
        """Test validation with missing both configurations."""
        with patch.object(app.logger, "error") as mock_error:
            with pytest.raises(ValueError, match="Missing required DynamoDB session configuration"):
                _validate_required_configs(app)

            mock_error.assert_called_once()

    def test_validate_table_name_format_valid(self, app):
        """Test validation of valid table name format."""
        app.config["SESSION_DYNAMODB_TABLE"] = "test-table-123"

        result = _validate_table_name_format(app)
        assert result == "test-table-123"

    def test_validate_table_name_format_valid_underscores(self, app):
        """Test validation of valid table name with underscores."""
        app.config["SESSION_DYNAMODB_TABLE"] = "test_table_123"

        result = _validate_table_name_format(app)
        assert result == "test_table_123"

    def test_validate_table_name_format_invalid_characters(self, app):
        """Test validation of invalid table name with special characters."""
        app.config["SESSION_DYNAMODB_TABLE"] = "test-table@123"

        with pytest.raises(ValueError, match="Invalid DynamoDB table name"):
            _validate_table_name_format(app)

    def test_validate_table_name_format_empty(self, app):
        """Test validation of empty table name."""
        app.config["SESSION_DYNAMODB_TABLE"] = ""

        with pytest.raises(ValueError, match="Invalid DynamoDB table name"):
            _validate_table_name_format(app)

    def test_test_dynamodb_connection_success(self, app, mock_table):
        """Test successful DynamoDB connection test."""
        app.config["SESSION_DYNAMODB"] = Mock()
        app.config["SESSION_DYNAMODB"].Table.return_value = mock_table

        with patch.object(app.logger, "info") as mock_info:
            with patch.object(app.logger, "warning") as mock_warning:
                with patch("app.extensions._test_dynamodb_permissions") as mock_test_permissions:
                    _test_dynamodb_connection(app, "test-table")

                    mock_info.assert_called()
                    mock_test_permissions.assert_called_once_with(mock_table)

    def test_test_dynamodb_connection_no_resource(self, app):
        """Test DynamoDB connection test without resource configured."""
        app.config["SESSION_DYNAMODB"] = None

        with patch.object(app.logger, "warning") as mock_warning:
            _test_dynamodb_connection(app, "test-table")

            mock_warning.assert_called_with(
                "SESSION_DYNAMODB resource not configured - Flask-Session will create its own"
            )

    def test_test_dynamodb_connection_exception(self, app):
        """Test DynamoDB connection test with exception."""
        app.config["SESSION_DYNAMODB"] = Mock()
        app.config["SESSION_DYNAMODB"].Table.side_effect = Exception("Connection failed")

        with patch.object(app.logger, "error") as mock_error:
            with patch.object(app.logger, "info") as mock_info:
                _test_dynamodb_connection(app, "test-table")

                mock_error.assert_called()
                mock_info.assert_called()

    def test_test_dynamodb_permissions_success(self, mock_table):
        """Test successful DynamoDB permissions test."""
        _test_dynamodb_permissions(mock_table)
        mock_table.scan.assert_called_once_with(Limit=1)

    def test_test_dynamodb_permissions_failure(self, mock_table):
        """Test DynamoDB permissions test with failure."""
        mock_table.scan.side_effect = Exception("Permission denied")

        with pytest.raises(Exception, match="Permission denied"):
            _test_dynamodb_permissions(mock_table)

    def test_configure_csrf_handlers_enabled(self, app):
        """Test CSRF handlers configuration when CSRF is enabled."""
        app.config["WTF_CSRF_ENABLED"] = True

        with patch("app.extensions.generate_csrf") as mock_generate_csrf:
            mock_generate_csrf.return_value = "test-csrf-token"

            _configure_csrf_handlers(app)

            # Test the after_request handler
            with app.test_request_context():
                response = app.test_client().get("/")
                assert response.headers.get("X-CSRFToken") == "test-csrf-token"

    def test_configure_csrf_handlers_disabled(self, app):
        """Test CSRF handlers configuration when CSRF is disabled."""
        app.config["WTF_CSRF_ENABLED"] = False

        _configure_csrf_handlers(app)

        # Should not add CSRF headers when disabled
        with app.test_request_context():
            response = app.test_client().get("/")
            assert "X-CSRFToken" not in response.headers

    def test_csrf_error_handler_api_request(self, app):
        """Test CSRF error handler for API requests."""
        app.config["WTF_CSRF_ENABLED"] = True
        _configure_csrf_handlers(app)

        with app.test_request_context("/api/test", headers={"X-Requested-With": "XMLHttpRequest"}):
            with patch("app.extensions.request") as mock_request:
                mock_request.path = "/api/test"
                mock_request.headers = {"X-Requested-With": "XMLHttpRequest"}

                csrf_error = CSRFError("CSRF token missing")
                response = app.error_handler_spec[None][403][CSRFError](csrf_error)

                assert response.status_code == 403
                assert "csrf_validation_failed" in response.get_json()["error_type"]

    def test_csrf_error_handler_web_request(self, app):
        """Test CSRF error handler for web requests."""
        app.config["WTF_CSRF_ENABLED"] = True
        _configure_csrf_handlers(app)

        with app.test_request_context("/test"):
            with patch("app.extensions.request") as mock_request:
                with patch("app.extensions.flash") as mock_flash:
                    with patch("app.extensions.redirect") as mock_redirect:
                        mock_request.path = "/test"
                        mock_request.headers = {}
                        mock_request.query_string = b"param=value"
                        mock_redirect.return_value = "redirected"

                        csrf_error = CSRFError("CSRF token missing")
                        response = app.error_handler_spec[None][403][CSRFError](csrf_error)

                        mock_flash.assert_called_once()
                        mock_redirect.assert_called_once()

    def test_init_app_success(self, app):
        """Test successful app initialization."""
        with patch("app.extensions.db") as mock_db:
            with patch("app.extensions.jwt") as mock_jwt:
                with patch("app.extensions.login_manager") as mock_login_manager:
                    with patch("app.extensions.migrate") as mock_migrate:
                        with patch("app.extensions.flask_session") as mock_flask_session:
                            with patch("app.extensions.limiter") as mock_limiter:
                                with patch("app.extensions.csrf") as mock_csrf:
                                    with patch("app.extensions._log_session_config") as mock_log_config:
                                        with patch("app.extensions._configure_csrf_handlers") as mock_csrf_handlers:
                                            init_app(app)

                                            mock_db.init_app.assert_called_once_with(app)
                                            mock_jwt.init_app.assert_called_once_with(app)
                                            mock_login_manager.init_app.assert_called_once_with(app)
                                            mock_migrate.init_app.assert_called_once_with(app, mock_db)
                                            mock_limiter.init_app.assert_called_once_with(app)
                                            mock_csrf.init_app.assert_called_once_with(app)
                                            mock_log_config.assert_called_once_with(app)
                                            mock_csrf_handlers.assert_called_once_with(app)

    def test_init_app_dynamodb_session(self, app):
        """Test app initialization with DynamoDB session."""
        app.config["SESSION_TYPE"] = "dynamodb"

        with patch("app.extensions._validate_dynamodb_session_config") as mock_validate:
            with patch("app.extensions.flask_session") as mock_flask_session:
                with patch("app.extensions._log_session_config") as mock_log_config:
                    init_app(app)

                    mock_validate.assert_called_once_with(app)
                    mock_flask_session.init_app.assert_called_once_with(app)

    def test_init_app_filesystem_session(self, app):
        """Test app initialization with filesystem session."""
        app.config["SESSION_TYPE"] = "filesystem"

        with patch("app.extensions.flask_session") as mock_flask_session:
            with patch("app.extensions._log_session_config") as mock_log_config:
                with patch.object(app.logger, "info") as mock_info:
                    init_app(app)

                    mock_flask_session.init_app.assert_called_once_with(app)
                    mock_info.assert_called_with("Using filesystem session with CacheLib backend")

    def test_init_app_redis_session(self, app):
        """Test app initialization with Redis session."""
        app.config["SESSION_TYPE"] = "redis"

        with patch("app.extensions.flask_session") as mock_flask_session:
            with patch("app.extensions._log_session_config") as mock_log_config:
                init_app(app)

                mock_flask_session.init_app.assert_called_once_with(app)

    def test_init_app_lambda_environment(self, app):
        """Test app initialization in Lambda environment."""
        with patch.dict(os.environ, {"AWS_LAMBDA_FUNCTION_NAME": "test-function"}):
            with patch("app.extensions._log_session_config") as mock_log_config:
                with patch.object(app.logger, "info") as mock_info:
                    init_app(app)

                    assert "is_lambda: True" in mock_info.call_args[0][0]

    def test_init_app_jwt_configuration(self, app):
        """Test JWT configuration during app initialization."""
        with patch("app.extensions._log_session_config"):
            with patch("app.extensions._configure_csrf_handlers"):
                init_app(app)

                assert app.config["JWT_SECRET_KEY"] == "test-secret-key"
                assert app.config["JWT_ACCESS_TOKEN_EXPIRES"] == 3600
                assert app.config["JWT_REFRESH_TOKEN_EXPIRES"] == 2592000

    def test_init_app_fallback_secret_key(self, app):
        """Test JWT configuration with fallback secret key."""
        app.config["SECRET_KEY"] = "dev-key-change-in-production"

        with patch("app.extensions._log_session_config"):
            with patch("app.extensions._configure_csrf_handlers"):
                with patch.object(app.logger, "warning") as mock_warning:
                    init_app(app)

                    assert app.config["JWT_SECRET_KEY"] == "dev-key-change-in-production"
                    mock_warning.assert_called_with(
                        "Using fallback JWT secret key - ensure SECRET_KEY is set in production"
                    )

    def test_unauthorized_handler_api_request(self, app):
        """Test unauthorized handler for API requests."""
        with app.test_request_context("/api/test"):
            with patch("app.extensions.request") as mock_request:
                mock_request.path = "/api/test"

                response = unauthorized()

                assert response.status_code == 401
                assert "Authentication required" in response.get_json()["message"]

    def test_unauthorized_handler_web_request(self, app):
        """Test unauthorized handler for web requests."""
        with app.test_request_context("/test"):
            with patch("app.extensions.request") as mock_request:
                with patch("app.extensions.redirect") as mock_redirect:
                    mock_request.path = "/test"
                    mock_request.url = "http://localhost/test"
                    mock_redirect.return_value = "redirected"

                    response = unauthorized()

                    mock_redirect.assert_called_once()

    def test_load_user_success(self, app):
        """Test successful user loading."""
        with app.app_context():
            with patch("app.extensions.db") as mock_db:
                with patch("app.extensions.User") as mock_user_class:
                    mock_user = Mock()
                    mock_db.session.get.return_value = mock_user

                    result = load_user("123")

                    assert result == mock_user
                    mock_db.session.get.assert_called_once_with(mock_user_class, 123)

    def test_load_user_not_found(self, app):
        """Test user loading when user not found."""
        with app.app_context():
            with patch("app.extensions.db") as mock_db:
                with patch("app.extensions.User") as mock_user_class:
                    mock_db.session.get.return_value = None

                    result = load_user("123")

                    assert result is None
                    mock_db.session.get.assert_called_once_with(mock_user_class, 123)

    def test_load_user_invalid_id(self, app):
        """Test user loading with invalid user ID."""
        with app.app_context():
            with patch("app.extensions.db") as mock_db:
                with patch("app.extensions.User") as mock_user_class:
                    mock_db.session.get.side_effect = ValueError("Invalid user ID")

                    result = load_user("invalid")

                    assert result is None

    def test_csrf_error_handler_logging(self, app):
        """Test CSRF error handler logging."""
        app.config["WTF_CSRF_ENABLED"] = True
        _configure_csrf_handlers(app)

        with app.test_request_context("/test"):
            with patch("app.extensions.request") as mock_request:
                with patch("app.extensions.flash") as mock_flash:
                    with patch("app.extensions.redirect") as mock_redirect:
                        with patch.object(app.logger, "warning") as mock_warning:
                            mock_request.path = "/test"
                            mock_request.method = "POST"
                            mock_request.host = "localhost"
                            mock_request.headers = {"User-Agent": "test"}
                            mock_redirect.return_value = "redirected"

                            csrf_error = CSRFError("CSRF token missing")
                            response = app.error_handler_spec[None][403][CSRFError](csrf_error)

                            assert mock_warning.call_count >= 2  # Multiple warning calls
