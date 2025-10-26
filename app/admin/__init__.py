"""Admin module for user management and system administration."""

from flask import Flask

from .lambda_admin import LambdaAdminHandler
from .operations import AdminOperationRegistry, BaseAdminOperation
from .routes import bp as admin_bp


def init_app(app: Flask) -> None:
    """Initialize the admin module with the Flask app.

    This function is called during app initialization to set up
    any admin-related functionality.

    Args:
        app: Flask application instance
    """
    # Register the admin blueprint
    app.register_blueprint(admin_bp)

    app.logger.debug("Admin module initialized with web interface and remote administration")


__all__ = [
    "LambdaAdminHandler",
    "BaseAdminOperation",
    "AdminOperationRegistry",
    "init_app",
    "admin_bp",
]
