"""Remote administration module for Lambda-based management."""

from flask import Flask

from .lambda_admin import LambdaAdminHandler
from .operations import AdminOperationRegistry, BaseAdminOperation


def init_app(app: Flask) -> None:
    """Initialize the admin module with the Flask app.

    This function is called during app initialization to set up
    any admin-related functionality.

    Args:
        app: Flask application instance
    """
    # Admin module is primarily for Lambda-based remote administration
    # No specific Flask app initialization required at this time
    app.logger.debug("Admin module initialized for remote administration")


__all__ = ["LambdaAdminHandler", "BaseAdminOperation", "AdminOperationRegistry", "init_app"]
