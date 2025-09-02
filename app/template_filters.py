"""Custom template filters for the application."""

from datetime import datetime, timezone

from flask import Flask

from app.constants.cuisines import (
    get_cuisine_color,
    get_cuisine_css_class,
    get_cuisine_icon,
)
from app.constants.meal_type_colors import get_meal_type_color
from app.constants.meal_types import get_meal_type_icon
from app.constants.order_types import get_order_type_css_class, get_order_type_icon


def time_ago(value: datetime) -> str:
    """Format a datetime as a relative time string (e.g., '2 hours ago').

    Args:
        value: The datetime object to format

    Returns:
        str: A human-readable relative time string
    """
    if not value:
        return "Never"

    now = datetime.now(timezone.utc)
    diff = now - value

    # Calculate time differences
    seconds = int(diff.total_seconds())
    minutes = seconds // 60
    hours = minutes // 60
    days = diff.days

    if days > 365:
        years = days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    if days > 30:
        months = days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    if days > 0:
        return f"{days} day{'s' if days > 1 else ''} ago"
    if hours > 0:
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    if minutes > 0:
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    return "Just now"


def meal_type_color(meal_type: str) -> str:
    """Get the background color for a meal type.

    Args:
        meal_type: The meal type name

    Returns:
        Hex color code or default gray if not found
    """
    return get_meal_type_color(meal_type, "background")


def meal_type_icon(meal_type: str) -> str:
    """Get the icon for a meal type.

    Args:
        meal_type: The meal type name

    Returns:
        Font Awesome icon name or default utensils if not found
    """
    return get_meal_type_icon(meal_type)


def restaurant_cuisine(restaurant) -> str:
    """Get the cuisine for a restaurant.

    Args:
        restaurant: The restaurant object

    Returns:
        The cuisine name or dash if not available
    """
    if restaurant and hasattr(restaurant, "cuisine") and restaurant.cuisine:
        return restaurant.cuisine
    return "-"


def cuisine_icon(cuisine_name: str) -> str:
    """Get icon for a cuisine type.

    Args:
        cuisine_name: Name of the cuisine

    Returns:
        Font Awesome icon name
    """
    return get_cuisine_icon(cuisine_name)


def cuisine_color(cuisine_name: str) -> str:
    """Get color for a cuisine type.

    Args:
        cuisine_name: Name of the cuisine

    Returns:
        Hex color code
    """
    return get_cuisine_color(cuisine_name)


def cuisine_css_class_filter(cuisine_name: str) -> str:
    """Get CSS class for a cuisine type.

    Args:
        cuisine_name: Name of the cuisine

    Returns:
        CSS class string
    """
    return get_cuisine_css_class(cuisine_name)


def meal_type_css_class_filter(meal_type: str) -> str:
    """Get the CSS class for a meal type using centralized approach.

    Args:
        meal_type: The meal type name

    Returns:
        CSS class name string
    """
    from app.constants.meal_types import get_meal_type_css_class

    return get_meal_type_css_class(meal_type)


def order_type_icon(order_type: str) -> str:
    """Get the icon for an order type.

    Args:
        order_type: The order type name

    Returns:
        Font Awesome icon name or default question if not found
    """
    return get_order_type_icon(order_type)


def order_type_css_class_filter(order_type: str) -> str:
    """Get the CSS class for an order type using centralized approach.

    Args:
        order_type: The order type name

    Returns:
        CSS class name string
    """
    return get_order_type_css_class(order_type)


def get_app_version() -> str:
    """Get the application version from git tags.

    Returns:
        str: Application version string, defaults to "development" if not found
    """
    try:
        from app._version import __version__

        return __version__
    except ImportError:
        return "development"


def init_app(app: Flask) -> None:
    """Initialize template filters for the Flask app.

    Args:
        app: The Flask application instance.
    """
    app.add_template_filter(time_ago, name="time_ago")
    app.add_template_filter(meal_type_color, name="meal_type_color")
    app.add_template_filter(meal_type_icon, name="meal_type_icon")
    app.add_template_filter(meal_type_css_class_filter, name="meal_type_css_class")
    app.add_template_filter(order_type_icon, name="order_type_icon")
    app.add_template_filter(order_type_css_class_filter, name="order_type_css_class")
    app.add_template_filter(restaurant_cuisine, name="restaurant_cuisine")
    app.add_template_filter(cuisine_icon, name="cuisine_icon")
    app.add_template_filter(cuisine_color, name="cuisine_color")
    app.add_template_filter(cuisine_css_class_filter, name="cuisine_css_class")

    # Add template global functions
    app.add_template_global(get_app_version, name="get_app_version")
