"""Health check blueprint."""

from flask import Blueprint

# Create the blueprint
bp = Blueprint("health", __name__)

# Import routes after creating the blueprint to avoid circular imports
from . import routes  # noqa: F401, E402
