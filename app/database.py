"""Database configuration and utilities for the Meal Expense Tracker.

This module provides a centralized way to manage database connections,
initialization, and utilities for the application.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Optional, cast

import boto3
from botocore.exceptions import ClientError
from flask import Flask, current_app
from sqlalchemy.engine import Engine
from sqlalchemy.orm import scoped_session

from .extensions import db

# Configure logger
logger = logging.getLogger(__name__)


def _get_database_uri_from_secrets_manager(secret_name: str) -> str:
    """Get database URI directly from AWS Secrets Manager.

    Args:
        secret_name: Name of the secret in Secrets Manager

    Returns:
        Database connection string
    """
    try:
        secrets_client = boto3.client("secretsmanager", region_name="us-east-1")

        # Get the secret
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret_string = str(response["SecretString"])

        logger.info(f"Successfully retrieved database URI from secret: {secret_name}")
        return secret_string

    except ClientError as e:
        logger.error(f"AWS Secrets Manager error: {e}")
        raise RuntimeError(f"Failed to retrieve secret '{secret_name}' from Secrets Manager: {e}")
    except Exception as e:
        logger.error(f"Unexpected error getting secret: {e}")
        raise RuntimeError(f"Failed to get secret: {e}")


if TYPE_CHECKING:
    from typing import TypeAlias

    from flask.typing import ResponseValue
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
engine: Engine | None = None

# Session factory will be created in init_database when engine is available


def _is_lambda_environment() -> bool:
    """Check if running in AWS Lambda environment."""
    return os.environ.get("AWS_EXECUTION_ENV", "").startswith("AWS_Lambda_") or bool(
        os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
    )


def _get_database_uri_from_env() -> str | None:
    """Get database URI from environment variable."""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        return None

    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+pg8000://", 1)
    elif db_url.startswith("postgresql://") and "+" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+pg8000://", 1)

    return db_url


def _get_database_uri_from_lambda(db_url: str) -> str:
    """Get database URI for Lambda environment with Secrets Manager."""
    if "placeholder" in db_url:
        # Get Supabase connection from Secrets Manager
        db_url = _get_database_uri_from_secrets_manager("meal-expense-tracker/dev/supabase-connection")
        logger.info("Successfully retrieved Supabase connection for Lambda")
        return db_url

    return db_url


def _get_database_uri_from_app_config(app: Flask | None = None) -> str | None:
    """Get database URI from app config."""
    try:
        app_to_use = app or current_app._get_current_object()
        if "SQLALCHEMY_DATABASE_URI" in app_to_use.config:
            return str(app_to_use.config["SQLALCHEMY_DATABASE_URI"])
    except RuntimeError:
        pass
    return None


def _get_database_uri_fallback() -> str:
    """Get fallback SQLite database URI."""
    instance_path = os.path.join(os.path.dirname(__file__), "..", "instance")
    os.makedirs(instance_path, exist_ok=True)
    db_path = os.path.join(instance_path, f"app-{os.getenv('FLASK_ENV', 'development')}.db")

    if os.path.exists(os.path.dirname(db_path)):
        return f"sqlite:///{db_path}?check_same_thread=False&timeout=30"

    logger.warning("No database path available, using in-memory SQLite database")
    return "sqlite:///:memory:"


def _handle_lambda_with_env_url(db_url: str) -> str:
    """Handle database URI in Lambda environment when DATABASE_URL exists."""
    try:
        db_url = _get_database_uri_from_lambda(db_url)
        return db_url
    except Exception as e:
        logger.error(f"Failed to get database URI from Secrets Manager: {e}")
        # Try Supabase secret as fallback
        try:
            db_url = _get_database_uri_from_secrets_manager("meal-expense-tracker/dev/supabase-connection")
            logger.info("Successfully retrieved Supabase connection from Secrets Manager")
            return db_url
        except Exception as supabase_error:
            logger.error(f"Also failed to get Supabase connection: {supabase_error}")
            raise RuntimeError(f"Failed to get database credentials from Secrets Manager: {e}")


def _get_lambda_database_uri() -> str:
    """Get database URI from Secrets Manager in Lambda environment."""
    # Get the secret name from environment variable
    secret_name = os.environ.get("DATABASE_SECRET_NAME", "meal-expense-tracker/dev/supabase-connection")

    try:
        db_url = _get_database_uri_from_secrets_manager(secret_name)
        logger.info(f"Successfully retrieved database connection from Secrets Manager: {secret_name}")
        return db_url
    except Exception as e:
        logger.error(f"Failed to get database connection from Secrets Manager: {e}")
        raise RuntimeError(
            f"DATABASE_URL must be set or secret '{secret_name}' must be available in Lambda environment"
        )


def _get_database_uri(app: Flask | None = None) -> str:
    """Get the database URI with proper fallback logic.

    Priority order:
    1. DATABASE_URL environment variable (with postgres:// to postgresql:// conversion)
    2. SQLALCHEMY_DATABASE_URI from app config
    3. SQLite database file in instance directory (development only)
    4. In-memory SQLite as last resort
    """
    # First, try environment variable
    db_url = _get_database_uri_from_env()
    if db_url:
        if _is_lambda_environment():
            return _handle_lambda_with_env_url(db_url)
        return db_url

    # In Lambda environment, try to get from Secrets Manager
    if _is_lambda_environment():
        return _get_lambda_database_uri()

    # Try app config
    db_url = _get_database_uri_from_app_config(app)
    if db_url:
        return db_url

    # Fall back to SQLite
    return _get_database_uri_fallback()


def init_database(app: Flask) -> None:
    """Initialize the database with the Flask app.

    This function configures SQLAlchemy with the appropriate database URI,
    sets up connection pooling for production, and ensures proper connection handling.
    """
    # Only initialize if not already done
    if "sqlalchemy" in app.extensions:
        return

    try:
        # In Lambda environment, resolve real database URI
        if _is_lambda_environment():
            logger.info("Lambda environment detected - resolving database URI from Secrets Manager")
            # Get the real database URI
            db_uri = _get_lambda_database_uri()
            app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
            app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
            app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
                "pool_pre_ping": True,
                "pool_recycle": 300,  # Recycle connections after 5 minutes
                "pool_size": 2,  # Reduced for Supabase free tier limits
                "max_overflow": 0,  # No overflow allowed on Supabase
            }
            # Initialize SQLAlchemy with the app
            db.init_app(app)
            logger.info("Database configured for Lambda with deferred initialization")
        else:
            # Non-Lambda environment - normal initialization
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


def _ensure_real_database_uri() -> None:
    """Ensure the database URI is resolved to real credentials in Lambda environment."""
    if not _is_lambda_environment():
        return

    # Check if we're still using placeholder credentials
    current_uri = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if "placeholder" in current_uri:
        logger.info("Resolving real database credentials from Secrets Manager...")
        try:
            # Get the real database URI from environment and Secrets Manager
            db_url = _get_database_uri_from_env()
            if db_url:
                real_uri = _get_database_uri_from_lambda(db_url)
                # Ensure the URI uses pg8000 driver
                if "postgresql://" in real_uri and "+" not in real_uri:
                    real_uri = real_uri.replace("postgresql://", "postgresql+pg8000://", 1)
                elif "postgres://" in real_uri:
                    real_uri = real_uri.replace("postgres://", "postgresql+pg8000://", 1)
                current_app.config["SQLALCHEMY_DATABASE_URI"] = real_uri
                logger.info("Successfully resolved real database credentials")
            else:
                logger.error("No DATABASE_URL environment variable found")
                raise RuntimeError("DATABASE_URL environment variable must be set in Lambda environment")
        except Exception as e:
            logger.error(f"Failed to resolve database credentials: {e}")
            raise RuntimeError(f"Failed to resolve database credentials: {e}")


def get_session() -> scoped_session:
    """Get a scoped database session."""
    if not hasattr(db, "session") or not db.session:
        raise RuntimeError("Database session factory not initialized. Make sure to call init_database() first.")

    # Ensure real database URI is resolved in Lambda environment
    _ensure_real_database_uri()

    return db.session


def get_engine() -> Engine:
    """Get the SQLAlchemy engine."""
    if not hasattr(db, "engine") or not db.engine:
        raise RuntimeError("Database engine not initialized. Make sure to call init_database() first.")
    # Type assertion: db.engine is Engine after the check above
    # Flask-SQLAlchemy's db.engine is not properly typed in stubs
    # Use explicit check instead of assert to avoid Bandit B101 warning
    if db.engine is None:
        raise RuntimeError("Database engine is None after initialization check")
    # Flask-SQLAlchemy's db.engine type is not properly exposed in stubs
    # Cast is needed for type safety; redundant cast warnings are disabled globally
    return cast(Engine, db.engine)
