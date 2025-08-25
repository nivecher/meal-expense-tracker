"""Test script for login functionality."""

from flask import url_for


def test_login_success(client, test_user, app):
    """Test successful login."""
    with app.app_context():
        login_url = url_for("auth.login")
        # Ensure we're not logged in initially
        with client.session_transaction() as sess:
            # Check for any user authentication indicators
            assert not any(key in sess for key in ["user_id", "_user_id", "user", "userid"])

        # Make login request
        response = client.post(
            login_url,
            data={
                "username": test_user.username,
                "password": "testpass",  # From test_user fixture
                "csrf_token": "dummy_csrf_token",  # Matches our test client
            },
            follow_redirects=True,
        )

        # Check response status and content
        assert response.status_code == 200

        # Check if we're logged in by checking session for any user identifier
        with client.session_transaction() as sess:
            # Check for any common session keys that indicate a user is logged in
            assert any(
                key in sess for key in ["user_id", "_user_id", "user", "userid"]
            ), f"No user identifier found in session: {dict(sess)}"

            # If user_id is present, verify it matches the test user
            if "user_id" in sess:
                assert sess["user_id"] == str(test_user.id)
            elif "_user_id" in sess:
                assert sess["_user_id"] == str(test_user.id)

        # Check for success indicators in the response
        success_indicators = [
            b"Welcome back!",
            b"<title>Meal Expense Tracker</title>",
            b"Logout",
            b"Dashboard",
            b"My Profile",
        ]
        assert any(
            indicator in response.data for indicator in success_indicators
        ), "No success indicator found in response"


def test_login_invalid_username(client, test_user, app):
    """Test login with invalid username."""
    with app.app_context():
        login_url = url_for("auth.login")
        # Ensure we're not logged in initially
        with client.session_transaction() as sess:
            assert "user_id" not in sess

        response = client.post(
            login_url,
            data={"username": "nonexistent_user", "password": "testpass", "csrf_token": "dummy_csrf_token"},
            follow_redirects=True,
        )

        # Check response status and content
        assert response.status_code == 200
        assert b"Invalid username or password" in response.data

        # Ensure we're still not logged in
        with client.session_transaction() as sess:
            assert "user_id" not in sess


def test_login_invalid_password(client, test_user, app):
    """Test login with invalid password."""
    with app.app_context():
        login_url = url_for("auth.login")
        # Ensure we're not logged in initially
        with client.session_transaction() as sess:
            assert "user_id" not in sess

        response = client.post(
            login_url,
            data={"username": test_user.username, "password": "wrongpassword", "csrf_token": "dummy_csrf_token"},
            follow_redirects=True,
        )

        # Check response status and content
        assert response.status_code == 200
        assert b"Invalid username or password" in response.data

        # Ensure we're still not logged in
        with client.session_transaction() as sess:
            assert "user_id" not in sess


def test_login_required_redirect(client, app):
    """Test that login is required for protected routes."""
    with app.app_context():
        # Get the URL for the protected route
        protected_url = url_for("main.index")
        login_url = url_for("auth.login", _external=False)

        # Make a request to the protected route without being logged in
        response = client.get(protected_url, follow_redirects=False)

        # The application might return either:
        # 1. A 302 redirect to the login page (web flow)
        # 2. A 401 Unauthorized (API flow)
        if response.status_code == 302:
            # Web flow - should redirect to login page with next parameter
            assert response.location.startswith(login_url)
            # The next parameter might be URL-encoded / or a full URL
            assert "next=%2F" in response.location or "next=http://localhost/" in response.location

            # Follow the redirect to the login page
            response = client.get(response.location, follow_redirects=True)
            assert response.status_code == 200
            # Check for login page indicators instead of specific message
            assert b"Login" in response.data or b"Sign In" in response.data
        else:
            # API flow - should return 401 Unauthorized
            assert response.status_code == 401
            assert b"You must be logged in to access this resource" in response.data

        # Ensure we're not logged in
        with client.session_transaction() as sess:
            assert "user_id" not in sess
