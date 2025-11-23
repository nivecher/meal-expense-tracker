"""Restaurant type constants for the meal expense tracker.

Single source of truth for restaurant types based on Google Places API types.
"""

from typing import Dict

# Google Places API supported restaurant types (single point of truth)
# Keys are Google Places API types, values are user-friendly display names
GOOGLE_RESTAURANT_TYPE_MAPPING = {
    # Restaurant types that are primarily food establishments
    "restaurant": "Restaurant",
    "cafe": "Cafe",
    "bar": "Bar",
    "bakery": "Bakery",
    "dessert_shop": "Dessert Shop",
    "ice_cream_shop": "Ice Cream Shop",
    "deli": "Deli",
    "food_court": "Food Court",
    "meal_takeaway": "Takeaway",
    "meal_delivery": "Delivery",
    "fast_food_restaurant": "Fast Food",
    "fine_dining_restaurant": "Fine Dining",
    "steak_house": "Steak House",
    "seafood_restaurant": "Seafood Restaurant",
    "pizza_restaurant": "Pizza Restaurant",
    "sushi_restaurant": "Sushi Restaurant",
    "breakfast_restaurant": "Breakfast Restaurant",
    "coffee_shop": "Coffee Shop",
    "sandwich_shop": "Sandwich Shop",
    "donut_shop": "Donut Shop",
    "juice_shop": "Juice Shop",
    "wine_bar": "Wine Bar",
    "pub": "Pub",
    "tea_house": "Tea House",
    # Non-restaurant food establishments
    "convenience_store": "Convenience Store",
    "grocery_store": "Grocery Store",
    "supermarket": "Supermarket",
    "gas_station": "Gas Station",
    # Default for non-food establishments
    "other": "Other",
}

# User-friendly restaurant type display data (derived from Google mapping)
RESTAURANT_TYPES: Dict[str, Dict[str, str]] = {}

# Color scheme for consistent UI display
_RESTAURANT_TYPE_COLORS = {
    "Restaurant": {"color": "#0d6efd", "icon": "utensils"},
    "Cafe": {"color": "#6c757d", "icon": "coffee"},
    "Bar": {"color": "#dc3545", "icon": "glass-cheers"},
    "Bakery": {"color": "#ffc107", "icon": "bread-slice"},
    "Dessert Shop": {"color": "#e83e8c", "icon": "birthday-cake"},
    "Ice Cream Shop": {"color": "#fd7e14", "icon": "ice-cream"},
    "Deli": {"color": "#20c997", "icon": "cut"},
    "Food Court": {"color": "#6f42c1", "icon": "utensils"},
    "Takeaway": {"color": "#17a2b8", "icon": "shopping-bag"},
    "Delivery": {"color": "#28a745", "icon": "truck"},
    "Fast Food": {"color": "#ffc107", "icon": "hamburger"},
    "Fine Dining": {"color": "#6f42c1", "icon": "gem"},
    "Steak House": {"color": "#dc3545", "icon": "drumstick-bite"},
    "Seafood Restaurant": {"color": "#0dcaf0", "icon": "fish"},
    "Pizza Restaurant": {"color": "#198754", "icon": "pizza-slice"},
    "Sushi Restaurant": {"color": "#6f42c1", "icon": "fish"},
    "Breakfast Restaurant": {"color": "#fd7e14", "icon": "egg"},
    "Coffee Shop": {"color": "#6c757d", "icon": "coffee"},
    "Sandwich Shop": {"color": "#20c997", "icon": "cut"},
    "Donut Shop": {"color": "#e83e8c", "icon": "birthday-cake"},
    "Juice Shop": {"color": "#198754", "icon": "leaf"},
    "Wine Bar": {"color": "#6f42c1", "icon": "wine-bottle"},
    "Pub": {"color": "#dc3545", "icon": "beer-mug-empty"},
    "Tea House": {"color": "#6c757d", "icon": "mug-hot"},
    "Convenience Store": {"color": "#6c757d", "icon": "store"},
    "Grocery Store": {"color": "#6c757d", "icon": "store"},
    "Supermarket": {"color": "#6c757d", "icon": "store"},
    "Gas Station": {"color": "#6c757d", "icon": "fuel-pump"},
    "Other": {"color": "#6c757d", "icon": "question-circle"},
}

