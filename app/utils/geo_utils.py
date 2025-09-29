"""
Geographic utility functions for distance calculations and location-based operations.
"""

import math
from typing import Optional


def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the distance between two points on Earth using the Haversine formula.

    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point

    Returns:
        Distance in kilometers
    """
    # Radius of Earth in kilometers
    R = 6371.0

    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    distance = R * c
    return distance


def calculate_distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the distance between two points on Earth in miles.

    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point

    Returns:
        Distance in miles
    """
    distance_km = calculate_distance_km(lat1, lon1, lat2, lon2)
    return distance_km * 0.621371  # Convert km to miles


def is_within_radius(lat1: float, lon1: float, lat2: float, lon2: float, radius_km: float) -> bool:
    """
    Check if two points are within a specified radius.

    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point
        radius_km: Radius in kilometers

    Returns:
        True if points are within radius, False otherwise
    """
    distance = calculate_distance_km(lat1, lon1, lat2, lon2)
    return distance <= radius_km


def validate_coordinates(latitude: Optional[float], longitude: Optional[float]) -> bool:
    """
    Validate that coordinates are within valid ranges.

    Args:
        latitude: Latitude value
        longitude: Longitude value

    Returns:
        True if coordinates are valid, False otherwise
    """
    if latitude is None or longitude is None:
        return False

    return -90 <= latitude <= 90 and -180 <= longitude <= 180


def format_distance(distance_km: float, unit: str = "km") -> str:
    """
    Format distance for display.

    Args:
        distance_km: Distance in kilometers
        unit: Unit to display ("km" or "miles")

    Returns:
        Formatted distance string
    """
    if unit.lower() == "miles":
        distance = distance_km * 0.621371
        return f"{distance:.1f} mi"
    else:
        return f"{distance_km:.1f} km"
