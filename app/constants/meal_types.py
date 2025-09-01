"""Centralized meal type constants for the meal expense tracker.

This module contains meal types with associated colors and icons
for consistent display across the application.
Following TIGER principles: Safety, Performance, Developer Experience

Font Awesome icon alignment:
- All icons below are Font Awesome 5+ (free) icon names.
- If a direct match is not available, a close alternative is chosen and noted.
- "pretzel" is NOT available in Font Awesome Free or Pro as of 2024-06. Closest alternatives for snacks: "cookie-bite", "candy-cane", or "cheese".
"""

from typing import Dict, List, Optional, TypedDict

from .colors import BOOTSTRAP_COLORS


class MealTypeData(TypedDict):
    """Type definition for meal type data."""

    name: str
    color: str
    icon: str
    description: str
    time_range: str


# Meal type color mapping using Bootstrap colors for consistency
MEAL_TYPE_COLORS = {
    "breakfast": BOOTSTRAP_COLORS["orange"]["hex"],  # #fd7e14 - warm sunrise
    "brunch": BOOTSTRAP_COLORS["red"]["hex"],  # #dc3545 - rich coral
    "lunch": BOOTSTRAP_COLORS["green"]["hex"],  # #198754 - fresh green
    "dinner": BOOTSTRAP_COLORS["blue"]["hex"],  # #0d6efd - evening blue
    "snacks": BOOTSTRAP_COLORS["yellow"]["hex"],  # #ffc107 - cheerful yellow
    "drinks": BOOTSTRAP_COLORS["cyan"]["hex"],  # #0dcaf0 - refreshing cyan
    "dessert": BOOTSTRAP_COLORS["purple"]["hex"],  # #6f42c1 - sweet purple
    "late night": BOOTSTRAP_COLORS["indigo"]["hex"],  # #6610f2 - deep night
    "groceries": BOOTSTRAP_COLORS["teal"]["hex"],  # #20c997 - natural teal
}


# All icons below are Font Awesome 5+ (free) icon names or best alternatives.
# See: https://fontawesome.com/icons?d=gallery&s=solid

MEAL_TYPE_CONSTANTS: List[MealTypeData] = [
    {
        "name": "breakfast",
        "color": MEAL_TYPE_COLORS["breakfast"],
        "icon": "bread-slice",  # Font Awesome: bread-slice (solid)
        "description": "Morning meal",
        "time_range": "6:00 AM - 11:00 AM",
    },
    {
        "name": "brunch",
        "color": MEAL_TYPE_COLORS["brunch"],
        "icon": "bacon",  # Font Awesome: bacon (solid). "egg" is not in FA Free.
        "description": "Late morning meal combining breakfast and lunch",
        "time_range": "10:00 AM - 2:00 PM",
    },
    {
        "name": "lunch",
        "color": MEAL_TYPE_COLORS["lunch"],
        "icon": "utensils",  # Font Awesome: utensils (solid)
        "description": "Midday meal",
        "time_range": "11:00 AM - 3:00 PM",
    },
    {
        "name": "dinner",
        "color": MEAL_TYPE_COLORS["dinner"],
        "icon": "drumstick-bite",  # Font Awesome: drumstick-bite (solid)
        "description": "Evening meal",
        "time_range": "5:00 PM - 10:00 PM",
    },
    {
        "name": "snacks",
        "color": MEAL_TYPE_COLORS["snacks"],
        "icon": "cookie-bite",  # Font Awesome: cookie-bite (solid)
        "description": "Light meal or snacks",
        "time_range": "Any time",
    },
    {
        "name": "drinks",
        "color": MEAL_TYPE_COLORS["drinks"],
        "icon": "coffee",  # Font Awesome: coffee (solid)
        "description": "Beverages only",
        "time_range": "Any time",
    },
    {
        "name": "dessert",
        "color": MEAL_TYPE_COLORS["dessert"],
        "icon": "ice-cream",  # Font Awesome: ice-cream (solid)
        "description": "Sweet treats and desserts",
        "time_range": "After meals",
    },
    {
        "name": "late night",
        "color": MEAL_TYPE_COLORS["late night"],
        "icon": "moon",  # Font Awesome: moon (solid)
        "description": "Late night meal or snacks",
        "time_range": "10:00 PM - 6:00 AM",
    },
    {
        "name": "groceries",
        "color": MEAL_TYPE_COLORS["groceries"],  # Bootstrap teal #20c997
        "icon": "shopping-cart",  # Font Awesome: shopping-cart (solid)
        "description": "Grocery shopping and food supplies",
        "time_range": "Any time",
    },
]


