"""Template filters for the application."""

from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote_plus

from flask import Flask


def time_ago(dt: datetime) -> str:
    """Return a string representing time since the given datetime.

    Args:
        dt: The datetime to calculate time since

    Returns:
        str: A string like "3 days ago" or "5 hours ago"
    """
    if not dt:
        return "Never"

    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    diff = now - dt
    periods = (
        (diff.days // 365, "year", "years"),
        (diff.days // 30, "month", "months"),
        (diff.days // 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds // 3600, "hour", "hours"),
        (diff.seconds // 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    )

    for period, singular, plural in periods:
        if period > 0:
            return f"{period} {singular if period == 1 else plural} ago"
    return "just now"


def _extract_restaurant_data(restaurant_data) -> Optional[dict]:
    """Extract restaurant data from object or dictionary."""
    if isinstance(restaurant_data, dict):
        return {
            "name": restaurant_data.get("name", ""),
            "google_place_id": restaurant_data.get("google_place_id"),
            "address": restaurant_data.get("address", ""),
            "city": restaurant_data.get("city", ""),
            "state": restaurant_data.get("state", ""),
            "postal_code": restaurant_data.get("postal_code", ""),
        }

    # Try to access as object attributes
    try:
        return {
            "name": getattr(restaurant_data, "name", ""),
            "google_place_id": getattr(restaurant_data, "google_place_id", None),
            "address": getattr(restaurant_data, "address", ""),
            "city": getattr(restaurant_data, "city", ""),
            "state": getattr(restaurant_data, "state", ""),
            "postal_code": getattr(restaurant_data, "postal_code", ""),
        }
    except (AttributeError, TypeError):
        return None


def _build_search_query(data: dict) -> Optional[str]:
    """Build search query from restaurant data."""
    search_parts = []

    # Always include restaurant name
    if data["name"]:
        search_parts.append(data["name"])

    # Add address details in order of specificity
    if data["address"]:
        search_parts.append(data["address"])
    elif data["city"]:
        search_parts.append(data["city"])

    # Add city if not already included in address
    if data["city"] and data["address"] and data["city"].lower() not in data["address"].lower():
        search_parts.append(data["city"])

    # Add state and postal code
    if data["state"]:
        search_parts.append(data["state"])
    if data["postal_code"]:
        search_parts.append(data["postal_code"])

    if search_parts:
        search_query = ", ".join(search_parts)
        return quote_plus(search_query)

    return None


def google_maps_url(restaurant_data) -> Optional[str]:
    """Generate a Google Maps URL for a restaurant object or dictionary (API token-free).

    Args:
        restaurant_data: Restaurant object or dictionary containing restaurant information

    Returns:
        Optional[str]: Google Maps URL or None if no location data is available
    """
    if not restaurant_data:
        return None

    # Handle Restaurant objects with the method
    if hasattr(restaurant_data, "get_google_maps_url"):
        return restaurant_data.get_google_maps_url()

    # Extract data from dictionary or object
    data = _extract_restaurant_data(restaurant_data)
    if not data:
        return None

    # First preference: Use place_id format with restaurant name
    if data["google_place_id"] and data["name"]:
        restaurant_name = quote_plus(data["name"])
        return f"https://www.google.com/maps/search/?api=1&query={restaurant_name}&query_place_id={data['google_place_id']}"

    # Second preference: Use search-based URL
    encoded_query = _build_search_query(data)
    if encoded_query:
        return f"https://www.google.com/maps/search/?api=1&query={encoded_query}"

    return None


def init_app(app: Flask):
    """Register the filter with the Flask app.

    Args:
        app: The Flask application instance
    """
    app.jinja_env.filters["time_ago"] = time_ago
    app.jinja_env.filters["google_maps_url"] = google_maps_url
