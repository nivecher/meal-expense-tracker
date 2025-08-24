"""Application Flask extensions.

This module initializes and configures all Flask extensions used in the application.
"""

from typing import Any, Optional, cast

import boto3
from flask import Flask, request, url_for
from flask.typing import ResponseReturnValue
from flask.wrappers import Response
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFError, CSRFProtect, generate_csrf

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

# Initialize Flask-Session
flask_session = Session()


def _configure_dynamodb_session(app: Flask) -> None:
    """Configure DynamoDB session storage for Flask-Session."""
    if app.config.get("SESSION_TYPE") != "dynamodb":
        return

    try:
        table_name = app.config.get("SESSION_DYNAMODB_TABLE")
        region = app.config.get("SESSION_DYNAMODB_REGION")
        endpoint_url = app.config.get("SESSION_DYNAMODB_ENDPOINT_URL")

        app.logger.info("DynamoDB Session Configuration:")
        app.logger.info("  Table: %s", table_name)
        app.logger.info("  Region: %s", region)
        app.logger.info("  Endpoint URL: %s", endpoint_url or "None (AWS default)")

        # Test AWS credentials and connectivity
        session = boto3.Session()
        app.logger.info("  AWS Profile: %s", session.profile_name or "default")
        app.logger.info("  AWS Region from session: %s", session.region_name or "not set")

    except Exception as e:
        app.logger.error("Error configuring DynamoDB session: %s", str(e))
        app.logger.exception("Full exception details:")


def _configure_session_fallback(app: Flask) -> None:
    """Configure fallback session storage if DynamoDB fails."""
    if app.config.get("SESSION_TYPE") == "dynamodb":
        app.logger.warning("Falling back to filesystem sessions due to DynamoDB error")
        app.config["SESSION_TYPE"] = "filesystem"
        # Use tempfile.gettempdir() for secure temporary directory
        import tempfile

        app.config["SESSION_FILE_DIR"] = tempfile.mkdtemp(prefix="flask_session_")
        app.config["SESSION_FILE_THRESHOLD"] = 100

        try:
            flask_session.init_app(app)
            app.logger.info("Successfully fell back to filesystem sessions")
        except Exception as fallback_error:
            app.logger.error("Fallback to filesystem sessions also failed: %s", str(fallback_error))
            raise


def _configure_csrf_handlers(app: Flask) -> None:
    """Configure CSRF protection and error handlers."""

    # Add CSRF token to response headers for API requests
    @app.after_request
    def add_csrf_headers(response: Response) -> Response:
        if request.path.startswith("/api/"):
            response.headers.set("X-CSRFToken", generate_csrf())
        return response

    # Exempt API routes from CSRF protection
    with app.app_context():
        from .api import bp as api_bp

        csrf.exempt(api_bp)

    # Global CSRF error handler
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e: CSRFError) -> Response:
        from flask import flash, jsonify, redirect

        message = str(getattr(e, "description", None) or getattr(e, "reason", None) or "CSRF validation failed")

        # AJAX or API request
        if request.path.startswith("/api/") or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            response = jsonify({"success": False, "message": message})
            response.status_code = 403
            return response

        # Normal web request
        flash(message, "error")
        return cast(Response, redirect(str(request.referrer) or url_for("main.index")))


def init_app(app: Flask) -> None:
    """Initialize all extensions with the Flask application."""
    # Initialize core extensions
    db.init_app(app)
    jwt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    # Configure DynamoDB session if needed
    _configure_dynamodb_session(app)

    # Initialize Flask-Session with error handling
    try:
        flask_session.init_app(app)
        app.logger.info("Flask-Session initialized successfully")
    except Exception as e:
        app.logger.error("Failed to initialize Flask-Session: %s", str(e))
        _configure_session_fallback(app)

    # Initialize rate limiter
    limiter.init_app(app)

    # Configure JWT settings
    secret_key = app.config.get("SECRET_KEY")
    if not secret_key or secret_key == "dev-key-change-in-production":
        app.logger.warning("Using fallback JWT secret key - ensure SECRET_KEY is set in production")
        secret_key = "dev-key-change-in-production"
    app.config["JWT_SECRET_KEY"] = secret_key
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 3600  # 1 hour
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = 2592000  # 30 days

    # Configure CSRF protection
    app.config.update(
        WTF_CSRF_CHECK_DEFAULT=True,
        WTF_CSRF_SSL_STRICT=True,
        WTF_CSRF_TIME_LIMIT=3600,
    )

    # Configure CSRF handlers
    _configure_csrf_handlers(app)


@login_manager.unauthorized_handler
def unauthorized() -> ResponseReturnValue:
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
