"""Restaurant type constants for the meal expense tracker.

Single source of truth for restaurant types based on Google Places API types.
"""

from typing import Dict, List, Optional

# Google Places API supported restaurant types (single point of truth)
# Keys are Google Places API types, values are user-friendly display names
# Source: https://developers.google.com/maps/documentation/places/web-service/place-types
GOOGLE_RESTAURANT_TYPE_MAPPING = {
    # Food and Drink (Table A) - alphabetical
    "acai_shop": "Acai Shop",
    "afghani_restaurant": "Afghani Restaurant",
    "african_restaurant": "African Restaurant",
    "american_restaurant": "American Restaurant",
    "argentinian_restaurant": "Argentinian Restaurant",
    "asian_fusion_restaurant": "Asian Fusion Restaurant",
    "asian_restaurant": "Asian Restaurant",
    "australian_restaurant": "Australian Restaurant",
    "austrian_restaurant": "Austrian Restaurant",
    "bagel_shop": "Bagel Shop",
    "bakery": "Bakery",
    "bangladeshi_restaurant": "Bangladeshi Restaurant",
    "bar": "Bar",
    "bar_and_grill": "Bar and Grill",
    "barbecue_restaurant": "Barbecue Restaurant",
    "basque_restaurant": "Basque Restaurant",
    "bavarian_restaurant": "Bavarian Restaurant",
    "beer_garden": "Beer Garden",
    "belgian_restaurant": "Belgian Restaurant",
    "bistro": "Bistro",
    "brazilian_restaurant": "Brazilian Restaurant",
    "breakfast_restaurant": "Breakfast Restaurant",
    "brewery": "Brewery",
    "brewpub": "Brewpub",
    "british_restaurant": "British Restaurant",
    "brunch_restaurant": "Brunch Restaurant",
    "buffet_restaurant": "Buffet Restaurant",
    "burmese_restaurant": "Burmese Restaurant",
    "burrito_restaurant": "Burrito Restaurant",
    "cafe": "Cafe",
    "cafeteria": "Cafeteria",
    "cajun_restaurant": "Cajun Restaurant",
    "cake_shop": "Cake Shop",
    "californian_restaurant": "Californian Restaurant",
    "cambodian_restaurant": "Cambodian Restaurant",
    "candy_store": "Candy Store",
    "cantonese_restaurant": "Cantonese Restaurant",
    "caribbean_restaurant": "Caribbean Restaurant",
    "cat_cafe": "Cat Cafe",
    "chicken_restaurant": "Chicken Restaurant",
    "chicken_wings_restaurant": "Chicken Wings Restaurant",
    "chilean_restaurant": "Chilean Restaurant",
    "chinese_noodle_restaurant": "Chinese Noodle Restaurant",
    "chinese_restaurant": "Chinese Restaurant",
    "chocolate_factory": "Chocolate Factory",
    "chocolate_shop": "Chocolate Shop",
    "cocktail_bar": "Cocktail Bar",
    "coffee_roastery": "Coffee Roastery",
    "coffee_shop": "Coffee Shop",
    "coffee_stand": "Coffee Stand",
    "colombian_restaurant": "Colombian Restaurant",
    "confectionery": "Confectionery",
    "croatian_restaurant": "Croatian Restaurant",
    "cuban_restaurant": "Cuban Restaurant",
    "czech_restaurant": "Czech Restaurant",
    "danish_restaurant": "Danish Restaurant",
    "deli": "Deli",
    "dessert_restaurant": "Dessert Restaurant",
    "dessert_shop": "Dessert Shop",
    "dim_sum_restaurant": "Dim Sum Restaurant",
    "diner": "Diner",
    "dog_cafe": "Dog Cafe",
    "donut_shop": "Donut Shop",
    "dumpling_restaurant": "Dumpling Restaurant",
    "dutch_restaurant": "Dutch Restaurant",
    "eastern_european_restaurant": "Eastern European Restaurant",
    "ethiopian_restaurant": "Ethiopian Restaurant",
    "european_restaurant": "European Restaurant",
    "falafel_restaurant": "Falafel Restaurant",
    "family_restaurant": "Family Restaurant",
    "fast_food_restaurant": "Fast Food Restaurant",
    "filipino_restaurant": "Filipino Restaurant",
    "fine_dining_restaurant": "Fine Dining",
    "fish_and_chips_restaurant": "Fish and Chips Restaurant",
    "fondue_restaurant": "Fondue Restaurant",
    "food_court": "Food Court",
    "french_restaurant": "French Restaurant",
    "fusion_restaurant": "Fusion Restaurant",
    "gastropub": "Gastropub",
    "german_restaurant": "German Restaurant",
    "greek_restaurant": "Greek Restaurant",
    "gyro_restaurant": "Gyro Restaurant",
    "halal_restaurant": "Halal Restaurant",
    "hamburger_restaurant": "Hamburger Restaurant",
    "hawaiian_restaurant": "Hawaiian Restaurant",
    "hookah_bar": "Hookah Bar",
    "hot_dog_restaurant": "Hot Dog Restaurant",
    "hot_dog_stand": "Hot Dog Stand",
    "hot_pot_restaurant": "Hot Pot Restaurant",
    "hungarian_restaurant": "Hungarian Restaurant",
    "ice_cream_shop": "Ice Cream Shop",
    "indian_restaurant": "Indian Restaurant",
    "indonesian_restaurant": "Indonesian Restaurant",
    "irish_pub": "Irish Pub",
    "irish_restaurant": "Irish Restaurant",
    "israeli_restaurant": "Israeli Restaurant",
    "italian_restaurant": "Italian Restaurant",
    "japanese_curry_restaurant": "Japanese Curry Restaurant",
    "japanese_izakaya_restaurant": "Japanese Izakaya Restaurant",
    "japanese_restaurant": "Japanese Restaurant",
    "juice_shop": "Juice Shop",
    "kebab_shop": "Kebab Shop",
    "korean_barbecue_restaurant": "Korean Barbecue Restaurant",
    "korean_restaurant": "Korean Restaurant",
    "latin_american_restaurant": "Latin American Restaurant",
    "lebanese_restaurant": "Lebanese Restaurant",
    "lounge_bar": "Lounge Bar",
    "malaysian_restaurant": "Malaysian Restaurant",
    "meal_delivery": "Delivery",
    "meal_takeaway": "Takeaway",
    "mediterranean_restaurant": "Mediterranean Restaurant",
    "mexican_restaurant": "Mexican Restaurant",
    "middle_eastern_restaurant": "Middle Eastern Restaurant",
    "mongolian_barbecue_restaurant": "Mongolian Barbecue Restaurant",
    "moroccan_restaurant": "Moroccan Restaurant",
    "noodle_shop": "Noodle Shop",
    "north_indian_restaurant": "North Indian Restaurant",
    "oyster_bar_restaurant": "Oyster Bar Restaurant",
    "pakistani_restaurant": "Pakistani Restaurant",
    "pastry_shop": "Pastry Shop",
    "persian_restaurant": "Persian Restaurant",
    "peruvian_restaurant": "Peruvian Restaurant",
    "pizza_delivery": "Pizza Delivery",
    "pizza_restaurant": "Pizza Restaurant",
    "polish_restaurant": "Polish Restaurant",
    "portuguese_restaurant": "Portuguese Restaurant",
    "pub": "Pub",
    "ramen_restaurant": "Ramen Restaurant",
    "restaurant": "Restaurant",
    "romanian_restaurant": "Romanian Restaurant",
    "russian_restaurant": "Russian Restaurant",
    "salad_shop": "Salad Shop",
    "sandwich_shop": "Sandwich Shop",
    "scandinavian_restaurant": "Scandinavian Restaurant",
    "seafood_restaurant": "Seafood Restaurant",
    "shawarma_restaurant": "Shawarma Restaurant",
    "snack_bar": "Snack Bar",
    "soul_food_restaurant": "Soul Food Restaurant",
    "soup_restaurant": "Soup Restaurant",
    "south_american_restaurant": "South American Restaurant",
    "south_indian_restaurant": "South Indian Restaurant",
    "southwestern_us_restaurant": "Southwestern US Restaurant",
    "spanish_restaurant": "Spanish Restaurant",
    "sports_bar": "Sports Bar",
    "sri_lankan_restaurant": "Sri Lankan Restaurant",
    "steak_house": "Steak House",
    "sushi_restaurant": "Sushi Restaurant",
    "swiss_restaurant": "Swiss Restaurant",
    "taco_restaurant": "Taco Restaurant",
    "taiwanese_restaurant": "Taiwanese Restaurant",
    "tapas_restaurant": "Tapas Restaurant",
    "tea_house": "Tea House",
    "tex_mex_restaurant": "Tex-Mex Restaurant",
    "thai_restaurant": "Thai Restaurant",
    "tibetan_restaurant": "Tibetan Restaurant",
    "tonkatsu_restaurant": "Tonkatsu Restaurant",
    "turkish_restaurant": "Turkish Restaurant",
    "ukrainian_restaurant": "Ukrainian Restaurant",
    "vegan_restaurant": "Vegan Restaurant",
    "vegetarian_restaurant": "Vegetarian Restaurant",
    "vietnamese_restaurant": "Vietnamese Restaurant",
    "western_restaurant": "Western Restaurant",
    "wine_bar": "Wine Bar",
    "winery": "Winery",
    "yakiniku_restaurant": "Yakiniku Restaurant",
    "yakitori_restaurant": "Yakitori Restaurant",
    # Shopping (food-related)
    "asian_grocery_store": "Asian Grocery Store",
    "butcher_shop": "Butcher Shop",
    "convenience_store": "Convenience Store",
    "discount_supermarket": "Discount Supermarket",
    "farmers_market": "Farmers Market",
    "food_store": "Food Store",
    "grocery_store": "Grocery Store",
    "health_food_store": "Health Food Store",
    "hypermarket": "Hypermarket",
    "liquor_store": "Liquor Store",
    "market": "Market",
    "supermarket": "Supermarket",
    "tea_store": "Tea Store",
    # Automotive (food-related)
    "gas_station": "Gas Station",
    # Services (food-related)
    "catering_service": "Catering Service",
    "food_delivery": "Food Delivery",
    # Entertainment (food-related)
    "internet_cafe": "Internet Cafe",
    # Default for unmapped types
    "other": "Other",
}

