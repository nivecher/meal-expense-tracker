"""Cost optimization configuration for Google APIs.

This module contains configuration settings and strategies for reducing Google API costs
while maintaining functionality and user experience.

Following TIGER principles:
- Testing: Configuration values are testable and predictable
- Interfaces: Simple configuration access patterns
- Generality: Reusable optimization strategies
- Examples: Clear documentation of cost impact
- Refactoring: Centralized cost optimization logic
"""

import os
from typing import Dict

# Google Places API cost optimization settings
COST_OPTIMIZATION_SETTINGS = {
    # Field mask optimization - use minimal data by default
    "default_field_mask": "search_essential",  # Instead of "comprehensive"
    "search_field_mask": "search_essential",  # Essential data for search results
    "details_field_mask": "place_details",  # Detailed data only when needed
    # Search result limits to reduce costs
    "max_search_results": 20,  # Limit results per search
    "max_autocomplete_results": 5,  # Limit autocomplete suggestions
    # Caching settings
    "enable_caching": True,  # Enable API response caching
    # Update cache_ttl_days to include dynamic adjustment logic
    "cache_ttl_days": {
        "place_details": 7,
        "search_results": (1 if os.environ.get("ENV") == "production" else 0.5),  # Dynamic based on environment
        "photos": 30,
    },
    # Photo optimization
    "max_photo_width": 300,  # Reduce photo size to save bandwidth
    "max_photos_per_place": 3,  # Limit photos per place
    # Search strategy optimization
    "prefer_nearby_search": True,  # Use nearby search when possible (cheaper)
    "fallback_to_text_search": True,  # Fallback to text search if needed
    "skip_photos_in_search": True,  # Skip photos in initial search (load on demand)
    # Rate limiting
    "requests_per_minute": 60,  # Limit API requests per minute
    "requests_per_hour": 1000,  # Limit API requests per hour
    # Cost monitoring
    "log_api_costs": True,  # Log API usage for monitoring
    "cost_alert_threshold": 100,  # Alert when daily costs exceed threshold
}


def get_cost_optimization_setting(key: str, default=None):
    """Get a cost optimization setting value.

    Args:
        key: Setting key (supports dot notation for nested keys)
        default: Default value if key not found

    Returns:
        Setting value or default
    """
    if "." in key:
        keys = key.split(".")
        value = COST_OPTIMIZATION_SETTINGS
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    else:
        return COST_OPTIMIZATION_SETTINGS.get(key, default)


def get_optimized_field_mask(use_case: str) -> str:
    """Get optimized field mask for specific use case.

    Args:
        use_case: Use case ('search', 'details', 'minimal', 'comprehensive')

    Returns:
        Optimized field mask string
    """
    field_mask_map = {
        "search": get_cost_optimization_setting("search_field_mask", "search_essential"),
        "details": get_cost_optimization_setting("details_field_mask", "comprehensive"),
        "minimal": "search_minimal",
        "comprehensive": "comprehensive",
    }

    return field_mask_map.get(use_case, "search_essential")


def get_cache_ttl(cache_type: str) -> int:
    """Get cache TTL in seconds for cache type.

    Args:
        cache_type: Type of cache ('place_details', 'search_results', 'photos')

    Returns:
        TTL in seconds
    """
    days = get_cost_optimization_setting(f"cache_ttl_days.{cache_type}", 1)
    return days * 24 * 60 * 60  # Convert days to seconds


def should_skip_photos() -> bool:
    """Check if photos should be skipped in API calls to reduce costs."""
    return get_cost_optimization_setting("skip_photos_in_search", True)


def get_max_search_results() -> int:
    """Get maximum number of search results to limit costs."""
    return get_cost_optimization_setting("max_search_results", 20)


def get_max_photo_width() -> int:
    """Get maximum photo width to reduce bandwidth costs."""
    return get_cost_optimization_setting("max_photo_width", 300)


def is_caching_enabled() -> bool:
    """Check if caching is enabled."""
    return get_cost_optimization_setting("enable_caching", True)


def should_log_costs() -> bool:
    """Check if API costs should be logged for monitoring."""
    return get_cost_optimization_setting("log_api_costs", True)


