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


def inject_cuisine_data():
    """Inject cuisine data into all templates.

    This provides centralized cuisine configuration to both templates
    and JavaScript without API calls.
    """
    from app.constants import CUISINES, MEAL_TYPES, get_cuisine_names

    return {
        "cuisines": CUISINES,
        "cuisine_names": get_cuisine_names(),
        "meal_types": MEAL_TYPES,
    }
