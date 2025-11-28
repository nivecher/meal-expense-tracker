"""
Service level detection utilities for restaurants using Google Places API data.

This module provides functions to determine restaurant service levels
(Fine Dining, Casual Dining, Fast Casual, Quick Service) based on
available Google Places API data like price level, place types, and
business attributes.

Following TIGER principles: Safety, Performance, Developer Experience
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ServiceLevel(Enum):
    """Restaurant service level categories."""

    FINE_DINING = "fine_dining"
    CASUAL_DINING = "casual_dining"
    FAST_CASUAL = "fast_casual"
    QUICK_SERVICE = "quick_service"
    UNKNOWN = "unknown"


class ServiceLevelDetector:
    """
    Detects restaurant service levels from Google Places API data.

    Uses a combination of price level, place types, and business attributes
    to determine the most likely service level category.
    """

    # Price level thresholds for service level detection
    PRICE_LEVEL_THRESHOLDS = {
        ServiceLevel.FINE_DINING: (3, 4),  # Expensive to Very Expensive
        ServiceLevel.CASUAL_DINING: (
            1,
            3,
        ),  # Inexpensive to Expensive (broader range for casual dining)
        ServiceLevel.FAST_CASUAL: (1, 2),  # Inexpensive to Moderate
        ServiceLevel.QUICK_SERVICE: (0, 1),  # Free to Inexpensive
    }

    # Place types that strongly indicate service level
    SERVICE_LEVEL_INDICATORS = {
        ServiceLevel.FINE_DINING: [
            "fine_dining_restaurant",
            "steakhouse",
            "seafood_restaurant",
            "upscale_restaurant",
        ],
        ServiceLevel.CASUAL_DINING: [
            "restaurant",
            "family_restaurant",
            "diner",
            "eatery",
            "grill",
            "kitchen",
            "pub",
            "tavern",
            "brewery",
            "brewpub",
            "gastropub",
            "sports_bar",
            "bar_and_grill",
        ],
        ServiceLevel.FAST_CASUAL: [
            "fast_casual_restaurant",
            "cafe",
            "coffee_shop",
            "bakery",
            "sandwich_shop",
            "salad_shop",
        ],
        ServiceLevel.QUICK_SERVICE: [
            "meal_takeaway",
            "fast_food_restaurant",
            "convenience_store",
            "gas_station",
            "food_court",
            "food_truck",
            "mobile_food",
            "cart",
            "stand",
            "kiosk",
            "fast_food",  # Add this for better detection
        ],
    }

    # Business attributes that indicate service level
    BUSINESS_ATTRIBUTES = {
        ServiceLevel.FINE_DINING: {
            "serves_dinner": True,
            "serves_lunch": True,
            "serves_breakfast": False,  # Less common in fine dining
            "has_takeout": False,  # Usually dine-in only
            "has_delivery": False,  # Usually dine-in only
        },
        ServiceLevel.CASUAL_DINING: {
            "serves_dinner": True,
            "serves_lunch": True,
            "serves_breakfast": True,
            "has_takeout": True,
            "has_delivery": True,  # Often available for casual dining
        },
        ServiceLevel.FAST_CASUAL: {
            "serves_dinner": True,
            "serves_lunch": True,
            "serves_breakfast": True,
            "has_takeout": True,
            "has_delivery": True,
        },
        ServiceLevel.QUICK_SERVICE: {
            "serves_dinner": True,
            "serves_lunch": True,
            "serves_breakfast": True,
            "has_takeout": True,
            "has_delivery": True,
        },
    }

    @classmethod
    def detect_service_level(
        cls,
        price_level: int | None,
        place_types: list[str] | None = None,
        business_attributes: dict[str, bool] | None = None,
        rating: float | None = None,
        user_ratings_total: int | None = None,
    ) -> tuple[ServiceLevel, float]:
        """
        Detect restaurant service level from Google Places API data.

        Args:
            price_level: Google Places price level (0-4)
            place_types: List of Google Places types
            business_attributes: Dict of business attributes (serves_dinner, has_takeout, etc.)
            rating: Google rating (1.0-5.0)
            user_ratings_total: Number of user ratings

        Returns:
            Tuple of (ServiceLevel, confidence_score)

        Example:
            >>> detector = ServiceLevelDetector()
            >>> level, confidence = detector.detect_service_level(
            ...     price_level=3,
            ...     place_types=["restaurant", "steakhouse"],
            ...     business_attributes={"serves_dinner": True, "has_takeout": False}
            ... )
            >>> print(level)  # ServiceLevel.FINE_DINING
        """
        # Input validation - safety first
        if place_types is None:
            place_types = []
        if business_attributes is None:
            business_attributes = {}

        # Enforce bounds
        if price_level is not None and (price_level < 0 or price_level > 4):
            price_level = None

        if rating is not None and (rating < 1.0 or rating > 5.0):
            rating = None

        # Calculate confidence scores for each service level
        scores = {}

        for service_level in ServiceLevel:
            if service_level == ServiceLevel.UNKNOWN:
                continue

            score = cls._calculate_service_level_score(
                service_level,
                price_level,
                place_types,
                business_attributes,
                rating,
                user_ratings_total,
            )
            scores[service_level] = score

        # Find the service level with highest confidence
        if not scores:
            return ServiceLevel.UNKNOWN, 0.0

        best_level = max(scores.items(), key=lambda x: x[1])
        return best_level[0], best_level[1]

    @classmethod
    def _calculate_service_level_score(
        cls,
        service_level: ServiceLevel,
        price_level: int | None,
        place_types: list[str],
        business_attributes: dict[str, bool],
        rating: float | None,
        user_ratings_total: int | None,
    ) -> float:
        """
        Calculate confidence score for a specific service level.

        Args:
            service_level: Service level to score
            price_level: Google Places price level
            place_types: List of Google Places types
            business_attributes: Dict of business attributes
            rating: Google rating
            user_ratings_total: Number of user ratings

        Returns:
            Confidence score (0.0-1.0)
        """
        score = 0.0
        factors = 0

        # Factor 1: Price level (weight: 0.4)
        if price_level is not None:
            min_price, max_price = cls.PRICE_LEVEL_THRESHOLDS[service_level]
            if min_price <= price_level <= max_price:
                score += 0.4
            factors += 1

        # Factor 2: Place types (weight: 0.3)
        if place_types:
            type_score = cls._calculate_type_score(service_level, place_types)
            score += type_score * 0.3
            factors += 1

        # Factor 3: Business attributes (weight: 0.2)
        if business_attributes:
            attr_score = cls._calculate_attribute_score(service_level, business_attributes)
            score += attr_score * 0.2
            factors += 1

        # Factor 4: Rating and review count (weight: 0.1)
        if rating is not None and user_ratings_total is not None:
            rating_score = cls._calculate_rating_score(service_level, rating, user_ratings_total)
            score += rating_score * 0.1
            factors += 1

        # Normalize score based on available factors
        if factors == 0:
            return 0.0

        return score / factors

    @classmethod
    def _calculate_type_score(cls, service_level: ServiceLevel, place_types: list[str]) -> float:
        """Calculate score based on place types."""
        indicators = cls.SERVICE_LEVEL_INDICATORS[service_level]

        # Check for exact matches
        for indicator in indicators:
            if indicator in place_types:
                return 1.0

        # Check for partial matches (e.g., "restaurant" in "mexican_restaurant")
        for place_type in place_types:
            for indicator in indicators:
                if indicator in place_type or place_type in indicator:
                    return 0.7

        # Default score for restaurant types
        if "restaurant" in place_types:
            return 0.5

        return 0.0

    @classmethod
    def _calculate_attribute_score(cls, service_level: ServiceLevel, business_attributes: dict[str, bool]) -> float:
        """Calculate score based on business attributes."""
        expected_attrs = cls.BUSINESS_ATTRIBUTES[service_level]
        matches = 0
        total = len(expected_attrs)

        for attr, expected_value in expected_attrs.items():
            if attr in business_attributes:
                if business_attributes[attr] == expected_value:
                    matches += 1

        return matches / total if total > 0 else 0.0

    @classmethod
    def _calculate_rating_score(cls, service_level: ServiceLevel, rating: float, user_ratings_total: int) -> float:
        """Calculate score based on rating and review count."""
        # Define rating thresholds for each service level
        rating_thresholds = {
            ServiceLevel.FINE_DINING: [
                (4.5, 100, 1.0),
                (4.0, 50, 0.7),
            ],
            ServiceLevel.CASUAL_DINING: [
                (3.8, 50, 1.0),
                (3.3, 25, 0.7),
            ],
            ServiceLevel.FAST_CASUAL: [
                (3.5, 25, 1.0),
                (3.0, 10, 0.7),
            ],
            ServiceLevel.QUICK_SERVICE: [
                (3.2, 10, 1.0),
                (2.8, 5, 0.7),
            ],
        }

        thresholds = rating_thresholds.get(service_level, [])

        for min_rating, min_reviews, score in thresholds:
            if rating >= min_rating and user_ratings_total >= min_reviews:
                return score

        return 0.0

    @classmethod
    def get_service_level_display_name(cls, service_level: ServiceLevel) -> str:
        """Get human-readable display name for service level."""
        display_names = {
            ServiceLevel.FINE_DINING: "Fine Dining",
            ServiceLevel.CASUAL_DINING: "Casual Dining",
            ServiceLevel.FAST_CASUAL: "Fast Casual",
            ServiceLevel.QUICK_SERVICE: "Quick Service",
            ServiceLevel.UNKNOWN: "Unknown",
        }
        return display_names.get(service_level, "Unknown")

    @classmethod
    def get_service_level_description(cls, service_level: ServiceLevel) -> str:
        """Get description for service level."""
        descriptions = {
            ServiceLevel.FINE_DINING: "Upscale restaurants with premium dining experience and full table service",
            ServiceLevel.CASUAL_DINING: "Full-service restaurants with table service, more affordable than fine dining",
            ServiceLevel.FAST_CASUAL: "Counter service with higher quality food, silverware typically provided",
            ServiceLevel.QUICK_SERVICE: "Fast food and quick service establishments, counter service only",
            ServiceLevel.UNKNOWN: "Service level could not be determined",
        }
        return descriptions.get(service_level, "Service level could not be determined")

    @classmethod
    def get_service_level_from_string(cls, service_level_str: str) -> ServiceLevel:
        """Get ServiceLevel enum from string value."""
        try:
            return ServiceLevel(service_level_str)
        except ValueError:
            return ServiceLevel.UNKNOWN


def detect_restaurant_service_level(google_places_data: dict[str, Any]) -> tuple[ServiceLevel, float]:
    """
    Detect service level from Google Places API response using business model characteristics.

    This function uses the new Google Places-based approach that analyzes actual
    restaurant data (price level, service options, reviews) to classify restaurants
    as QSR vs Fast Casual based on their business model.

    Args:
        google_places_data: Dictionary containing Google Places API response data

    Returns:
        Tuple of (ServiceLevel, confidence_score)

    Example:
        >>> place_data = {
        ...     "priceLevel": 3,
        ...     "outdoorSeating": True,
        ...     "curbsidePickup": False,
        ...     "reviews": [{"text": "Fresh ingredients and great atmosphere"}]
        ... }
        >>> level, confidence = detect_restaurant_service_level(place_data)
    """
    # Use the new Google Places-based detection
    service_level = detect_service_level_from_google_places(google_places_data)

    # Calculate confidence based on available data
    confidence = 0.5  # Base confidence

    # Increase confidence if we have key indicators
    if google_places_data.get("priceLevel") is not None:
        confidence += 0.2
    if google_places_data.get("reviews"):
        confidence += 0.2
    if google_places_data.get("outdoorSeating") is not None or google_places_data.get("curbsidePickup") is not None:
        confidence += 0.1

    # Cap confidence at 1.0
    confidence = min(confidence, 1.0)

    return service_level, confidence


def detect_service_level_from_name(restaurant_name: str) -> ServiceLevel:
    """
    Detect service level from restaurant name using Google Places API data.

    This function should be used when Google Places API data is available.
    For name-only detection, it returns UNKNOWN to encourage using Google Places data.

    Args:
        restaurant_name: Name of the restaurant

    Returns:
        ServiceLevel enum value

    Note:
        This function now returns UNKNOWN to encourage using Google Places API data
        for accurate service level detection based on actual restaurant characteristics.
    """
    if not restaurant_name or not isinstance(restaurant_name, str):
        return ServiceLevel.UNKNOWN

    # Return UNKNOWN to encourage using Google Places API data
    # Name-based detection is unreliable and should be avoided
    return ServiceLevel.UNKNOWN


def detect_service_level_from_google_places(place_data: dict) -> ServiceLevel:
    """
    Classify restaurant service level based on Google Places API types.

    This uses Google's standard place types to classify restaurants into service levels.
    Simple and reliable approach that follows Google's classification system.

    Args:
        place_data: Dictionary containing Google Places API response data

    Returns:
        ServiceLevel enum value
    """
    if not place_data:
        return ServiceLevel.UNKNOWN

    types = place_data.get("types", [])
    if not types:
        return ServiceLevel.UNKNOWN

    types_lower = [t.lower() for t in types]

    # Quick Service (Fast Food) - Google's primary indicators
    if any(
        indicator in types_lower
        for indicator in [
            "fast_food_restaurant",  # Google's primary fast food type
            "fast_food",  # Alternative fast food type
            "meal_takeaway",  # Takeaway food
            "food_court",  # Food court vendors
            "convenience_store",  # Convenience stores with food
        ]
    ):
        return ServiceLevel.QUICK_SERVICE

    # Fast Casual - Counter service but higher quality
    elif any(
        indicator in types_lower
        for indicator in [
            "fast_casual_restaurant",  # Google's fast casual type
            "fast_casual",  # Alternative fast casual type
        ]
    ):
        return ServiceLevel.FAST_CASUAL

    # Fine Dining - Upscale establishments
    elif any(
        indicator in types_lower
        for indicator in [
            "fine_dining_restaurant",  # Google's fine dining type
            "fine_dining",  # Alternative fine dining type
            "upscale_restaurant",  # Upscale restaurants
        ]
    ):
        return ServiceLevel.FINE_DINING

    # Casual Dining - Regular sit-down restaurants
    elif "restaurant" in types_lower:
        return ServiceLevel.CASUAL_DINING

    # Unknown - no clear restaurant indicators
    else:
        return ServiceLevel.UNKNOWN


def _calculate_price_score(price_level: int | None, score_type: str) -> float:
    """Calculate score based on price level."""
    if price_level is None:
        return 0.0

    # Define price level mappings for each service type
    price_mappings = {
        "fine_dining": {4: 2.0, 3: 1.0},
        "fast_casual": {3: 1.0, 2: 1.0, 1: -1.0, 0: -1.0},
        "quick_service": {1: 2.0, 0: 2.0, 2: 1.0, 3: -1.0, 4: -1.0},
    }

    return price_mappings.get(score_type, {}).get(price_level, 0.0)


def _calculate_amenities_score(place_data: dict, score_type: str) -> float:
    """Calculate score based on amenities and service options."""
    # Define amenity scoring rules for each service type
    amenity_rules: dict[str, list[tuple]] = {
        "fine_dining": [("outdoorSeating", 0.5), ("servesAlcohol", 1.0), ("reservable", 2.0)],
        "fast_casual": [("outdoorSeating", 1.0), ("servesAlcohol", 0.5)],
        "quick_service": [
            ("takeout", 1.0),
            ("curbsidePickup", 0.5),
            ("dineIn", 0.5, False),  # Special case: False value
            ("reservable", -1.0),
            ("servesAlcohol", -0.5),
        ],
    }

    score = 0.0
    rules: list[tuple] = amenity_rules.get(score_type, [])

    for rule in rules:
        if len(rule) == 3:  # Special case with expected value
            key, points, expected_value = rule
            if place_data.get(key) == expected_value:
                score += points
        else:  # Normal case
            key, points = rule
            if place_data.get(key):
                score += points

    # Special case for fast_casual: penalty for takeout-only
    if score_type == "fast_casual":
        if place_data.get("dineIn") == False and place_data.get("takeout") == True:
            score -= 1.0
        if place_data.get("curbsidePickup"):
            score -= 1.0

    return score


def _calculate_reviews_score(reviews: list, score_type: str) -> float:
    """Calculate score based on review content analysis."""
    # Define keyword scoring rules for each service type
    keyword_rules = {
        "fine_dining": {
            "positive": (
                ["prix fixe", "chef", "elegant", "wine list", "sommelier", "formal", "dress code"],
                1.0,
            ),
            "neutral": (
                ["family-friendly", "comfort food", "generous portions", "wait staff"],
                0.5,
            ),
        },
        "fast_casual": {
            "positive": (
                ["fresh ingredients", "customizable", "made to order", "healthy", "assembly line"],
                0.5,
            ),
            "negative": (["fast", "quick", "cheap", "convenient", "drive-thru"], -1.0),
        },
        "quick_service": {
            "positive": (
                [
                    "fast",
                    "quick",
                    "cheap",
                    "convenient",
                    "drive-thru",
                    "fast food",
                    "takeout",
                    "to-go",
                ],
                1.0,
            ),
            "negative": (["fresh ingredients", "customizable", "made to order", "healthy"], -0.5),
        },
    }

    score = 0.0
    rules = keyword_rules.get(score_type, {})

    for review in reviews:
        review_text = review.get("text", "").lower()

        for rule_type, (keywords, points) in rules.items():
            if any(kw in review_text for kw in keywords):
                score += points

    return score
