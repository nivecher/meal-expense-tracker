"""Application Flask extensions.

This module initializes and configures all Flask extensions used in the application.
"""

import logging
import os
from typing import Any, Optional, Union, cast

from flask import (
    Flask,
    current_app,
    flash,
    jsonify,
    redirect,
    request,
    session,
    url_for,
)
from flask.wrappers import Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFError, CSRFProtect, generate_csrf

logger = logging.getLogger(__name__)

# Development fallback secret key (only used when SECRET_KEY env var is not set)
# This is safe because production environments must set SECRET_KEY
_DEV_FALLBACK_SECRET = "dev-key-change-in-production"  # nosec B105

# Initialize SQLAlchemy
db = SQLAlchemy()


# Initialize LoginManager for session-based authentication
login_manager = LoginManager()
login_manager.login_view = "auth.login"

# Initialize rate limiter to prevent abuse
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["400 per day", "100 per hour"],
    storage_uri="memory://",
)

# Initialize CSRF protection (will be conditionally configured based on environment)
csrf = CSRFProtect()

# Initialize Flask-Migrate for database migrations
migrate = Migrate()


def _log_session_config(app: Flask) -> None:
    """Log session configuration for debugging - Single responsibility."""
    app.logger.info("Session backend: signed-cookies (Flask default)")
    app.logger.info("  Cookie name: %s", app.config.get("SESSION_COOKIE_NAME", "session"))
    app.logger.info("  Cookie secure: %s", app.config.get("SESSION_COOKIE_SECURE", False))
    app.logger.info("  Cookie httponly: %s", app.config.get("SESSION_COOKIE_HTTPONLY", True))
    app.logger.info("  Cookie samesite: %s", app.config.get("SESSION_COOKIE_SAMESITE", "Lax"))
    app.logger.info("  Session lifetime: %s seconds", app.config.get("PERMANENT_SESSION_LIFETIME", 3600))


def _configure_csrf_handlers(app: Flask) -> None:
    """Configure CSRF protection and error handlers."""
    # Get the csrf_enabled status from app config
    csrf_enabled = app.config.get("WTF_CSRF_ENABLED", True)

    # Only configure CSRF handlers if CSRF is enabled
    if csrf_enabled:
        # Add CSRF token to response headers for all requests (helps with Lambda/API Gateway)
        @app.after_request
        def add_csrf_headers(response: Response) -> Response:
            # Always add CSRF token to headers for better Lambda/API Gateway compatibility
            response.headers.set("X-CSRFToken", generate_csrf())
            return response

        # Configure CSRF validation for API routes
        # API routes should validate CSRF tokens from headers
        with app.app_context():
            pass

            # Instead of exempting the entire API blueprint, we'll handle CSRF validation
            # in the API routes themselves using a custom decorator or middleware
            # This allows for more granular control over CSRF protection

        # Global CSRF error handler (only if CSRF is enabled)
        @app.errorhandler(CSRFError)
        def handle_csrf_error(e: CSRFError) -> Response:
            # Enhanced logging for Lambda/API Gateway debugging
            is_lambda = os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None
            app.logger.warning(f"CSRF error: {e} - Host: {request.host} - Path: {request.path} - Lambda: {is_lambda}")
            app.logger.warning(f"CSRF error details - Method: {request.method}, Headers: {dict(request.headers)}")
            app.logger.warning(
                f"CSRF error - Session: {dict(session) if hasattr(session, '__dict__') else 'No session'}"
            )

            message = "The CSRF session token is missing or invalid."

            # AJAX or API request
            if request.path.startswith("/api/") or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                response = jsonify({"status": "error", "message": message, "error_type": "csrf_validation_failed"})
                response.status_code = 403
                return cast(Response, response)

            # Normal web request - redirect to login with current URL as next parameter
            flash(message, "error")
            # In Lambda/API Gateway, use the current path as next parameter for better UX
            current_path = request.path
            if request.query_string:
                current_path += f"?{request.query_string.decode()}"
            return cast(Response, redirect(url_for("auth.login", next=current_path)))


def _configure_migration_directory(app: Flask) -> None:
    """Configure Flask-Migrate with Lambda-aware directory handling."""
    # In Lambda, we need to handle the read-only filesystem
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        # Lambda environment - use environment variable if set, otherwise /var/task/migrations
        migration_dir = os.environ.get("MIGRATIONS_DIR")
        if not migration_dir:
            migration_dir = "/var/task/migrations"
        logger.info(f"Lambda environment detected, using migration directory: {migration_dir}")
    else:
        # Local environment - use standard location
        migration_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "migrations")

    migrate.init_app(app, db, directory=migration_dir)


