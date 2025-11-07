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
    logger.info(f"Main blueprint routes before registration: {[rule.rule for rule in bp.url_map.iter_rules()]}")
    app.register_blueprint(bp)
    logger.info("Main blueprint registered")
    logger.info(
        f"Main blueprint routes after registration: {[rule.rule for rule in app.url_map.iter_rules() if 'main.' in rule.endpoint]}"
    )
    return None
