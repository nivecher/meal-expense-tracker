"""API blueprint for the application."""

from flask import Blueprint
from flask_cors import CORS

bp = Blueprint("api", __name__)
CORS(bp)  # Enable CORS for all routes in this blueprint

# Import routes at the bottom to avoid circular imports
from app.api import routes  # noqa: E402, F401
