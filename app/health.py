"""Health check endpoints for the application."""

from datetime import datetime
from flask import Blueprint, jsonify
from sqlalchemy import text

from app import db, version


bp = Blueprint("health", __name__)


@bp.route("/health")
@bp.route("/api/health")  # Support both paths for backward compatibility
def health_check():
    """Health check endpoint to verify the application and database are running.

    Returns:
        JSON: Status, version, and database connectivity information
    """
    try:
        # Check database connection
        db.session.execute(text("SELECT 1"))
        db_status = "connected"
        status_code = 200
        status = "healthy"
    except Exception as e:
        db_status = f"disconnected: {str(e)}"
        status_code = 500
        status = "unhealthy"

    return (
        jsonify(
            {
                "status": status,
                "version": version.get("app", "unknown"),
                "timestamp": datetime.utcnow().isoformat(),
                "database": db_status,
            }
        ),
        status_code,
    )
