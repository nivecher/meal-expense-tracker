"""
Centralized Color Constants for Meal Expense Tracker
Following TIGER principles: Safety, Performance, Developer Experience

This module provides a single source of truth for all colors used throughout
the application, ensuring consistency and maintainability.
"""

from typing import Dict, TypedDict


class ColorData(TypedDict):
    """Type definition for color data with semantic meaning."""

    hex: str
    name: str
    description: str


# Bootstrap 5 compatible color palette
BOOTSTRAP_COLORS: dict[str, ColorData] = {
    "orange": {
        "hex": "#fd7e14",
        "name": "Orange",
        "description": "Bootstrap orange - warm, energetic",
    },
    "green": {
        "hex": "#198754",
        "name": "Green",
        "description": "Bootstrap success green - fresh, positive",
    },
    "cyan": {
        "hex": "#0dcaf0",
        "name": "Cyan",
        "description": "Bootstrap info cyan - cool, refreshing",
    },
    "red": {
        "hex": "#dc3545",
        "name": "Red",
        "description": "Bootstrap danger red - attention, urgency",
    },
    "purple": {
        "hex": "#6f42c1",
        "name": "Purple",
        "description": "Bootstrap purple - creative, premium",
    },
    "blue": {
        "hex": "#0d6efd",
        "name": "Blue",
        "description": "Bootstrap primary blue - trustworthy, professional",
    },
    "gray": {
        "hex": "#6c757d",
        "name": "Gray",
        "description": "Bootstrap secondary gray - neutral, balanced",
    },
    "yellow": {
        "hex": "#ffc107",
        "name": "Yellow",
        "description": "Bootstrap warning yellow - caution, attention",
    },
    "teal": {"hex": "#20c997", "name": "Teal", "description": "Bootstrap teal - calm, natural"},
    "indigo": {
        "hex": "#6610f2",
        "name": "Indigo",
        "description": "Bootstrap indigo - deep, sophisticated",
    },
}


# Category-specific color mapping
CATEGORY_COLORS: dict[str, str] = {
    "restaurants": BOOTSTRAP_COLORS["orange"]["hex"],  # #fd7e14
    "groceries": BOOTSTRAP_COLORS["green"]["hex"],  # #198754
    "drinks": BOOTSTRAP_COLORS["cyan"]["hex"],  # #0dcaf0
    "fast_food": BOOTSTRAP_COLORS["red"]["hex"],  # #dc3545
    "entertainment": BOOTSTRAP_COLORS["purple"]["hex"],  # #6f42c1
    "snacks_vending": BOOTSTRAP_COLORS["blue"]["hex"],  # #0d6efd
    "other": BOOTSTRAP_COLORS["gray"]["hex"],  # #6c757d
}


def get_color_hex(color_key: str) -> str:
    """
    Get hex color value with validation and fallback.

    Args:
        color_key: Bootstrap color key (e.g., 'orange', 'green')

    Returns:
        Hex color string with fallback to gray

    Following TIGER principles:
    - Safety: Input validation with fallback
    - Performance: Simple dict lookup
    - Developer Experience: Clear parameter names and documentation
    """
    if not color_key:
        return BOOTSTRAP_COLORS["gray"]["hex"]

    normalized_key = color_key.lower().strip()

    if normalized_key not in BOOTSTRAP_COLORS:
        return BOOTSTRAP_COLORS["gray"]["hex"]  # Default fallback

    return BOOTSTRAP_COLORS[normalized_key]["hex"]


def get_category_color(category_key: str) -> str:
    """
    Get category color with validation and fallback.

    Args:
        category_key: Category key (e.g., 'restaurants', 'groceries')

    Returns:
        Hex color string with fallback to gray
    """
    if not category_key:
        return BOOTSTRAP_COLORS["gray"]["hex"]

    normalized_key = category_key.lower().strip().replace(" ", "_").replace("&", "")

    if normalized_key not in CATEGORY_COLORS:
        return BOOTSTRAP_COLORS["gray"]["hex"]  # Default fallback

    return CATEGORY_COLORS[normalized_key]


def get_all_bootstrap_colors() -> dict[str, ColorData]:
    """
    Get all Bootstrap colors for use in color selectors.

    Returns:
        Complete Bootstrap color dictionary
    """
    return BOOTSTRAP_COLORS.copy()
