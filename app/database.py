"""Database configuration and utilities for the Meal Expense Tracker.

This module provides a centralized way to manage database connections,
initialization, and utilities for the application.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Optional

from flask import Flask, current_app
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy.orm import scoped_session, sessionmaker

from .extensions import db

# Configure logger
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from flask.typing import ResponseValue
    from typing_extensions import TypeAlias
    from werkzeug.wrappers import Response as WerkzeugResponse

# Type alias for scoped session
ScopedSession = scoped_session

if TYPE_CHECKING:
    FlaskResponse: TypeAlias = ResponseValue | WerkzeugResponse

__all__ = [
    "db",
    "init_database",
    "create_tables",
    "drop_tables",
    "get_session",
    "get_engine",
]

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


def _is_lambda_environment() -> bool:
    """Check if running in AWS Lambda environment."""
    return os.environ.get("AWS_EXECUTION_ENV", "").startswith("AWS_Lambda_") or bool(
        os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
    )


def _get_database_uri(app: Optional[Flask] = None) -> str:
    """Get the database URI with proper fallback logic.

    Priority order:
    1. DATABASE_URL environment variable (with postgres:// to postgresql:// conversion)
    2. SQLALCHEMY_DATABASE_URI from app config
    3. SQLite database file in instance directory (development only)
    4. In-memory SQLite as last resort
    """
    # First, try environment variable
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return db_url

    # In Lambda, require DATABASE_URL
    if _is_lambda_environment():
        raise RuntimeError("DATABASE_URL environment variable must be set in Lambda environment")

    # Try app config
    try:
        app_to_use = app or current_app._get_current_object()
        if "SQLALCHEMY_DATABASE_URI" in app_to_use.config:
            return str(app_to_use.config["SQLALCHEMY_DATABASE_URI"])
    except RuntimeError:
        pass

    # Fall back to SQLite in development
    instance_path = os.path.join(os.path.dirname(__file__), "..", "instance")
    os.makedirs(instance_path, exist_ok=True)
    db_path = os.path.join(instance_path, "meal_expense_tracker.db")

    if os.path.exists(os.path.dirname(db_path)):
        return f"sqlite:///{db_path}?check_same_thread=False&timeout=30"

    # Last resort: in-memory database
    logger.warning("No database path available, using in-memory SQLite database")
    return "sqlite:///:memory:"


def init_database(app: Flask) -> None:
    """Initialize the database with the Flask app.

    This function configures SQLAlchemy with the appropriate database URI,
    sets up connection pooling for production, and ensures proper connection handling.
    """
    # Only initialize if not already done
    if "sqlalchemy" in app.extensions:
        return

    try:
        # Get and set the database URI
        db_uri = _get_database_uri(app)
        app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

        # Configure connection pooling for production databases
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

        logger.info(f"Database initialized successfully with URI: {db_uri}")

    except Exception as e:
        logger.error("Failed to initialize database: %s", e)
        raise RuntimeError(f"Failed to initialize database: {e}") from e


def create_tables() -> None:
    """Create all database tables if they don't exist."""
    with current_app.app_context():
        db.create_all()


def drop_tables() -> None:
    """Drop all database tables."""
    with current_app.app_context():
        db.drop_all()


def get_session() -> scoped_session:
    """Get a scoped database session."""
    if not hasattr(db, "session") or not db.session:
        raise RuntimeError("Database session factory not initialized. Make sure to call init_database() first.")
    return db.session


def get_engine() -> Engine:
    """Get the SQLAlchemy engine."""
    if not hasattr(db, "engine") or not db.engine:
        raise RuntimeError("Database engine not initialized. Make sure to call init_database() first.")
    return db.engine
