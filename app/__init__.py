from collections.abc import Callable
import logging
from typing import Any, Optional, cast

from dotenv import load_dotenv
from flask import Flask, Response, request
from flask_cors import CORS

from config import get_config

# Load environment variables from .env file
load_dotenv()

# Initialize logger
logger = logging.getLogger(__name__)

__all__ = ["create_app"]


def create_app(config_name: str | None = None) -> Flask:
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


def _is_lambda_env_for_url_generation(app: Flask) -> tuple[bool, str]:
    """Check if we're in Lambda environment and get server name."""
    server_name = app.config.get("SERVER_NAME")
    is_lambda = bool(server_name and server_name != "localhost:5000" and "localhost" not in server_name)
    return is_lambda, str(server_name or "")


def _create_lambda_url_for(app: Flask) -> Callable[..., str]:
    """Create a Lambda-aware url_for function."""
    original_url_for = app.url_for

    def lambda_url_for(endpoint: str, **values: Any) -> str:
        """Override url_for to use correct host in Lambda/API Gateway environment."""
        is_lambda, server_name = _is_lambda_env_for_url_generation(app)

        if is_lambda and "_external" not in values:
            # Force external URLs in Lambda to use the configured SERVER_NAME
            values["_external"] = True
            url: str = original_url_for(endpoint, **values)
            # Replace the host in the generated URL
            if "://" in url:
                protocol, rest = url.split("://", 1)
                if "/" in rest:
                    host, path = rest.split("/", 1)
                    url = f"{protocol}://{server_name}/{path}"
                else:
                    url = f"{protocol}://{server_name}"
            return url
        else:
            return cast(str, original_url_for(endpoint, **values))

    return lambda_url_for


def _create_lambda_redirect(app: Flask) -> Callable[[str, int], Response]:
    """Create a Lambda-aware redirect function."""
    from flask import redirect as original_redirect

    def lambda_redirect(location: str, code: int = 302) -> Response:
        """Override redirect to fix Location headers in Lambda environment."""
        is_lambda, server_name = _is_lambda_env_for_url_generation(app)

        if is_lambda and location.startswith("http"):
            # Check if the location uses API Gateway domain
            if "execute-api" in location or "amazonaws.com" in location:
                # Replace the host in the redirect URL
                if "://" in location:
                    protocol, rest = location.split("://", 1)
                    if "/" in rest:
                        host, path = rest.split("/", 1)
                        location = f"{protocol}://{server_name}/{path}"
                    else:
                        location = f"{protocol}://{server_name}"

        return cast(Response, original_redirect(location, code))

    return lambda_redirect


def _configure_request_handlers(app: Flask) -> None:
    """Configure request and response handlers."""

    # Override url_for to use correct host in Lambda environment
    app.url_for = _create_lambda_url_for(app)

    # Override redirect to fix Location headers in Lambda environment
    import flask

    flask.redirect = _create_lambda_redirect(app)  # type: ignore[assignment]

    # Configure static file headers
    @app.after_request
    def add_static_headers(response: Response) -> Response:
        """Add cache-control and other headers for static files."""
        if response.headers.get("Content-Type"):
            content_type = _fix_content_type_headers(response)
            _set_cache_control_headers(response, content_type)
            _set_security_headers(response, content_type)
        return response

    # Register service worker route with proper headers
    @app.route("/service-worker.js")
    def service_worker() -> Response:
        response = app.send_static_file("js/service-worker.js")
        response.headers["Service-Worker-Allowed"] = "/"
        response.headers["Content-Type"] = "application/javascript"
        response.headers["Cache-Control"] = "no-cache, max-age=0"
        return response


