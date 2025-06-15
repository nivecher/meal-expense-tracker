"""Health check endpoints for the application."""

from flask import Blueprint, jsonify
from sqlalchemy import text

from app import db


bp = Blueprint("health", __name__)


@bp.route("/health")
def health_check():
    """Health check endpoint to verify the application and database are running."""
    try:
        # Check database connection
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return (
            jsonify(
                {"status": "unhealthy", "database": "disconnected", "error": str(e)}
            ),
            500,
        )
