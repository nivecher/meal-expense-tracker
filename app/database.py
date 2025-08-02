"""Database configuration and utilities for the Meal Expense Tracker.

This module provides a centralized way to manage database connections,
initialization, and utilities for the application.
"""

from __future__ import annotations

# Standard library imports
import logging
import os
from typing import TYPE_CHECKING, Optional, TypeVar

# Third-party imports
from flask import Flask, current_app
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy.orm import scoped_session, sessionmaker

# Local application imports
from .extensions import db  # Import the existing SQLAlchemy instance

if TYPE_CHECKING:
    from flask.typing import ResponseValue
    from typing_extensions import TypeAlias
    from werkzeug.wrappers import Response as WerkzeugResponse

# Type variable for SQLAlchemy models
T = TypeVar("T")

# Type alias for scoped session
ScopedSession = scoped_session

if TYPE_CHECKING:
    # Type aliases for better readability
    FlaskResponse: TypeAlias = ResponseValue | WerkzeugResponse

# Export the db instance for use in other modules
__all__ = [
    "db",
    "get_database_uri",
    "init_database",
    "create_tables",
    "drop_tables",
    "get_session",
    "get_engine",
]

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy engine
engine: Optional[Engine] = None

# Create a thread-local session factory without binding to an engine yet
db_session_factory: ScopedSession = scoped_session(
    sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=None,  # Will be set in init_database
        class_=SQLAlchemySession,
    )
)


def _get_database_path() -> str:
    """Get the appropriate database path based on the environment."""
    # Use instance folder in the application directory by default
    instance_path = os.environ.get("INSTANCE_PATH")
    if instance_path:
        return os.path.join(instance_path, "meal_expenses.db")

    # Fall back to a local instance directory
    return os.path.join("instance", "meal_expenses.db")


def _is_lambda_environment() -> bool:
    """Check if running in AWS Lambda environment."""
    return bool(os.environ.get("AWS_EXECUTION_ENV") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))


def _get_environment_database_url() -> Optional[str]:
    """Get database URL from environment variables with proper formatting."""
    if "DATABASE_URL" not in os.environ:
        return None

    db_url = os.environ["DATABASE_URL"]
    # Ensure the URL starts with postgresql:// (not postgres://)
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return db_url


def _initialize_sqlite_database() -> str:
    """Initialize and return SQLite database URI."""
    try:
        db_path = _get_database_path()
        db_dir = os.path.dirname(db_path)

        # Create directory if it doesn't exist
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, mode=0o755, exist_ok=True)

        # Ensure the database file exists
        if not os.path.exists(db_path):
            with open(db_path, "w", encoding="utf-8"):
                os.chmod(db_path, 0x180)  # 0o600 in hex
            logger.info("Initialized SQLite database at %s", db_path)

        return f"sqlite:///{os.path.abspath(db_path)}"
    except Exception as e:
        logger.error("Failed to initialize SQLite database: %s", e)
        return "sqlite:///:memory:"


def _get_app_database_uri(app: "Flask") -> str:
    """Get database URI from Flask app configuration."""
    # Check for testing environment first
    if app.config.get("TESTING", False):
        return "sqlite:///:memory:"

    # Check for explicitly configured database URI
    if app.config.get("SQLALCHEMY_DATABASE_URI"):
        return app.config["SQLALCHEMY_DATABASE_URI"]

    # Default to SQLite in development
    return _initialize_sqlite_database()


def get_database_uri(app: Optional["Flask"] = None) -> str:
    """Get the database URI from environment or use SQLite as default.

    Priority order:
    1. DATABASE_URL environment variable (with postgres:// to postgresql:// conversion)
    2. In Lambda, fail if no DATABASE_URL is provided
    3. In-memory SQLite for testing or when no app context is available
    4. SQLALCHEMY_DATABASE_URI from app config
    5. SQLite database file in instance directory (development only)

    Args:
        app: Optional Flask app instance. If not provided, uses current_app

    Returns:
        str: The database URI

    Raises:
        RuntimeError: If in Lambda environment and no DATABASE_URL is provided
    """
    # Check for environment variable first (highest priority)
    if db_url := _get_environment_database_url():
        return db_url

    # Handle Lambda environment
    if _is_lambda_environment():
        raise RuntimeError("DATABASE_URL environment variable is required in Lambda environment")

    # Handle testing or missing app context
    if app is None and not current_app:
        logger.warning("No app context available, using in-memory SQLite database")
        return "sqlite:///:memory:"

    # Get app instance if not provided
    app = app or current_app._get_current_object()  # type: ignore

    return _get_app_database_uri(app)


