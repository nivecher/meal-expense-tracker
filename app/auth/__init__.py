"""Authentication package initialization."""

import logging

from flask import Blueprint

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
    from .models import User  # noqa: F401

    # Register the auth blueprint
    app.register_blueprint(bp, url_prefix="/auth")
