"""Tests for CSRF protection in API routes."""

import pytest
from flask import url_for
from flask_wtf.csrf import generate_csrf


class TestCSRFProtection:
    """Test CSRF protection for API routes."""

    def test_api_get_request_no_csrf_required(self, client, test_user):
        """Test that GET requests to API don't require CSRF tokens."""
        with client.session_transaction() as sess:
            sess["_fresh"] = True
            sess["_user_id"] = str(test_user.id)

        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_api_post_request_without_csrf_fails(self, client, test_user):
        """Test that POST requests to API without CSRF token fail."""
        with client.session_transaction() as sess:
            sess["_fresh"] = True
            sess["_user_id"] = str(test_user.id)

        response = client.post(
            "/api/v1/expenses",
            json={"amount": 10.0, "date": "2024-01-01"},
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 403
        assert "csrf" in response.get_json()["error_type"]

    def test_api_post_request_with_csrf_succeeds(self, client, test_user):
        """Test that POST requests to API with CSRF token succeed."""
        with client.session_transaction() as sess:
            sess["_fresh"] = True
            sess["_user_id"] = str(test_user.id)

        # Get CSRF token from response headers
        response = client.get("/api/v1/health")
        csrf_token = response.headers.get("X-CSRFToken")

        response = client.post(
            "/api/v1/expenses",
            json={"amount": 10.0, "date": "2024-01-01"},
            headers={"Content-Type": "application/json", "X-CSRFToken": csrf_token},
        )
        assert response.status_code == 201

    def test_api_put_request_with_csrf_succeeds(self, client, test_user, test_expense):
        """Test that PUT requests to API with CSRF token succeed."""
        with client.session_transaction() as sess:
            sess["_fresh"] = True
            sess["_user_id"] = str(test_user.id)

        # Get CSRF token from response headers
        response = client.get("/api/v1/health")
        csrf_token = response.headers.get("X-CSRFToken")

        response = client.put(
            f"/api/v1/expenses/{test_expense.id}",
            json={"amount": 15.0, "date": "2024-01-01"},
            headers={"Content-Type": "application/json", "X-CSRFToken": csrf_token},
        )
        assert response.status_code == 200

    def test_api_delete_request_with_csrf_succeeds(self, client, test_user, test_expense):
        """Test that DELETE requests to API with CSRF token succeed."""
        with client.session_transaction() as sess:
            sess["_fresh"] = True
            sess["_user_id"] = str(test_user.id)

        # Get CSRF token from response headers
        response = client.get("/api/v1/health")
        csrf_token = response.headers.get("X-CSRFToken")

        response = client.delete(f"/api/v1/expenses/{test_expense.id}", headers={"X-CSRFToken": csrf_token})
        assert response.status_code == 204

    def test_api_request_with_invalid_csrf_fails(self, client, test_user):
        """Test that API requests with invalid CSRF token fail."""
        with client.session_transaction() as sess:
            sess["_fresh"] = True
            sess["_user_id"] = str(test_user.id)

        response = client.post(
            "/api/v1/expenses",
            json={"amount": 10.0, "date": "2024-01-01"},
            headers={"Content-Type": "application/json", "X-CSRFToken": "invalid-token"},
        )
        assert response.status_code == 403
        assert "csrf" in response.get_json()["error_type"]

    def test_csrf_token_in_response_headers(self, client, test_user):
        """Test that CSRF tokens are included in API response headers."""
        with client.session_transaction() as sess:
            sess["_fresh"] = True
            sess["_user_id"] = str(test_user.id)

        response = client.get("/api/v1/health")
        assert "X-CSRFToken" in response.headers
        assert response.headers["X-CSRFToken"] is not None
        assert len(response.headers["X-CSRFToken"]) > 0
