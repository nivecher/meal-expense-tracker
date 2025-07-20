"""Database configuration and utilities for the Meal Expense Tracker.

This module provides a centralized way to manage database connections,
initialization, and utilities for the application.
"""

from __future__ import annotations

# Standard library imports
import logging
import os
import sys
from typing import TYPE_CHECKING, Optional, TypeVar

# Third-party imports
from flask import Flask, current_app
from sqlalchemy.engine import Engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.session import Session as SQLAlchemySession

# Local application imports
from .extensions import db

if TYPE_CHECKING:
    from flask.typing import ResponseValue
    from typing_extensions import TypeAlias
    from werkzeug.wrappers import Response as WerkzeugResponse

# Type variable for SQLAlchemy models
T = TypeVar("T")

# Type alias for scoped session
ScopedSession: TypeAlias = scoped_session[sessionmaker[SQLAlchemySession]]

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

# Initialize SQLAlchemy without binding to an app yet
engine: Optional[Engine] = None

# Create a thread-local session factory
db_session_factory: ScopedSession = scoped_session(
    sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db.engine if db.engine else None,
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


def get_database_uri(app: Optional["Flask"] = None) -> str:
    """Get the database URI from environment or use SQLite as default.

    Args:
        app: Optional Flask app instance. If not provided, uses current_app

    Returns:
        str: The database URI
    """
    # 1. Check for DATABASE_URL in environment (highest priority)
    if "DATABASE_URL" in os.environ:
        return os.environ["DATABASE_URL"]

    # 2. Check for TESTING flag
    if app is None and not current_app:
        logger.warning("No app context available, using in-memory SQLite database")
        return "sqlite:///:memory:"

    # Get app instance if not provided
    app = app or current_app._get_current_object()  # type: ignore

    if app.config.get("TESTING", False):
        return "sqlite:///:memory:"

    # 3. Use configured SQLALCHEMY_DATABASE_URI if set
    if app.config.get("SQLALCHEMY_DATABASE_URI"):
        return app.config["SQLALCHEMY_DATABASE_URI"]

    # 4. Default to SQLite in the instance directory
    try:
        db_path = _get_database_path()
        db_dir = os.path.dirname(db_path)

        # Create directory if it doesn't exist
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, mode=0o755, exist_ok=True)

        # Ensure the database file exists
        if not os.path.exists(db_path):
            with open(db_path, "w", encoding="utf-8"):
                os.chmod(db_path, 0o600)
            logger.info("Initialized SQLite database at %s", db_path)

        return f"sqlite:///{os.path.abspath(db_path)}"

    except Exception as e:
        logger.error("Failed to initialize database: %s", e)
        logger.warning("Falling back to in-memory SQLite database")
        return "sqlite:///:memory:"


def init_database(app: "Flask") -> None:
    """Initialize the database with the Flask app.

    Args:
        app: The Flask application instance to initialize with the database

    Raises:
        RuntimeError: If there's an error initializing the database
    """
    global engine

    try:
        # Configure SQLAlchemy
        app.config.setdefault("SQLALCHEMY_DATABASE_URI", get_database_uri(app))
        app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)

        # Initialize the database with the app
        db.init_app(app)

        # Create the engine
        engine = db.engine

        # Configure the session factory
        db_session_factory.configure(bind=engine)

        # Create tables only if not running a db command
        if "db" not in sys.argv:
            with app.app_context():
                # Import models to ensure they are registered with SQLAlchemy
                from .auth import models as auth_models  # noqa: F401
                from .expenses import models as expense_models  # noqa: F401
                from .restaurants import models as restaurant_models  # noqa: F401

                # Tables will be created by Flask-Migrate
                # db.create_all()
                logger.info("Database tables managed by Flask-Migrate.")

    except Exception as e:
        logger.error("Failed to initialize database: %s", e)
        raise RuntimeError(f"Failed to initialize database: {e}") from e


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

    Returns:
        ScopedSession: A scoped SQLAlchemy session

    Raises:
        RuntimeError: If the database session factory is not initialized
    """
    if db_session_factory is None:
        raise RuntimeError("Database session factory not initialized. Call init_database() first.")
    return db_session_factory


def get_engine() -> Engine:
    """Get the SQLAlchemy engine.

    Returns:
        Engine: The SQLAlchemy engine instance

    Raises:
        RuntimeError: If the engine is not initialized
    """
    if engine is None:
        raise RuntimeError("Database engine not initialized. Call init_database() first.")
    return engine
