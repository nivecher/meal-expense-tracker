from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

from flask import Blueprint, current_app, jsonify, request
from flask_wtf.csrf import validate_csrf

bp = Blueprint("api", __name__)

F = TypeVar("F", bound=Callable[..., Any])


def validate_api_csrf(f: F) -> F:
    """Decorator to validate CSRF tokens for API routes.

    This decorator checks for CSRF tokens in the X-CSRFToken header
    and validates them against the session token.
    """

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        # Skip CSRF validation if CSRF is disabled
        if not current_app.config.get("WTF_CSRF_ENABLED", True):
            return f(*args, **kwargs)

        # Skip CSRF validation for GET requests
        if request.method == "GET":
            return f(*args, **kwargs)

        # Get CSRF token from header
        csrf_token = request.headers.get("X-CSRFToken")

        if not csrf_token:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "CSRF token is missing from request headers",
                        "error_type": "csrf_missing",
                    }
                ),
                403,
            )

        try:
            # Validate the CSRF token
            validate_csrf(csrf_token)
        except Exception as e:
            current_app.logger.warning(f"CSRF validation failed: {str(e)}")
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "CSRF token is invalid or expired",
                        "error_type": "csrf_invalid",
                    }
                ),
                403,
            )

        return f(*args, **kwargs)

    return cast(F, decorated_function)


# Import routes to register them with the blueprint
from . import routes  # noqa: E402, F401
