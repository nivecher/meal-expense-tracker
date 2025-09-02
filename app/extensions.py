"""Application Flask extensions.

This module initializes and configures all Flask extensions used in the application.
"""

from typing import Any, Optional, Union, cast

from flask import Flask, request, url_for
from flask.wrappers import Response
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_session import Session
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

# Initialize CSRF protection (will be conditionally configured based on environment)
csrf = CSRFProtect()

# Initialize Flask-Migrate for database migrations
migrate = Migrate()

# Initialize Flask-Session
flask_session = Session()


def _log_session_config(app: Flask) -> None:
    """Log session configuration for debugging - Single responsibility."""
    session_type = app.config.get("SESSION_TYPE")

    if session_type == "dynamodb":
        app.logger.info("Session backend: dynamodb")
        table = app.config.get("SESSION_DYNAMODB_TABLE")
        region = app.config.get("SESSION_DYNAMODB_REGION")
        endpoint = app.config.get("SESSION_DYNAMODB_ENDPOINT_URL")
        key_prefix = app.config.get("SESSION_KEY_PREFIX", "")

        app.logger.info("  Table: %s, Region: %s, Endpoint: %s", table, region, endpoint or "AWS default")
        if key_prefix:
            app.logger.info("  Key prefix: %s", key_prefix)
    elif session_type is None:
        app.logger.info("Session backend: signed-cookies (Flask default)")
        app.logger.info("  Cookie name: %s", app.config.get("SESSION_COOKIE_NAME", "session"))
        app.logger.info("  Cookie secure: %s", app.config.get("SESSION_COOKIE_SECURE", False))
        app.logger.info("  Session lifetime: %s seconds", app.config.get("PERMANENT_SESSION_LIFETIME", 3600))
    else:
        app.logger.info("Session backend: %s", session_type)


def _validate_dynamodb_session_config(app: Flask) -> None:
    """Validate DynamoDB session configuration - Single responsibility."""
    if app.config.get("SESSION_TYPE") != "dynamodb":
        return

    _validate_required_configs(app)
    table_name = _validate_table_name_format(app)
    _test_dynamodb_connection(app, table_name)
    app.logger.info("DynamoDB session configuration validated successfully")


def _validate_required_configs(app: Flask) -> None:
    """Validate required DynamoDB session configuration parameters."""
    required_configs = {"SESSION_DYNAMODB_TABLE": "DynamoDB table name", "SESSION_DYNAMODB_REGION": "AWS region"}

    missing_configs = []
    for config_key, description in required_configs.items():
        if not app.config.get(config_key):
            missing_configs.append(f"{config_key} ({description})")

    if missing_configs:
        error_msg = f"Missing required DynamoDB session configuration: {', '.join(missing_configs)}"
        app.logger.error(error_msg)
        raise ValueError(error_msg)


def _validate_table_name_format(app: Flask) -> str:
    """Validate DynamoDB table name format."""
    table_name = app.config.get("SESSION_DYNAMODB_TABLE", "")
    if not table_name.replace("-", "").replace("_", "").isalnum():
        raise ValueError(
            f"Invalid DynamoDB table name: {table_name}. Must contain only alphanumeric characters, hyphens, and underscores."
        )
    return table_name


def _test_dynamodb_connection(app: Flask, table_name: str) -> None:
    """Test DynamoDB connection and permissions."""
    try:
        dynamodb_resource = app.config.get("SESSION_DYNAMODB")
        if dynamodb_resource:
            # Test connection by attempting to describe the table with retry logic
            table = dynamodb_resource.Table(table_name)
            table.load()  # This will raise an exception if table doesn't exist or connection fails
            app.logger.info("DynamoDB session table connection verified: %s", table_name)
            app.logger.info("Table status: %s", table.table_status)

            # Test basic table operations to ensure permissions are correct
            try:
                _test_dynamodb_permissions(table)
                app.logger.info("DynamoDB table permissions verified successfully")
            except Exception as perm_error:
                app.logger.warning("DynamoDB table permissions test failed: %s", str(perm_error))
                app.logger.warning("This may indicate insufficient IAM permissions")
        else:
            app.logger.warning("SESSION_DYNAMODB resource not configured - Flask-Session will create its own")
    except Exception as e:
        app.logger.error("DynamoDB session table verification failed: %s", str(e))
        # Don't fail startup - let Flask-Session handle the error gracefully
        app.logger.info("Note: Ensure the DynamoDB table '%s' exists and is accessible", table_name)
        app.logger.info("Check IAM permissions and network connectivity")


def _test_dynamodb_permissions(table) -> None:
    """Test DynamoDB table permissions."""
    try:
        # Try a simple scan operation to verify permissions
        table.scan(Limit=1)
        # Note: We can't access app logger from table object, so we'll log success at caller level
    except Exception as perm_error:
        # Note: We can't access app logger from table object, so we'll log warning at caller level
        raise perm_error


def _configure_csrf_handlers(app: Flask) -> None:
    """Configure CSRF protection and error handlers."""
    # Get the csrf_enabled status from app config
    csrf_enabled = app.config.get("WTF_CSRF_ENABLED", True)

    # Only configure CSRF handlers if CSRF is enabled
    if csrf_enabled:
        from flask_wtf.csrf import generate_csrf

        # Add CSRF token to response headers for API requests
        @app.after_request
        def add_csrf_headers(response: Response) -> Response:
            if request.path.startswith("/api/"):
                response.headers.set("X-CSRFToken", generate_csrf())
            return response

        # Configure CSRF validation for API routes
        # API routes should validate CSRF tokens from headers
        with app.app_context():
            from .api import bp as api_bp

            # Instead of exempting the entire API blueprint, we'll handle CSRF validation
            # in the API routes themselves using a custom decorator or middleware
            # This allows for more granular control over CSRF protection

        # Global CSRF error handler (only if CSRF is enabled)
        @app.errorhandler(CSRFError)
        def handle_csrf_error(e: CSRFError) -> Response:
            from flask import flash, jsonify, redirect

            # Log the CSRF error details for debugging
            app.logger.warning(f"CSRF error: {e} - Host: {request.host} - Path: {request.path}")

            message = "The CSRF session token is missing or invalid."

            # AJAX or API request
            if request.path.startswith("/api/") or request.headers.get("X-Requested-With") == "XMLHttpRequest":
                response = jsonify({"status": "error", "message": message, "error_type": "csrf_validation_failed"})
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
    migrate.init_app(app, db)

    # Initialize Flask-Session based on session type
    session_type = app.config.get("SESSION_TYPE")

    if session_type == "dynamodb":
        # Validate DynamoDB configuration
        _validate_dynamodb_session_config(app)
        flask_session.init_app(app)
    elif session_type is None:
        # Using Flask's default signed cookie sessions - no Flask-Session needed
        app.logger.info("Using Flask's default signed cookie sessions (ideal for Lambda)")
    else:
        # Other session types (filesystem, redis, etc.)
        flask_session.init_app(app)

    _log_session_config(app)

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

    # Check if we're running in AWS Lambda environment
    import os

    lambda_function_name = os.getenv("AWS_LAMBDA_FUNCTION_NAME")
    is_lambda = lambda_function_name is not None

    app.logger.info(f"Environment detection - AWS_LAMBDA_FUNCTION_NAME: {lambda_function_name}, is_lambda: {is_lambda}")

    # Configure CSRF protection
    app.logger.info("Enabling CSRF protection")
    csrf.init_app(app)
    app.config.update(
        WTF_CSRF_ENABLED=True,
        WTF_CSRF_CHECK_DEFAULT=True,
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
