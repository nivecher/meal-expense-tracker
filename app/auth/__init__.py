"""Authentication package initialization."""

import logging
from typing import TYPE_CHECKING

from flask import Blueprint

if TYPE_CHECKING:
    from flask import Flask

# Initialize Blueprint
bp = Blueprint("auth", __name__, url_prefix="/auth")

# Configure logger
logger = logging.getLogger(__name__)


def init_app(app: "Flask") -> None:
    """Initialize the auth blueprint with the Flask app.

    Args:
        app: The Flask application instance
    """
    # Import models here to avoid circular imports
    # Import routes after blueprint creation to avoid circular imports
    from . import api  # noqa: F401
    from . import cli  # noqa: F401
    from . import routes  # noqa: F401
    from .models import User  # noqa: F401

    # Register the auth blueprint
    app.register_blueprint(bp)

    # Register CLI commands
    cli.register_commands(app)
