"""
Application factory for the Meal Expense Tracker Flask application.

This module contains the application factory function that creates and configures
the Flask application instance for both WSGI and AWS Lambda environments.
"""

import json
import logging
import os

import boto3
import urllib
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from config import config

# Import extensions from extensions module
from .extensions import db, login_manager, migrate

# Version information
from typing import Optional, TypedDict

from ._version import __version__


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
        client = boto3.client(
            "secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-1")
        )
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

        logger.info(
            "Successfully retrieved database credentials from AWS Secrets Manager"
        )
        return secret_creds

    except ClientError as e:
        error_msg = (
            f"Failed to retrieve database credentials from "
            f"AWS Secrets Manager: {str(e)}"
        )
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


def get_database_url() -> str:
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
    logger = logging.getLogger(__name__)
    # 1. Check for explicit DATABASE_URL
    if db_url := os.environ.get("DATABASE_URL"):
        logger.info("Using database URL from DATABASE_URL environment variable")
        return db_url
    # 2. Try to construct URL from credentials
    try:
        creds = get_db_credentials()
        db_url = "postgresql://{username}:{password}@{host}:{port}/{dbname}".format(
            username=creds["username"],
            password=urllib.parse.quote_plus(creds["password"]),
            host=creds["host"],
            port=creds["port"],
            dbname=creds["dbname"],
        )
        logger.info("Constructed database URL from credentials")
        return db_url
    except Exception as e:
        # In production, fail fast if we can't construct a valid URL
        if os.environ.get("FLASK_ENV") == "production":
            raise RuntimeError(
                "Failed to construct database URL from credentials. " f"Error: {str(e)}"
            ) from e
    # 3. Fall back to SQLite for development
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "instance/meal_expenses.db"
    )
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    logger.warning("Falling back to SQLite database for development")
    return f"sqlite:///{db_path}"


def create_app(config_obj=None):
    """Create and configure the Flask application.

    Args:
        config_obj (str or object): Either a configuration name (str) or a
                                 configuration class/object. If None, uses
                                 FLASK_ENV environment variable or defaults to
                                 'development'.

    Returns:
        Flask: The configured Flask application instance
    """
    app = Flask(__name__)

    # Load environment variables
    load_dotenv()
    # Handle different types of configuration input
    if config_obj is None:
        # Default to FLASK_ENV or 'development'
        config_name = os.getenv("FLASK_ENV", "development")
        config_obj = config[config_name]

    # If config_obj is a string, treat it as a config name
    if isinstance(config_obj, str):
        config_obj = config[config_obj]

    # Load the configuration
    app.config.from_object(config_obj)

    # Initialize the configuration if it has an init_app method
    if hasattr(config_obj, "init_app"):
        config_obj.init_app(app)

    # Configure logging
    _configure_logging(app)

    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)

    # Initialize and configure login manager
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    # Configure session management based on environment
    if app.config.get("SESSION_TYPE") == "dynamodb":
        try:
            from flask_session import Session

            Session(app)
            app.logger.info("Configured DynamoDB for session storage")
        except ImportError:
            app.logger.warning(
                "Flask-Session not installed. Using default session backend."
            )
    else:
        # Default session configuration for development
        app.config.update(
            SESSION_COOKIE_SECURE=app.config.get("SESSION_COOKIE_SECURE", False),
            SESSION_COOKIE_HTTPONLY=app.config.get("SESSION_COOKIE_HTTPONLY", True),
            SESSION_COOKIE_SAMESITE=app.config.get("SESSION_COOKIE_SAMESITE", "Lax"),
            PERMANENT_SESSION_LIFETIME=app.config.get(
                "PERMANENT_SESSION_LIFETIME", 86400
            ),  # 24 hours
        )
        app.logger.info("Using default session configuration")

    # Initialize the user loader
    from app.auth.models import init_login_manager

    init_login_manager(login_manager)

    # Enable CORS for all routes
    CORS(app)

    # Register blueprints
    _register_blueprints(app)

    # Shell context for flask shell
    @app.shell_context_processor
    def make_shell_context():
        return {"db": db}

    return app


def _register_blueprints(app):
    """Register all blueprints with the application."""
    from app.auth import bp as auth_bp
    from app.expenses import bp as expenses_bp
    from app.restaurants import bp as restaurants_bp
    from app.main import bp as main_bp
    from app.health import bp as health_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(expenses_bp, url_prefix="/expenses")
    app.register_blueprint(restaurants_bp, url_prefix="/restaurants")
    app.register_blueprint(main_bp, url_prefix="/")
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
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

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
