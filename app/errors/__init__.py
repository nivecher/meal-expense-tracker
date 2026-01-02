"""Error handling and custom error pages for the application."""

from __future__ import annotations

from typing import Tuple, Union, cast

from flask import Blueprint, Flask, Response, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

# Initialize Blueprint
bp = Blueprint("errors", __name__)


def init_app(app: Flask) -> None:
    """Initialize error handlers with the Flask application."""
    app.register_blueprint(bp)

    # Register global error handlers
    app.register_error_handler(401, unauthorized_error)
    app.register_error_handler(404, not_found_error)
    app.register_error_handler(500, internal_error)
    app.register_error_handler(Exception, handle_exception)


def _is_api_request() -> bool:
    """Check if the request is an API request."""
    accept_header = request.headers.get("Accept", "")
    x_requested_with = request.headers.get("X-Requested-With", "")

    # Check multiple indicators that this is an API request
    is_api = (
        request.path.startswith("/api/") or x_requested_with == "XMLHttpRequest" or "application/json" in accept_header
    )

    return is_api


def _create_error_response(
    message: str, status_code: int, error_type: str = "error"
) -> Response | tuple[Response, int]:
    """Create a standardized error response.

    Args:
        message: The error message
        status_code: The HTTP status code
        error_type: The type of error (error, warning, info)

    Returns:
        JSON response for API requests, rendered template for web requests
    """
    if _is_api_request():
        response = jsonify({"status": error_type, "message": message, "code": status_code})
        response.status_code = status_code
        return cast(Response, response)

    # For web requests, render an error template
    # Flask accepts (str, int) tuples as responses, which it converts to Response
    template_response = render_template("errors/error.html", message=message, status_code=status_code)
    return cast(tuple[Response, int], (template_response, status_code))


@bp.app_errorhandler(401)
def unauthorized_error(error: HTTPException) -> Response | tuple[Response, int]:
    """Handle 401 Unauthorized errors."""
    # Check if this is an API request - if so, return JSON
    if _is_api_request():
        response = jsonify({"status": "error", "message": "Authentication required", "code": 401})
        response.status_code = 401
        response.headers["Content-Type"] = "application/json"
        return cast(Response, response)

    # For web requests, render an error template
    return _create_error_response("Authentication required", 401)


@bp.app_errorhandler(404)
def not_found_error(error: HTTPException) -> Response | tuple[Response, int]:
    """Handle 404 Not Found errors."""
    # Check if this is an API request - if so, return JSON
    # This ensures routes that explicitly return 404 JSON responses are handled correctly
    if _is_api_request():
        # Return JSON response matching the format expected by frontend
        response = jsonify({"success": False, "message": "Resource not found", "code": 404})
        response.status_code = 404
        response.headers["Content-Type"] = "application/json"
        return cast(Response, response)

    # For web requests, render an error template
    return _create_error_response("Page not found", 404)


@bp.app_errorhandler(500)
def internal_error(error: Exception) -> Response | tuple[Response, int]:
    """Handle 500 Internal Server errors."""
    return _create_error_response("Internal server error", 500)


@bp.app_errorhandler(Exception)
def handle_exception(error: Exception) -> Response | tuple[Response, int]:
    """Handle all unhandled exceptions."""
    # Log the error for debugging
    from flask import current_app

    current_app.logger.error(f"Unhandled exception: {str(error)}", exc_info=True)

    return _create_error_response("An unexpected error occurred", 500)


@bp.app_errorhandler(HTTPException)
def handle_http_exception(error: HTTPException) -> Response | tuple[Response, int]:
    """Handle HTTP exceptions."""
    status_code = error.code if error.code is not None else 500
    return _create_error_response(error.description or "HTTP error occurred", status_code)
