"""Centralized cuisine constants for the meal expense tracker.

This module contains cuisine types with associated colors and icons
for consistent display across the application.
Following TIGER principles: Safety, Performance, Developer Experience
"""

from typing import Dict, List, Optional, TypedDict

from .colors import BOOTSTRAP_COLORS


class CuisineData(TypedDict):
    """Type definition for cuisine data."""

    name: str
    color: str
    icon: str
    description: str


# Cuisine color mapping using Bootstrap colors for consistency
CUISINE_COLORS = {
    # Asian cuisines - reds and oranges
    "Chinese": BOOTSTRAP_COLORS["red"]["hex"],  # #dc3545
    "Japanese": BOOTSTRAP_COLORS["purple"]["hex"],  # #6f42c1
    "Korean": BOOTSTRAP_COLORS["red"]["hex"],  # #dc3545
    "Thai": BOOTSTRAP_COLORS["green"]["hex"],  # #198754
    "Vietnamese": BOOTSTRAP_COLORS["teal"]["hex"],  # #20c997
    "Indian": BOOTSTRAP_COLORS["orange"]["hex"],  # #fd7e14
    "Sushi": BOOTSTRAP_COLORS["purple"]["hex"],  # #6f42c1
    # European cuisines - blues and purples
    "Italian": BOOTSTRAP_COLORS["green"]["hex"],  # #198754
    "French": BOOTSTRAP_COLORS["indigo"]["hex"],  # #6610f2
    "German": BOOTSTRAP_COLORS["gray"]["hex"],  # #6c757d
    "Spanish": BOOTSTRAP_COLORS["yellow"]["hex"],  # #ffc107
    "Greek": BOOTSTRAP_COLORS["blue"]["hex"],  # #0d6efd
    "British": BOOTSTRAP_COLORS["indigo"]["hex"],  # #6610f2
    "Turkish": BOOTSTRAP_COLORS["red"]["hex"],  # #dc3545
    # American cuisines - blues and teals
    "American": BOOTSTRAP_COLORS["blue"]["hex"],  # #0d6efd
    "Mexican": BOOTSTRAP_COLORS["orange"]["hex"],  # #fd7e14
    "Barbecue": BOOTSTRAP_COLORS["red"]["hex"],  # #dc3545
    "Pizza": BOOTSTRAP_COLORS["green"]["hex"],  # #198754
    "Fast Food": BOOTSTRAP_COLORS["yellow"]["hex"],  # #ffc107
    # Specialty cuisines
    "Seafood": BOOTSTRAP_COLORS["cyan"]["hex"],  # #0dcaf0
    "Steakhouse": BOOTSTRAP_COLORS["red"]["hex"],  # #dc3545
    "Mediterranean": BOOTSTRAP_COLORS["cyan"]["hex"],  # #0dcaf0
    "Lebanese": BOOTSTRAP_COLORS["green"]["hex"],  # #198754
    "Ethiopian": BOOTSTRAP_COLORS["orange"]["hex"],  # #fd7e14
    "Moroccan": BOOTSTRAP_COLORS["orange"]["hex"],  # #fd7e14
    "Brazilian": BOOTSTRAP_COLORS["green"]["hex"],  # #198754
    "Peruvian": BOOTSTRAP_COLORS["red"]["hex"],  # #dc3545
    "Argentinian": BOOTSTRAP_COLORS["blue"]["hex"],  # #0d6efd
    "Breakfast & Brunch": BOOTSTRAP_COLORS["yellow"]["hex"],  # #ffc107 TODO handle alternatives better
    "Breakfast and Brunch": BOOTSTRAP_COLORS["yellow"]["hex"],  # #ffc107
    "Breakfast&Brunch": BOOTSTRAP_COLORS["yellow"]["hex"],  # #ffc107
    "Breakfast - Brunch": BOOTSTRAP_COLORS["yellow"]["hex"],  # #ffc107
    "Breakfast": BOOTSTRAP_COLORS["yellow"]["hex"],  # #ffc107
    "Brunch": BOOTSTRAP_COLORS["yellow"]["hex"],  # #ffc107
    "Coffee House": "#92400e",  # Custom brown
    "Coffee Bar": "#92400e",  # Custom brown
    "Cafe": "#92400e",  # Custom brown
    "Deli": BOOTSTRAP_COLORS["teal"]["hex"],  # #20c997
    "Bakery": BOOTSTRAP_COLORS["yellow"]["hex"],  # #ffc107
    "Ice Cream": "#e83e8c",  # Custom pink
}

