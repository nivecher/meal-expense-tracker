"""Tests for Lambda handler error response handling."""

import json
import os
from unittest.mock import Mock, patch

import pytest

from lambda_handler import _create_error_response, _is_api_request_from_event


class TestLambdaErrorHandling:
    """Test Lambda handler error response creation."""

    def test_is_api_request_from_path(self) -> None:
        """Test API request detection from path."""
        event = {"rawPath": "/api/users", "headers": {}}
        assert _is_api_request_from_event(event) is True

    def test_is_api_request_from_accept_header(self) -> None:
        """Test API request detection from Accept header."""
        event = {"rawPath": "/users", "headers": {"Accept": "application/json"}}
        assert _is_api_request_from_event(event) is True

    def test_is_api_request_from_x_requested_with(self) -> None:
        """Test API request detection from X-Requested-With header."""
        event = {"rawPath": "/users", "headers": {"X-Requested-With": "XMLHttpRequest"}}
        assert _is_api_request_from_event(event) is True

    def test_is_api_request_web_request(self) -> None:
        """Test web request detection (not API)."""
        event = {"rawPath": "/users", "headers": {"Accept": "text/html"}}
        assert _is_api_request_from_event(event) is False

    def test_create_error_response_api_json(self) -> None:
        """Test error response creation for API requests returns JSON."""
        event = {"rawPath": "/api/test", "headers": {}}
        response = _create_error_response(
            status_code=500,
            error_message="Internal server error",
            error_type="ProgrammingError",
            request_id="test-request-id",
            event=event,
        )

        assert response["statusCode"] == 500
        assert response["headers"]["Content-Type"] == "application/json"
        body = json.loads(response["body"])
        assert body["error"] == "Internal server error"
        assert body["error_type"] == "ProgrammingError"
        assert body["request_id"] == "test-request-id"
        assert "traceback" not in body  # No traceback in default (prod) mode

    def test_create_error_response_api_json_with_traceback_non_prod(self) -> None:
        """Test error response includes traceback in non-production for API requests."""
        event = {"rawPath": "/api/test", "headers": {}}
        with patch.dict(os.environ, {"ENVIRONMENT": "dev"}):
            response = _create_error_response(
                status_code=500,
                error_message="Internal server error",
                error_type="ProgrammingError",
                traceback_str="Traceback (most recent call last):\n  File test.py",
                request_id="test-request-id",
                event=event,
            )

            assert response["statusCode"] == 500
            assert response["headers"]["Content-Type"] == "application/json"
            body = json.loads(response["body"])
            assert "traceback" in body
            assert isinstance(body["traceback"], list)

    def test_create_error_response_web_html(self) -> None:
        """Test error response creation for web requests returns HTML."""
        event = {"rawPath": "/users", "headers": {"Accept": "text/html"}}
        response = _create_error_response(
            status_code=500,
            error_message="Internal server error",
            error_type="ProgrammingError",
            request_id="test-request-id",
            event=event,
        )

        assert response["statusCode"] == 500
        assert response["headers"]["Content-Type"] == "text/html; charset=utf-8"
        assert "<!DOCTYPE html>" in response["body"]
        assert "500" in response["body"]
        assert "Internal server error" in response["body"]
        assert "Go to Homepage" in response["body"]
        # Should not include traceback or error_type in HTML
        assert "traceback" not in response["body"].lower()
        assert "ProgrammingError" not in response["body"]

    def test_create_error_response_web_html_no_traceback(self) -> None:
        """Test web HTML responses never include traceback even in non-prod."""
        event = {"rawPath": "/users", "headers": {"Accept": "text/html"}}
        with patch.dict(os.environ, {"ENVIRONMENT": "dev"}):
            response = _create_error_response(
                status_code=500,
                error_message="Internal server error",
                error_type="ProgrammingError",
                traceback_str="Traceback (most recent call last):\n  File test.py",
                request_id="test-request-id",
                event=event,
            )

            assert response["statusCode"] == 500
            assert response["headers"]["Content-Type"] == "text/html; charset=utf-8"
            # Traceback should not appear in HTML response
            assert "Traceback" not in response["body"]
            assert "test.py" not in response["body"]

    def test_create_error_response_no_event_defaults_to_json(self) -> None:
        """Test error response defaults to JSON when event is not provided."""
        response = _create_error_response(
            status_code=500,
            error_message="Internal server error",
            request_id="test-request-id",
        )

        assert response["statusCode"] == 500
        assert response["headers"]["Content-Type"] == "application/json"
        body = json.loads(response["body"])
        assert body["error"] == "Internal server error"

    def test_create_error_response_case_insensitive_headers(self) -> None:
        """Test API request detection handles case-insensitive headers."""
        # Test lowercase headers
        event1 = {"rawPath": "/test", "headers": {"accept": "application/json"}}
        assert _is_api_request_from_event(event1) is True

        # Test mixed case headers
        event2 = {"rawPath": "/test", "headers": {"Accept": "application/json"}}
        assert _is_api_request_from_event(event2) is True

        # Test X-Requested-With in different cases
        event3 = {"rawPath": "/test", "headers": {"x-requested-with": "XMLHttpRequest"}}
        assert _is_api_request_from_event(event3) is True

        event4 = {"rawPath": "/test", "headers": {"X-Requested-With": "XMLHttpRequest"}}
        assert _is_api_request_from_event(event4) is True
