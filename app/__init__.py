"""
Application factory for the Meal Expense Tracker Flask application.

This module contains the application factory function that creates and configures
the Flask application instance for both WSGI and AWS Lambda environments.
"""

import logging
import os
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from dotenv import load_dotenv
from config import config

# Version information
from ._version import __version__

# Version information dictionary used throughout the application
version = {"app": __version__, "api": "v1"}

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()


def create_app(config_name=None):
    """Create and configure the Flask application.

    Args:
        config_name (str): The configuration to use (development, testing,
                         production, etc.) If None, uses FLASK_ENV environment
                         variable or defaults to 'development'.

    Returns:
        Flask: The configured Flask application instance
    """
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)

    # Load default configuration
    app.config.from_object(config[config_name])

    # Load environment variables
    load_dotenv()

    # Initialize configuration
    config[config_name].init_app(app)

    # Configure logging
    _configure_logging(app)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # Enable CORS for all routes
    CORS(app)

    # Register blueprints
    _register_blueprints(app)

    # Shell context for flask shell
    @app.shell_context_processor
    def make_shell_context():
        return {"db": db}

    return app


def _register_blueprints(app):
    """Register all blueprints with the application."""
    from app.auth import bp as auth_bp
    from app.expenses import bp as expenses_bp
    from app.restaurants import bp as restaurants_bp
    from app.main import bp as main_bp
    from app.health import bp as health_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(expenses_bp, url_prefix="/api/expenses")
    app.register_blueprint(restaurants_bp, url_prefix="/api/restaurants")
    app.register_blueprint(main_bp, url_prefix="/")
    app.register_blueprint(health_bp)


def _configure_logging(app):
    """Configure application logging."""
    if app.config.get("ENV") == "production":
        logging.basicConfig(level=logging.INFO)
        app.logger.setLevel(logging.INFO)
    else:
        logging.basicConfig(level=logging.DEBUG)
        app.logger.setLevel(logging.DEBUG)
