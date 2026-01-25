"""Error handling and custom error pages for the application."""

from __future__ import annotations

from typing import Tuple, Union, cast

from flask import Blueprint, Flask, Response, jsonify, render_template, request
from sqlalchemy.exc import PendingRollbackError
from werkzeug.exceptions import HTTPException

# Initialize Blueprint
bp = Blueprint("errors", __name__)


def init_app(app: Flask) -> None:
    """Initialize error handlers with the Flask application."""
    app.register_blueprint(bp)

    # Register global error handlers
    # Note: 401 is handled by Flask-Login's unauthorized_handler in app/extensions.py
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


def _clean_database_session() -> None:
    """Clean the database session to prevent PendingRollbackError during error rendering.

    This ensures that when error templates are rendered, they won't fail due to
    database session issues. The session is rolled back and all objects are expunged.
    """
    try:
        from sqlalchemy.exc import InvalidRequestError

        from app.extensions import db

        # Check if session exists and is in a bad state
        if hasattr(db, "session") and db.session:
            try:
                # Try to rollback if there's a pending rollback
                if db.session.is_active:
                    db.session.rollback()
            except (PendingRollbackError, InvalidRequestError):
                # Session is already in a bad state, force rollback
                try:
                    db.session.rollback()
                except Exception:  # nosec B110
                    pass  # Ignore errors during cleanup

            # Expunge all objects to clear the session
            try:
                db.session.expunge_all()
            except Exception:  # nosec B110
                pass  # Ignore errors during cleanup
    except Exception:  # nosec B110
        # If we can't clean the session, that's okay - we'll try to render anyway
        pass


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

    # Clean database session before rendering to prevent PendingRollbackError
    _clean_database_session()

    # For web requests, render an error template
    # Flask accepts (str, int) tuples as responses, which it converts to Response
    try:
        template_response = render_template("errors/error.html", message=message, status_code=status_code)
        return cast(tuple[Response, int], (template_response, status_code))
    except Exception as render_error:
        # If template rendering fails (e.g., due to database issues), return a simple HTML response
        from flask import current_app

        current_app.logger.error(f"Failed to render error template: {str(render_error)}", exc_info=True)
        # Return a simple HTML error page without template dependencies
        simple_html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{status_code} - Error</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
    <div style="text-align: center; padding: 50px;">
        <h1>{status_code}</h1>
        <h2>An Error Occurred</h2>
        <p>{message}</p>
        <p>We're sorry, but something went wrong. Please try again later.</p>
        <a href="/">Go to Homepage</a>
    </div>
</body>
</html>"""
        response = Response(simple_html, status=status_code, mimetype="text/html")
        return cast(Response, response)


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

    # Clean database session before creating error response
    _clean_database_session()

    # Determine error message based on exception type
    if isinstance(error, PendingRollbackError):
        error_message = "A database error occurred. Please try again."
    else:
        error_message = "An unexpected error occurred"

    return _create_error_response(error_message, 500)


@bp.app_errorhandler(HTTPException)
def handle_http_exception(error: HTTPException) -> Response | tuple[Response, int]:
    """Handle HTTP exceptions."""
    status_code = error.code if error.code is not None else 500
    return _create_error_response(error.description or "HTTP error occurred", status_code)
