"""Merchants package for restaurant brand/franchise management."""

from flask import Blueprint

from .models import Merchant

# Create blueprint
bp = Blueprint("merchants", __name__, url_prefix="/restaurants/merchants")

# Import routes to register them with the blueprint
from . import routes  # noqa: F401, E402

__all__ = ["Merchant", "bp"]
