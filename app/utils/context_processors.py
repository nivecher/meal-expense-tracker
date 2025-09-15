"""Context processors for Flask application.

This module provides context processors that make data available
to all templates globally.
"""

from flask_login import current_user


def inject_user_context():
    """Inject current user context into all templates.

    This makes the current user available in template filters
    for timezone-aware formatting.
    """
    return {
        "current_user": current_user,
        "user": current_user,  # Alternative name for compatibility
    }
