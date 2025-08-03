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

# Configure logger
logger = logging.getLogger(__name__)

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


def _get_database_path() -> Optional[str]:
    """Get the appropriate database path based on the environment.

    Returns:
        Optional[str]: Path to the database file, or None if using a different database
    """
    # In Lambda, we expect DATABASE_URL to be set in environment variables
    if _is_lambda_environment():
        return None

    # In development, use a file-based SQLite database
    instance_path = os.path.join(os.path.dirname(__file__), "..", "instance")
    os.makedirs(instance_path, exist_ok=True)
    return os.path.join(instance_path, "meal_expense_tracker.db")


def _is_lambda_environment() -> bool:
    """Check if running in AWS Lambda environment.

    Returns:
        bool: True if running in AWS Lambda, False otherwise
    """
    return os.environ.get("AWS_EXECUTION_ENV", "").startswith("AWS_Lambda_") or os.environ.get(
        "AWS_LAMBDA_FUNCTION_NAME"
    )


def _get_environment_database_url() -> Optional[str]:
    """Get database URL from environment variables with proper formatting.

    Returns:
        Optional[str]: The database URL with proper formatting, or None if not set
    """
    db_url = os.environ.get("DATABASE_URL")
    if db_url and db_url.startswith("postgres://"):
        # SQLAlchemy 2.0+ requires postgresql:// instead of postgres://
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return db_url


def _initialize_sqlite_database() -> str:
    """Initialize and return SQLite database URI.

    Returns:
        str: SQLite database URI
    """
    db_path = _get_database_path()
    if db_path:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        # Use SQLite with WAL mode for better concurrency
        return f"sqlite:///{db_path}?check_same_thread=False&timeout=30"

    # Fall back to in-memory database if no path is available
    # (should only happen in tests or if _get_database_path() is modified)
    logging.warning(
        "No database path available, using in-memory SQLite database. " "Data will be lost when the application exits."
    )
    return "sqlite:///:memory:"


def _get_app_database_uri(app: "Flask") -> str:
    """Get database URI from Flask app configuration.

    Args:
        app: The Flask application instance

    Returns:
        str: The database URI from app config or a default SQLite URI
    """
    if "SQLALCHEMY_DATABASE_URI" in app.config:
        return str(app.config["SQLALCHEMY_DATABASE_URI"])

    # Fall back to SQLite in development
    db_path = _get_database_path()
    if db_path:
        return f"sqlite:///{db_path}"

    # Last resort: in-memory database
    return "sqlite:///:memory:"


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
    # First, try to get the database URL from environment variables
    db_url = _get_environment_database_url()
    if db_url:
        return db_url

    # In Lambda, we require DATABASE_URL to be set
    if _is_lambda_environment():
        raise RuntimeError("DATABASE_URL environment variable must be set in Lambda environment")

    # If we have an app context, try to get the database URI from the app config
    try:
        current_app_obj = current_app._get_current_object()  # type: ignore[attr-defined]
        app_to_use = app or current_app_obj
        return _get_app_database_uri(app_to_use)
    except RuntimeError:
        # No app context, use SQLite with a fallback to in-memory
        return _initialize_sqlite_database()


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
    # Only initialize if not already done
    if "sqlalchemy" in app.extensions:
        return

    # Get the database URI
    try:
        db_uri = get_database_uri(app)
        app.config["SQLALCHEMY_DATABASE_URI"] = db_uri

        # Configure SQLAlchemy
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

        # Configure connection pooling for production
        if not db_uri.startswith("sqlite"):
            app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
                "pool_pre_ping": True,
                "pool_recycle": 300,  # Recycle connections after 5 minutes
                "pool_size": 5,
                "max_overflow": 10,
            }

        # Initialize SQLAlchemy with the app
        db.init_app(app)

        # Create tables if they don't exist
        with app.app_context():
            db.create_all()

    except Exception as e:
        logger.error("Failed to initialize database: %s", e)
        raise RuntimeError(f"Failed to initialize database: {e}") from e


def create_tables() -> None:
    """Create all database tables if they don't exist.

    This function is kept for backward compatibility but the main
    initialization happens in init_database().

    Raises:
        RuntimeError: If called outside of an application context
    """
    with current_app.app_context():
        db.create_all()


def drop_tables() -> None:
    """Drop all database tables.

    Raises:
        RuntimeError: If called outside of an application context
    """
    with current_app.app_context():
        db.drop_all()


def get_session() -> scoped_session[SQLAlchemySession]:
    """Get a scoped database session.

    This function ensures that a session is created within the application context
    and properly handles the session lifecycle.

    Returns:
        scoped_session[SQLAlchemySession]: A scoped SQLAlchemy session

    Raises:
        RuntimeError: If the database session factory is not initialized or outside app context
    """
    if not hasattr(db, "session") or not db.session:
        raise RuntimeError("Database session factory not initialized. " "Make sure to call init_database() first.")
    return db.session


def get_engine() -> Engine:
    """Get the SQLAlchemy engine.

    This function returns the SQLAlchemy engine, ensuring it's properly initialized
    within an application context.

    Returns:
        Engine: The SQLAlchemy engine instance

    Raises:
        RuntimeError: If the engine is not initialized or called outside application context
    """
    if not hasattr(db, "engine") or not db.engine:
        raise RuntimeError(
            "Database engine not initialized. Make sure to call init_database() first. "
            "If you're seeing this in a test, make sure to set up a test application context."
        )
    return db.engine
