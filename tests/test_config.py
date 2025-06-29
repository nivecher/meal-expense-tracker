"""Test configuration for SQLite in-memory database with SQLAlchemy 2.0."""

from typing import Any, Dict, Optional

from flask import Flask
from flask.testing import FlaskClient as BaseFlaskClient


class TestConfig:
    """Test configuration with SQLite in-memory database for SQLAlchemy 2.0."""

    # Application settings
    SECRET_KEY = "test-secret-key"
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False
    LOGIN_DISABLED = False

    # Database settings for SQLAlchemy 2.0
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SQLAlchemy 2.0 engine options
    SQLALCHEMY_ENGINE_OPTIONS: Dict[str, Any] = {
        "connect_args": {"check_same_thread": False},
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "echo": False,
    }

    # Session configuration
    SQLALCHEMY_SESSION_OPTIONS: Dict[str, Any] = {
        "expire_on_commit": False,
        "autoflush": False,
    }

    # Login manager configuration
    LOGIN_DISABLED = False
    LOGIN_VIEW = "auth.login"
    LOGIN_MESSAGE_CATEGORY = "info"

    @classmethod
    def init_app(cls, app: Flask) -> Flask:
        """Initialize the application with this configuration.

        Args:
            app: The Flask application instance

        Returns:
            The configured Flask application instance
        """
        # Configure the app with our settings
        app.config.from_object(cls)

        # Initialize extensions
        from app.auth.models import init_login_manager
        from app.extensions import db, login_manager, migrate

        # Initialize SQLAlchemy
        db.init_app(app)

        # Initialize Flask-Migrate
        migrate.init_app(app, db)

        # Initialize Login Manager with authentication
        login_manager.init_app(app)
        login_manager.login_view = cls.LOGIN_VIEW
        login_manager.login_message_category = cls.LOGIN_MESSAGE_CATEGORY
        init_login_manager(login_manager)

        # Ensure login manager is registered in app.extensions
        if "login_manager" not in app.extensions:
            app.extensions["login_manager"] = login_manager

        # Import all models to ensure they are registered with SQLAlchemy
        from app.auth import models as auth_models  # noqa: F401

        # Initialize login manager
        from app.auth.models import init_login_manager
        from app.expenses import init_default_categories
        from app.expenses import models as expense_models  # noqa: F401
        from app.expenses.category import Category  # noqa: F401
        from app.restaurants import models as restaurant_models  # noqa: F401

        login_manager.init_app(app)
        init_login_manager(login_manager)

        # Register blueprints
        from app.auth.routes import auth_bp
        from app.expenses.routes import bp as expenses_bp
        from app.main.routes import main_bp
        from app.restaurants.routes import bp as restaurants_bp

        app.register_blueprint(auth_bp, url_prefix="/auth")
        app.register_blueprint(expenses_bp, url_prefix="/expenses")
        app.register_blueprint(main_bp)
        app.register_blueprint(restaurants_bp, url_prefix="/restaurants")

        # Create all database tables and initialize data
        with app.app_context():
            # Create all tables
            db.create_all()

            # Initialize default categories
            try:
                init_default_categories()
                db.session.commit()
            except Exception as e:
                app.logger.error(f"Failed to initialize default categories: {e}")
                db.session.rollback()
                raise

        return app


class TestClient(BaseFlaskClient):
    """Custom test client that handles JSON requests and authentication.

    This extends Flask's test client to handle authentication tokens and JSON requests.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the test client with optional authentication."""
        super().__init__(*args, **kwargs)
        self.auth_token: Optional[str] = None

    def set_auth_token(self, token: str) -> None:
        """Set the authentication token for subsequent requests.

        Args:
            token: The authentication token to use for requests
        """
        self.auth_token = token

    def open(self, *args: Any, **kwargs: Any) -> Any:
        """Open a request with optional authentication.

        Args:
            *args: Positional arguments to pass to the parent class
            **kwargs: Keyword arguments to pass to the parent class

        Returns:
            The response from the request
        """
        headers = kwargs.pop("headers", {})
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        if headers:
            kwargs["headers"] = headers
        return super().open(*args, **kwargs)
