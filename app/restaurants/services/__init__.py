"""Service layer for the restaurants blueprint.

This module serves as the main entry point for restaurant-related services.
It re-exports the service functions from the services module.
"""

from .services import (
    export_restaurants_to_csv,
    get_restaurant,
    import_restaurants_from_csv,
    process_restaurant_form,
)

# Re-export the functions for backward compatibility
__all__ = [
    "get_restaurant",
    "process_restaurant_form",
    "import_restaurants_from_csv",
    "export_restaurants_to_csv",
]
