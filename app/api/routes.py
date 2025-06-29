"""API routes for the application."""

from flask import jsonify
from flask_login import current_user, login_required

from app.api import bp


@bp.route("/status")
def status():
    """Return API status information."""
    return jsonify(
        {"status": "ok", "version": "1.0", "user": current_user.get_id() if current_user.is_authenticated else None}
    )


@bp.route("/config")
@login_required
def config():
    """Return application configuration (safely)."""
    from flask import current_app

    # Only include non-sensitive configuration
    return jsonify(
        {
            "debug": current_app.config.get("DEBUG", False),
            "environment": current_app.config.get("ENV", "production"),
            "google_places_configured": bool(current_app.config.get("GOOGLE_PLACES_API_KEY")),
            "version": current_app.config.get("VERSION", "unknown"),
        }
    )
