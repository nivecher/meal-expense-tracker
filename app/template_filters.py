"""Custom template filters for the application."""

from datetime import datetime

from flask import Flask

from app.constants.cuisines import (
    get_cuisine_color,
    get_cuisine_css_class,
    get_cuisine_icon,
)
from app.constants.meal_type_colors import get_meal_type_color
from app.constants.meal_types import get_meal_type_icon
from app.constants.order_types import get_order_type_css_class, get_order_type_icon
from app.utils.timezone_utils import (
    format_current_time_for_user,
    format_date_for_user,
    format_datetime_for_user,
    get_timezone_display_name,
    time_ago_for_user,
)


def time_ago(value: datetime) -> str:
    """Format a datetime as a relative time string (e.g., '2 hours ago').

    Args:
        value: The datetime object to format

    Returns:
        str: A human-readable relative time string in user's timezone
    """
    # Get user timezone from Flask context
    user_timezone = None
    try:
        from flask_login import current_user

        if current_user and current_user.is_authenticated:
            user_timezone = current_user.timezone
    except Exception:  # nosec B110 - Intentional fallback when Flask-Login context unavailable
        # Fall back to UTC if user context not available (e.g., CLI context)
        pass

    return time_ago_for_user(value, user_timezone)


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


def format_datetime_user_tz(value: datetime, format_str: str = "%B %d, %Y at %I:%M %p") -> str:
    """Format a datetime for display in user's timezone.

    Args:
        value: The datetime object to format
        format_str: Python strftime format string

    Returns:
        str: Formatted datetime string in user's timezone
    """
    # Get user timezone from Flask context
    user_timezone = None
    try:
        from flask_login import current_user

        if current_user and current_user.is_authenticated:
            user_timezone = current_user.timezone
    except Exception:  # nosec B110 - Intentional fallback when Flask-Login context unavailable
        # Fall back to UTC if user context not available (e.g., CLI context)
        pass

    return format_datetime_for_user(value, user_timezone, format_str)


def format_date_user_tz(value: datetime, format_str: str = "%B %d, %Y") -> str:
    """Format a date for display in user's timezone.

    Args:
        value: The datetime object to format
        format_str: Python strftime format string

    Returns:
        str: Formatted date string in user's timezone
    """
    # Get user timezone from Flask context
    user_timezone = None
    try:
        from flask_login import current_user

        if current_user and current_user.is_authenticated:
            user_timezone = current_user.timezone
    except Exception:  # nosec B110 - Intentional fallback when Flask-Login context unavailable
        # Fall back to UTC if user context not available (e.g., CLI context)
        pass

    return format_date_for_user(value, user_timezone, format_str)


def current_time_user_tz(format_str: str = "%B %d, %Y at %I:%M:%S %p %Z") -> str:
    """Get current time formatted for user's timezone.

    Args:
        format_str: Python strftime format string

    Returns:
        str: Formatted current time string in user's timezone
    """
    # Get user timezone from Flask context
    user_timezone = None
    try:
        from flask_login import current_user

        if current_user and current_user.is_authenticated:
            user_timezone = current_user.timezone
    except Exception:  # nosec B110 - Intentional fallback when Flask-Login context unavailable
        # Fall back to UTC if user context not available (e.g., CLI context)
        pass

    return format_current_time_for_user(user_timezone, format_str)


def timezone_display_name(timezone_str: str) -> str:
    """Get a human-readable display name for a timezone.

    Args:
        timezone_str: The timezone string (e.g., 'America/New_York')

    Returns:
        str: Human-readable timezone name
    """
    return get_timezone_display_name(timezone_str)


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
    # Timezone-aware filters
    app.add_template_filter(time_ago, name="time_ago")
    app.add_template_filter(format_datetime_user_tz, name="format_datetime_user_tz")
    app.add_template_filter(format_date_user_tz, name="format_date_user_tz")
    app.add_template_filter(timezone_display_name, name="timezone_display_name")

    # Existing filters
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
    app.add_template_global(current_time_user_tz, name="current_time_user_tz")
