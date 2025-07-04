"""Database configuration and utilities for the Meal Expense Tracker.

This module provides a centralized way to manage database connections,
initialization, and utilities for the application.
"""

import logging
import os
from typing import Optional

from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.engine import Engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Initialize logger
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy without binding to an app yet
db = SQLAlchemy()

# Create a thread-local session factory
Session = scoped_session(sessionmaker(autocommit=False, autoflush=False))


def _get_database_path() -> str:
    """Get the appropriate database path based on the environment."""
    # Use instance folder in the application directory by default
    instance_path = os.environ.get("INSTANCE_PATH")
    if instance_path:
        return os.path.join(instance_path, "meal_expenses.db")

    # Fall back to a local instance directory
    return os.path.join("instance", "meal_expenses.db")


def get_database_uri(app: Optional[Flask] = None) -> str:
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


def init_database(app: Flask) -> None:
    """Initialize the database with the Flask app.

    Args:
        app: The Flask application instance
    """
    # Configure SQLAlchemy
    db_uri = get_database_uri(app)
    logger.info("Initializing database with URI: %s", db_uri)

    app.config.update(
        SQLALCHEMY_DATABASE_URI=db_uri,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={
            "pool_pre_ping": True,
            "pool_recycle": 300,
        },
    )

    # Register teardown for the session first to ensure it's properly registered
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        Session.remove()
        logger.debug("Database session removed")

    # Initialize SQLAlchemy with the app
    db.init_app(app)

    # Configure the session factory to use the app's database
    with app.app_context():
        Session.configure(bind=db.engine)

        # Import models to ensure they are registered with SQLAlchemy
        from .auth import models as auth_models  # noqa: F401
        from .expenses import models as expense_models  # noqa: F401
        from .restaurants import models as restaurant_models  # noqa: F401

        # Create tables if they don't exist
        db.create_all()
        logger.info("Database tables created/verified")


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


def get_session() -> scoped_session:
    """Get a scoped database session.

    Returns:
        SQLAlchemy scoped session
    """
    return Session


def get_engine() -> Engine:
    """Get the SQLAlchemy engine.

    Returns:
        SQLAlchemy engine
    """
    return db.engine
