"""
Application factory for the Meal Expense Tracker Flask application.

This module contains the application factory function that creates and configures
the Flask application instance for both WSGI and AWS Lambda environments.
"""

import json
import logging
import os
from typing import Optional, TypedDict

import boto3
from botocore.exceptions import ClientError
from flask import Flask
from flask_cors import CORS
from sqlalchemy.pool import StaticPool

from config import config
from ._version import __version__
from .extensions import db, login_manager, migrate


# Version information dictionary used throughout the application
version = {"app": __version__, "api": "v1"}


class DBCredentials(TypedDict, total=False):
    """Type definition for database connection credentials."""

    username: str
    password: str
    host: str
    port: str
    dbname: str


def _get_credentials_from_env() -> Optional[DBCredentials]:
    """Extract database credentials from environment variables.

    Returns:
        Optional[DBCredentials]: Dictionary of credentials if all required
        environment variables are set, None otherwise.
    """
    creds: DBCredentials = {
        "username": os.environ.get("DB_USERNAME"),
        "password": os.environ.get("DB_PASSWORD"),
        "host": os.environ.get("DB_HOST"),
        "port": os.environ.get("DB_PORT", "5432"),
        "dbname": os.environ.get("DB_NAME"),
    }
    return creds if all(creds.values()) else None


def _get_credentials_from_secrets_manager() -> Optional[DBCredentials]:
    """Retrieve database credentials from AWS Secrets Manager.

    Returns:
        Optional[DBCredentials]: Dictionary of credentials if successful,
        None otherwise.

    Raises:
        RuntimeError: If there's an error retrieving or parsing the secret.
    """
    logger = logging.getLogger(__name__)
    if not (secret_arn := os.environ.get("DB_SECRET_ARN")):
        return None
    try:
        logger.info("Fetching database credentials from AWS Secrets Manager")
        client = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        response = client.get_secret_value(SecretId=secret_arn)
        secret = json.loads(response["SecretString"])

        # Map secret fields to our expected format
        secret_creds: DBCredentials = {
            "username": secret.get("username"),
            "password": secret.get("password"),
            "host": secret.get("hostname") or secret.get("host"),
            "port": str(secret.get("port", "5432")),
            "dbname": secret.get("dbname") or secret.get("database"),
        }

        # Verify we have all required fields
        if not all(secret_creds.values()):
            missing = [k for k, v in secret_creds.items() if not v]
            raise ValueError(f"Missing required fields in secret: {', '.join(missing)}")

        logger.info("Successfully retrieved database credentials from AWS Secrets Manager")
        return secret_creds

    except ClientError as e:
        error_msg = f"Failed to retrieve database credentials from " f"AWS Secrets Manager: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e
    except (json.JSONDecodeError, KeyError) as e:
        error_msg = f"Invalid secret format in AWS Secrets Manager: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e


def get_db_credentials() -> DBCredentials:
    """Get database credentials from available sources.

    Priority:
    1. Environment variables (DB_*)
    2. AWS Secrets Manager (if DB_SECRET_ARN is set)

    Returns:
        DBCredentials: Database connection credentials.

    Raises:
        RuntimeError: If no valid credentials can be found.
    """
    logger = logging.getLogger(__name__)
    # Try environment variables first
    if creds := _get_credentials_from_env():
        logger.info("Using database credentials from environment variables")
        return creds
    # Fall back to AWS Secrets Manager
    try:
        if creds := _get_credentials_from_secrets_manager():
            return creds
    except Exception as e:
        logger.warning("Failed to get credentials from AWS Secrets Manager: %s", str(e))

    # No credentials found
    error_msg = (
        "Could not find valid database credentials. "
        "Please set either DB_* environment variables or DB_SECRET_ARN "
        "pointing to a valid AWS Secrets Manager secret."
    )
    logger.error(error_msg)
    raise RuntimeError(error_msg)


