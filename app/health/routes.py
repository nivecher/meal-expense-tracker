"""Health check endpoints for the application."""

import logging
from datetime import UTC, datetime

from flask import jsonify
from sqlalchemy import text

from app import db, version

from . import bp  # Import the blueprint from __init__.py

# Configure logger
logger = logging.getLogger(__name__)


@bp.route("/")
def check():
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

    return jsonify(
        {
            "status": "ok",
            "version": version,
            "timestamp": datetime.now(UTC).isoformat(),
            "database": db_status,
        }
    )