def get_meal_type_constants() -> List[MealTypeData]:
    """Get all meal type constants.

    Returns:
        List of meal type data dictionaries with name, color, icon, description, and time_range

    Example:
        meal_types = get_meal_type_constants()
        print(meal_types[0])  # {'name': 'breakfast', 'color': '#f59e0b', ...}
    """
    return MEAL_TYPE_CONSTANTS.copy()


def get_meal_type_names() -> List[str]:
    """Get list of all meal type names.

    Returns:
        List of meal type names in order

    Example:
        names = get_meal_type_names()
        print(names[:3])  # ['breakfast', 'brunch', 'lunch']
    """
    return [meal_type["name"] for meal_type in MEAL_TYPE_CONSTANTS]


def get_meal_type_data(meal_type_name: str) -> Optional[MealTypeData]:
    """Get meal type data by name.

    Args:
        meal_type_name: Name of the meal type to look up

    Returns:
        Meal type data dictionary or None if not found

    Example:
        data = get_meal_type_data('breakfast')
        print(data['color'])  # '#f59e0b'
    """
    # Input validation - safety first
    if not meal_type_name or not isinstance(meal_type_name, str):
        return None

    # Enforce bounds to prevent excessive processing
    if len(meal_type_name) > 50:
        return None

    # Case-insensitive lookup
    normalized_name = meal_type_name.strip().lower()

    for meal_type in MEAL_TYPE_CONSTANTS:
        if meal_type["name"].lower() == normalized_name:
            return meal_type.copy()  # Return copy for safety

    return None


def get_meal_type_color(meal_type_name: str) -> str:
    """Get color for a meal type using centralized Bootstrap colors.

    Args:
        meal_type_name: Name of the meal type

    Returns:
        Hex color code or default Bootstrap gray if not found

    Example:
        color = get_meal_type_color('breakfast')
        print(color)  # '#fd7e14'
    """
    meal_type_data = get_meal_type_data(meal_type_name)
    return meal_type_data["color"] if meal_type_data else BOOTSTRAP_COLORS["gray"]["hex"]


def get_meal_type_icon(meal_type_name: str) -> str:
    """Get icon for a meal type.

    Args:
        meal_type_name: Name of the meal type

    Returns:
        Font Awesome icon name or default question icon if not found

    Example:
        icon = get_meal_type_icon('breakfast')
        print(icon)  # 'bread-slice'
    """
    meal_type_data = get_meal_type_data(meal_type_name)
    return meal_type_data["icon"] if meal_type_data else "question"  # Default question mark


def get_meal_type_css_class(meal_type_name: str) -> str:
    """Get CSS class name for a meal type (consistent with category approach).

    Args:
        meal_type_name: Name of the meal type

    Returns:
        CSS class string for meal type styling

    Example:
        css_class = get_meal_type_css_class('breakfast')
        print(css_class)  # 'breakfast'
    """
    if not meal_type_name or not isinstance(meal_type_name, str):
        return "meal-type-default"

    # Normalize to lowercase and replace spaces with hyphens for CSS class
    normalized_name = meal_type_name.strip().lower().replace(" ", "-")

    # Validate meal type exists
    if get_meal_type_data(meal_type_name):
        return normalized_name

    return "meal-type-default"


def create_meal_type_map() -> Dict[str, MealTypeData]:
    """Create a dictionary mapping meal type names to data for fast lookup.

    Returns:
        Dictionary with meal type names as keys and MealTypeData as values

    Example:
        meal_type_map = create_meal_type_map()
        breakfast_data = meal_type_map.get('breakfast')
    """
    return {meal_type["name"]: meal_type for meal_type in MEAL_TYPE_CONSTANTS}


def validate_meal_type_name(meal_type_name: str) -> bool:
    """Validate if a meal type name exists in our constants.

    Args:
        meal_type_name: Name to validate

    Returns:
        True if meal type exists, False otherwise

    Example:
        is_valid = validate_meal_type_name('breakfast')  # True
        is_invalid = validate_meal_type_name('unknown')  # False
    """
    return get_meal_type_data(meal_type_name) is not None


def get_meal_type_for_time(hour: int) -> str:
    """Suggest a meal type based on the hour of day.

    Args:
        hour: Hour in 24-hour format (0-23)

    Returns:
        Suggested meal type name

    Example:
        meal_type = get_meal_type_for_time(8)  # 'breakfast'
        meal_type = get_meal_type_for_time(19)  # 'dinner'
    """
    # Input validation
    if not isinstance(hour, int) or hour < 0 or hour > 23:
        return "snacks"  # Default fallback

    # Time-based meal type suggestions
    if 6 <= hour < 11:
        return "breakfast"
    elif 11 <= hour < 15:
        return "lunch"
    elif 17 <= hour < 22:
        return "dinner"
    elif 22 <= hour or hour < 6:
        return "late night"
    else:
        return "snacks"  # Between meal times
