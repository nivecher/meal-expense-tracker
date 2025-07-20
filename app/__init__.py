import logging
import os

from flask import Flask

from config import config

from .extensions import init_extensions, jwt

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

__all__ = ["create_app", "jwt"]


def create_app(config_name=None):
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.environ.get("FLASK_CONFIG", "default")

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    init_extensions(app)

    # Register blueprints
    logger.debug("Registering blueprints...")

    from .main import bp as main_bp

    app.register_blueprint(main_bp)
    logger.debug(f"Registered blueprint: {main_bp.name} " f"at {main_bp.url_prefix or '/'}")

    from .auth import bp as auth_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
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

    # Log registered routes
    logger.debug("Registered routes:")
    for rule in app.url_map.iter_rules():
        methods = list(rule.methods - {"OPTIONS", "HEAD"})
        logger.debug(f"  {rule.endpoint}: {rule.rule} {methods}")

    return app
