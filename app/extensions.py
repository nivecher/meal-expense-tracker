"""Application extensions module.

This module initializes and configures all Flask extensions used in the application.
"""

from flask import Flask
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

# Initialize SQLAlchemy
db = SQLAlchemy()

# Re-export for backward compatibility
database = db

# Initialize extensions
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"
csrf = CSRFProtect()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

# Initialize JWT
jwt = JWTManager()


def init_extensions(app: Flask) -> None:
    """Initialize all Flask extensions.

    Args:
        app: The Flask application instance
    """
    # Initialize database
    db.init_app(app)

    # Initialize migrations
    migrate.init_app(app, db)

    # Initialize login manager
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"
    login_manager.refresh_view = "auth.login"
    login_manager.needs_refresh_message = "Session expired. Please log in again."
    login_manager.needs_refresh_message_category = "info"

    # Import and initialize the login manager with user loader
    from .auth.models import init_login_manager

    init_login_manager(login_manager)

    # Initialize CSRF protection
    csrf.init_app(app)

    # Initialize rate limiting
    limiter.init_app(app)

    # Initialize JWT
    jwt.init_app(app)

    # Set up application context for extensions
    with app.app_context():
        # Import models to ensure they are registered with SQLAlchemy
        from . import models  # noqa: F401
        from .auth import models as auth_models  # noqa: F401
        from .expenses import models as expense_models  # noqa: F401
        from .restaurants import models as restaurant_models  # noqa: F401