def _get_database_url() -> str:
    """Construct a database URL from available configuration sources.

    Priority order:
    1. DATABASE_URL environment variable
    2. Credentials from get_db_credentials() (AWS Secrets Manager or env vars)
    3. SQLite fallback for development only

    Returns:
        str: A SQLAlchemy-compatible database URL.

    Raises:
        RuntimeError: If required configuration is missing in production.
    """
    app_logger = logging.getLogger(__name__)

    # 1. Check for explicit DATABASE_URL
    if db_url := os.getenv("DATABASE_URL"):
        return _ensure_proper_db_url(db_url)

    # 2. Try to get credentials from environment or Secrets Manager
    try:
        creds = get_db_credentials()
        return _ensure_proper_db_url(
            f"postgresql+psycopg2://{creds['username']}:{creds['password']}@"
            f"{creds['host']}:{creds['port']}/{creds['dbname']}"
        )
    except RuntimeError as e:
        # Only log the error if we're not in production
        if os.environ.get("FLASK_ENV") != "production":
            app_logger.warning("Could not get database credentials: %s", e)

    # 3. Fall back to SQLite for development
    if os.environ.get("FLASK_ENV") != "production":
        app_logger.warning("No database configuration found, using SQLite")
        db_dir = os.path.join(os.path.dirname(__file__), "instance")
        os.makedirs(db_dir, exist_ok=True)
        db_file = os.path.join(db_dir, "meal_expenses.db")
        return f"sqlite:///{db_file}?check_same_thread=False"

    raise RuntimeError(
        "Database configuration is required in production. "
        "Please set DATABASE_URL or configure database credentials."
    )


def _ensure_proper_db_url(db_url: str) -> str:
    """Ensure the database URL is properly formatted for SQLAlchemy 2.0.

    Args:
        db_url: The database URL to check/format

    Returns:
        str: A properly formatted database URL
    """
    # Handle SQLite URLs
    if db_url.startswith("sqlite"):
        # Ensure check_same_thread is set for SQLite
        if "?" not in db_url:
            db_url += "?check_same_thread=False"
        elif "check_same_thread=" not in db_url:
            db_url += "&check_same_thread=False"
        return db_url

    # Handle PostgreSQL URLs
    if db_url.startswith("postgres"):
        # Ensure we're using psycopg2 driver
        if "postgresql+psycopg2" not in db_url:
            db_url = db_url.replace("postgresql://", "postgresql+psycopg2://")
            db_url = db_url.replace("postgres://", "postgresql+psycopg2://")

    return db_url


def _configure_sqlalchemy(app):
    """Configure SQLAlchemy for the application.

    Args:
        app: Flask application instance
    """
    # Get database URI
    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")

    # Configure engine options based on database type
    if db_uri.startswith("sqlite"):
        # SQLite specific configuration
        engine_options = {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
            "future": True,  # Enable SQLAlchemy 2.0 behavior
        }
        _configure_sqlite(app)
    else:
        # PostgreSQL/other databases
        engine_options = {"pool_pre_ping": True, "pool_recycle": 300, "future": True}  # Enable SQLAlchemy 2.0 behavior

        # Add PostgreSQL specific options
        if db_uri.startswith("postgresql"):
            engine_options.update(
                {
                    "pool_size": 5,
                    "max_overflow": 10,
                    "pool_timeout": 30,
                }
            )

    # Set the engine options in the app config
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = engine_options

    # Initialize SQLAlchemy with the app
    db.init_app(app)

    # Initialize Flask-Migrate
    migrate.init_app(app, db)


def _configure_sqlite(app):
    """Configure SQLite specific settings.

    Args:
        app: Flask application instance
    """
    if "sqlite" in app.config.get("SQLALCHEMY_DATABASE_URI", ""):
        from sqlalchemy import event
        from sqlalchemy.engine import Engine

        # Enable foreign key constraints for SQLite
        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()


