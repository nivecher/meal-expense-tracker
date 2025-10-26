"""Google Places API response caching service.

This module provides intelligent caching for Google Places API responses to reduce costs
and improve performance. Caches are organized by data type and have appropriate TTLs.

Following TIGER principles:
- Testing: Cache operations are pure and testable
- Interfaces: Simple cache get/set operations
- Generality: Reusable caching patterns for different data types
- Examples: Clear cache key patterns and TTL strategies
- Refactoring: Single responsibility for caching logic
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Cache TTLs in seconds (24 hours = 86400 seconds)
CACHE_TTLS = {
    "place_details": 86400 * 7,  # 7 days - place details change rarely
    "place_search": 86400,  # 1 day - search results can change daily
    "place_photos": 86400 * 30,  # 30 days - photos rarely change
    "geocoding": 86400 * 30,  # 30 days - addresses rarely change
    "place_autocomplete": 3600,  # 1 hour - autocomplete can change frequently
}

# Cache key prefixes
CACHE_PREFIXES = {
    "place_details": "gp:details:",
    "place_search": "gp:search:",
    "place_photos": "gp:photos:",
    "geocoding": "gp:geocode:",
    "place_autocomplete": "gp:autocomplete:",
}


class GooglePlacesCache:
    """Service for caching Google Places API responses."""

    def __init__(self):
        """Initialize the cache service."""
        self.redis_client = self._get_redis_client()

    def _get_redis_client(self):
        """Get Redis client from Flask app context."""
        try:
            from app.extensions import redis_client

            return redis_client
        except ImportError:
            logger.warning("Redis not available, caching disabled")
            return None

    def _is_cache_available(self) -> bool:
        """Check if caching is available."""
        return self.redis_client is not None

    def _generate_cache_key(self, cache_type: str, identifier: str) -> str:
        """Generate a cache key for the given type and identifier.

        Args:
            cache_type: Type of cache (place_details, place_search, etc.)
            identifier: Unique identifier for the cached data

        Returns:
            Cache key string
        """
        prefix = CACHE_PREFIXES.get(cache_type, "gp:unknown:")

        # For complex identifiers, hash them to keep keys reasonable length
        if len(identifier) > 100:
            identifier = hashlib.md5(identifier.encode(), usedforsecurity=False).hexdigest()

        return f"{prefix}{identifier}"

    def _serialize_data(self, data: Any) -> str:
        """Serialize data for storage in cache.

        Args:
            data: Data to serialize

        Returns:
            Serialized JSON string
        """
        try:
            return json.dumps(data, default=str)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize cache data: {e}")
            return json.dumps({"error": "serialization_failed"})

    def _deserialize_data(self, data: str) -> Any:
        """Deserialize data from cache.

        Args:
            data: Serialized JSON string

        Returns:
            Deserialized data or None if failed
        """
        try:
            return json.loads(data)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to deserialize cache data: {e}")
            return None

    def get(self, cache_type: str, identifier: str) -> Optional[Any]:
        """Get cached data.

        Args:
            cache_type: Type of cache (place_details, place_search, etc.)
            identifier: Unique identifier for the cached data

        Returns:
            Cached data or None if not found
        """
        if not self._is_cache_available():
            return None

        try:
            cache_key = self._generate_cache_key(cache_type, identifier)
            cached_data = self.redis_client.get(cache_key)

            if cached_data:
                logger.debug(f"Cache hit for {cache_type}: {identifier[:50]}...")
                return self._deserialize_data(cached_data)
            else:
                logger.debug(f"Cache miss for {cache_type}: {identifier[:50]}...")
                return None

        except Exception as e:
            logger.error(f"Cache get error for {cache_type}: {e}")
            return None

    def set(self, cache_type: str, identifier: str, data: Any, ttl: Optional[int] = None) -> bool:
        """Set cached data.

        Args:
            cache_type: Type of cache (place_details, place_search, etc.)
            identifier: Unique identifier for the cached data
            data: Data to cache
            ttl: Time to live in seconds (uses default if None)

        Returns:
            True if successful, False otherwise
        """
        if not self._is_cache_available():
            return False

        try:
            cache_key = self._generate_cache_key(cache_type, identifier)
            serialized_data = self._serialize_data(data)

            # Use default TTL if not provided
            if ttl is None:
                ttl = CACHE_TTLS.get(cache_type, 3600)

            # Store in cache
            self.redis_client.setex(cache_key, ttl, serialized_data)
            logger.debug(f"Cached {cache_type}: {identifier[:50]}... (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Cache set error for {cache_type}: {e}")
            return False

    def delete(self, cache_type: str, identifier: str) -> bool:
        """Delete cached data.

        Args:
            cache_type: Type of cache (place_details, place_search, etc.)
            identifier: Unique identifier for the cached data

        Returns:
            True if successful, False otherwise
        """
        if not self._is_cache_available():
            return False

        try:
            cache_key = self._generate_cache_key(cache_type, identifier)
            result = self.redis_client.delete(cache_key)
            logger.debug(f"Deleted cache for {cache_type}: {identifier[:50]}...")
            return bool(result)

        except Exception as e:
            logger.error(f"Cache delete error for {cache_type}: {e}")
            return False

    def clear_cache_type(self, cache_type: str) -> bool:
        """Clear all cached data of a specific type.

        Args:
            cache_type: Type of cache to clear

        Returns:
            True if successful, False otherwise
        """
        if not self._is_cache_available():
            return False

        try:
            prefix = CACHE_PREFIXES.get(cache_type, f"gp:{cache_type}:")
            pattern = f"{prefix}*"

            # Get all keys matching the pattern
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted_count = self.redis_client.delete(*keys)
                logger.info(f"Cleared {deleted_count} cache entries for {cache_type}")
                return True
            else:
                logger.debug(f"No cache entries found for {cache_type}")
                return True

        except Exception as e:
            logger.error(f"Cache clear error for {cache_type}: {e}")
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        if not self._is_cache_available():
            return {"error": "Redis not available"}

        try:
            stats = {}
            for cache_type, prefix in CACHE_PREFIXES.items():
                pattern = f"{prefix}*"
                keys = self.redis_client.keys(pattern)
                stats[cache_type] = {
                    "count": len(keys),
                    "prefix": prefix,
                }

            # Add total stats
            total_keys = sum(stat["count"] for stat in stats.values())
            stats["total"] = {
                "count": total_keys,
                "types": len(stats),
            }

            return stats

        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {"error": str(e)}

    # Specialized cache methods for common use cases

    def cache_place_details(self, place_id: str, data: Any) -> bool:
        """Cache place details data."""
        return self.set("place_details", place_id, data)

    def get_place_details(self, place_id: str) -> Optional[Any]:
        """Get cached place details."""
        return self.get("place_details", place_id)

    def cache_search_results(
        self, query: str, location: Optional[Tuple[float, float]], radius: float, results: Any
    ) -> bool:
        """Cache search results with query parameters."""
        # Create a composite key from search parameters
        if location:
            key = f"{query}|{location[0]:.4f},{location[1]:.4f}|{radius:.1f}"
        else:
            key = f"{query}|no_location|{radius:.1f}"
        return self.set("place_search", key, results)

    def get_search_results(self, query: str, location: Optional[Tuple[float, float]], radius: float) -> Optional[Any]:
        """Get cached search results."""
        if location:
            key = f"{query}|{location[0]:.4f},{location[1]:.4f}|{radius:.1f}"
        else:
            key = f"{query}|no_location|{radius:.1f}"
        return self.get("place_search", key)

    def cache_photos(self, place_id: str, photos: List[Dict[str, Any]]) -> bool:
        """Cache photo data for a place."""
        return self.set("place_photos", place_id, photos)

    def get_photos(self, place_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached photo data."""
        return self.get("place_photos", place_id)


def get_google_places_cache() -> GooglePlacesCache:
    """Get a Google Places cache instance.

    Returns:
        GooglePlacesCache instance
    """
    return GooglePlacesCache()
