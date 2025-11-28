"""Tests for extensions module."""

import os
from unittest.mock import Mock, patch

from flask import Flask
import pytest

from app.extensions import (
    _configure_csrf_handlers,
    _log_session_config,
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

    def test_log_session_config_signed_cookies(self, app) -> None:
        """Test logging signed cookies session configuration."""
        app.config.update(
            {"SESSION_COOKIE_NAME": "test-session", "SESSION_COOKIE_SECURE": True, "PERMANENT_SESSION_LIFETIME": 7200}
        )

        with patch.object(app.logger, "info") as mock_info:
            _log_session_config(app)

            assert mock_info.call_count == 6
            calls = [call[0][0] for call in mock_info.call_args_list]
            assert any("Session backend: signed-cookies (Flask default)" in call for call in calls)
            assert any("Cookie name: %s" in call for call in calls)
            assert any("Cookie secure: %s" in call for call in calls)
            assert any("Cookie httponly: %s" in call for call in calls)
            assert any("Cookie samesite: %s" in call for call in calls)
            assert any("Session lifetime: %s seconds" in call for call in calls)

    def test_configure_csrf_handlers_disabled(self, app) -> None:
        """Test CSRF handlers configuration when CSRF is disabled."""
        app.config["WTF_CSRF_ENABLED"] = False

        _configure_csrf_handlers(app)

        # Should not add CSRF headers when disabled
        with app.test_request_context():
            response = app.test_client().get("/")
            assert "X-CSRFToken" not in response.headers

    def test_init_app_success(self, app) -> None:
        """Test successful app initialization."""
        with patch("app.extensions.db") as mock_db:
            with patch("app.extensions.login_manager") as mock_login_manager:
                with patch("app.extensions.migrate") as mock_migrate:
                    with patch("app.extensions.limiter") as mock_limiter:
                        with patch("app.extensions.csrf") as mock_csrf:
                            with patch("app.extensions._log_session_config") as mock_log_config:
                                with patch("app.extensions._configure_csrf_handlers") as mock_csrf_handlers:
                                    init_app(app)

                                    mock_db.init_app.assert_called_once_with(app)
                                    mock_login_manager.init_app.assert_called_once_with(app)
                                    # Check that migrate.init_app was called with app, db, and directory
                                    mock_migrate.init_app.assert_called_once()
                                    call_args = mock_migrate.init_app.call_args
                                    assert call_args[0][0] == app  # First positional arg is app
                                    assert call_args[0][1] == mock_db  # Second positional arg is db
                                    assert "directory" in call_args[1]  # directory is a keyword arg
                                    mock_limiter.init_app.assert_called_once_with(app)
                                    mock_csrf.init_app.assert_called_once_with(app)
                                    mock_log_config.assert_called_once_with(app)
                                    mock_csrf_handlers.assert_called_once_with(app)

    def test_init_app_lambda_environment(self, app) -> None:
        """Test app initialization in Lambda environment."""
        with patch.dict(os.environ, {"AWS_LAMBDA_FUNCTION_NAME": "test-function"}):
            with patch("app.extensions._log_session_config"):
                with patch.object(app.logger, "info") as mock_info:
                    init_app(app)

                    calls = [call[0][0] for call in mock_info.call_args_list]
                    assert any("is_lambda: True" in call for call in calls)

    def test_unauthorized_handler_api_request(self, app) -> None:
        """Test unauthorized handler for API requests."""
        with app.test_request_context("/api/test"):
            with patch("app.extensions.request") as mock_request:
                mock_request.path = "/api/test"

                response = unauthorized()

                assert response.status_code == 401
                assert "Authentication required" in response.get_json()["message"]

    def test_unauthorized_handler_web_request(self, app) -> None:
        """Test unauthorized handler for web requests."""
        with app.test_request_context("/test"):
            with patch("app.extensions._handle_web_unauthorized") as mock_web_handler:
                mock_web_handler.return_value = "redirected"

                result = unauthorized()

                mock_web_handler.assert_called_once()
                assert result == "redirected"

    def test_load_user_success(self, app) -> None:
        """Test successful user loading."""
        with app.app_context():
            with patch("app.extensions.db") as mock_db:
                with patch("app.auth.models.User") as mock_user_class:
                    mock_user = Mock()
                    mock_db.session.get.return_value = mock_user

                    result = load_user("123")

                    assert result == mock_user
                    mock_db.session.get.assert_called_once_with(mock_user_class, 123)

    def test_load_user_not_found(self, app) -> None:
        """Test user loading when user not found."""
        with app.app_context():
            with patch("app.extensions.db") as mock_db:
                with patch("app.auth.models.User") as mock_user_class:
                    mock_db.session.get.return_value = None

                    result = load_user("123")

                    assert result is None
                    mock_db.session.get.assert_called_once_with(mock_user_class, 123)

    def test_load_user_invalid_id(self, app) -> None:
        """Test user loading with invalid user ID."""
        with app.app_context():
            with patch("app.extensions.db") as mock_db:
                with patch("app.auth.models.User"):
                    # The function should return None for invalid user IDs without calling db.session.get
                    result = load_user("invalid")

                    assert result is None
                    # Should not call db.session.get for invalid IDs
                    mock_db.session.get.assert_not_called()
