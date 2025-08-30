"""Expenses blueprint."""

from flask import Blueprint

bp = Blueprint("expenses", __name__)

# Import routes after blueprint creation to avoid circular imports
from . import routes, services  # noqa: E402
