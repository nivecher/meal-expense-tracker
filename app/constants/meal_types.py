"""Meal type constants for the meal expense tracker."""

from typing import Dict, List, Optional

# Simple meal type definitions with colors and icons
MEAL_TYPES = {
    "breakfast": {
        "color": "#fd7e14",  # Orange
        "icon": "bread-slice",
        "description": "Morning meal",
        "time_range": "6:00 AM - 11:00 AM",
    },
    "brunch": {
        "color": "#dc3545",  # Red
        "icon": "bacon",
        "description": "Late morning meal",
        "time_range": "10:00 AM - 2:00 PM",
    },
    "lunch": {
        "color": "#198754",  # Green
        "icon": "utensils",
        "description": "Midday meal",
        "time_range": "11:00 AM - 3:00 PM",
    },
    "dinner": {
        "color": "#0d6efd",  # Blue
        "icon": "drumstick-bite",
        "description": "Evening meal",
        "time_range": "5:00 PM - 10:00 PM",
    },
    "snacks": {
        "color": "#ffc107",  # Yellow
        "icon": "cookie-bite",
        "description": "Light meal or snacks",
        "time_range": "Any time",
    },
    "drinks": {
        "color": "#0dcaf0",  # Cyan
        "icon": "coffee",
        "description": "Beverages only",
        "time_range": "Any time",
    },
    "dessert": {
        "color": "#6f42c1",  # Purple
        "icon": "ice-cream",
        "description": "Sweet treats",
        "time_range": "After meals",
    },
    "late night": {
        "color": "#6610f2",  # Indigo
        "icon": "moon",
        "description": "Late night meal",
        "time_range": "10:00 PM - 6:00 AM",
    },
    "groceries": {
        "color": "#20c997",  # Teal
        "icon": "shopping-cart",
        "description": "Grocery shopping",
        "time_range": "Any time",
    },
}


# Simple helper functions for backward compatibility
def get_meal_type_names() -> list[str]:
    """Get list of all meal type names."""
    return list(MEAL_TYPES.keys())


def get_meal_type_data(meal_type_name: str) -> dict[str, str] | None:
    """Get meal type data by name."""
    if not meal_type_name or not isinstance(meal_type_name, str):
        return None
    return MEAL_TYPES.get(meal_type_name.strip().lower())


def get_meal_type_color(meal_type_name: str) -> str:
    """Get color for a meal type."""
    data = get_meal_type_data(meal_type_name)
    return data["color"] if data else "#6c757d"  # Default gray


def get_meal_type_icon(meal_type_name: str) -> str:
    """Get icon for a meal type."""
    data = get_meal_type_data(meal_type_name)
    return data["icon"] if data else "question"


def validate_meal_type_name(meal_type_name: str) -> bool:
    """Check if meal type exists."""
    return get_meal_type_data(meal_type_name) is not None