# Top 10 most popular types shown first in form picklist (by Google type key)
_POPULAR_TYPE_ORDER = [
    "restaurant",
    "cafe",
    "bar",
    "bakery",
    "fast_food_restaurant",
    "pizza_restaurant",
    "coffee_shop",
    "mexican_restaurant",
    "chinese_restaurant",
    "italian_restaurant",
]

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
    "Fast Food Restaurant": {"color": "#ffc107", "icon": "hamburger"},
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
RESTAURANT_TYPES: dict[str, dict[str, str]] = {}
for google_type, display_name in GOOGLE_RESTAURANT_TYPE_MAPPING.items():
    if display_name in _RESTAURANT_TYPE_COLORS:
        RESTAURANT_TYPES[display_name] = {
            **_RESTAURANT_TYPE_COLORS[display_name],
            "google_type": google_type,
            "description": f"{display_name} establishment",
        }
    else:
        RESTAURANT_TYPES[display_name] = {
            "color": "#6c757d",
            "icon": "question-circle",
            "google_type": google_type,
            "description": f"{display_name} establishment",
        }


def get_restaurant_type_form_choices() -> list[tuple[str, str]]:
    """Get restaurant type choices for form picklist.

    Returns (value, label) tuples ordered with most popular first,
    then remaining types alphabetically by display name.
    """
    popular_choices, other_choices = _get_popular_and_other_choices()
    return popular_choices + other_choices


