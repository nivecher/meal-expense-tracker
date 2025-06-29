"""Restaurants blueprint."""

from flask import Blueprint

# Initialize Blueprint
bp = Blueprint("restaurants", __name__)

# Import routes after blueprint creation to avoid circular imports
from . import routes  # noqa: E402
