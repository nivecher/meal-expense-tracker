import logging
import os
from typing import Optional

from flask import Flask, jsonify
from flask.typing import ResponseReturnValue
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

    # Register service worker route with proper headers
    @app.route("/service-worker.js")
    def service_worker():
        response = app.send_static_file("js/service-worker.js")
        response.headers["Service-Worker-Allowed"] = "/"
        response.headers["Content-Type"] = "application/javascript"
        return response

    # Ensure required config values are set
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise ValueError("SQLALCHEMY_DATABASE_URI is not configured")

    # Set default SQLAlchemy config if not set
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)

    # Configure logging
    log_level = logging.DEBUG if app.debug else logging.INFO
    logger.setLevel(log_level)

    # Log app configuration
    logger.debug("Application configuration:")
    logger.debug(f"- ENV: {app.config.get('ENV', 'Not set')}")
    logger.debug(f"- DEBUG: {app.debug}")
    logger.debug(f"- DATABASE_URI: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')}")

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

    # Configure CORS
    _configure_cors(app)

    # Log registered routes
    _log_registered_routes(app)

    return app


def _configure_jwt_handlers(app: Flask) -> None:
    """Configure JWT error handlers."""

    @jwt.invalid_token_loader
    def invalid_token_callback(error: str) -> ResponseReturnValue:
        return jsonify({"status": "error", "message": "Invalid or expired token", "error": str(error)}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error: str) -> ResponseReturnValue:
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

    # Feature blueprints
    blueprints = [
        ("restaurants", "/restaurants"),
        ("expenses", "/expenses"),
        ("api", "/api/v1"),
        ("reports", "/reports"),
    ]

    for name, url_prefix in blueprints:
        module = __import__(f"app.{name}", fromlist=["bp"])
        bp = getattr(module, "bp")
        app.register_blueprint(bp, url_prefix=url_prefix)
        logger.debug(f"Registered blueprint: {bp.name} at {url_prefix}")


def _configure_cors(app: Flask) -> None:
    """Configure CORS settings."""
    # Get CORS configuration from environment
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
                "supports_credentials": False,
            }
        },
    )


def _log_registered_routes(app: Flask) -> None:
    """Log all registered routes for debugging."""
    logger.debug("Registered routes:")
    for rule in app.url_map.iter_rules():
        methods = list(rule.methods - {"OPTIONS", "HEAD"})
        logger.debug(f"  {rule.endpoint}: {rule.rule} {methods}")
