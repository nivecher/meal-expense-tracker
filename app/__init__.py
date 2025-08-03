import logging
import os
from typing import Optional

from flask import Flask, jsonify
from flask.typing import ResponseReturnValue
from flask_cors import CORS

from config import config

from .extensions import jwt

# Initialize logger
logger = logging.getLogger(__name__)

__all__ = ["create_app", "jwt"]


def create_app(config_name: Optional[str] = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        config_name: The name of the configuration to use. If None, defaults to
            the value of the FLASK_CONFIG environment variable, or 'default' if not set.

    Returns:
        The configured Flask application instance.
    """
    if config_name is None:
        config_name = os.environ.get("FLASK_CONFIG", "default")
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Configure logging based on the DEBUG setting
    log_level = logging.DEBUG if app.debug else logging.INFO
    logger.setLevel(log_level)

    # Debug template loading
    logger.debug(f"Using configuration: {config_name}")
    logger.debug(f"Current working directory: {os.getcwd()}")
    logger.debug(f"Template folder: {os.path.abspath('app/templates')}")
    logger.debug(f"Static folder: {os.path.abspath('app/static')}")

    # Initialize all extensions
    from .extensions import init_app as init_extensions

    init_extensions(app)

    # Configure JWT settings
    @jwt.invalid_token_loader
    def invalid_token_callback(error: str) -> ResponseReturnValue:
        return jsonify({"status": "error", "message": "Invalid or expired token", "error": str(error)}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error: str) -> ResponseReturnValue:
        return jsonify({"status": "error", "message": "Missing authorization token", "error": str(error)}), 401

    # Register blueprints
    logger.debug("Registering blueprints...")

    from .main import bp as main_bp

    app.register_blueprint(main_bp)
    logger.debug(f"Registered blueprint: {main_bp.name} " f"at {main_bp.url_prefix or '/'}")

    # Import and initialize auth blueprint
    from .auth import bp as auth_bp
    from .auth import init_app as init_auth

    # Initialize auth blueprint (which will register itself)
    init_auth(app)
    logger.debug(f"Registered blueprint: {auth_bp.name} at /auth")

    from .restaurants import bp as restaurants_bp

    app.register_blueprint(restaurants_bp, url_prefix="/restaurants")
    logger.debug(f"Registered blueprint: {restaurants_bp.name} " "at /restaurants")

    from .expenses import bp as expenses_bp

    app.register_blueprint(expenses_bp, url_prefix="/expenses")
    logger.debug(f"Registered blueprint: {expenses_bp.name} at /expenses")

    from .api import bp as api_bp

    app.register_blueprint(api_bp, url_prefix="/api/v1")
    logger.debug(f"Registered blueprint: {api_bp.name} at /api/v1")

    from .reports import bp as reports_bp

    app.register_blueprint(reports_bp, url_prefix="/reports")
    logger.debug(f"Registered blueprint: {reports_bp.name} at /reports")

    # Register error handlers
    from .errors import init_app as init_errors

    init_errors(app)
    logger.debug("Registered error handlers")

    # Log registered routes
    logger.debug("Registered routes:")
    for rule in app.url_map.iter_rules():
        methods = list(rule.methods - {"OPTIONS", "HEAD"})
        logger.debug(f"  {rule.endpoint}: {rule.rule} {methods}")

    # Get CORS configuration from environment
    cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
    cors_methods = os.getenv("CORS_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
    cors_allow_headers = os.getenv("CORS_ALLOW_HEADERS", "Content-Type,X-CSRF-Token,X-Requested-With").split(",")
    cors_expose_headers = os.getenv("CORS_EXPOSE_HEADERS", "Content-Length,X-CSRF-Token").split(",")

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

    return app
