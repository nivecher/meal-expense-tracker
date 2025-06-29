"""Authentication package initialization."""

import logging

from flask import Blueprint
from flask_login import LoginManager

# Initialize Blueprint
bp = Blueprint("auth", __name__)

# Configure logger
logger = logging.getLogger(__name__)

# Import routes after blueprint creation to avoid circular imports
from . import routes  # noqa: E402


def init_app(app):
    """Initialize the auth blueprint with the Flask app.

    Args:
        app: The Flask application instance
    """
    # Import models here to avoid circular imports
    from . import models  # noqa: F401
    from .models import init_login_manager

    # Register the auth blueprint
    app.register_blueprint(bp, url_prefix="/auth")

    # Initialize login manager
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"
    login_manager.init_app(app)

    # Initialize the login manager
    init_login_manager(login_manager)
