"""
Meal Type Color Constants
Following TIGER principles: Safety, Performance, Developer Experience

Centralized color definitions for meal types to ensure consistency
and maintainability across the application.
"""

# Option 1: Natural Time-Based Progression
MEAL_TYPE_COLORS = {
    "breakfast": {
        "background": "#fed7aa",  # orange-200 - warm sunrise
        "border": "#f97316",  # orange-500
        "text": "#9a3412",  # orange-800
        "icon": "#ea580c",  # orange-600
        "css_class": "breakfast",
    },
    "brunch": {
        "background": "#fecaca",  # red-200 - rich coral
        "border": "#ef4444",  # red-500
        "text": "#991b1b",  # red-800
        "icon": "#dc2626",  # red-600
        "css_class": "brunch",
    },
    "lunch": {
        "background": "#dcfce7",  # green-200 - fresh green
        "border": "#22c55e",  # green-500
        "text": "#166534",  # green-800
        "icon": "#15803d",  # green-700
        "css_class": "lunch",
    },
    "dinner": {
        "background": "#dbeafe",  # blue-200 - deep blue
        "border": "#3b82f6",  # blue-500
        "text": "#1e3a8a",  # blue-800
        "icon": "#2563eb",  # blue-600
        "css_class": "dinner",
    },
    "late night": {
        "background": "#e2e8f0",  # slate-200 - dark slate
        "border": "#64748b",  # slate-500
        "text": "#334155",  # slate-700
        "icon": "#475569",  # slate-600
        "css_class": "late-night",
    },
    "snacks": {
        "background": "#fde68a",  # yellow-200 - warm brown/amber
        "border": "#eab308",  # yellow-500
        "text": "#a16207",  # yellow-800
        "icon": "#ca8a04",  # yellow-600
        "css_class": "snacks",
    },
    "drinks": {
        "background": "#cffafe",  # cyan-200 - cool teal
        "border": "#06b6d4",  # cyan-500
        "text": "#0f766e",  # teal-700
        "icon": "#0e7490",  # cyan-700
        "css_class": "drinks",
    },
    "dessert": {
        "background": "#fce7f3",  # pink-200 - sweet pink
        "border": "#ec4899",  # pink-500
        "text": "#be185d",  # pink-700
        "icon": "#db2777",  # pink-600
        "css_class": "dessert",
    },
}


def get_meal_type_color(meal_type: str, color_type: str = "background") -> str:
    """
    Get color for a meal type with validation and fallback.

    Args:
        meal_type: The meal type name (case insensitive)
        color_type: Type of color ('background', 'border', 'text', 'icon')

    Returns:
        Hex color string with fallback for unknown types

    Following TIGER principles:
    - Safety: Input validation with fallback
    - Performance: Simple dict lookup
    - Developer Experience: Clear parameter names and documentation
    """
    if not meal_type:
        return "#f8f9fa"  # Default gray background

    normalized_type = meal_type.lower().strip()

    if normalized_type not in MEAL_TYPE_COLORS:
        return "#f8f9fa"  # Default gray for unknown types

    colors = MEAL_TYPE_COLORS[normalized_type]

    if color_type not in colors:
        return colors.get("background", "#f8f9fa")

    return colors[color_type]


def get_meal_type_css_class(meal_type: str) -> str:
    """
    Get CSS class name for a meal type.

    Args:
        meal_type: The meal type name (case insensitive)

    Returns:
        CSS class name string
    """
    if not meal_type:
        return "meal-type-default"

    normalized_type = meal_type.lower().strip()

    if normalized_type not in MEAL_TYPE_COLORS:
        return "meal-type-default"

    return MEAL_TYPE_COLORS[normalized_type]["css_class"]


def get_all_meal_type_colors() -> dict:
    """
    Get all meal type colors for use in CSS generation.

    Returns:
        Complete color dictionary
    """
    return MEAL_TYPE_COLORS.copy()