def _configure_session_backend(app: Flask) -> None:
    """Configure session backend and log configuration."""
    # Use Flask's built-in signed cookie sessions - no external session backend needed
    app.logger.info("Using Flask's default signed cookie sessions (ideal for all environments)")

    _log_session_config(app)


def init_app(app: Flask) -> None:
    """Initialize all extensions with the Flask application."""
    # Initialize core extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Configure components
    _configure_migration_directory(app)
    _configure_session_backend(app)

    # Initialize rate limiter
    limiter.init_app(app)

    # Configure CSRF secret key (same as Flask SECRET_KEY for consistency)
    secret_key = app.config.get("SECRET_KEY")
    if not secret_key:
        # Development fallback - production must set SECRET_KEY environment variable
        app.logger.warning("Using fallback CSRF secret key - ensure SECRET_KEY is set in production")
        # Get from environment first, fallback to dev key only if not set
        env_secret = os.getenv("SECRET_KEY")
        secret_key = env_secret if env_secret else _DEV_FALLBACK_SECRET

    # Check if we're running in AWS Lambda environment
    lambda_function_name = os.getenv("AWS_LAMBDA_FUNCTION_NAME")
    is_lambda = lambda_function_name is not None

    app.logger.info(f"Environment detection - AWS_LAMBDA_FUNCTION_NAME: {lambda_function_name}, is_lambda: {is_lambda}")

    # Configure CSRF protection
    app.logger.info("Enabling CSRF protection")
    # Set CSRF configuration BEFORE initializing the extension
    app.config.update(
        WTF_CSRF_ENABLED=True,
        WTF_CSRF_CHECK_DEFAULT=False,  # RELAXED: Disable CSRF checking by default for testing
        WTF_CSRF_SSL_STRICT=False,
        WTF_CSRF_TIME_LIMIT=3600,
        WTF_CSRF_REFERRER_CHECK=False,
    )
    # Set secret key separately to allow proper suppression comment
    app.config["WTF_CSRF_SECRET_KEY"] = secret_key  # nosec B105
    # Initialize CSRF protection AFTER configuration is set
    csrf.init_app(app)

    # Configure CSRF handlers
    _configure_csrf_handlers(app)


def _is_lambda_environment() -> bool:
    """Check if running in AWS Lambda environment."""
    server_name = current_app.config.get("SERVER_NAME")
    return bool(server_name and server_name != "localhost:5000" and "localhost" not in server_name)


def _fix_api_gateway_url(url: str, server_name: str) -> str:
    """Replace API Gateway domain with CloudFront domain in URL."""
    if not url:
        return url

    # Check for various API Gateway domain patterns
    api_patterns = ["execute-api", "amazonaws.com", "api.dev.nivecher.com"]
    if not any(pattern in url for pattern in api_patterns):
        return url

    if "://" in url:
        protocol, rest = url.split("://", 1)
        if "/" in rest:
            host, path = rest.split("/", 1)
            return f"{protocol}://{server_name}/{path}"
        else:
            return f"{protocol}://{server_name}"

    return url


def _handle_api_unauthorized() -> Response:
    """Handle unauthorized API requests."""
    response = jsonify({"status": "error", "message": "Authentication required", "code": 401})
    response.status_code = 401
    return cast(Response, response)


def _handle_web_unauthorized() -> Response:
    """Handle unauthorized web requests with fixed URLs for Lambda."""
    next_url = request.url
    server_name = current_app.config.get("SERVER_NAME")

    # Fix URLs in Lambda environment
    if _is_lambda_environment() and server_name:
        next_url = _fix_api_gateway_url(next_url, server_name)

    # Generate login URL with fixed next parameter
    login_url = url_for(login_manager.login_view, next=next_url, _external=True)

    # Fix login URL if needed
    if _is_lambda_environment() and server_name:
        login_url = _fix_api_gateway_url(login_url, server_name)

    return cast(Response, redirect(login_url))


@login_manager.unauthorized_handler
def unauthorized() -> Response | str:
    """Handle unauthorized requests.

    For API requests, return a 401 JSON response.
    For web requests, redirect to the login page.
    """
    if request.path.startswith("/api/"):
        return _handle_api_unauthorized()

    return _handle_web_unauthorized()


@login_manager.user_loader
def load_user(user_id: str) -> Any | None:
    """Load a user from the database.

    Only returns active users. Inactive users are treated as non-existent
    to prevent access after account deactivation.
    """
    # Lazy import to avoid circular imports
    from app.auth.models import User

    try:
        if not user_id or not user_id.isdigit():
            return None

        user_id_int = int(user_id)
        user = db.session.get(User, user_id_int)

        # Only return the user if they exist and are active
        if user and user.is_active:
            return user

        return None
    except (ValueError, TypeError):
        return None