def init_database(app: "Flask") -> None:
    """Initialize the database with the Flask app.

    This function configures SQLAlchemy with the appropriate database URI,
    sets up connection pooling for production, and ensures proper connection handling
    for both development and production environments.

    Note: This function is a no-op if SQLAlchemy is already initialized on the app.

    Args:
        app: The Flask application instance to initialize with the database

    Raises:
        RuntimeError: If there's an error initializing the database
    """
    # Skip if SQLAlchemy is already initialized
    if hasattr(app, "extensions") and "sqlalchemy" in app.extensions:
        logger.debug("SQLAlchemy already initialized, skipping database initialization")
        return

    try:
        # Get database URI and ensure it's properly formatted
        db_uri = get_database_uri(app)

        # Configure SQLAlchemy
        engine_options = {
            "pool_pre_ping": True,  # Enable connection health checks
            "pool_recycle": 300,  # Recycle connections after 5 minutes
            "pool_timeout": 30,  # Wait 30 seconds for a connection from the pool
            "pool_size": 5,  # Maintain 5 persistent connections
            "max_overflow": 10,  # Allow up to 10 additional connections during peak
        }

        # Update app config with database settings
        app.config.update(
            SQLALCHEMY_DATABASE_URI=db_uri,
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SQLALCHEMY_ENGINE_OPTIONS=engine_options,
        )

        # Initialize the database with the app
        db.init_app(app)

        # Configure connection pooling based on environment
        if _is_lambda_environment() or app.config.get("ENV") == "production":
            # Use RDS Proxy connection pooling in production/Lambda
            app.config.setdefault("SQLALCHEMY_ENGINE_OPTIONS", engine_options)
        elif db_uri and db_uri.startswith("sqlite"):
            # Use SQLite with WAL mode for development
            @app.teardown_appcontext
            def _shutdown_session(exception=None):
                if db.session:
                    if exception and db.session.is_active:
                        db.session.rollback()
                    db.session.remove()

        # Create all tables if they don't exist
        with app.app_context():
            db.create_all()

        logger.info("Database initialized successfully with URI: %s", db_uri)
        # Import models to ensure they are registered with SQLAlchemy
        from . import models  # noqa: F401
        from .auth import models as auth_models  # noqa: F401
        from .expenses import models as expense_models  # noqa: F401
        from .restaurants import models as restaurant_models  # noqa: F401

        logger.info("Database tables created/verified")

    except Exception as e:
        logger.error("Error initializing database: %s", str(e), exc_info=True)
        raise RuntimeError(f"Failed to initialize database: {str(e)}") from e


def create_tables() -> None:
    """Create all database tables if they don't exist.

    This function is kept for backward compatibility but the main
    initialization happens in init_database().
    """
    if not current_app:
        raise RuntimeError("create_tables() must be called within an application context")

    try:
        with current_app.app_context():
            db.create_all()
            logger.info("Database tables created via create_tables()")
    except Exception as e:
        logger.error("Failed to create database tables: %s", e)
        raise


def drop_tables() -> None:
    """Drop all database tables."""
    try:
        db.drop_all()
        logger.info("Dropped all database tables")
    except Exception as e:
        logger.error("Failed to drop database tables: %s", e)
        raise


def get_session() -> ScopedSession:
    """Get a scoped database session.

    This function ensures that a session is created within the application context
    and properly handles the session lifecycle.

    Returns:
        ScopedSession: A scoped SQLAlchemy session

    Raises:
        RuntimeError: If the database session factory is not initialized
    """
    if db_session_factory is None:
        raise RuntimeError("Database session factory not initialized. Call init_database() first.")

    # Ensure we're in an application context
    if not current_app:
        raise RuntimeError("Attempted to create database session outside of application context.")

    return db_session_factory()


def get_engine() -> Engine:
    """Get the SQLAlchemy engine.

    This function returns the SQLAlchemy engine, ensuring it's properly initialized
    within an application context.

    Returns:
        Engine: The SQLAlchemy engine instance

    Raises:
        RuntimeError: If the engine is not initialized or called outside application context
    """
    # Ensure we're in an application context
    if not current_app:
        raise RuntimeError(
            "Attempted to access database engine outside of application context. "
            "This typically means you need to use the database within a route or a function "
            "that has access to the Flask application context."
        )

    if engine is None:
        raise RuntimeError(
            "Database engine not initialized. Call init_database() with a Flask app first. "
            "If you're seeing this in a test, make sure to set up a test application context."
        )

    return engine
