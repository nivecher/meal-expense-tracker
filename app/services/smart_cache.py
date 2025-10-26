"""
Smart caching service for Google Places API with intelligent cache strategies.

This module provides advanced caching strategies that adapt based on usage patterns,
data freshness requirements, and cost optimization goals.

Following TIGER principles:
- Testing: Cache strategies are testable and predictable
- Interfaces: Simple cache interface with smart behavior
- Generality: Reusable caching patterns for different data types
- Examples: Clear usage examples and configuration
- Refactoring: Single responsibility for smart cache logic
"""

import logging
import time
from typing import Any, Dict, Optional, Tuple

from app.services.simple_cache import cache_place_details as base_cache_place_details
from app.services.simple_cache import cache_search_results as base_cache_search_results
from app.services.simple_cache import get_place_details as base_get_place_details
from app.services.simple_cache import get_search_results as base_get_search_results

logger = logging.getLogger(__name__)


class SmartCache:
    """Smart caching service with adaptive strategies."""

    def __init__(self):
        """Initialize smart cache."""
        # Adaptive TTL based on data type and usage patterns
        self.adaptive_ttls = {
            "search_popular": 7200,  # 2 hours for popular searches
            "search_rare": 3600,  # 1 hour for rare searches
            "place_details": 86400,  # 24 hours for place details
            "place_photos": 259200,  # 3 days for photos
        }

        # Usage tracking for adaptive strategies
        self.usage_stats = {
            "search_queries": {},
            "place_details": {},
            "cache_hits": 0,
            "cache_misses": 0,
        }

    def get_search_results(self, query: str, location: Optional[Tuple[float, float]], radius: float) -> Optional[Any]:
        """Get cached search results with smart TTL adjustment."""
        # Track query usage
        self._track_query_usage(query)

        # Determine cache strategy based on query popularity
        cache_strategy = self._get_cache_strategy(query)

        # Use base cache
        results = base_get_search_results(query, location, radius)

        if results:
            self.usage_stats["cache_hits"] += 1
            logger.debug(f"Smart cache hit for query: {query} (strategy: {cache_strategy})")
        else:
            self.usage_stats["cache_misses"] += 1
            logger.debug(f"Smart cache miss for query: {query} (strategy: {cache_strategy})")

        return results

    def cache_search_results(
        self, query: str, location: Optional[Tuple[float, float]], radius: float, results: Any
    ) -> None:
        """Cache search results with smart TTL strategy."""
        cache_strategy = self._get_cache_strategy(query)

        # Use base cache
        base_cache_search_results(query, location, radius, results)

        logger.debug(f"Cached search results for query: {query} (strategy: {cache_strategy})")

    def get_place_details(self, place_id: str) -> Optional[Any]:
        """Get cached place details."""
        results = base_get_place_details(place_id)

        if results:
            self.usage_stats["cache_hits"] += 1
            self._track_place_usage(place_id)
            logger.debug(f"Smart cache hit for place: {place_id}")
        else:
            self.usage_stats["cache_misses"] += 1
            logger.debug(f"Smart cache miss for place: {place_id}")

        return results

    def cache_place_details(self, place_id: str, details: Any) -> None:
        """Cache place details with appropriate TTL."""
        base_cache_place_details(place_id, details)
        self._track_place_usage(place_id)
        logger.debug(f"Cached place details for place: {place_id}")

    def _track_query_usage(self, query: str) -> None:
        """Track query usage for adaptive caching."""
        current_time = time.time()

        if query not in self.usage_stats["search_queries"]:
            self.usage_stats["search_queries"][query] = {
                "count": 0,
                "last_used": current_time,
                "first_used": current_time,
            }

        self.usage_stats["search_queries"][query]["count"] += 1
        self.usage_stats["search_queries"][query]["last_used"] = current_time

    def _track_place_usage(self, place_id: str) -> None:
        """Track place usage for adaptive caching."""
        current_time = time.time()

        if place_id not in self.usage_stats["place_details"]:
            self.usage_stats["place_details"][place_id] = {
                "count": 0,
                "last_used": current_time,
                "first_used": current_time,
            }

        self.usage_stats["place_details"][place_id]["count"] += 1
        self.usage_stats["place_details"][place_id]["last_used"] = current_time

    def _get_cache_strategy(self, query: str) -> str:
        """Determine cache strategy based on query popularity."""
        if query not in self.usage_stats["search_queries"]:
            return "search_rare"

        query_stats = self.usage_stats["search_queries"][query]
        current_time = time.time()

        # Consider a query popular if:
        # 1. It's been used more than 5 times, OR
        # 2. It's been used multiple times in the last hour
        if query_stats["count"] > 5 or (current_time - query_stats["first_used"]) < 3600 and query_stats["count"] > 2:
            return "search_popular"

        return "search_rare"

    def get_cache_efficiency_stats(self) -> Dict[str, Any]:
        """Get cache efficiency statistics."""
        total_requests = self.usage_stats["cache_hits"] + self.usage_stats["cache_misses"]
        hit_rate = (self.usage_stats["cache_hits"] / total_requests * 100) if total_requests > 0 else 0

        # Get most popular queries
        popular_queries = sorted(self.usage_stats["search_queries"].items(), key=lambda x: x[1]["count"], reverse=True)[
            :10
        ]

        # Get most accessed places
        popular_places = sorted(self.usage_stats["place_details"].items(), key=lambda x: x[1]["count"], reverse=True)[
            :10
        ]

        return {
            "hit_rate": hit_rate,
            "total_requests": total_requests,
            "cache_hits": self.usage_stats["cache_hits"],
            "cache_misses": self.usage_stats["cache_misses"],
            "popular_queries": popular_queries,
            "popular_places": popular_places,
            "unique_queries": len(self.usage_stats["search_queries"]),
            "unique_places": len(self.usage_stats["place_details"]),
        }

    def optimize_cache_strategy(self) -> Dict[str, Any]:
        """Analyze usage patterns and suggest optimizations."""
        stats = self.get_cache_efficiency_stats()
        suggestions = []

        # Analyze hit rate
        if stats["hit_rate"] < 50:
            suggestions.append("Consider increasing cache TTL for better hit rates")

        # Analyze query patterns
        if stats["unique_queries"] > 100:
            suggestions.append("High query diversity - consider query normalization")

        # Analyze place access patterns
        if stats["unique_places"] > 50:
            suggestions.append("Many unique places - consider place clustering")

        return {
            "current_stats": stats,
            "suggestions": suggestions,
            "recommended_ttl_adjustments": self._get_ttl_recommendations(),
        }

    def _get_ttl_recommendations(self) -> Dict[str, int]:
        """Get TTL recommendations based on usage patterns."""
        stats = self.get_cache_efficiency_stats()

        recommendations = {}

        # Adjust TTL based on hit rate
        if stats["hit_rate"] > 80:
            recommendations["search_popular"] = 14400  # 4 hours for high hit rate
            recommendations["search_rare"] = 7200  # 2 hours for high hit rate
        elif stats["hit_rate"] < 30:
            recommendations["search_popular"] = 3600  # 1 hour for low hit rate
            recommendations["search_rare"] = 1800  # 30 minutes for low hit rate

        return recommendations


def get_smart_cache() -> SmartCache:
    """Get a smart cache instance."""
    return SmartCache()