# Environment-specific overrides
def apply_environment_overrides():
    """Apply environment-specific cost optimization overrides."""
    env = os.getenv("FLASK_ENV", "development")

    if env == "production":
        # Production: Aggressive cost optimization
        COST_OPTIMIZATION_SETTINGS.update(
            {
                "default_field_mask": "search_essential",
                "max_search_results": 15,
                "max_photo_width": 200,
                "skip_photos_in_search": True,
                "requests_per_minute": 30,  # More conservative in production
            }
        )
    elif env == "development":
        # Development: More permissive for testing
        COST_OPTIMIZATION_SETTINGS.update(
            {
                "default_field_mask": "search_basic",
                "max_search_results": 10,
                "max_photo_width": 300,
                "skip_photos_in_search": False,  # Show photos in dev for testing
                "requests_per_minute": 60,
            }
        )


# Initialize environment overrides
apply_environment_overrides()


class CostOptimizer:
    """Cost optimization utilities for Google API usage."""

    @staticmethod
    def estimate_api_cost(api_calls: Dict[str, int]) -> Dict[str, float]:
        """Estimate API costs based on call counts.

        Args:
            api_calls: Dictionary of API call types and counts

        Returns:
            Dictionary with cost estimates
        """
        # Google Places API pricing (as of 2024)
        pricing = {
            "text_search": 0.032,  # $0.032 per request
            "nearby_search": 0.032,  # $0.032 per request
            "place_details": 0.017,  # $0.017 per request
            "place_photos": 0.007,  # $0.007 per request
            "autocomplete": 0.00283,  # $0.00283 per request
        }

        costs = {}
        total_cost = 0.0

        for api_type, count in api_calls.items():
            price_per_call = pricing.get(api_type, 0.0)
            cost = count * price_per_call
            costs[api_type] = cost
            total_cost += cost

        costs["total"] = total_cost
        return costs

    @staticmethod
    def get_cost_savings_with_cache(
        cache_hit_rate: float, daily_api_calls: int, avg_cost_per_call: float
    ) -> Dict[str, float]:
        """Calculate cost savings from caching.

        Args:
            cache_hit_rate: Cache hit rate (0.0 to 1.0)
            daily_api_calls: Number of API calls per day
            avg_cost_per_call: Average cost per API call

        Returns:
            Dictionary with savings calculations
        """
        total_daily_cost = daily_api_calls * avg_cost_per_call
        cached_calls = daily_api_calls * cache_hit_rate
        savings = cached_calls * avg_cost_per_call
        remaining_cost = total_daily_cost - savings

        return {
            "total_daily_cost": total_daily_cost,
            "cached_calls": cached_calls,
            "savings": savings,
            "remaining_cost": remaining_cost,
            "savings_percentage": (savings / total_daily_cost) * 100 if total_daily_cost > 0 else 0,
        }

    @staticmethod
    def optimize_search_strategy(query: str, has_location: bool) -> Dict[str, any]:
        """Recommend optimal search strategy based on query characteristics.

        Args:
            query: Search query string
            has_location: Whether user location is available

        Returns:
            Dictionary with optimization recommendations
        """
        recommendations = {
            "preferred_method": "text_search",
            "field_mask": "search_essential",
            "max_results": 20,
            "reason": "Default recommendation",
        }

        # Analyze query characteristics
        query_lower = query.lower()

        if has_location and len(query.split()) <= 2:
            # Short query with location - use nearby search (cheaper)
            recommendations.update(
                {
                    "preferred_method": "nearby_search",
                    "reason": "Short query with location - nearby search is more cost-effective",
                }
            )
        elif "restaurant" in query_lower or "food" in query_lower:
            # Generic food query - use nearby search if location available
            if has_location:
                recommendations.update(
                    {
                        "preferred_method": "nearby_search",
                        "field_mask": "search_basic",
                        "reason": "Generic food query with location - nearby search recommended",
                    }
                )
        elif len(query.split()) > 3:
            # Complex query - use text search with minimal field mask
            recommendations.update(
                {
                    "field_mask": "search_minimal",
                    "max_results": 15,
                    "reason": "Complex query - minimal field mask to reduce costs",
                }
            )

        return recommendations
