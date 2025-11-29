"""Cuisine constants for the meal expense tracker.

Single source of truth based on Google Places New API supported types.
"""

from typing import Dict, List, Optional

# Google Places API supported cuisine types (single point of truth)
# Keys are Google Places API types, values are user-friendly display names
GOOGLE_CUISINE_MAPPING = {
    # Core restaurant types that Google Places API supports
    "american_restaurant": "American",
    "chinese_restaurant": "Chinese",
    "italian_restaurant": "Italian",
    "japanese_restaurant": "Japanese",
    "mexican_restaurant": "Mexican",
    "french_restaurant": "French",
    "german_restaurant": "German",
    "greek_restaurant": "Greek",
    "indian_restaurant": "Indian",
    "korean_restaurant": "Korean",
    "thai_restaurant": "Thai",
    "vietnamese_restaurant": "Vietnamese",
    "mediterranean_restaurant": "Mediterranean",
    "spanish_restaurant": "Spanish",
    "lebanese_restaurant": "Lebanese",
    "turkish_restaurant": "Turkish",
    "moroccan_restaurant": "Moroccan",
    "middle_eastern_restaurant": "Middle Eastern",
    # Specialty restaurant types
    "pizza_restaurant": "Pizza",
    "seafood_restaurant": "Seafood",
    "steak_house": "Steakhouse",
    "sushi_restaurant": "Sushi",
    "fast_food_restaurant": "Fast Food",
    # Other supported types
    "barbecue_restaurant": "Barbecue",
    "breakfast_restaurant": "Breakfast",
    "cafe": "Cafe",
    "diner": "Diner",
    "vegan_restaurant": "Vegan",
    "vegetarian_restaurant": "Vegetarian",
}

# User-friendly cuisine display data (derived from Google mapping)
CUISINES: dict[str, dict[str, str]] = {}

# Color scheme for consistent UI display
_CUISINE_COLORS = {
    "American": {"color": "#0d6efd", "icon": "flag-usa"},
    "Chinese": {"color": "#dc3545", "icon": "bowl-rice"},
    "Italian": {"color": "#198754", "icon": "pizza-slice"},
    "Japanese": {"color": "#6f42c1", "icon": "seedling"},
    "Mexican": {"color": "#fd7e14", "icon": "pepper-hot"},
    "French": {"color": "#6610f2", "icon": "utensils"},
    "German": {"color": "#6c757d", "icon": "utensils"},
    "Greek": {"color": "#0d6efd", "icon": "utensils"},
    "Indian": {"color": "#fd7e14", "icon": "fire"},
    "Korean": {"color": "#dc3545", "icon": "utensils"},
    "Thai": {"color": "#198754", "icon": "utensils"},
    "Vietnamese": {"color": "#20c997", "icon": "utensils"},
    "Mediterranean": {"color": "#0dcaf0", "icon": "utensils"},
    "Spanish": {"color": "#ffc107", "icon": "utensils"},
    "Lebanese": {"color": "#198754", "icon": "utensils"},
    "Turkish": {"color": "#dc3545", "icon": "utensils"},
    "Moroccan": {"color": "#fd7e14", "icon": "utensils"},
    "Middle Eastern": {"color": "#fd7e14", "icon": "utensils"},
    "Pizza": {"color": "#198754", "icon": "pizza-slice"},
    "Seafood": {"color": "#0dcaf0", "icon": "fish"},
    "Steakhouse": {"color": "#dc3545", "icon": "drumstick-bite"},
    "Sushi": {"color": "#6f42c1", "icon": "fish"},
    "Fast Food": {"color": "#ffc107", "icon": "hamburger"},
    "Barbecue": {"color": "#dc3545", "icon": "fire"},
    "Breakfast": {"color": "#fd7e14", "icon": "bread-slice"},
    "Cafe": {"color": "#6c757d", "icon": "coffee"},
    "Diner": {"color": "#6c757d", "icon": "utensils"},
    "Vegan": {"color": "#198754", "icon": "leaf"},
    "Vegetarian": {"color": "#198754", "icon": "leaf"},
}

# Build CUISINES dict from the mapping
for google_type, display_name in GOOGLE_CUISINE_MAPPING.items():
    if display_name in _CUISINE_COLORS:
        CUISINES[display_name] = {
            **_CUISINE_COLORS[display_name],
            "google_type": google_type,
            "description": f"{display_name} cuisine",
        }
    else:
        # Default styling for unmapped cuisines
        CUISINES[display_name] = {
            "color": "#6c757d",
            "icon": "utensils",
            "google_type": google_type,
            "description": f"{display_name} cuisine",
        }


# Helper functions
def get_cuisine_constants() -> list[dict[str, str]]:
    """Get list of all cuisine data."""
    return [{"name": k, **v} for k, v in CUISINES.items()]


def get_cuisine_names() -> list[str]:
    """Get list of all cuisine names."""
    return list(CUISINES.keys())


def get_cuisine_data(cuisine_name: str) -> dict[str, str] | None:
    """Get cuisine data by name."""
    if not cuisine_name or not isinstance(cuisine_name, str):
        return None

    # Try exact match first, then case-insensitive match
    cuisine_name = cuisine_name.strip()
    if cuisine_name in CUISINES:
        return CUISINES[cuisine_name]

    # Case-insensitive lookup
    cuisine_lower = cuisine_name.lower()
    for name, data in CUISINES.items():
        if name.lower() == cuisine_lower:
            return data

    return None


def get_cuisine_color(cuisine_name: str) -> str:
    """Get color for a cuisine."""
    data = get_cuisine_data(cuisine_name)
    return data["color"] if data else "#6c757d"


def get_cuisine_icon(cuisine_name: str) -> str:
    """Get icon for a cuisine."""
    data = get_cuisine_data(cuisine_name)
    return data["icon"] if data else "question"


def validate_cuisine_name(cuisine_name: str) -> bool:
    """Check if cuisine exists."""
    return get_cuisine_data(cuisine_name) is not None


def get_google_type_for_cuisine(cuisine_name: str) -> str | None:
    """Get Google Places API type for a cuisine name."""
    data = get_cuisine_data(cuisine_name)
    return data["google_type"] if data else None


def get_cuisine_for_google_type(google_type: str) -> str | None:
    """Get user-friendly cuisine name for Google Places API type."""
    if not google_type or not isinstance(google_type, str):
        return None

    google_type = google_type.strip().lower()
    for cuisine_name, data in CUISINES.items():
        if data["google_type"].lower() == google_type:
            return cuisine_name

    return None


def format_cuisine_type(cuisine_type: str, max_length: int = 100) -> str:
    """Format cuisine type with proper capitalization and length limits."""
    if not cuisine_type:
        return ""

    # Capitalize each word
    formatted = " ".join(word.capitalize() for word in str(cuisine_type).split())

    # Truncate if too long
    if len(formatted) > max_length:
        formatted = formatted[:max_length].rstrip()

    return formatted
