"""Service layer for the restaurants blueprint.

This module serves as the main entry point for restaurant-related services.
It re-exports the service functions from the services module.
"""

from .services import (
    create_restaurant,
    delete_restaurant_by_id,
    export_restaurants_for_user,
    get_restaurant_for_user,
    get_restaurants_with_stats,
    get_unique_cuisines,
    import_restaurants_from_csv,
    update_restaurant,
)

__all__ = [
    "get_restaurants_with_stats",
    "get_unique_cuisines",
    "create_restaurant",
    "update_restaurant",
    "get_restaurant_for_user",
    "delete_restaurant_by_id",
    "import_restaurants_from_csv",
    "export_restaurants_for_user",
]
