"""Service initialization and management.

This module provides functions to initialize and manage services that require
AWS resources or other external dependencies.
"""

from flask import Flask


def init_services(app: Flask) -> None:
    """Initialize all services that require AWS resources or other external dependencies.

    Args:
        app: The Flask application instance
    """
    # Import here to avoid circular imports
    from app.restaurants.services.places import init_places_service

    # Initialize the PlacesService with the Google API key from SSM
    try:
        places_service = init_places_service(app)
        app.places_service = places_service
        app.logger.info("Successfully initialized PlacesService")
    except Exception as e:
        app.logger.error("Failed to initialize PlacesService: %s", str(e))
        # Re-raise in development to fail fast
        if app.config.get("FLASK_ENV") == "development":
            raise