def _configure_session(app):
    """Configure session management for the application.

    Args:
        app: Flask application instance
    """
    if app.config.get("SESSION_TYPE") == "dynamodb":
        try:
            from flask_session import Session

            Session(app)
            app.logger.info("Configured DynamoDB for session storage")
        except ImportError:
            app.logger.warning("Flask-Session not installed. Using default session backend.")
    else:
        # Default session configuration for development
        app.config.update(
            SESSION_COOKIE_SECURE=app.config.get("SESSION_COOKIE_SECURE", False),
            SESSION_COOKIE_HTTPONLY=app.config.get("SESSION_COOKIE_HTTPONLY", True),
            SESSION_COOKIE_SAMESITE=app.config.get("SESSION_COOKIE_SAMESITE", "Lax"),
            PERMANENT_SESSION_LIFETIME=app.config.get("PERMANENT_SESSION_LIFETIME", 86400),  # 24 hours
        )
        app.logger.info("Using default session configuration")


def _setup_config(app, config_obj):
    """Set up application configuration.

    Args:
        app: Flask application instance
        config_obj: Configuration object or name

    Returns:
        The configuration object
    """
    if config_obj is None:
        # Load configuration from environment variable or use default
        config_name = os.getenv("FLASK_ENV", "development")
        config_obj = config[config_name]

    if isinstance(config_obj, str):
        config_obj = config[config_obj]

    app.config.from_object(config_obj)

    # Allow for environment variable overrides
    if "SQLALCHEMY_DATABASE_URI" not in app.config:
        app.config["SQLALCHEMY_DATABASE_URI"] = _get_database_url()

    return config_obj


def _setup_extensions(app):
    """Set up Flask extensions.

    Args:
        app: Flask application instance
    """
    # Configure SQLAlchemy for the app
    _configure_sqlalchemy(app)

    # Initialize and configure login manager
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    # Initialize login manager for authentication
    from app.auth.models import init_login_manager

    init_login_manager(login_manager)

    # Import models to ensure they are registered with SQLAlchemy
    from app.auth import models as auth_models  # noqa: F401
    from app.expenses import models as expense_models  # noqa: F401
    from app.expenses.category import Category  # noqa: F401
    from app.restaurants import models as restaurant_models  # noqa: F401
    from app.expenses import init_default_categories

    # Initialize default categories after the database is created
    with app.app_context():
        try:
            init_default_categories()
        except Exception as e:
            app.logger.error(f"Failed to initialize default categories: {e}")

    # Enable CORS for all routes
    CORS(app)


def create_app(config_obj=None):
    """Create and configure the Flask application.

    Args:
        config_obj: Configuration object or name of configuration to use.

    Returns:
        Flask: The configured Flask application.
    """
    # Create and configure the app
    app = Flask(__name__)

    # Set up configuration
    _setup_config(app, config_obj)
    # Configure logging
    _configure_logging(app)
    # Set up extensions
    _setup_extensions(app)
    # Register blueprints
    _register_blueprints(app)
    # Add shell context
    _add_shell_context(app)

    return app


def _add_shell_context(app):
    """Add shell context to the Flask application.

    Args:
        app: Flask application instance
    """

    @app.shell_context_processor
    def make_shell_context():
        """Make objects available in the Flask shell."""
        from sqlalchemy.orm import Session

        return {
            "db": db,
            "session": db.session,
            "Session": Session,
            "engine": db.engine,
        }


def _register_blueprints(app):
    """Register all blueprints with the application."""
    from app.auth import bp as auth_bp
    from app.expenses import bp as expenses_bp
    from app.main import bp as main_bp
    from app.restaurants import bp as restaurants_bp
    from app.health import bp as health_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(expenses_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(restaurants_bp)
    app.register_blueprint(health_bp)


def _configure_logging(app):
    """Configure application logging."""
    # Configure the root logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    # Set the logging level for the app logger
    app.logger.setLevel(logging.INFO)


def setup_logger(app=None):
    """Configure and return a formatter for the application logs.

    Args:
        app: Optional Flask application instance. If provided, configures logging
             based on the app's configuration.

    Returns:
        logging.Formatter: Configured formatter for log messages
    """
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    if app is not None:
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(app.config.get("LOG_LEVEL", logging.INFO))

        # Clear any existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Add console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # In production, also log to a file
        if app.config.get("ENV") == "production":
            file_handler = logging.FileHandler("app.log")
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

    return formatter
