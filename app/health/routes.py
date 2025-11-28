"""Health check endpoints for the application."""

from datetime import UTC, datetime, timezone
import logging
from typing import cast

from flask import Response, jsonify
from sqlalchemy import text

from app.extensions import db

from . import bp  # Import the blueprint from __init__.py

# Configure logger
logger = logging.getLogger(__name__)


@bp.route("/")
def check() -> Response:
    """Health check endpoint to verify the application and database are running.

    Returns:
        JSON: Status, version, and database connectivity information
    """
    try:
        # Test database connection
        db.session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        db_status = f"error: {str(e)}"

    # Get version with fallback if import fails
    try:
        from app._version import __version__
    except ImportError:
        logger.warning("Could not import version information")
        __version__ = "unknown"

    return cast(
        Response,
        jsonify(
            {
                "status": "ok",
                "version": __version__,
                "timestamp": datetime.now(UTC).isoformat(),
                "database": db_status,
            }
        ),
    )
