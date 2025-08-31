"""Centralized cuisine constants for the meal expense tracker.

This module contains cuisine types with associated colors and icons
for consistent display across the application.
Following TIGER principles: Safety, Performance, Developer Experience
"""

from typing import Dict, List, Optional, TypedDict


class CuisineData(TypedDict):
    """Type definition for cuisine data."""

    name: str
    color: str
    icon: str
    description: str


# Cuisine constants with colors and icons
CUISINE_CONSTANTS: List[CuisineData] = [
    {
        "name": "Chinese",
        "color": "#dc2626",  # Bolder Red
        "icon": "utensils",
        "description": "Chinese cuisine",
    },
    {
        "name": "Italian",
        "color": "#16a34a",  # Bolder Green
        "icon": "pizza-slice",
        "description": "Italian cuisine",
    },
    {
        "name": "Japanese",
        "color": "#e91e63",  # Bolder Pink
        "icon": "fish",
        "description": "Japanese cuisine",
    },
    {
        "name": "Mexican",
        "color": "#ea580c",  # Bolder Orange
        "icon": "pepper-hot",
        "description": "Mexican cuisine",
    },
    {
        "name": "Indian",
        "color": "#f59e0b",  # Bolder Yellow
        "icon": "fire",
        "description": "Indian cuisine",
    },
    {
        "name": "Thai",
        "color": "#059669",  # Bolder Teal
        "icon": "leaf",
        "description": "Thai cuisine",
    },
    {
        "name": "French",
        "color": "#7c3aed",  # Bolder Purple
        "icon": "wine-glass",
        "description": "French cuisine",
    },
    {
        "name": "American",
        "color": "#2563eb",  # Bolder Blue
        "icon": "utensils",
        "description": "American cuisine",
    },
    {
        "name": "Barbecue",
        "color": "#7c2d12",  # Bolder Brown (smoky, hearty)
        "icon": "drumstick-bite",
        "description": "Barbecue cuisine",
    },
    {
        "name": "Pizza",
        "color": "#16a34a",  # Bolder Green (similar to Italian)
        "icon": "pizza-slice",
        "description": "Pizza restaurants",
    },
    {
        "name": "Seafood",
        "color": "#0891b2",  # Bolder Cyan
        "icon": "fish",
        "description": "Seafood restaurants",
    },
    {
        "name": "Steakhouse",
        "color": "#7c2d12",  # Bolder Brown
        "icon": "drumstick-bite",
        "description": "Steakhouse restaurants",
    },
    {
        "name": "Sushi",
        "color": "#e91e63",  # Bolder Pink (similar to Japanese)
        "icon": "fish",
        "description": "Sushi restaurants",
    },
    {
        "name": "Korean",
        "color": "#dc2626",  # Bolder Red
        "icon": "fire",
        "description": "Korean cuisine",
    },
    {
        "name": "Vietnamese",
        "color": "#059669",  # Bolder Teal
        "icon": "utensils",
        "description": "Vietnamese cuisine",
    },
    {
        "name": "Mediterranean",
        "color": "#0891b2",  # Bolder Cyan
        "icon": "leaf",
        "description": "Mediterranean cuisine",
    },
    {
        "name": "Greek",
        "color": "#2563eb",  # Bolder Blue
        "icon": "leaf",
        "description": "Greek cuisine",
    },
    {
        "name": "Spanish",
        "color": "#f59e0b",  # Bolder Yellow
        "icon": "pepper-hot",
        "description": "Spanish cuisine",
    },
    {
        "name": "German",
        "color": "#6b7280",  # Bolder Gray
        "icon": "beer",
        "description": "German cuisine",
    },
    {
        "name": "British",
        "color": "#7c3aed",  # Bolder Purple
        "icon": "crown",
        "description": "British cuisine",
    },
    {
        "name": "Turkish",
        "color": "#dc2626",  # Bolder Red
        "icon": "star",
        "description": "Turkish cuisine",
    },
    {
        "name": "Lebanese",
        "color": "#16a34a",  # Bolder Green
        "icon": "leaf",
        "description": "Lebanese cuisine",
    },
    {
        "name": "Ethiopian",
        "color": "#f59e0b",  # Bolder Yellow
        "icon": "fire",
        "description": "Ethiopian cuisine",
    },
    {
        "name": "Moroccan",
        "color": "#ea580c",  # Bolder Orange
        "icon": "star",
        "description": "Moroccan cuisine",
    },
    {
        "name": "Brazilian",
        "color": "#16a34a",  # Bolder Green
        "icon": "leaf",
        "description": "Brazilian cuisine",
    },
    {
        "name": "Peruvian",
        "color": "#dc2626",  # Bolder Red
        "icon": "pepper-hot",
        "description": "Peruvian cuisine",
    },
    {
        "name": "Argentinian",
        "color": "#2563eb",  # Bolder Blue
        "icon": "drumstick-bite",
        "description": "Argentinian cuisine",
    },
    {
        "name": "Fast Food",  # TODO should remove this?
        "color": "#fbbf24",  # Bolder Amber
        "icon": "burger",
        "description": "Fast food cuisine",
    },
]


