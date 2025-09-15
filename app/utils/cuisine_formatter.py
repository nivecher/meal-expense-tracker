"""
Cuisine type formatting utilities for Google Places data.

This module provides consistent formatting for cuisine types across the application,
following TIGER principles: Safety, Performance, Developer Experience.
"""

from typing import Optional

from app.constants.cuisines import get_cuisine_data, get_cuisine_names


def format_cuisine_type(cuisine_type: Optional[str], max_length: int = 100) -> str:
    """
    Format cuisine type from Google Places data with proper capitalization.

    Args:
        cuisine_type: Raw cuisine type from Google Places or user input
        max_length: Maximum length for cuisine string (default: 100)

    Returns:
        Formatted cuisine type or empty string if invalid

    Example:
        format_cuisine_type('mexican')  # returns 'Mexican'
        format_cuisine_type('ITALIAN')  # returns 'Italian'
        format_cuisine_type('chinese_restaurant')  # returns 'Chinese'
    """
    # Input validation - safety first
    if not cuisine_type or not isinstance(cuisine_type, str):
        return ""

    # Enforce bounds to prevent overflow
    trimmed_input = cuisine_type.strip()
    if len(trimmed_input) == 0 or len(trimmed_input) > max_length:
        return ""

    # Try to get cuisine data first (handles fuzzy matching)
    cuisine_data = get_cuisine_data(trimmed_input)
    if cuisine_data:
        return cuisine_data["name"]

    # If no exact match, try to format the input
    return _capitalize_words(trimmed_input)


def _capitalize_words(text: str) -> str:
    """
    Capitalize words in a string, handling common separators.

    Args:
        text: Input text to capitalize

    Returns:
        Properly capitalized text

    Example:
        _capitalize_words('mexican_restaurant')  # returns 'Mexican Restaurant'
        _capitalize_words('fast-food')  # returns 'Fast Food'
    """
    if not text:
        return ""

    # Split on whitespace, underscore, or dash
    words = text.split()
    if not words:
        # Handle case where text is just separators
        words = text.replace("_", " ").replace("-", " ").split()

    # Capitalize each word
    capitalized_words = []
    for word in words:
        # Handle separators within words
        if "_" in word or "-" in word:
            sub_words = word.replace("_", " ").replace("-", " ").split()
            capitalized_sub_words = [w.capitalize() for w in sub_words if w]
            capitalized_words.extend(capitalized_sub_words)
        else:
            capitalized_words.append(word.capitalize())

    return " ".join(capitalized_words)


def get_cuisine_display_name(cuisine_type: Optional[str]) -> str:
    """
    Get display name for a cuisine type with fallback formatting.

    Args:
        cuisine_type: Raw cuisine type

    Returns:
        Display-ready cuisine name

    Example:
        get_cuisine_display_name('mexican')  # returns 'Mexican'
        get_cuisine_display_name('unknown')  # returns 'Unknown'
    """
    if not cuisine_type:
        return "Unknown"

    formatted = format_cuisine_type(cuisine_type)
    return formatted if formatted else "Unknown"


def validate_cuisine_type(cuisine_type: Optional[str]) -> bool:
    """
    Validate if a cuisine type is recognized or can be formatted.

    Args:
        cuisine_type: Cuisine type to validate

    Returns:
        True if cuisine is valid or can be formatted, False otherwise

    Example:
        validate_cuisine_type('Italian')  # returns True
        validate_cuisine_type('xyz123')  # returns False
    """
    if not cuisine_type:
        return False

    # Check if it's a known cuisine
    if get_cuisine_data(cuisine_type):
        return True

    # Check if it can be formatted (basic validation)
    formatted = format_cuisine_type(cuisine_type)
    return bool(formatted and len(formatted.strip()) > 0)


def get_available_cuisine_types() -> list[str]:
    """
    Get list of all available cuisine types.

    Returns:
        List of available cuisine type names

    Example:
        cuisines = get_available_cuisine_types()
        print(cuisines[:3])  # ['Chinese', 'Italian', 'Japanese']
    """
    return get_cuisine_names()
