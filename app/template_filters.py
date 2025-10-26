"""Custom template filters for the application."""

from datetime import datetime

from flask import Flask

from app.constants.cuisines import (
    get_cuisine_color,
    get_cuisine_icon,
    validate_cuisine_name,
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
    if not cuisine_name or not isinstance(cuisine_name, str):
        return "cuisine-default"

    # Normalize to lowercase and replace spaces with hyphens for CSS class
    normalized_name = cuisine_name.strip().lower().replace(" ", "-")

    # Validate cuisine exists
    if validate_cuisine_name(cuisine_name):
        return normalized_name

    return "cuisine-default"


def meal_type_css_class_filter(meal_type: str) -> str:
    """Get the CSS class for a meal type.

    Args:
        meal_type: The meal type name

    Returns:
        CSS class name string
    """
    from app.constants import validate_meal_type_name

    if not meal_type or not isinstance(meal_type, str):
        return "meal-type-default"

    # Normalize to lowercase and replace spaces with hyphens for CSS class
    normalized_name = meal_type.strip().lower().replace(" ", "-")

    # Validate meal type exists
    if validate_meal_type_name(meal_type):
        return normalized_name

    return "meal-type-default"


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


def service_level_icon(service_level: str) -> str:
    """Get the icon for a service level.

    Args:
        service_level: The service level name

    Returns:
        Font Awesome icon name or default question if not found
    """
    if not service_level:
        return "question"

    service_level_lower = service_level.lower().strip().replace("_", "-")

    # Service level icon mapping
    icon_mapping = {
        "fine-dining": "crown",  # Premium/upscale
        "casual-dining": "utensils",  # Traditional restaurant
        "fast-casual": "clock",  # Quick but quality
        "quick-service": "bolt",  # Fast service
        "unknown": "question",  # Unknown/undetermined
    }

    return icon_mapping.get(service_level_lower, "question")


def service_level_color(service_level: str) -> str:
    """Get the color for a service level.

    Args:
        service_level: The service level name

    Returns:
        Hex color code or default gray if not found
    """
    if not service_level:
        return "#6c757d"

    service_level_lower = service_level.lower().strip().replace("_", "-")

    # Service level color mapping with enhanced colors
    color_mapping = {
        "fine-dining": "#8b0000",  # Dark red - premium/luxury
        "casual-dining": "#ff6b35",  # Orange-red - warm/comfortable
        "fast-casual": "#2d5016",  # Dark green - fresh/quality
        "quick-service": "#ffa500",  # Orange - fast/energetic
        "unknown": "#6c757d",  # Gray - neutral/unknown
    }

    return color_mapping.get(service_level_lower, "#6c757d")


def service_level_css_class_filter(service_level: str) -> str:
    """Get the CSS class for a service level.

    Args:
        service_level: The service level name

    Returns:
        CSS class name string
    """
    if not service_level:
        return "service-level-default"

    service_level_lower = service_level.lower().strip().replace("_", "-")

    # Return the normalized service level as CSS class
    return f"service-level-{service_level_lower}"


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

    # Service level filters
    app.add_template_filter(service_level_icon, name="service_level_icon")
    app.add_template_filter(service_level_color, name="service_level_color")
    app.add_template_filter(service_level_css_class_filter, name="service_level_css_class")

    # Add template global functions
    app.add_template_global(get_app_version, name="get_app_version")
    app.add_template_global(current_time_user_tz, name="current_time_user_tz")
