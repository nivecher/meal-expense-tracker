"""Centralized category constants for the meal expense tracker.

This module contains the default categories that are created for new users
and provides utilities for category management.

Following TIGER principles: Safety, Performance, Developer Experience
"""

from typing import List, TypedDict

from .colors import get_category_color


class CategoryData(TypedDict):
    """Type definition for category data."""

    name: str
    description: str
    color: str
    icon: str


# Default categories created for new users
DEFAULT_CATEGORIES: List[CategoryData] = [
    {
        "name": "Restaurants",
        "description": "Restaurant meals and takeout",
        "color": get_category_color("restaurants"),  # Orange #fd7e14
        "icon": "utensils",
    },
    {
        "name": "Groceries",
        "description": "Grocery shopping and food supplies",
        "color": get_category_color("groceries"),  # Green #198754
        "icon": "shopping-cart",
    },
    {
        "name": "Drinks",
        "description": "Beverages, coffee, and drinks",
        "color": get_category_color("drinks"),  # Cyan #0dcaf0
        "icon": "coffee",
    },
    {
        "name": "Fast Food",
        "description": "Quick service and fast food",
        "color": get_category_color("fast_food"),  # Red #dc3545
        "icon": "hamburger",
    },
    {
        "name": "Entertainment",
        "description": "Movies, events, and entertainment",
        "color": get_category_color("entertainment"),  # Purple #6f42c1
        "icon": "theater-masks",
    },
    {
        "name": "Snacks & Vending",
        "description": "Snacks and vending machines",
        "color": get_category_color("snacks_vending"),  # Blue #0d6efd
        "icon": "car",  # Vending machine access, drive-through snacks
    },
    {
        "name": "Other",
        "description": "Miscellaneous expenses",
        "color": get_category_color("other"),  # Gray #6c757d
        "icon": "question",
    },
]


def get_default_categories() -> List[CategoryData]:
    """Get the default categories for new users.

    Returns:
        List of default category data dictionaries
    """
    return DEFAULT_CATEGORIES.copy()


def get_category_names() -> List[str]:
    """Get just the names of default categories.

    Returns:
        List of default category names
    """
    return [category["name"] for category in DEFAULT_CATEGORIES]


def get_category_by_name(name: str) -> CategoryData | None:
    """Get a specific category by name.

    Args:
        name: The name of the category to find

    Returns:
        Category data dictionary or None if not found
    """
    for category in DEFAULT_CATEGORIES:
        if category["name"] == name:
            return category.copy()
    return None
