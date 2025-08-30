"""
Google Maps API Configuration and Optimization
Handles caching, headers, and performance optimization for Google Maps API calls.
"""

from typing import Any, Dict

from flask import current_app


class GoogleMapsOptimizer:
    """Optimizes Google Maps API requests with proper caching headers."""

    @staticmethod
    def get_optimized_headers() -> Dict[str, str]:
        """
        Get optimized headers for Google Maps API requests.

        Returns:
            Dict with cache-control and other performance headers
        """
        return {
            "Cache-Control": "public, max-age=300, s-maxage=600",  # 5min client, 10min proxy
            "User-Agent": f"MealExpenseTracker/{current_app.config.get('APP_VERSION', '1.0.0')}",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
        }

    @staticmethod
    def get_api_config() -> Dict[str, Any]:
        """
        Get optimized Google Maps API configuration.

        Returns:
            Configuration dict with performance optimizations
        """
        return {
            "libraries": ["places", "geometry"],
            "language": "en",
            "region": "US",
            "loading": "async",
            "defer": True,
            "callback": "_googlemaps_loaded",
            # Performance optimizations
            "v": "beta",  # Use latest stable version
            "channel": current_app.config.get("GOOGLE_MAPS_CHANNEL", "production"),
        }

    @staticmethod
    def get_places_request_config() -> Dict[str, Any]:
        """
        Get optimized configuration for Places API requests.

        Returns:
            Configuration for Places API with caching
        """
        return {
            "fields": [
                "place_id",
                "formatted_address",
                "name",
                "geometry",
                "types",
                "rating",
                "user_ratings_total",
                "price_level",
                "website",
                "formatted_phone_number",
            ],
            "language": "en",
            "region": "US",
        }


def configure_google_maps_csp() -> Dict[str, str]:
    """
    Configure Content Security Policy for Google Maps.

    Returns:
        CSP directives for Google Maps API
    """
    return {
        "script-src": "'self' 'unsafe-inline' https://maps.googleapis.com",
        "connect-src": "'self' https://maps.googleapis.com https://places.googleapis.com",
        "img-src": "'self' data: https://maps.googleapis.com https://maps.gstatic.com",
        "style-src": "'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src": "'self' https://fonts.gstatic.com",
        "frame-src": "'self' https://www.google.com",
    }


def get_maps_script_url(api_key: str) -> str:
    """
    Generate optimized Google Maps script URL with caching parameters.

    Args:
        api_key: Google Maps API key

    Returns:
        Optimized script URL with performance parameters
    """
    config = GoogleMapsOptimizer.get_api_config()

    params = [
        f"key={api_key}",
        f"libraries={','.join(config['libraries'])}",
        f"language={config['language']}",
        f"region={config['region']}",
        f"v={config['v']}",
        f"loading={config['loading']}",
        f"callback={config['callback']}",
    ]

    if config.get("channel"):
        params.append(f"channel={config['channel']}")

    return f"https://maps.googleapis.com/maps/api/js?{'&'.join(params)}"
