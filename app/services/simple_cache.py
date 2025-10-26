"""Simple in-memory caching for Google API responses.

This module provides lightweight in-memory caching for Google Places API responses.
No database persistence - keeps it simple and fast.

Following TIGER principles:
- Testing: Simple cache operations that are easy to test
- Interfaces: Minimal cache interface with get/set operations
- Generality: Reusable caching patterns
- Examples: Clear usage examples
- Refactoring: Single responsibility for simple caching logic
"""

import time
from typing import Any, Dict, Optional, Tuple

# Global in-memory cache
_cache: Dict[str, Any] = {}
_cache_ttl: Dict[str, float] = {}
_default_ttl = 3600  # 1 hour


def _generate_search_key(query: str, location: Optional[Tuple[float, float]], radius: float) -> str:
    """Generate cache key for search results."""
    if location:
        return f"search:{query}|{location[0]:.4f},{location[1]:.4f}|{radius:.1f}"
    return f"search:{query}|no_location|{radius:.1f}"


def _generate_place_key(place_id: str) -> str:
    """Generate cache key for place details."""
    return f"place:{place_id}"


def _is_expired(cache_key: str, ttl_seconds: int = _default_ttl) -> bool:
    """Check if cache entry is expired."""
    if cache_key not in _cache:
        return True

    cached_time = _cache_ttl.get(cache_key, 0)
    return (time.time() - cached_time) > ttl_seconds


def get_search_results(query: str, location: Optional[Tuple[float, float]], radius: float) -> Optional[Any]:
    """Get cached search results."""
    cache_key = _generate_search_key(query, location, radius)
    if _is_expired(cache_key):
        return None
    return _cache.get(cache_key)


def cache_search_results(query: str, location: Optional[Tuple[float, float]], radius: float, results: Any) -> None:
    """Cache search results."""
    cache_key = _generate_search_key(query, location, radius)
    _cache[cache_key] = results
    _cache_ttl[cache_key] = time.time()


def get_place_details(place_id: str) -> Optional[Any]:
    """Get cached place details."""
    cache_key = _generate_place_key(place_id)
    if _is_expired(cache_key):
        return None
    return _cache.get(cache_key)


def cache_place_details(place_id: str, data: Any) -> None:
    """Cache place details."""
    cache_key = _generate_place_key(place_id)
    _cache[cache_key] = data
    _cache_ttl[cache_key] = time.time()


def clear_expired_cache() -> int:
    """Clear expired cache entries. Returns number of entries cleared."""
    current_time = time.time()
    expired_keys = [key for key, timestamp in _cache_ttl.items() if (current_time - timestamp) >= _default_ttl]

    for key in expired_keys:
        _cache.pop(key, None)
        _cache_ttl.pop(key, None)

    return len(expired_keys)


def get_cache_stats() -> Dict[str, int]:
    """Get cache statistics."""
    return {
        "total_entries": len(_cache),
        "expired_entries": len([k for k in _cache.keys() if _is_expired(k)]),
    }


# Legacy compatibility - SimpleCache class for backward compatibility
class SimpleCache:
    """Legacy compatibility class - delegates to global functions."""

    def get_search_results(self, query: str, location: Optional[Tuple[float, float]], radius: float) -> Optional[Any]:
        return get_search_results(query, location, radius)

    def cache_search_results(
        self, query: str, location: Optional[Tuple[float, float]], radius: float, results: Any
    ) -> bool:
        cache_search_results(query, location, radius, results)
        return True

    def get_place_details(self, place_id: str) -> Optional[Any]:
        return get_place_details(place_id)

    def cache_place_details(self, place_id: str, data: Any) -> bool:
        cache_place_details(place_id, data)
        return True

    def clear_expired(self) -> int:
        return clear_expired_cache()


def get_simple_cache() -> SimpleCache:
    """Get a simple cache instance for backward compatibility."""
    return SimpleCache()
