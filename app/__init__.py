"""
Application factory for the Meal Expense Tracker Flask application.

This module contains the application factory function that creates and configures
the Flask application instance for both WSGI and AWS Lambda environments.
"""

import logging
from typing import Any, Dict, Optional

from flask import Flask, jsonify
from flask_cors import CORS
from flask_wtf.csrf import generate_csrf

from config import config

from .database import db, init_database
from .extensions import login_manager


def get_version() -> str:
    """Get the application version."""
    try:
        from importlib.metadata import version as get_package_version

        return get_package_version("meal-expense-tracker")
    except ImportError:
        # Fallback for development/editable installs
        try:
            from setuptools_scm import get_version

            return get_version(fallback_version="0.0.0.dev0")
        except ImportError:
            return "0.0.0.dev0"


# Version information dictionary used throughout the application
__version__ = get_version()
version = {"app": __version__, "api": "v1"}


def _configure_logging(app: Flask) -> None:
    """Configure application logging."""
    if app.debug:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def _configure_extensions(app: Flask) -> None:
    """Configure Flask extensions and services.

    Args:
        app: The Flask application instance
    """
    logger = logging.getLogger(__name__)

    # Initialize database
    init_database(app)
    logger.info("Database initialized")

    # Import models to ensure they are registered with SQLAlchemy
    from .auth import models as _  # noqa: F401

    # Initialize Flask-Migrate
    from .extensions import migrate

    migrate.init_app(app, db)
    logger.info("Flask-Migrate initialized")

    # Initialize login manager
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    # Initialize the login manager with the user loader
    from .auth.models import init_login_manager

    init_login_manager(login_manager)

    # Enable CORS if needed
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # CSRF protection
    app.config["WTF_CSRF_ENABLED"] = True
    app.config["WTF_CSRF_TIME_LIMIT"] = 3600  # 1 hour

    # Initialize services with AWS resources (e.g., SSM Parameter Store)
    if app.config.get("ENABLE_AWS_SERVICES", True):
        try:
            from .services import init_services

            init_services(app)
            logger.info("AWS services initialized")
        except Exception as e:
            logger.error("Failed to initialize AWS services: %s", str(e))
            if app.config.get("FLASK_ENV") == "development":
                raise

    # Add CSRF token to all templates
    @app.context_processor
    def inject_csrf_token():
        return {"csrf_token": generate_csrf}

    # Register custom template filters
    from .utils.filters import init_app as init_filters

    init_filters(app)


def _setup_config(app: Flask, config_obj: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Set up application configuration.

    Args:
        app: Flask application instance
        config_obj: Configuration dictionary or None

    Returns:
        The configuration object
    """
    # Default configuration
    app.config.from_object(config["default"])

    # Override with environment-specific config if provided
    if config_obj is not None:
        if isinstance(config_obj, dict):
            app.config.update(config_obj)
        else:
            app.config.from_object(config_obj)

    # Override with environment variables if present
    app.config.from_prefixed_env()

    # Database configuration is handled in _configure_extensions
    # to ensure proper initialization order with SQLAlchemy
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Configure session
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # 1 hour

    # Log configuration
    logger = logging.getLogger(__name__)
    logger.info("Using configuration: %s", app.config.get("ENV", "default"))
    logger.debug("Database URL: %s", app.config.get("SQLALCHEMY_DATABASE_URI"))

    return app.config


def _register_blueprints(app: Flask) -> None:
    """Register all blueprints with the application.

    Args:
        app: Flask application instance
    """
    from app.api import bp as api_bp
    from app.auth import bp as auth_bp
    from app.errors import bp as errors_bp
    from app.expenses import bp as expenses_bp
    from app.main import bp as main_bp
    from app.restaurants import bp as restaurants_bp

    # Register blueprints with URL prefixes
    blueprints = [
        (api_bp, "/api"),
        (auth_bp, "/auth"),
        (main_bp, ""),
        (errors_bp, ""),
        (restaurants_bp, "/restaurants"),
        (expenses_bp, "/expenses"),
    ]

    for blueprint, url_prefix in blueprints:
        app.register_blueprint(blueprint, url_prefix=url_prefix)


def _add_shell_context(app: Flask) -> None:
    """Add shell context for Flask shell.

    Args:
        app: Flask application instance
    """

    @app.shell_context_processor
    def make_shell_context():
        from .auth.models import User

        return {
            "db": db,
            "User": User,
        }


def create_app(config_obj: Optional[Dict[str, Any]] = None) -> Flask:
    """Create and configure the Flask application.

    Args:
        config_obj: Configuration dictionary or None

    Returns:
        Flask: The configured Flask application.
    """
    app = Flask(__name__)

    # Set up configuration
    _setup_config(app, config_obj)

    # Configure logging
    _configure_logging(app)

    # Configure extensions and services
    _configure_extensions(app)

    # Register blueprints
    _register_blueprints(app)

    # Add shell context
    _add_shell_context(app)

    @app.route("/health")
    def health_check() -> tuple:
        """Health check endpoint for monitoring."""
        return jsonify({"status": "ok", "version": version})

    @app.route("/health/db")
    def db_health_check() -> tuple:
        """Database health check endpoint."""
        from .utils.db_utils import check_database_connection

        success, message = check_database_connection()
        status_code = 200 if success else 503
        return (jsonify({"database": "ok" if success else "error", "message": message}), status_code)

    @app.teardown_appcontext
    def shutdown_session(exception=None) -> None:
        """Remove database session at the end of the request."""
        if db.session is not None:
            db.session.remove()

    return app