def get_restaurant_type_form_choices_grouped() -> list[tuple[str, list[tuple[str, str]]]]:
    """Get restaurant type choices grouped for optgroup rendering.

    Returns [(group_label, [(value, label), ...]), ...] for use in
    HTML select optgroups. Popular choices first, then alphabetical.
    """
    popular_choices, other_choices = _get_popular_and_other_choices()
    return [
        ("Popular", popular_choices),
        ("All Types (A–Z)", other_choices),
    ]


def _get_popular_and_other_choices() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Split choices into popular (alphabetical) and other (alphabetical)."""
    popular_set = set(_POPULAR_TYPE_ORDER)
    popular_choices = []
    other_choices = []

    for google_type in _POPULAR_TYPE_ORDER:
        if google_type in GOOGLE_RESTAURANT_TYPE_MAPPING:
            display_name = GOOGLE_RESTAURANT_TYPE_MAPPING[google_type]
            popular_choices.append((google_type, display_name))

    # Sort popular choices alphabetically by display name
    popular_choices.sort(key=lambda x: x[1])

    for google_type, display_name in sorted(GOOGLE_RESTAURANT_TYPE_MAPPING.items(), key=lambda x: x[1]):
        if google_type not in popular_set:
            other_choices.append((google_type, display_name))

    return popular_choices, other_choices


# Helper functions
def get_restaurant_type_constants() -> list[dict[str, str]]:
    """Get list of all restaurant type data."""
    return [{"name": k, **v} for k, v in RESTAURANT_TYPES.items()]


def get_restaurant_type_names() -> list[str]:
    """Get list of all restaurant type names."""
    return list(RESTAURANT_TYPES.keys())


def get_restaurant_type_data(type_name: str) -> dict[str, str] | None:
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


def get_restaurant_type_color(type_name: str) -> str:
    """Get color for a restaurant type."""
    data = get_restaurant_type_data(type_name)
    return data["color"] if data else "#6c757d"


def get_restaurant_type_icon(type_name: str) -> str:
    """Get icon for a restaurant type."""
    data = get_restaurant_type_data(type_name)
    return data["icon"] if data else "question-circle"


def validate_restaurant_type_name(type_name: str) -> bool:
    """Check if restaurant type exists."""
    return get_restaurant_type_data(type_name) is not None


def get_google_type_for_restaurant_type(type_name: str) -> str | None:
    """Get Google Places API type for a restaurant type name."""
    data = get_restaurant_type_data(type_name)
    return data["google_type"] if data else None


def get_restaurant_type_for_google_type(google_type: str) -> str | None:
    """Get user-friendly restaurant type name for Google Places API type."""
    if not google_type or not isinstance(google_type, str):
        return None

    google_type = google_type.strip().lower()
    for type_name, data in RESTAURANT_TYPES.items():
        if data["google_type"].lower() == google_type:
            return type_name

    return None


def format_restaurant_type(type_name: str, max_length: int = 100) -> str:
    """Format restaurant type with proper capitalization and length limits."""
    if not type_name:
        return ""

    # Capitalize each word
    formatted = " ".join(word.capitalize() for word in str(type_name).split())

    # Truncate if too long
    if len(formatted) > max_length:
        formatted = formatted[:max_length].rstrip()

    return formatted


def get_food_establishment_types() -> list[str]:
    """Get list of Google Places types that are primarily food establishments."""
    excluded = {"convenience_store", "grocery_store", "supermarket", "gas_station", "other"}
    return [t for t in GOOGLE_RESTAURANT_TYPE_MAPPING if t not in excluded]


def get_non_restaurant_types() -> list[str]:
    """Get list of Google Places types that are not restaurants but may sell food."""
    return ["convenience_store", "grocery_store", "supermarket", "gas_station"]


def is_food_establishment(primary_type: str) -> bool:
    """Check if a Google Places primary type represents a food establishment."""
    if not primary_type:
        return False
    return primary_type in get_food_establishment_types()


def map_google_primary_type_to_form_type(primary_type: str | None) -> str:
    """Map Google Places primaryType to restaurant form type choice value.

    Returns form field value (e.g. 'cafe', 'restaurant', 'other') for comparison.
    """
    if not primary_type or not isinstance(primary_type, str):
        return "other"
    primary_type_lower = primary_type.strip().lower()
    if primary_type_lower in GOOGLE_RESTAURANT_TYPE_MAPPING:
        return primary_type_lower
    # Fallback for unmapped food types (e.g. future Google types)
    if "restaurant" in primary_type_lower or primary_type_lower in (
        "cafe",
        "bar",
        "bakery",
        "food",
    ):
        return "restaurant"
    return "other"


def map_google_primary_type_to_display_type(primary_type: str) -> str:
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
