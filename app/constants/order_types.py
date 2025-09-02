"""Centralized order type constants for the meal expense tracker.

This module contains order types with associated colors and icons
for consistent display across the application.
Following TIGER principles: Safety, Performance, Developer Experience

Font Awesome icon alignment:
- All icons below are Font Awesome 5+ (free) icon names.
- Icons chosen to be intuitive and consistent with meal type styling.
"""

from typing import Dict, List, Optional, TypedDict

from .colors import BOOTSTRAP_COLORS


class OrderTypeData(TypedDict):
    """Type definition for order type data."""

    name: str
    color: str
    icon: str
    description: str


# Order type color mapping using Bootstrap colors for consistency
ORDER_TYPE_COLORS = {
    "dine_in": BOOTSTRAP_COLORS["blue"]["hex"],  # #0d6efd - primary blue
    "takeout": BOOTSTRAP_COLORS["green"]["hex"],  # #198754 - success green
    "delivery": BOOTSTRAP_COLORS["orange"]["hex"],  # #fd7e14 - warning orange
    "drive_thru": BOOTSTRAP_COLORS["purple"]["hex"],  # #6f42c1 - purple
    "catering": BOOTSTRAP_COLORS["teal"]["hex"],  # #20c997 - info teal
    "other": BOOTSTRAP_COLORS["gray"]["hex"],  # #6c757d - secondary gray
}


# All icons below are Font Awesome 5+ (free) icon names
# See: https://fontawesome.com/icons?d=gallery&s=solid

ORDER_TYPE_CONSTANTS: List[OrderTypeData] = [
    {
        "name": "dine_in",
        "color": ORDER_TYPE_COLORS["dine_in"],
        "icon": "utensils",  # Font Awesome: utensils (solid)
        "description": "Dining at the restaurant",
    },
    {
        "name": "takeout",
        "color": ORDER_TYPE_COLORS["takeout"],
        "icon": "shopping-bag",  # Font Awesome: shopping-bag (solid)
        "description": "Takeout/carryout order",
    },
    {
        "name": "delivery",
        "color": ORDER_TYPE_COLORS["delivery"],
        "icon": "truck",  # Font Awesome: truck (solid)
        "description": "Food delivered to location",
    },
    {
        "name": "drive_thru",
        "color": ORDER_TYPE_COLORS["drive_thru"],
        "icon": "car",  # Font Awesome: car (solid)
        "description": "Drive-through service",
    },
    {
        "name": "catering",
        "color": ORDER_TYPE_COLORS["catering"],
        "icon": "users",  # Font Awesome: users (solid)
        "description": "Catered event",
    },
    {
        "name": "other",
        "color": ORDER_TYPE_COLORS["other"],
        "icon": "question",  # Font Awesome: question (solid)
        "description": "Other ordering method",
    },
]


def get_order_type_constants() -> List[OrderTypeData]:
    """Get all order type constants.

    Returns:
        List of order type data dictionaries with name, color, icon, and description

    Example:
        order_types = get_order_type_constants()
        print(order_types[0])  # {'name': 'dine_in', 'color': '#0d6efd', ...}
    """
    return ORDER_TYPE_CONSTANTS.copy()


def get_order_type_names() -> List[str]:
    """Get list of all order type names.

    Returns:
        List of order type names in order

    Example:
        names = get_order_type_names()
        print(names[:3])  # ['dine_in', 'takeout', 'delivery']
    """
    return [order_type["name"] for order_type in ORDER_TYPE_CONSTANTS]


def get_order_type_data(order_type_name: str) -> Optional[OrderTypeData]:
    """Get order type data by name.

    Args:
        order_type_name: Name of the order type to look up

    Returns:
        Order type data dictionary or None if not found

    Example:
        data = get_order_type_data('dine_in')
        print(data['color'])  # '#0d6efd'
    """
    # Input validation - safety first
    if not order_type_name or not isinstance(order_type_name, str):
        return None

    # Enforce bounds to prevent excessive processing
    if len(order_type_name) > 50:
        return None

    # Case-insensitive lookup
    normalized_name = order_type_name.strip().lower()

    for order_type in ORDER_TYPE_CONSTANTS:
        if order_type["name"].lower() == normalized_name:
            return order_type.copy()  # Return copy for safety

    return None


def get_order_type_color(order_type_name: str) -> str:
    """Get color for an order type using centralized Bootstrap colors.

    Args:
        order_type_name: Name of the order type

    Returns:
        Hex color code or default Bootstrap gray if not found

    Example:
        color = get_order_type_color('dine_in')
        print(color)  # '#0d6efd'
    """
    order_type_data = get_order_type_data(order_type_name)
    return order_type_data["color"] if order_type_data else BOOTSTRAP_COLORS["gray"]["hex"]


def get_order_type_icon(order_type_name: str) -> str:
    """Get icon for an order type.

    Args:
        order_type_name: Name of the order type

    Returns:
        Font Awesome icon name or default question icon if not found

    Example:
        icon = get_order_type_icon('dine_in')
        print(icon)  # 'utensils'
    """
    order_type_data = get_order_type_data(order_type_name)
    return order_type_data["icon"] if order_type_data else "question"  # Default question mark


def get_order_type_css_class(order_type_name: str) -> str:
    """Get CSS class name for an order type (consistent with meal type approach).

    Args:
        order_type_name: Name of the order type

    Returns:
        CSS class string for order type styling

    Example:
        css_class = get_order_type_css_class('dine_in')
        print(css_class)  # 'dine-in'
    """
    if not order_type_name or not isinstance(order_type_name, str):
        return "order-type-default"

    # Normalize to lowercase and replace underscores with hyphens for CSS class
    normalized_name = order_type_name.strip().lower().replace("_", "-")

    # Validate order type exists
    if get_order_type_data(order_type_name):
        return normalized_name

    return "order-type-default"


def create_order_type_map() -> Dict[str, OrderTypeData]:
    """Create a dictionary mapping order type names to data for fast lookup.

    Returns:
        Dictionary with order type names as keys and OrderTypeData as values

    Example:
        order_type_map = create_order_type_map()
        dine_in_data = order_type_map.get('dine_in')
    """
    return {order_type["name"]: order_type for order_type in ORDER_TYPE_CONSTANTS}


def validate_order_type_name(order_type_name: str) -> bool:
    """Validate if an order type name exists in our constants.

    Args:
        order_type_name: Name to validate

    Returns:
        True if order type exists, False otherwise

    Example:
        is_valid = validate_order_type_name('dine_in')  # True
        is_invalid = validate_order_type_name('unknown')  # False
    """
    return get_order_type_data(order_type_name) is not None
