"""Tests for admin routes to improve coverage."""

from unittest.mock import Mock, patch

from flask import Flask
import pytest

from app.admin.routes import (
    _create_user_from_form_data,
    _extract_user_form_data,
    _handle_password_notification,
    _validate_user_form_data,
    generate_secure_password,
    send_password_reset_notification,
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

    def test_generate_secure_password(self) -> None:
        """Test secure password generation with various lengths and edge cases."""
        # Basic functionality
        password = generate_secure_password()
        assert isinstance(password, str)
        assert len(password) == 12  # Default length

        # Custom lengths
        assert len(generate_secure_password(8)) == 8
        assert len(generate_secure_password(16)) == 16
        assert len(generate_secure_password(32)) == 32
        assert len(generate_secure_password(100)) == 100

        # Edge cases
        assert generate_secure_password(0) == ""
        assert generate_secure_password(-5) == ""
        assert len(generate_secure_password(1)) == 1

        # Uniqueness
        password2 = generate_secure_password()
        assert password != password2

        # Uniqueness across many generations
        passwords = {generate_secure_password() for _ in range(50)}
        assert len(passwords) > 45  # Allow for some collisions

    def test_generate_secure_password_character_requirements(self) -> None:
        """Test that generated passwords contain expected character types."""
        # Generate multiple passwords to account for randomness
        passwords = [generate_secure_password(20) for _ in range(10)]

        # At least one password should contain each character type
        has_lowercase = any(any(c.islower() for c in p) for p in passwords)
        has_uppercase = any(any(c.isupper() for c in p) for p in passwords)
        has_digit = any(any(c.isdigit() for c in p) for p in passwords)

        assert has_lowercase, "No lowercase letters found in any generated password"
        assert has_uppercase, "No uppercase letters found in any generated password"
        assert has_digit, "No digits found in any generated password"

        # Verify all passwords have correct length
        assert all(len(p) == 20 for p in passwords)

        # Test character distribution in a longer password
        password = generate_secure_password(100)
        lowercase_count = sum(1 for c in password if c.islower())
        uppercase_count = sum(1 for c in password if c.isupper())
        digit_count = sum(1 for c in password if c.isdigit())

        # Should have reasonable distribution (no single type dominates)
        total = len(password)
        assert lowercase_count < total * 0.8
        assert uppercase_count < total * 0.8
        assert digit_count < total * 0.8

    def test_generate_secure_password_type_safety(self) -> None:
        """Test that function handles type safety."""
        # Test with float input (should raise TypeError)
        with pytest.raises(TypeError):
            generate_secure_password(12.5)

        # Test with string input (should raise TypeError)
        with pytest.raises(TypeError):
            generate_secure_password("12")

    def test_extract_user_form_data(self, app) -> None:
        """Test extracting user form data with various scenarios."""
        # Full form data
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
                "send_password_notification": "on",
            },
        ):
            form_data = _extract_user_form_data()

            assert form_data["username"] == "testuser"
            assert form_data["email"] == "test@example.com"
            assert form_data["first_name"] == "Test"
            assert form_data["last_name"] == "User"
            assert form_data["is_admin"] is True
            assert form_data["is_active"] is True
            assert form_data["send_password_notification"] is True

        # Empty form
        with app.test_request_context("/admin/users/create", method="POST", data={}):
            form_data = _extract_user_form_data()

            assert form_data["username"] == ""
            assert form_data["email"] == ""
            assert form_data["first_name"] == ""
            assert form_data["last_name"] == ""
            assert form_data["is_admin"] is False
            assert form_data["is_active"] is False
            assert form_data["send_password_notification"] is False

        # Partial form data (missing fields)
        with app.test_request_context(
            "/admin/users/create",
            method="POST",
            data={"username": "testuser"},
        ):
            form_data = _extract_user_form_data()

            assert form_data["username"] == "testuser"
            assert form_data["email"] == ""
            assert form_data["is_admin"] is False

    def test_validate_user_form_data(self) -> None:
        """Test validating user form data with various scenarios."""
        # Valid data
        form_data = {
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "is_admin": True,
            "is_active": True,
            "send_password_notification": True,
        }

        with patch("app.admin.routes.User") as mock_user_class:
            mock_query = Mock()
            mock_query.filter.return_value.first.return_value = None
            mock_user_class.query = mock_query

            is_valid, error_message = _validate_user_form_data(form_data)
            assert is_valid is True
            assert error_message == ""

        # Missing required fields
        form_data["username"] = ""
        is_valid, error_message = _validate_user_form_data(form_data)
        assert is_valid is False
        assert error_message == "Username and email are required"

        # None values
        form_data = {
            "username": None,
            "email": None,
            "first_name": "Test",
            "last_name": "User",
            "is_admin": True,
            "is_active": True,
            "send_password_notification": True,
        }
        is_valid, error_message = _validate_user_form_data(form_data)
        assert is_valid is False
        assert error_message == "Username and email are required"

        # Existing user
        form_data = {
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "is_admin": True,
            "is_active": True,
            "send_password_notification": True,
        }

        with patch("app.admin.routes.User") as mock_user_class:
            mock_query = Mock()
            mock_existing_user = Mock()
            mock_query.filter.return_value.first.return_value = mock_existing_user
            mock_user_class.query = mock_query

            is_valid, error_message = _validate_user_form_data(form_data)
            assert is_valid is False
            assert error_message == "User with this username or email already exists"

    def test_create_user_from_form_data(self, app) -> None:
        """Test creating user from form data with various scenarios."""
        # Full form data
        form_data = {
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "is_admin": True,
            "is_active": True,
            "send_password_notification": True,
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

        # Minimal form data
        form_data = {
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "",
            "last_name": "",
            "is_admin": False,
            "is_active": True,
            "send_password_notification": False,
        }

        with app.app_context():
            with patch("app.admin.routes.db") as mock_db:
                with patch("app.admin.routes.User") as mock_user_class:
                    mock_user = Mock()
                    mock_user_class.return_value = mock_user

                    user = _create_user_from_form_data(form_data, "password123")

                    assert user == mock_user
                    mock_user.set_password.assert_called_once_with("password123")

    def test_handle_password_notification(self, app, mock_user) -> None:
        """Test handling password notification with various scenarios."""
        # Disabled notification
        with app.test_request_context():
            with patch("app.admin.routes.flash") as mock_flash:
                _handle_password_notification(mock_user, "password123", False)
                mock_flash.assert_called_once_with("User created successfully. Password: password123", "success")

        # None user
        with app.test_request_context():
            with patch("app.admin.routes.flash") as mock_flash:
                _handle_password_notification(None, "password123", False)
                mock_flash.assert_called_once_with("User created successfully. Password: password123", "success")

        # Empty password
        mock_user2 = Mock()
        with app.test_request_context():
            with patch("app.admin.routes.flash") as mock_flash:
                _handle_password_notification(mock_user2, "", False)
                mock_flash.assert_called_once_with("User created successfully. Password: ", "success")


class TestAdminRoutesCoverage:
    """Tests to improve coverage for uncovered routes and functions."""

    def test_route_functions_exist(self) -> None:
        """Test that route functions exist and are callable."""
        from app.admin.routes import (
            create_user,
            dashboard,
            delete_user,
            get_user_stats,
            list_users,
            reset_user_password,
            toggle_user_active,
            toggle_user_admin,
            view_user,
        )

        # Test that all route functions exist and are callable
        assert callable(dashboard)
        assert callable(list_users)
        assert callable(view_user)
        assert callable(reset_user_password)
        assert callable(toggle_user_admin)
        assert callable(toggle_user_active)
        assert callable(delete_user)
        assert callable(create_user)
        assert callable(get_user_stats)
