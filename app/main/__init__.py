"""Main package initialization."""

import logging

from flask import Blueprint

# Initialize Blueprint
bp = Blueprint("main", __name__)

# Configure logger
logger = logging.getLogger(__name__)

# Import routes after blueprint creation to avoid circular imports
from . import routes  # noqa: E402


def init_app(app):
    """Initialize the main package with the Flask app.

    Args:
        app: The Flask application instance
    """
    app.register_blueprint(bp)
    logger.info("Main blueprint registered")
    return None
