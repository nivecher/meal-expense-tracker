"""Error handling and custom error pages for the application."""

from __future__ import annotations

from typing import Tuple, Union

from flask import Blueprint, Flask, Response, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

# Initialize Blueprint
bp = Blueprint("errors", __name__)


def init_app(app: Flask) -> None:
    """Initialize error handlers with the Flask application."""
    app.register_blueprint(bp)

    # Register global error handlers
    app.register_error_handler(404, not_found_error)
    app.register_error_handler(500, internal_error)
    app.register_error_handler(Exception, handle_exception)


def _is_api_request() -> bool:
    """Check if the request is an API request."""
    return request.path.startswith("/api/") or request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _create_error_response(
    message: str, status_code: int, error_type: str = "error"
) -> Union[Response, Tuple[Response, int]]:
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
        return response

    # For web requests, render an error template
    return (render_template("errors/error.html", message=message, status_code=status_code), status_code)


@bp.app_errorhandler(404)
def not_found_error(error: HTTPException) -> Union[Response, Tuple[Response, int]]:
    """Handle 404 Not Found errors."""
    return _create_error_response("Page not found", 404)


@bp.app_errorhandler(500)
def internal_error(error: Exception) -> Union[Response, Tuple[Response, int]]:
    """Handle 500 Internal Server errors."""
    return _create_error_response("Internal server error", 500)


@bp.app_errorhandler(Exception)
def handle_exception(error: Exception) -> Union[Response, Tuple[Response, int]]:
    """Handle all unhandled exceptions."""
    # Log the error for debugging
    from flask import current_app

    current_app.logger.error(f"Unhandled exception: {str(error)}", exc_info=True)

    return _create_error_response("An unexpected error occurred", 500)


@bp.app_errorhandler(HTTPException)
def handle_http_exception(error: HTTPException) -> Union[Response, Tuple[Response, int]]:
    """Handle HTTP exceptions."""
    return _create_error_response(error.description or "HTTP error occurred", error.code)
