"""Profile package initialization."""

from flask import Blueprint

# Initialize Blueprint
bp = Blueprint("profile", __name__, url_prefix="/api/profile")

# Import routes to register them with the blueprint
from . import api  # noqa: E402, F401
