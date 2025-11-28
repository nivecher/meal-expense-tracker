"""Tests for auth API endpoints."""

from unittest.mock import patch

from flask import url_for

from app.auth.models import User


class TestAuthAPI:
    """Test authentication API endpoints."""

    def test_api_login_success(self, client, test_user, app) -> None:
        """Test successful API login."""
        response = client.post(
            url_for("auth.api_login"),
            json={"username": "testuser_1", "password": "testpass"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert data["message"] == "Logged in successfully."
        assert data["user"]["username"] == "testuser_1"
        assert data["user"]["email"] == "testuser_1@example.com"

    def test_api_login_invalid_username(self, client, test_user, app) -> None:
        """Test API login with invalid username."""
        response = client.post(
            url_for("auth.api_login"),
            json={"username": "nonexistent", "password": "testpass"},
        )

        assert response.status_code == 401
        data = response.get_json()
        assert data["status"] == "error"
        assert data["message"] == "Invalid username or password."

    def test_api_login_invalid_password(self, client, test_user, app) -> None:
        """Test API login with invalid password."""
        response = client.post(
            url_for("auth.api_login"),
            json={"username": "testuser_1", "password": "wrongpass"},
        )

        assert response.status_code == 401
        data = response.get_json()
        assert data["status"] == "error"
        assert data["message"] == "Invalid username or password."

    def test_api_login_missing_username(self, client, app) -> None:
        """Test API login with missing username."""
        response = client.post(
            url_for("auth.api_login"),
            json={"password": "testpass"},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["status"] == "error"
        assert data["message"] == "Username and password are required."

    def test_api_login_missing_password(self, client, app) -> None:
        """Test API login with missing password."""
        response = client.post(
            url_for("auth.api_login"),
            json={"username": "testuser_1"},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["status"] == "error"
        assert data["message"] == "Username and password are required."

    def test_api_login_no_data(self, client, app) -> None:
        """Test API login with no JSON data."""
        response = client.post(
            url_for("auth.api_login"),
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["status"] == "error"
        assert data["message"] == "Username and password are required."

    def test_api_login_invalid_json(self, client, app) -> None:
        """Test API login with invalid JSON."""
        response = client.post(
            url_for("auth.api_login"),
            data="invalid json",
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["status"] == "error"
        assert data["message"] == "Username and password are required."

    @patch("app.auth.api.login_user")
    def test_api_login_exception_during_login(self, mock_login_user, client, test_user, app) -> None:
        """Test API login when login_user raises an exception."""
        mock_login_user.side_effect = Exception("Login failed")

        response = client.post(
            url_for("auth.api_login"),
            json={"username": "testuser_1", "password": "testpass"},
        )

        assert response.status_code == 500
        data = response.get_json()
        assert data["status"] == "error"
        assert data["message"] == "An error occurred during login."

    def test_api_logout_success(self, client, auth, test_user, app) -> None:
        """Test successful API logout."""
        auth.login("testuser_1", "testpass")

        response = client.post(url_for("auth.api_logout"))

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert data["message"] == "Logged out successfully."

    def test_api_logout_not_authenticated(self, client, app) -> None:
        """Test API logout when user is not authenticated."""
        response = client.post(url_for("auth.api_logout"))

        assert response.status_code == 400
        data = response.get_json()
        assert data["status"] == "error"
        assert data["message"] == "No user is currently logged in."

    @patch("app.auth.api.logout_user")
    def test_api_logout_exception_during_logout(self, mock_logout_user, client, auth, test_user, app) -> None:
        """Test API logout when logout_user raises an exception."""
        auth.login("testuser_1", "testpass")
        mock_logout_user.side_effect = Exception("Logout failed")

        response = client.post(url_for("auth.api_logout"))

        assert response.status_code == 500
        data = response.get_json()
        assert data["status"] == "error"
        assert data["message"] == "An error occurred during logout."

    def test_api_login_user_with_no_password_hash(self, client, app) -> None:
        """Test API login with user that has no password hash."""
        # Create a user without password hash
        user = User(username="nopass", email="nopass@example.com")
        user.password_hash = None

        with patch("app.auth.api.User.query") as mock_query:
            mock_query.filter_by.return_value.first.return_value = user

            response = client.post(
                url_for("auth.api_login"),
                json={"username": "nopass", "password": "anypass"},
            )

            assert response.status_code == 401
            data = response.get_json()
            assert data["status"] == "error"
            assert data["message"] == "Invalid username or password."

    def test_api_login_inactive_user(self, client, app) -> None:
        """Test API login with inactive user."""
        # Create an inactive user
        user = User(username="inactive", email="inactive@example.com")
        user.is_active = False
        user.set_password("testpass")

        with patch("app.auth.api.User.query") as mock_query:
            mock_query.filter_by.return_value.first.return_value = user

            response = client.post(
                url_for("auth.api_login"),
                json={"username": "inactive", "password": "testpass"},
            )

            assert response.status_code == 401
            data = response.get_json()
            assert data["status"] == "error"
            assert data["message"] == "Invalid username or password."

    @patch("app.auth.api.limiter.limit")
    def test_api_login_rate_limit_exceeded(self, mock_limit, client, app) -> None:
        """Test API login when rate limit is exceeded."""
        from flask_limiter import RateLimitExceeded

        mock_limit.side_effect = RateLimitExceeded()

        response = client.post(
            url_for("auth.api_login"),
            json={"username": "testuser_1", "password": "testpass"},
        )

        assert response.status_code == 429
        data = response.get_json()
        assert data["status"] == "error"
        assert data["message"] == "Too many login attempts. Please try again later."

    def test_api_login_remember_user(self, client, test_user, app) -> None:
        """Test that API login remembers the user."""
        with patch("app.auth.api.login_user") as mock_login:
            response = client.post(
                url_for("auth.api_login"),
                json={"username": "testuser_1", "password": "testpass"},
            )

            assert response.status_code == 200
            # Verify login_user was called with remember=True
            mock_login.assert_called_once()
            call_args = mock_login.call_args
            assert call_args[1]["remember"] is True

    def test_api_logout_logs_username(self, client, auth, test_user, app) -> None:
        """Test that API logout logs the username."""
        auth.login("testuser_1", "testpass")

        with patch("app.auth.api.current_app.logger") as mock_logger:
            response = client.post(url_for("auth.api_logout"))

            assert response.status_code == 200
            # Verify logging was called
            mock_logger.info.assert_called()
            log_call = mock_logger.info.call_args[0][0]
            assert "testuser_1" in log_call
            assert "logged out successfully" in log_call