# Build RESTAURANT_TYPES dict from the mapping
for google_type, display_name in GOOGLE_RESTAURANT_TYPE_MAPPING.items():
    if display_name in _RESTAURANT_TYPE_COLORS:
        RESTAURANT_TYPES[display_name] = {
            **_RESTAURANT_TYPE_COLORS[display_name],
            "google_type": google_type,
            "description": f"{display_name} establishment",
        }
    else:
        # Default styling for unmapped types
        RESTAURANT_TYPES[display_name] = {
            "color": "#6c757d",
            "icon": "question-circle",
            "google_type": google_type,
            "description": f"{display_name} establishment",
        }


# Helper functions
def get_restaurant_type_constants():
    """Get list of all restaurant type data."""
    return [{"name": k, **v} for k, v in RESTAURANT_TYPES.items()]


def get_restaurant_type_names():
    """Get list of all restaurant type names."""
    return list(RESTAURANT_TYPES.keys())


def get_restaurant_type_data(type_name):
    """Get restaurant type data by name."""
    if not type_name or not isinstance(type_name, str):
        return None

    # Try exact match first, then case-insensitive match
    type_name = type_name.strip()
    if type_name in RESTAURANT_TYPES:
        return RESTAURANT_TYPES[type_name]

    # Case-insensitive lookup
    type_lower = type_name.lower()
    for name, data in RESTAURANT_TYPES.items():
        if name.lower() == type_lower:
            return data

    return None


def get_restaurant_type_color(type_name):
    """Get color for a restaurant type."""
    data = get_restaurant_type_data(type_name)
    return data["color"] if data else "#6c757d"


def get_restaurant_type_icon(type_name):
    """Get icon for a restaurant type."""
    data = get_restaurant_type_data(type_name)
    return data["icon"] if data else "question-circle"


def validate_restaurant_type_name(type_name):
    """Check if restaurant type exists."""
    return get_restaurant_type_data(type_name) is not None


def get_google_type_for_restaurant_type(type_name):
    """Get Google Places API type for a restaurant type name."""
    data = get_restaurant_type_data(type_name)
    return data["google_type"] if data else None


def get_restaurant_type_for_google_type(google_type):
    """Get user-friendly restaurant type name for Google Places API type."""
    if not google_type or not isinstance(google_type, str):
        return None

    google_type = google_type.strip().lower()
    for type_name, data in RESTAURANT_TYPES.items():
        if data["google_type"].lower() == google_type:
            return type_name

    return None


def format_restaurant_type(type_name, max_length=100):
    """Format restaurant type with proper capitalization and length limits."""
    if not type_name:
        return ""

    # Capitalize each word
    formatted = " ".join(word.capitalize() for word in str(type_name).split())

    # Truncate if too long
    if len(formatted) > max_length:
        formatted = formatted[:max_length].rstrip()

    return formatted


def get_food_establishment_types():
    """Get list of Google Places types that are primarily food establishments."""
    food_types = []
    for google_type, display_name in GOOGLE_RESTAURANT_TYPE_MAPPING.items():
        if google_type not in ["convenience_store", "grocery_store", "supermarket", "gas_station", "other"]:
            food_types.append(google_type)
    return food_types


def get_non_restaurant_types():
    """Get list of Google Places types that are not restaurants but may sell food."""
    return ["convenience_store", "grocery_store", "supermarket", "gas_station"]


def is_food_establishment(primary_type):
    """Check if a Google Places primary type represents a food establishment."""
    if not primary_type:
        return False
    return primary_type in get_food_establishment_types()


def map_google_primary_type_to_display_type(primary_type):
    """Map Google Places primary type to display type, defaulting to 'Other' for non-restaurant types."""
    if not primary_type:
        return "Other"

    display_type = get_restaurant_type_for_google_type(primary_type)
    if display_type:
        return display_type

    # Default non-restaurant types to "Other"
    if primary_type not in get_food_establishment_types():
        return "Other"

    return "Restaurant"  # Fallback for unmapped food types
