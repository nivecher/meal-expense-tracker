"""
Backend cuisine formatting utilities for consistent cuisine type handling
Provides validation and formatting following TIGER principles
"""

import re
from typing import Optional

# Map of common cuisine types to standardized format
CUISINE_STANDARDIZATION_MAP = {
    "mexican": "Mexican",
    "italian": "Italian",
    "chinese": "Chinese",
    "japanese": "Japanese",
    "indian": "Indian",
    "thai": "Thai",
    "french": "French",
    "american": "American",
    "pizza": "Pizza",
    "seafood": "Seafood",
    "steakhouse": "Steakhouse",
    "sushi": "Sushi",
    "korean": "Korean",
    "vietnamese": "Vietnamese",
    "mediterranean": "Mediterranean",
    "greek": "Greek",
    "spanish": "Spanish",
    "german": "German",
    "british": "British",
    "turkish": "Turkish",
    "lebanese": "Lebanese",
    "ethiopian": "Ethiopian",
    "moroccan": "Moroccan",
    "brazilian": "Brazilian",
    "peruvian": "Peruvian",
    "argentinian": "Argentinian",
    "fast food": "Fast Food",
    "fast-food": "Fast Food",
    "fastfood": "Fast Food",
    "fine dining": "Fine Dining",
    "fine-dining": "Fine Dining",
}


def format_cuisine_type(cuisine_input: Optional[str], max_length: int = 100) -> Optional[str]:
    """
    Format and standardize cuisine type input with proper capitalization.

    Args:
        cuisine_input: Raw cuisine type string from user input or API
        max_length: Maximum allowed length for cuisine string (default: 100)

    Returns:
        Formatted cuisine type string or None if invalid/empty

    Examples:
        format_cuisine_type('mexican') -> 'Mexican'
        format_cuisine_type('ITALIAN') -> 'Italian'
        format_cuisine_type('fast-food') -> 'Fast Food'
        format_cuisine_type('  thai  ') -> 'Thai'
        format_cuisine_type('') -> None
        format_cuisine_type(None) -> None
    """
    # Input validation - safety first
    if not cuisine_input or not isinstance(cuisine_input, str):
        return None

    # Sanitize and enforce bounds
    trimmed = cuisine_input.strip()
    if not trimmed or len(trimmed) > max_length:
        return None

    # Remove potentially harmful characters and normalize
    cleaned = re.sub(r'[<>"\';]', "", trimmed)
    if not cleaned:
        return None

    # Convert to lowercase for mapping
    lower_cuisine = cleaned.lower()

    # Check direct mapping first (most common cases)
    if lower_cuisine in CUISINE_STANDARDIZATION_MAP:
        return CUISINE_STANDARDIZATION_MAP[lower_cuisine]

    # Handle compound cuisine types (e.g., "mexican-american", "asian fusion")
    if "-" in lower_cuisine or " " in lower_cuisine:
        return _format_compound_cuisine(lower_cuisine)

    # Default: capitalize first letter of each word
    return _capitalize_words(cleaned)


def _format_compound_cuisine(cuisine: str) -> str:
    """
    Format compound cuisine types (e.g., "mexican-american", "asian fusion").

    Args:
        cuisine: Lowercase cuisine string containing separators

    Returns:
        Properly formatted compound cuisine string
    """
    # Split on common separators and format each part
    parts = re.split(r"[-\s/]+", cuisine)
    formatted_parts = []

    for part in parts:
        if part in CUISINE_STANDARDIZATION_MAP:
            formatted_parts.append(CUISINE_STANDARDIZATION_MAP[part])
        else:
            formatted_parts.append(_capitalize_words(part))

    return " ".join(formatted_parts)


def _capitalize_words(text: str) -> str:
    """
    Capitalize first letter of each word in a string.

    Args:
        text: Input string to capitalize

    Returns:
        String with each word capitalized
    """
    if not text:
        return ""

    # Handle special cases and preserve existing formatting for known words
    words = text.split()
    formatted_words = []

    for word in words:
        # Handle common prepositions and articles (keep lowercase)
        if word.lower() in ["and", "or", "of", "the", "a", "an", "in", "on", "at", "to", "for"]:
            formatted_words.append(word.lower())
        else:
            # Capitalize first letter, preserve rest
            formatted_words.append(word.capitalize())

    # Always capitalize first word
    if formatted_words:
        formatted_words[0] = formatted_words[0].capitalize()

    return " ".join(formatted_words)


def validate_cuisine_input(cuisine_input: Optional[str]) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Validate and format cuisine input for database storage.

    Args:
        cuisine_input: Raw cuisine input from user

    Returns:
        Tuple of (is_valid, formatted_cuisine, error_message)

    Examples:
        validate_cuisine_input('mexican') -> (True, 'Mexican', None)
        validate_cuisine_input('') -> (True, None, None)
        validate_cuisine_input('x' * 101) -> (False, None, 'Cuisine type too long (max 100 characters)')
    """
    # Allow empty/None cuisine (optional field)
    if not cuisine_input:
        return True, None, None

    # Check length bounds
    if len(cuisine_input.strip()) > 100:
        return False, None, "Cuisine type too long (max 100 characters)"

    # Format the cuisine
    formatted = format_cuisine_type(cuisine_input)

    if formatted is None:
        return False, None, "Invalid cuisine type format"

    return True, formatted, None


def sanitize_cuisine_for_storage(restaurant_data: dict) -> dict:
    """
    Sanitize cuisine data in restaurant dictionary before database storage.

    Args:
        restaurant_data: Dictionary containing restaurant data

    Returns:
        Dictionary with sanitized cuisine field

    Example:
        data = {'name': 'Test', 'cuisine': 'mexican'}
        sanitize_cuisine_for_storage(data) -> {'name': 'Test', 'cuisine': 'Mexican'}
    """
    if not isinstance(restaurant_data, dict):
        return restaurant_data

    # Make a copy to avoid modifying original
    sanitized_data = restaurant_data.copy()

    if "cuisine" in sanitized_data:
        formatted_cuisine = format_cuisine_type(sanitized_data["cuisine"])
        sanitized_data["cuisine"] = formatted_cuisine

    return sanitized_data