def _fix_content_type_headers(response: Response) -> str:
    """Fix content-type headers for different file types."""
    content_type = response.headers.get("Content-Type", "")
    path = request.path

    # Skip service worker - it has its own content type handling
    if path == "/service-worker.js":
        return content_type

    # Content type mappings
    if path:
        # CSS and JavaScript files
        if path.endswith(".css"):
            response.headers["Content-Type"] = "text/css; charset=utf-8"
            return "text/css; charset=utf-8"
        elif path.endswith(".js"):
            response.headers["Content-Type"] = "text/javascript; charset=utf-8"
            return "text/javascript; charset=utf-8"

        # Font files (no charset)
        elif path.endswith(".woff2"):
            response.headers["Content-Type"] = "font/woff2"
            return "font/woff2"
        elif path.endswith((".woff", ".ttf", ".eot", ".otf")):
            ext = path.split(".")[-1]
            mime_type = f"font/{ext}"
            response.headers["Content-Type"] = mime_type
            return mime_type

    # HTML/text responses - ensure UTF-8
    if content_type and ("text/" in content_type or "html" in content_type):
        base_content_type = content_type.split(";")[0].strip()
        if "charset=" not in content_type:
            response.headers["Content-Type"] = f"{base_content_type}; charset=utf-8"
            return cast(str, response.headers["Content-Type"])

    return content_type


def _set_cache_control_headers(response: Response, content_type: str) -> None:
    """Set appropriate cache control headers based on content type."""
    # Static assets that rarely change - cache for 1 year
    if any(ext in content_type for ext in ["css", "javascript", "image", "font/"]):
        response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    # HTML pages - short cache to ensure updates are seen
    elif "html" in content_type:
        response.headers["Cache-Control"] = "no-cache, max-age=0, must-revalidate"
    # Other content - moderate caching
    else:
        response.headers["Cache-Control"] = "public, max-age=3600"


def _set_security_headers(response: Response, content_type: str) -> None:
    """Set security headers for responses."""
    # Essential security headers - always set for all responses
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"  # Legacy support

    # Additional security headers
    response.headers["Permissions-Policy"] = "geolocation=(self), microphone=(), camera=()"

    # Remove deprecated headers if they exist
    response.headers.pop("Pragma", None)
    response.headers.pop("Expires", None)  # Remove deprecated Expires header

    # Content Security Policy - only for HTML responses to avoid unnecessary headers on static resources
    if content_type and "html" in content_type:
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://code.jquery.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://maps.googleapis.com https://maps.gstatic.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "font-src 'self' https://cdn.jsdelivr.net https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https: blob: https://places.googleapis.com https://maps.googleapis.com; "
            "connect-src 'self' https://maps.googleapis.com https://places.googleapis.com https://cdn.jsdelivr.net; "
            "frame-src 'self' data: blob:; "
            "frame-ancestors 'none'; "
            "object-src 'none'; "
            "base-uri 'self';"
        )
        response.headers["Content-Security-Policy"] = csp


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
    from .utils.context_processors import inject_cuisine_data, inject_user_context

    app.context_processor(inject_user_context)
    app.context_processor(inject_cuisine_data)
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


def _register_blueprints(app: Flask) -> None:
    """Register all application blueprints."""
    logger.debug("Registering blueprints...")

    # Register main blueprint
    from .main import bp as main_bp

    app.register_blueprint(main_bp)
    logger.debug(f"Registered blueprint: {main_bp.name} at /")

    # Register auth blueprint
    from .auth import init_app as init_auth

    init_auth(app)
    logger.debug("Registered auth blueprint at /auth")

    # Register feature blueprints
    blueprint_configs = [
        ("restaurants", "/restaurants"),
        ("expenses", "/expenses"),
        ("api", "/api/v1"),
        ("reports", "/reports"),
        ("health", "/health"),
    ]

    for module_name, url_prefix in blueprint_configs:
        try:
            module = __import__(f"app.{module_name}", fromlist=["bp"])
            bp = module.bp
            app.register_blueprint(bp, url_prefix=url_prefix)
            logger.debug(f"Registered blueprint: {bp.name} at {url_prefix}")
        except ImportError as e:
            logger.warning(f"Could not import {module_name} blueprint: {e}")


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
                    "methods": [
                        "GET",
                        "POST",
                        "PUT",
                        "DELETE",
                        "OPTIONS",
                        "HEAD",
                        "PATCH",
                    ],  # All methods
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
