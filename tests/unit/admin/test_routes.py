"""Tests for admin routes to improve coverage."""

from unittest.mock import Mock, patch

import pytest
from flask import Flask

from app.admin.routes import (
    _create_user_from_form_data,
    _extract_user_form_data,
    _handle_password_email,
    _validate_user_form_data,
    generate_secure_password,
    send_password_reset_email,
)


class TestAdminRoutes:
    """Test admin route helper functions."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        return app

    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = Mock()
        user.username = "testuser"
        user.email = "test@example.com"
        user.get_display_name.return_value = "Test User"
        return user

    def test_generate_secure_password(self):
        """Test secure password generation."""
        password = generate_secure_password()

        assert isinstance(password, str)
        assert len(password) == 12  # Default length

        # Test custom length
        password_16 = generate_secure_password(16)
        assert len(password_16) == 16

        # Test that passwords are different
        password2 = generate_secure_password()
        assert password != password2

    def test_generate_secure_password_characters(self):
        """Test that generated passwords contain expected characters."""
        password = generate_secure_password(50)  # Longer password for better testing

        # Should contain at least one of each character type
        assert any(c.islower() for c in password)
        assert any(c.isupper() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

    def test_generate_secure_password_length_variations(self):
        """Test password generation with different lengths."""
        # Test minimum length
        password_8 = generate_secure_password(8)
        assert len(password_8) == 8

        # Test longer length
        password_32 = generate_secure_password(32)
        assert len(password_32) == 32

        # Test very long length
        password_100 = generate_secure_password(100)
        assert len(password_100) == 100

    def test_generate_secure_password_uniqueness(self):
        """Test that generated passwords are unique."""
        passwords = set()
        for _ in range(100):
            password = generate_secure_password()
            passwords.add(password)

        # Should have generated mostly unique passwords
        assert len(passwords) > 90  # Allow for some collisions

    def test_generate_secure_password_character_distribution(self):
        """Test that passwords have good character distribution."""
        password = generate_secure_password(100)

        # Count character types
        lowercase_count = sum(1 for c in password if c.islower())
        uppercase_count = sum(1 for c in password if c.isupper())
        digit_count = sum(1 for c in password if c.isdigit())
        special_count = sum(1 for c in password if c in "!@#$%^&*()_+-=[]{}|;:,.<>?")

        # Should have reasonable distribution
        assert lowercase_count > 0
        assert uppercase_count > 0
        assert digit_count > 0
        assert special_count > 0

        # No single type should dominate
        total = len(password)
        assert lowercase_count < total * 0.8
        assert uppercase_count < total * 0.8
        assert digit_count < total * 0.8
        assert special_count < total * 0.8

    def test_generate_secure_password_edge_cases(self):
        """Test password generation edge cases."""
        # Test length 1
        password_1 = generate_secure_password(1)
        assert len(password_1) == 1

        # Test length 0 (should return empty string)
        password_0 = generate_secure_password(0)
        assert len(password_0) == 0

        # Test negative length (should return empty string)
        password_neg = generate_secure_password(-5)
        assert len(password_neg) == 0

    def test_generate_secure_password_type_safety(self):
        """Test that function handles type safety."""
        # Test with float input (should raise TypeError)
        try:
            generate_secure_password(12.5)
            assert False, "Should have raised TypeError"
        except TypeError:
            pass  # Expected

        # Test with string input (should raise TypeError)
        try:
            generate_secure_password("12")
            assert False, "Should have raised TypeError"
        except TypeError:
            pass  # Expected

    @patch("app.admin.routes.current_app")
    def test_send_password_reset_email_disabled(self, mock_app, mock_user):
        """Test sending password reset email when email is disabled."""
        with patch("app.admin.routes.is_email_enabled") as mock_email_enabled:
            mock_email_enabled.return_value = False

            result = send_password_reset_email(mock_user, "newpassword123")
            assert result is False
            mock_app.logger.info.assert_called_once()

    @patch("app.admin.routes.current_app")
    def test_send_password_reset_email_success(self, mock_app, mock_user):
        """Test sending password reset email successfully."""
        with patch("app.admin.routes.is_email_enabled") as mock_email_enabled:
            with patch("app.admin.routes.send_password_reset_email") as mock_send_email:
                mock_email_enabled.return_value = True
                mock_send_email.return_value = True

                result = send_password_reset_email(mock_user, "newpassword123")
                assert result is True
                mock_send_email.assert_called_once_with(mock_user.email, mock_user.username, "newpassword123")

    @patch("app.admin.routes.current_app")
    def test_send_password_reset_email_failure(self, mock_app, mock_user):
        """Test sending password reset email when email fails."""
        with patch("app.admin.routes.is_email_enabled") as mock_email_enabled:
            with patch("app.admin.routes.send_password_reset_email") as mock_send_email:
                mock_email_enabled.return_value = True
                mock_send_email.return_value = False

                result = send_password_reset_email(mock_user, "newpassword123")
                assert result is False
                mock_app.logger.warning.assert_called_once()

    @patch("app.admin.routes.current_app")
    def test_send_password_reset_email_exception(self, mock_app, mock_user):
        """Test sending password reset email when exception occurs."""
        with patch("app.admin.routes.is_email_enabled", side_effect=Exception("Email service error")):
            result = send_password_reset_email(mock_user, "newpassword123")
            assert result is False
            mock_app.logger.error.assert_called_once()
            mock_app.logger.info.assert_called_once()

    def test_extract_user_form_data(self, app):
        """Test extracting user form data."""
        with app.test_request_context(
            "/admin/users/create",
            method="POST",
            data={
                "username": "testuser",
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User",
                "is_admin": "on",
                "is_active": "on",
                "send_password_email": "on",
            },
        ):
            form_data = _extract_user_form_data()

            assert form_data["username"] == "testuser"
            assert form_data["email"] == "test@example.com"
            assert form_data["first_name"] == "Test"
            assert form_data["last_name"] == "User"
            assert form_data["is_admin"] is True
            assert form_data["is_active"] is True
            assert form_data["send_password_email"] is True

    def test_extract_user_form_data_empty(self, app):
        """Test extracting user form data with empty form."""
        with app.test_request_context("/admin/users/create", method="POST", data={}):
            form_data = _extract_user_form_data()

            assert form_data["username"] == ""
            assert form_data["email"] == ""
            assert form_data["first_name"] == ""
            assert form_data["last_name"] == ""
            assert form_data["is_admin"] is False
            assert form_data["is_active"] is False
            assert form_data["send_password_email"] is False

    def test_validate_user_form_data_valid(self):
        """Test validating valid user form data."""
        form_data = {
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "is_admin": True,
            "is_active": True,
            "send_password_email": True,
        }

        with patch("app.admin.routes.User") as mock_user_class:
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = None
            mock_user_class.query = mock_query

            is_valid, error_message = _validate_user_form_data(form_data)
            assert is_valid is True
            assert error_message == ""

    def test_validate_user_form_data_missing_required(self):
        """Test validating user form data with missing required fields."""
        form_data = {
            "username": "",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "is_admin": True,
            "is_active": True,
            "send_password_email": True,
        }

        is_valid, error_message = _validate_user_form_data(form_data)
        assert is_valid is False
        assert error_message == "Username and email are required"

    def test_validate_user_form_data_existing_user(self):
        """Test validating user form data with existing user."""
        form_data = {
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "is_admin": True,
            "is_active": True,
            "send_password_email": True,
        }

        with patch("app.admin.routes.User") as mock_user_class:
            mock_query = Mock()
            mock_existing_user = Mock()
            mock_query.filter.return_value.first.return_value = mock_existing_user
            mock_user_class.query = mock_query

            is_valid, error_message = _validate_user_form_data(form_data)
            assert is_valid is False
            assert error_message == "User with this username or email already exists"

    def test_create_user_from_form_data(self, app):
        """Test creating user from form data."""
        form_data = {
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "is_admin": True,
            "is_active": True,
            "send_password_email": True,
        }

        with app.app_context():
            with patch("app.admin.routes.db") as mock_db:
                with patch("app.admin.routes.User") as mock_user_class:
                    mock_user = Mock()
                    mock_user_class.return_value = mock_user

                    user = _create_user_from_form_data(form_data, "password123")

                    assert user == mock_user
                    mock_user.set_password.assert_called_once_with("password123")
                    mock_db.session.add.assert_called_once_with(mock_user)
                    mock_db.session.flush.assert_called_once()

    def test_handle_password_email_disabled(self, app, mock_user):
        """Test handling password email when disabled."""
        with app.test_request_context():
            with patch("app.admin.routes.flash") as mock_flash:
                _handle_password_email(mock_user, "password123", False)
                mock_flash.assert_called_once_with("User created successfully. Password: password123", "success")

    def test_handle_password_email_enabled_success(self, app, mock_user):
        """Test handling password email when enabled and successful."""
        with app.test_request_context():
            with patch("app.admin.routes.flash") as mock_flash:
                with patch("app.admin.routes.is_email_enabled") as mock_email_enabled:
                    with patch("app.admin.routes.send_welcome_email") as mock_send_email:
                        mock_email_enabled.return_value = True
                        mock_send_email.return_value = True

                        _handle_password_email(mock_user, "password123", True)
                        mock_flash.assert_called_once_with(
                            f"User created and welcome email sent to {mock_user.email}", "success"
                        )

    def test_handle_password_email_enabled_failure(self, app, mock_user):
        """Test handling password email when enabled but fails."""
        with app.test_request_context():
            with patch("app.admin.routes.flash") as mock_flash:
                with patch("app.admin.routes.is_email_enabled") as mock_email_enabled:
                    with patch("app.admin.routes.send_welcome_email") as mock_send_email:
                        mock_email_enabled.return_value = True
                        mock_send_email.return_value = False

                        _handle_password_email(mock_user, "password123", True)
                        mock_flash.assert_called_once_with(
                            "User created but email failed. Password: password123", "warning"
                        )

    def test_handle_password_email_disabled_service(self, app, mock_user):
        """Test handling password email when email service is disabled."""
        with app.test_request_context():
            with patch("app.admin.routes.flash") as mock_flash:
                with patch("app.admin.routes.is_email_enabled") as mock_email_enabled:
                    mock_email_enabled.return_value = False

                    _handle_password_email(mock_user, "password123", True)
                    mock_flash.assert_called_once_with(
                        "User created successfully. Password: password123 (Email disabled)", "success"
                    )

    def test_handle_password_email_exception(self, app, mock_user):
        """Test handling password email when exception occurs."""
        with app.test_request_context():
            with patch("app.admin.routes.flash") as mock_flash:
                with patch("app.admin.routes.is_email_enabled", side_effect=Exception("Email service error")):
                    with patch("app.admin.routes.current_app") as mock_app:
                        _handle_password_email(mock_user, "password123", True)
                        mock_flash.assert_called_once_with(
                            "User created but email failed. Password: password123", "warning"
                        )
                        mock_app.logger.error.assert_called_once()
