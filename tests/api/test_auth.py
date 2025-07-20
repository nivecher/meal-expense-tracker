"""Test authentication endpoints and functionality."""

from bs4 import BeautifulSoup
from flask import url_for
from flask.testing import FlaskClient


def test_login_logout(client: FlaskClient, test_user):
    """Test user login and logout flow."""
    # Test accessing login page
    login_url = url_for("auth.login")
    response = client.get(login_url)
    assert response.status_code == 200
    assert b"Login" in response.data

    # Extract CSRF token from the form's hidden input
    soup = BeautifulSoup(response.data, "html.parser")
    csrf_input = soup.find("input", {"name": "csrf_token"})

    # If we can't find the CSRF token, check if CSRF is disabled in test config
    csrf_token = ""
    if csrf_input:
        csrf_token = csrf_input.get("value", "")

    # Test successful login with correct credentials
    login_data = {
        "username": "testuser_1",  # Match the test user from conftest.py
        "password": "testpass",  # Match the test password from conftest.py
        "remember_me": "y",  # 'y' is the value for checked checkbox
        "csrf_token": csrf_token,  # Include CSRF token if it exists
        "submit": "Sign In",
    }

    # Submit login form
    response = client.post(
        login_url,
        data=login_data,
        follow_redirects=True,
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "text/html"},
    )

    # Verify successful login (should redirect to home page)
    assert response.status_code == 200
    assert b"Meal Expense Tracker" in response.data  # Check for home page content

    # Test accessing a protected page
    profile_url = url_for("auth.profile")
    response = client.get(profile_url, follow_redirects=True)
    assert response.status_code == 200
    assert b"<h1>Profile</h1>" in response.data  # Verify we can access profile

    # Test logout
    logout_url = url_for("auth.logout")
    response = client.get(logout_url, follow_redirects=True)
    assert response.status_code == 200
    assert b"You have been logged out" in response.data

    # Verify we can't access protected pages after logout
    response = client.get(profile_url, follow_redirects=True)
    assert response.status_code == 200
    # Should redirect to login page
    assert any(msg in response.data for msg in [b"Please log in to access this page", b"Login"])

    # Test accessing protected page while logged in
    response = client.get(profile_url, follow_redirects=True)
    assert response.status_code == 200
    assert b"Profile" in response.data

    # Test logout
    response = client.get(logout_url, follow_redirects=True)
    assert response.status_code == 200
    assert b"You have been logged out" in response.data

    # Verify we're logged out by checking profile access
    response = client.get(profile_url, follow_redirects=True)
    assert response.status_code == 200
    assert b"Please log in to access this page" in response.data


def test_login_invalid_credentials(client: FlaskClient, test_user):
    """Test login with invalid credentials."""
    login_url = url_for("auth.login")

    # Test invalid username
    response = client.post(
        login_url,
        data={"username": "nonexistent", "password": "wrongpassword", "submit": "Sign In"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data

    # Test invalid password
    response = client.post(
        login_url,
        data={"username": "testuser", "password": "wrongpassword", "submit": "Sign In"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_access_protected_route_unauthenticated(client: FlaskClient):
    """Test accessing protected route without authentication."""
    profile_url = url_for("auth.profile")
    response = client.get(profile_url, follow_redirects=True)
    assert response.status_code == 200
    assert b"Please log in to access this page" in response.data


def test_health_check(client: FlaskClient):
    """Test health check endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json["status"] == "healthy"
