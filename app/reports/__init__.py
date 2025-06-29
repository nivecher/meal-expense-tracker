"""Reports blueprint for the application."""

from flask import Blueprint

bp = Blueprint("reports", __name__)

# Import routes at the bottom to avoid circular imports
from app.reports import routes  # noqa: E402, F401
