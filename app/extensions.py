"""Application Flask extensions.

This module initializes and configures all Flask extensions used in the application.
"""

from typing import Optional, TypeVar

from flask import Flask, request
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, UserMixin
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy.model import Model
from flask_wtf.csrf import CSRFProtect, generate_csrf

# Type variable for database models
ModelType = TypeVar("ModelType", bound=Model)

# Initialize SQLAlchemy
db = SQLAlchemy()


# Initialize JWT for token-based authentication
jwt = JWTManager()


# Initialize LoginManager for session-based authentication
login_manager = LoginManager()
login_manager.login_view = "auth.login"


# Initialize rate limiter to prevent abuse
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"], storage_uri="memory://")


# Initialize CSRF protection
csrf = CSRFProtect()


# Initialize Flask-Migrate for database migrations
migrate = Migrate()


def init_app(app: Flask) -> None:
    """Initialize all extensions with the Flask application.

    Args:
        app: The Flask application instance
    """
    # Initialize all extensions
    db.init_app(app)
    jwt.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    # Configure rate limiter
    limiter.init_app(app)

    # Configure JWT settings
    app.config["JWT_SECRET_KEY"] = app.config.get("SECRET_KEY", "dev-key-change-me")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 3600  # 1 hour
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = 2592000  # 30 days

    # Configure CSRF protection
    app.config.update(
        WTF_CSRF_CHECK_DEFAULT=True,  # Enable CSRF by default
        WTF_CSRF_SSL_STRICT=True,  # Enforce HTTPS in production
        WTF_CSRF_TIME_LIMIT=3600,  # 1 hour CSRF token lifetime
    )

    # Add CSRF token to response headers for API requests
    @app.after_request
    def add_csrf_headers(response):
        if request.path.startswith("/api/"):
            response.headers.set("X-CSRFToken", generate_csrf())
        return response

    # Exempt API routes from CSRF protection
    with app.app_context():
        from .api import bp as api_bp

        csrf.exempt(api_bp)


# Add user loader for Flask-Login
@login_manager.user_loader
def load_user(user_id: str) -> Optional[UserMixin]:
    """Load a user from the database.

    Args:
        user_id: The ID of the user to load

    Returns:
        The user object if found, None otherwise
    """
    from app.auth.models import User  # Import here to avoid circular imports

    return User.query.get(int(user_id))


# No need for app context here - models will be imported when needed by the application
