"""Categories blueprint."""

from flask import Blueprint

bp = Blueprint("categories", __name__)

# Import routes after blueprint creation to avoid circular imports
from . import services  # noqa: E402
