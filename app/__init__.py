import logging
from typing import Optional, Union

from flask import Flask, jsonify, request
from flask_cors import CORS

from config import get_config

from .extensions import jwt

# Initialize logger
logger = logging.getLogger(__name__)

__all__ = ["create_app", "jwt"]


def create_app(config_name: Optional[str] = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        config_name: This parameter is kept for backward compatibility but not used.
                    The configuration is determined by FLASK_ENV environment variable.
    Returns:
        Flask: The configured Flask application instance.
    """
    # Get the appropriate configuration based on FLASK_ENV
    config = get_config()

    # Create the Flask application
    app = Flask(__name__)

    # Load configuration from config object
    app.config.from_object(config)

    # Configure app components
    _configure_request_handlers(app)
    _configure_app_settings(app)
    _configure_logging(app)
    _initialize_components(app)
    _initialize_admin_and_cli(app)

    return app


def _configure_request_handlers(app: Flask) -> None:
    """Configure request and response handlers."""

    # Configure static file headers
    @app.after_request
    def add_static_headers(response):
        """Add cache-control and other headers for static files."""
        if response.headers.get("Content-Type"):
            content_type = _fix_content_type_headers(response)
            _set_cache_control_headers(response, content_type)
            _set_security_headers(response, content_type)
        return response

    # Register service worker route with proper headers
    @app.route("/service-worker.js")
    def service_worker():
        response = app.send_static_file("js/service-worker.js")
        response.headers["Service-Worker-Allowed"] = "/"
        response.headers["Content-Type"] = "application/javascript"
        response.headers["Cache-Control"] = "no-cache, max-age=0"
        return response


def _fix_content_type_headers(response) -> str:
    """Fix content-type headers for different file types."""
    content_type = response.headers.get("Content-Type")

    # Fix CSS and JavaScript file content-type headers
    if request.path and any(request.path.endswith(ext) for ext in [".css", ".js"]):
        mime_type_map = {
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
        }
        for ext, mime_type in mime_type_map.items():
            if request.path.endswith(ext):
                response.headers["Content-Type"] = mime_type
                return mime_type

    # Fix font file content-type headers (no charset for fonts)
    elif request.path and any(request.path.endswith(ext) for ext in [".woff2", ".woff", ".ttf", ".eot", ".otf"]):
        font_type_map = {
            ".woff2": "font/woff2",
            ".woff": "font/woff",
            ".ttf": "font/ttf",
            ".eot": "font/eot",
            ".otf": "font/otf",
        }
        for ext, mime_type in font_type_map.items():
            if request.path.endswith(ext):
                response.headers["Content-Type"] = mime_type
                return mime_type

    # Fix charset for HTML/text responses - ensure UTF-8 is properly set
    elif "text/" in content_type or "html" in content_type:
        base_content_type = content_type.split(";")[0].strip()
        if "html" in base_content_type or "text/" in base_content_type:
            response.headers["Content-Type"] = f"{base_content_type}; charset=utf-8"
            return response.headers["Content-Type"]

    return content_type


def _set_cache_control_headers(response, content_type: str) -> None:
    """Set appropriate cache control headers based on content type."""
    if any(ext in content_type for ext in ["css", "javascript", "image", "font/"]):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"  # 1 year, immutable
    elif "html" in content_type:
        response.headers["Cache-Control"] = "no-cache, max-age=0"  # Prevent caching of HTML
    else:
        response.headers["Cache-Control"] = "public, max-age=3600"  # 1 hour


def _set_security_headers(response, content_type: str) -> None:
    """Set security headers for responses."""
    # Essential security headers - always set for all responses
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Content Security Policy (replaces X-Frame-Options with better support)
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://code.jquery.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://maps.googleapis.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://maps.googleapis.com https://cdn.jsdelivr.net; "
        "frame-ancestors 'none';"
    )
    response.headers["Content-Security-Policy"] = csp

    # Additional security headers
    response.headers["Permissions-Policy"] = "geolocation=(self), microphone=(), camera=()"

    # Remove deprecated headers if they exist
    response.headers.pop("Pragma", None)
    response.headers.pop("Expires", None)  # Remove deprecated Expires header

    # Only add CSP for HTML responses to avoid unnecessary headers on static resources
    if content_type and "html" in content_type:
        response.headers["Content-Security-Policy"] = (
            "frame-ancestors 'none'; default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://code.jquery.com https://maps.googleapis.com https://maps.gstatic.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com https://cdnjs.cloudflare.com; img-src 'self' data: https: blob:; connect-src 'self' https://places.googleapis.com https://maps.googleapis.com https://cdn.jsdelivr.net; object-src 'none'; base-uri 'self';"
        )


def _configure_app_settings(app: Flask) -> None:
    """Configure basic application settings and validation."""
    # Ensure required config values are set
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise ValueError("SQLALCHEMY_DATABASE_URI is not configured")

    # Set default SQLAlchemy config if not set
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)


def _configure_logging(app: Flask) -> None:
    """Configure application logging."""
    # Configure logging
    log_level = logging.DEBUG if app.debug else logging.INFO
    logger.setLevel(log_level)

    # Log app configuration
    logger.debug("Application configuration:")
    logger.debug(f"- ENV: {app.config.get('ENV', 'Not set')}")
    logger.debug(f"- DEBUG: {app.debug}")
    logger.debug(f"- DATABASE_URI: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')}")


def _initialize_components(app: Flask) -> None:
    """Initialize core application components."""
    # Initialize all extensions
    from .database import init_database
    from .extensions import init_app as init_extensions

    # Initialize extensions
    init_extensions(app)

    # Initialize the database
    init_database(app)

    # Configure JWT settings
    _configure_jwt_handlers(app)

    # Register blueprints
    _register_blueprints(app)

    # Register error handlers
    from .errors import init_app as init_errors

    init_errors(app)
    logger.debug("Registered error handlers")

    # Initialize template filters
    from .template_filters import init_app as init_template_filters
    from .utils.filters import init_app as init_utils_filters

    init_template_filters(app)
    init_utils_filters(app)
    logger.debug("Template filters initialized")

    # Initialize context processors
    from .utils.context_processors import inject_user_context

    app.context_processor(inject_user_context)
    logger.debug("Context processors initialized")

    # Configure CORS
    _configure_cors(app)

    # Log registered routes
    _log_registered_routes(app)


def _initialize_admin_and_cli(app: Flask) -> None:
    """Initialize admin module and CLI commands."""
    # Initialize admin module if available
    try:
        from . import admin

        admin.init_app(app)
    except ImportError:
        logger.warning("Admin module not available")

    # Initialize CLI commands
    from .auth.cli import register_commands as register_auth_commands
    from .expenses.cli import register_commands as register_expenses_commands
    from .restaurants.cli import register_commands as register_restaurant_commands

    register_auth_commands(app)
    register_expenses_commands(app)
    register_restaurant_commands(app)
    logger.debug("Initialized CLI commands")


def _configure_jwt_handlers(app: Flask) -> None:
    """Configure JWT error handlers."""

    @jwt.invalid_token_loader
    def invalid_token_callback(error: str) -> Union[str, tuple]:
        return jsonify({"status": "error", "message": "Invalid or expired token", "error": str(error)}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error: str) -> Union[str, tuple]:
        return jsonify({"status": "error", "message": "Missing authorization token", "error": str(error)}), 401


def _register_blueprints(app: Flask) -> None:
    """Register all application blueprints."""
    logger.debug("Registering blueprints...")

    # Main blueprint
    from .main import bp as main_bp

    app.register_blueprint(main_bp)
    logger.debug(f"Registered blueprint: {main_bp.name} at {main_bp.url_prefix or '/'}")

    # Auth blueprint
    from .auth import bp as auth_bp
    from .auth import init_app as init_auth

    init_auth(app)
    logger.debug(f"Registered blueprint: {auth_bp.name} at /auth")

    # Feature blueprints - use explicit imports for reliability
    try:
        from .restaurants import bp as restaurants_bp

        app.register_blueprint(restaurants_bp, url_prefix="/restaurants")
        logger.debug(f"Registered blueprint: {restaurants_bp.name} at /restaurants")
    except ImportError as e:
        logger.warning(f"Could not import restaurants blueprint: {e}")

    try:
        from .expenses import bp as expenses_bp

        app.register_blueprint(expenses_bp, url_prefix="/expenses")
        logger.debug(f"Registered blueprint: {expenses_bp.name} at /expenses")
    except ImportError as e:
        logger.warning(f"Could not import expenses blueprint: {e}")

    try:
        from .api import bp as api_bp

        app.register_blueprint(api_bp, url_prefix="/api/v1")
        logger.debug(f"Registered blueprint: {api_bp.name} at /api/v1")
    except ImportError as e:
        logger.warning(f"Could not import api blueprint: {e}")

    try:
        from .reports import bp as reports_bp

        app.register_blueprint(reports_bp, url_prefix="/reports")
        logger.debug(f"Registered blueprint: {reports_bp.name} at /reports")
    except ImportError as e:
        logger.warning(f"Could not import reports blueprint: {e}")


def _configure_cors(app: Flask) -> None:
    """Configure CORS settings based on environment."""
    import os

    environment = os.getenv("ENVIRONMENT", "dev")
    is_lambda = os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None
    if is_lambda and environment == "dev":
        # Lambda development - use permissive settings for API Gateway
        app.logger.info("Using permissive CORS configuration for Lambda development")
        CORS(
            app,
            resources={
                r"/*": {
                    "origins": "*",  # Allow all origins
                    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],  # All methods
                    "allow_headers": "*",  # Allow all headers
                    "expose_headers": [
                        "Content-Length",
                        "X-CSRFToken",
                        "Set-Cookie",
                        "Location",
                    ],  # Expose important headers
                    "supports_credentials": True,  # Enable credentials for session cookies
                }
            },
        )
    else:
        # Local development or production - use standard settings
        app.logger.info("Using standard CORS configuration")
        cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
        cors_methods = os.getenv("CORS_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
        cors_allow_headers = os.getenv("CORS_ALLOW_HEADERS", "Content-Type,X-CSRFToken,X-Requested-With").split(",")
        cors_expose_headers = os.getenv("CORS_EXPOSE_HEADERS", "Content-Length,X-CSRFToken").split(",")

        # Configure CORS
        CORS(
            app,
            resources={
                r"/*": {
                    "origins": cors_origins,
                    "methods": cors_methods,
                    "allow_headers": cors_allow_headers,
                    "expose_headers": cors_expose_headers,
                    "supports_credentials": False,  # Standard setting for local development
                }
            },
        )


def _log_registered_routes(app: Flask) -> None:
    """Log all registered routes for debugging."""
    logger.debug("Registered routes:")
    for rule in app.url_map.iter_rules():
        methods = list(rule.methods - {"OPTIONS", "HEAD"})
        logger.debug(f"  {rule.endpoint}: {rule.rule} {methods}")