def get_cuisine_constants() -> List[CuisineData]:
    """Get all cuisine constants.

    Returns:
        List of cuisine data dictionaries with name, color, icon, and description

    Example:
        cuisines = get_cuisine_constants()
        print(cuisines[0])  # {'name': 'Chinese', 'color': '#dc3545', ...}
    """
    return CUISINE_CONSTANTS.copy()


def get_cuisine_names() -> List[str]:
    """Get list of all cuisine names.

    Returns:
        List of cuisine names in order

    Example:
        names = get_cuisine_names()
        print(names[:3])  # ['Chinese', 'Italian', 'Japanese']
    """
    return [cuisine["name"] for cuisine in CUISINE_CONSTANTS]


def get_cuisine_data(cuisine_name: str) -> Optional[CuisineData]:
    """Get cuisine data by name.

    Args:
        cuisine_name: Name of the cuisine to look up

    Returns:
        Cuisine data dictionary or None if not found

    Example:
        data = get_cuisine_data('Italian')
        print(data['color'])  # '#198754'
    """
    # Input validation - safety first
    if not cuisine_name or not isinstance(cuisine_name, str):
        return None

    # Enforce bounds to prevent excessive processing
    if len(cuisine_name) > 100:
        return None

    # Case-insensitive lookup
    normalized_name = cuisine_name.strip()

    for cuisine in CUISINE_CONSTANTS:
        if cuisine["name"].lower() == normalized_name.lower():
            return cuisine.copy()  # Return copy for safety

    return None


def get_cuisine_color(cuisine_name: str) -> str:
    """Get color for a cuisine type.

    Args:
        cuisine_name: Name of the cuisine

    Returns:
        Hex color code or default gray color if not found

    Example:
        color = get_cuisine_color('Mexican')
        print(color)  # '#fd7e14'
    """
    cuisine_data = get_cuisine_data(cuisine_name)
    return cuisine_data["color"] if cuisine_data else "#6c757d"  # Default gray


def get_cuisine_icon(cuisine_name: str) -> str:
    """Get icon for a cuisine type.

    Args:
        cuisine_name: Name of the cuisine

    Returns:
        Font Awesome icon name or default question icon if not found

    Example:
        icon = get_cuisine_icon('Italian')
        print(icon)  # 'pizza-slice'
    """
    cuisine_data = get_cuisine_data(cuisine_name)
    return cuisine_data["icon"] if cuisine_data else "question"  # Default question


def create_cuisine_map() -> Dict[str, CuisineData]:
    """Create a dictionary mapping cuisine names to data for fast lookup.

    Returns:
        Dictionary with cuisine names as keys and CuisineData as values

    Example:
        cuisine_map = create_cuisine_map()
        italian_data = cuisine_map.get('Italian')
    """
    return {cuisine["name"]: cuisine for cuisine in CUISINE_CONSTANTS}


def validate_cuisine_name(cuisine_name: str) -> bool:
    """Validate if a cuisine name exists in our constants.

    Args:
        cuisine_name: Name to validate

    Returns:
        True if cuisine exists, False otherwise

    Example:
        is_valid = validate_cuisine_name('Chinese')  # True
        is_invalid = validate_cuisine_name('Unknown')  # False
    """
    return get_cuisine_data(cuisine_name) is not None
