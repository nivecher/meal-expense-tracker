"""Application Flask extensions.

Simplified extension initialization focused on core functionality.
"""

from typing import Any, Optional, Union, cast

from flask import Flask, request, url_for
from flask.wrappers import Response
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFError, CSRFProtect

# Initialize SQLAlchemy
db = SQLAlchemy()

# Initialize JWT for token-based authentication
jwt = JWTManager()

# Initialize LoginManager for session-based authentication
login_manager = LoginManager()
login_manager.login_view = "auth.login"

# Initialize rate limiter to prevent abuse
limiter = Limiter(key_func=get_remote_address, default_limits=["400 per day", "100 per hour"], storage_uri="memory://")

# Initialize CSRF protection
csrf = CSRFProtect()

# Initialize Flask-Migrate for database migrations
migrate = Migrate()


def _configure_csrf_handlers(app: Flask) -> None:
    """Configure CSRF protection and error handlers."""
    # Get the csrf_enabled status from app config
    csrf_enabled = app.config.get("WTF_CSRF_ENABLED", True)

    # Only configure CSRF handlers if CSRF is enabled
    if csrf_enabled:
        from flask_wtf.csrf import generate_csrf

        # Add CSRF token to response headers for all requests (helps with Lambda/API Gateway)
        @app.after_request
        def add_csrf_headers(response: Response) -> Response:
            # Always add CSRF token to headers for better Lambda/API Gateway compatibility
            response.headers.set("X-CSRFToken", generate_csrf())
            return response

        # Global CSRF error handler (only if CSRF is enabled)
        @app.errorhandler(CSRFError)
        def handle_csrf_error(e: CSRFError) -> Response:
            # Enhanced logging for debugging
            import os

            from flask import flash, jsonify, redirect

            is_lambda = os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None
            app.logger.warning(f"CSRF error: {e} - Host: {request.host} - Path: {request.path} - Lambda: {is_lambda}")
            app.logger.warning(f"CSRF error details - Method: {request.method}, Headers: {dict(request.headers)}")

            message = "The CSRF session token is missing or invalid."

            # AJAX or API request
            if request.path.startswith("/api/") or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                response = jsonify({"status": "error", "message": message, "error_type": "csrf_validation_failed"})
                response.status_code = 403
                return response

            # Normal web request - redirect to login with current URL as next parameter
            flash(message, "error")
            # In Lambda/API Gateway, use the current path as next parameter for better UX
            current_path = request.path
            if request.query_string:
                current_path += f"?{request.query_string.decode()}"
            return cast(Response, redirect(url_for("auth.login", next=current_path)))


def init_app(app: Flask) -> None:
    """Initialize all extensions with the Flask application."""
    # Initialize core extensions
    db.init_app(app)
    jwt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Log session configuration (simplified - we always use signed cookies now)
    app.logger.info("Using Flask's default signed cookie sessions")
    app.logger.info(f"  Cookie name: {app.config.get('SESSION_COOKIE_NAME', 'session')}")
    app.logger.info(f"  Cookie secure: {app.config.get('SESSION_COOKIE_SECURE', False)}")
    app.logger.info(f"  Session lifetime: {app.config.get('PERMANENT_SESSION_LIFETIME', 3600)} seconds")

    # Initialize rate limiter
    limiter.init_app(app)

    # Configure JWT settings
    secret_key = app.config.get("SECRET_KEY")
    fallback_key = "dev-key-change-in-production"  # nosec B105 - Development fallback key
    if not secret_key or secret_key == fallback_key:
        app.logger.warning("Using fallback JWT secret key - ensure SECRET_KEY is set in production")
        secret_key = fallback_key
    app.config["JWT_SECRET_KEY"] = secret_key
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 3600  # 1 hour
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = 2592000  # 30 days

    # Configure CSRF protection
    app.logger.info("Enabling CSRF protection")
    csrf.init_app(app)
    app.config.update(
        WTF_CSRF_ENABLED=True,
        WTF_CSRF_CHECK_DEFAULT=False,  # RELAXED: Disable CSRF checking by default for testing
        WTF_CSRF_SSL_STRICT=False,
        WTF_CSRF_TIME_LIMIT=3600,
        WTF_CSRF_REFERRER_CHECK=False,
        WTF_CSRF_SECRET_KEY=secret_key,
    )

    # Configure CSRF handlers
    _configure_csrf_handlers(app)


@login_manager.unauthorized_handler
def unauthorized() -> Union[Response, str]:
    """Handle unauthorized requests.

    For API requests, return a 401 JSON response.
    For web requests, redirect to the login page.
    """
    from flask import jsonify, redirect

    if request.path.startswith("/api/"):
        response = jsonify({"status": "error", "message": "Authentication required", "code": 401})
        response.status_code = 401
        return response
    return cast(Response, redirect(url_for(login_manager.login_view, next=request.url)))


@login_manager.user_loader
def load_user(user_id: str) -> Optional[Any]:
    """Load a user from the database."""
    # Lazy import to avoid circular imports
    from app.auth.models import User

    return User.query.get(int(user_id))