# Cuisine constants with colors and icons
CUISINE_CONSTANTS: List[CuisineData] = [
    {
        "name": "Chinese",
        "color": "#dc2626",  # Bolder Red
        "icon": "bowl-rice",  # Traditional Chinese rice bowl
        "description": "Chinese cuisine",
    },
    {
        "name": "Italian",
        "color": "#16a34a",  # Bolder Green
        "icon": "pizza-slice",  # Iconic Italian food
        "description": "Italian cuisine",
    },
    {
        "name": "Japanese",
        "color": "#bc002d",  # Japanese Flag Red
        "icon": "fish",  # Sushi/sashimi focus
        "description": "Japanese cuisine",
    },
    {
        "name": "Mexican",
        "color": "#006847",  # Mexican Flag Green
        "icon": "pepper-hot",  # Spicy Mexican food
        "description": "Mexican cuisine",
    },
    {
        "name": "Indian",
        "color": "#f59e0b",  # Bolder Yellow
        "icon": "fire",  # Spicy Indian cuisine
        "description": "Indian cuisine",
    },
    {
        "name": "Thai",
        "color": "#059669",  # Bolder Teal
        "icon": "leaf",  # Fresh herbs and ingredients
        "description": "Thai cuisine",
    },
    {
        "name": "French",
        "color": "#7c3aed",  # Bolder Purple
        "icon": "wine-glass",  # French dining culture
        "description": "French cuisine",
    },
    {
        "name": "American",
        "color": "#2563eb",  # Bolder Blue
        "icon": "flag-usa",  # US flag (Font Awesome has this one)
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
        "icon": "shrimp",  # Maritime/seafood symbol
        "description": "Seafood restaurants",
    },
    {
        "name": "Steakhouse",
        "color": "#7c2d12",  # Bolder Brown
        "icon": "cow",  # Steakhouse/beef symbol
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
        "icon": "fire",  # Spicy Korean cuisine
        "description": "Korean cuisine",
    },
    {
        "name": "Vietnamese",
        "color": "#da020e",  # Vietnamese Flag Red
        "icon": "bowl-food",  # Vietnamese pho bowls
        "description": "Vietnamese cuisine",
    },
    {
        "name": "Mediterranean",
        "color": "#0891b2",  # Bolder Cyan
        "icon": "seedling",  # Fresh herbs and ingredients
        "description": "Mediterranean cuisine",
    },
    {
        "name": "Greek",
        "color": "#2563eb",  # Bolder Blue
        "icon": "leaf",  # Mediterranean herbs
        "description": "Greek cuisine",
    },
    {
        "name": "Spanish",
        "color": "#f59e0b",  # Bolder Yellow
        "icon": "pepper-hot",  # Spanish spices
        "description": "Spanish cuisine",
    },
    {
        "name": "German",
        "color": "#6b7280",  # Bolder Gray
        "icon": "beer",  # German beer culture
        "description": "German cuisine",
    },
    {
        "name": "British",
        "color": "#7c3aed",  # Bolder Purple
        "icon": "crown",  # British culture
        "description": "British cuisine",
    },
    {
        "name": "Turkish",
        "color": "#dc2626",  # Bolder Red
        "icon": "star",  # Turkish star
        "description": "Turkish cuisine",
    },
    {
        "name": "Lebanese",
        "color": "#16a34a",  # Bolder Green
        "icon": "leaf",  # Mediterranean herbs
        "description": "Lebanese cuisine",
    },
    {
        "name": "Ethiopian",
        "color": "#f59e0b",  # Bolder Yellow
        "icon": "fire",  # Spicy Ethiopian cuisine
        "description": "Ethiopian cuisine",
    },
    {
        "name": "Moroccan",
        "color": "#ea580c",  # Bolder Orange
        "icon": "star",  # Moroccan culture
        "description": "Moroccan cuisine",
    },
    {
        "name": "Brazilian",
        "color": "#16a34a",  # Bolder Green
        "icon": "drumstick-bite",  # Churrasco/grilled meat
        "description": "Brazilian cuisine",
    },
    {
        "name": "Peruvian",
        "color": "#dc2626",  # Bolder Red
        "icon": "flag",  # Peruvian flag representation
        "description": "Peruvian cuisine",
    },
    {
        "name": "Argentinian",
        "color": "#2563eb",  # Bolder Blue
        "icon": "flag",  # Argentinian flag representation
        "description": "Argentinian cuisine",
    },
    {
        "name": "Fast Food",  # TODO should remove this?
        "color": "#fbbf24",  # Bolder Amber
        "icon": "hamburger",
        "description": "Fast food cuisine",
    },
    {
        "name": "Breakfast & Brunch",
        "color": "#f59e0b",  # Bolder Yellow
        "icon": "coffee",
        "description": "Breakfast and brunch restaurants",
    },
    {
        "name": "Breakfast and Brunch",
        "color": "#f59e0b",  # Bolder Yellow
        "icon": "coffee",
        "description": "Breakfast and brunch restaurants",
    },
    {
        "name": "Breakfast&Brunch",
        "color": "#f59e0b",  # Bolder Yellow
        "icon": "coffee",
        "description": "Breakfast and brunch restaurants",
    },
    {
        "name": "Breakfast - Brunch",
        "color": "#f59e0b",  # Bolder Yellow
        "icon": "coffee",
        "description": "Breakfast and brunch restaurants",
    },
    {
        "name": "Breakfast",
        "color": "#f59e0b",  # Bolder Yellow
        "icon": "coffee",
        "description": "Breakfast restaurants",
    },
    {
        "name": "Brunch",
        "color": "#f59e0b",  # Bolder Yellow
        "icon": "coffee",
        "description": "Brunch restaurants",
    },
    {
        "name": "Coffee House",
        "color": "#92400e",  # Custom brown
        "icon": "coffee",
        "description": "Coffee houses and cafes",
    },
    {
        "name": "Coffee Bar",
        "color": "#92400e",  # Custom brown
        "icon": "coffee",
        "description": "Coffee bars and cafes",
    },
    {
        "name": "Cafe",
        "color": "#92400e",  # Bolder Brown
        "icon": "coffee",
        "description": "Cafe and coffee shops",
    },
    {
        "name": "Deli",
        "color": "#059669",  # Bolder Teal
        "icon": "sandwich",
        "description": "Deli and sandwich shops",
    },
    {
        "name": "Bakery",
        "color": "#fbbf24",  # Bolder Amber
        "icon": "bread-slice",
        "description": "Bakery and pastry shops",
    },
    {
        "name": "Ice Cream",
        "color": "#ec4899",  # Bolder Pink
        "icon": "ice-cream",
        "description": "Ice cream and dessert shops",
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


def _fuzzy_match_cuisine(normalized_name: str) -> Optional[CuisineData]:
    """Helper function for fuzzy cuisine matching.

    Args:
        normalized_name: Normalized cuisine name to match

    Returns:
        Matched cuisine data or None
    """
    for cuisine in CUISINE_CONSTANTS:
        cuisine_lower = cuisine["name"].lower()

        # Special handling for breakfast/brunch variations
        if "breakfast" in normalized_name or "brunch" in normalized_name:
            if "breakfast" in cuisine_lower or "brunch" in cuisine_lower:
                return cuisine.copy()

        # Special handling for other common variations
        elif "fast food" in normalized_name and "fast food" in cuisine_lower:
            return cuisine.copy()
        elif "ice cream" in normalized_name and "ice cream" in cuisine_lower:
            return cuisine.copy()
        elif "coffee" in normalized_name and "cafe" in cuisine_lower:
            return cuisine.copy()

    return None


def get_cuisine_data(cuisine_name: str) -> Optional[CuisineData]:
    """Get cuisine data by name with fuzzy matching for common variations.

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

    # Normalize the input
    normalized_name = cuisine_name.strip().lower()

    # Remove common punctuation and extra spaces
    normalized_name = normalized_name.replace("&", " and ").replace("-", " ")
    normalized_name = " ".join(normalized_name.split())  # Remove extra spaces

    # First, try exact match (case-insensitive)
    for cuisine in CUISINE_CONSTANTS:
        if cuisine["name"].lower() == normalized_name:
            return cuisine.copy()  # Return copy for safety

    # Then, try fuzzy matching
    return _fuzzy_match_cuisine(normalized_name)


def get_cuisine_color(cuisine_name: str) -> str:
    """Get color for a cuisine using centralized Bootstrap colors.

    Args:
        cuisine_name: Name of the cuisine

    Returns:
        Hex color code or default Bootstrap gray if not found

    Example:
        color = get_cuisine_color('Mexican')
        print(color)  # '#fd7e14'
    """
    if not cuisine_name or not isinstance(cuisine_name, str):
        return BOOTSTRAP_COLORS["gray"]["hex"]

    # Try centralized color mapping first
    if cuisine_name in CUISINE_COLORS:
        return CUISINE_COLORS[cuisine_name]

    # Fallback to cuisine data
    cuisine_data = get_cuisine_data(cuisine_name)
    return cuisine_data["color"] if cuisine_data else BOOTSTRAP_COLORS["gray"]["hex"]


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


def get_cuisine_css_class(cuisine_name: str) -> str:
    """Get CSS class name for a cuisine (consistent with category approach).

    Args:
        cuisine_name: Name of the cuisine

    Returns:
        CSS class string for cuisine styling

    Example:
        css_class = get_cuisine_css_class('Chinese')
        print(css_class)  # 'chinese'
    """
    if not cuisine_name or not isinstance(cuisine_name, str):
        return "cuisine-default"

    # Normalize to lowercase and replace spaces with hyphens for CSS class
    normalized_name = cuisine_name.strip().lower().replace(" ", "-")

    # Validate cuisine exists
    if get_cuisine_data(cuisine_name):
        return normalized_name

    return "cuisine-default"
