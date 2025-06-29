"""
Application factory for the Meal Expense Tracker Flask application.

This module contains the application factory function that creates and configures
the Flask application instance for both WSGI and AWS Lambda environments.
"""

import json
import logging
import os
import traceback
from typing import Optional, TypedDict

import boto3
from botocore.exceptions import ClientError
from flask import current_app, Flask
from flask_cors import CORS
from flask_wtf.csrf import generate_csrf
from sqlalchemy.pool import StaticPool

from config import config

from .extensions import db, login_manager, migrate

try:
    from importlib.metadata import version as get_package_version

    __version__ = get_package_version("meal-expense-tracker")
except ImportError:
    # Fallback for development/editable installs
    try:
        from setuptools_scm import get_version

        __version__ = get_version(fallback_version="0.0.0.dev0")
    except ImportError:
        __version__ = "0.0.0.dev0"

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
    logger = logging.getLogger(__name__)

    # Define required environment variables
    required_vars = ["DB_USERNAME", "DB_PASSWORD", "DB_HOST", "DB_NAME"]
    optional_vars = {"DB_PORT": "5432"}  # var_name: default_value

    # Check for missing required variables
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        logger.debug(f"Missing required environment variables: {', '.join(missing_vars)}")
        return None

    # Get all required variables
    creds: DBCredentials = {
        "username": os.environ["DB_USERNAME"],  # Required, already checked above
        "password": os.environ["DB_PASSWORD"],  # Required, already checked above
        "host": os.environ["DB_HOST"],  # Required, already checked above
        "port": os.environ.get("DB_PORT", optional_vars["DB_PORT"]),
        "dbname": os.environ["DB_NAME"],  # Required, already checked above
    }

    # Log that we found all required environment variables
    logger.debug("Found all required database credentials in environment variables")

    # Log a safe version of the credentials (without password)
    safe_creds = creds.copy()
    safe_creds["password"] = "*" * 8
    logger.debug(f"Database credentials from environment: {safe_creds}")
    return creds if all(creds.values()) else None


def _get_secrets_manager_client(region: str = "us-east-1"):
    """Create and return a Secrets Manager client.

    Args:
        region: AWS region to use for the client

    Returns:
        boto3 client for AWS Secrets Manager
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Initializing Secrets Manager client in region: {region}")
    session = boto3.Session(region_name=region)
    client = session.client("secretsmanager")
    logger.info("Created Secrets Manager client")
    return client


def _describe_secret(client, secret_arn: str) -> bool:
    """Describe a secret to check permissions.

    Args:
        client: Secrets Manager client
        secret_arn: ARN of the secret to describe

    Returns:
        bool: True if the secret can be described, False otherwise
    """
    logger = logging.getLogger(__name__)
    try:
        logger.info(f"Describing secret: {secret_arn}")
        client.describe_secret(SecretId=secret_arn)
        logger.info("Successfully described secret")
        return True
    except Exception as e:
        logger.error(f"Failed to describe secret: {str(e)}")
        return False


def _extract_credentials_from_secret(secret: dict) -> Optional[DBCredentials]:
    """Extract and validate credentials from secret data.

    Args:
        secret: Dictionary containing secret data

    Returns:
        DBCredentials if valid, None otherwise
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Secret keys: {list(secret.keys())}")

    # Map the secret fields to the expected credential keys
    secret_creds: DBCredentials = {
        "username": secret.get("db_username"),
        "password": secret.get("db_password"),
        "host": secret.get("db_host"),
        "port": str(secret.get("db_port", "5432")),
        "dbname": secret.get("db_name"),
    }

    # Log the values (without passwords)
    logger.info(f"Mapped credentials - username: {secret_creds['username']}")
    logger.info(f"Mapped credentials - host: {secret_creds['host']}")
    logger.info(f"Mapped credentials - port: {secret_creds['port']}")
    logger.info(f"Mapped credentials - dbname: {secret_creds['dbname']}")
    logger.info(f"Mapped credentials - password: {'*' * 8 if secret_creds['password'] else 'None'}")

    # Check if all required fields are present
    if not all(secret_creds.values()):
        missing = [k for k, v in secret_creds.items() if not v]
        error_msg = f"Missing required database credentials in secret: {', '.join(missing)}"
        logger.error(error_msg)
        logger.error(f"Available secret keys: {list(secret.keys())}")
        return None

    return secret_creds


def _get_credentials_from_secrets_manager() -> Optional[DBCredentials]:
    """Retrieve database credentials from AWS Secrets Manager.

    Returns:
        Optional[DBCredentials]: Dictionary of credentials if successful,
        None otherwise.
    """
    logger = logging.getLogger(__name__)
    secret_arn = os.environ.get("DB_SECRET_ARN")
    region = os.environ.get("AWS_REGION", "us-east-1")

    if not secret_arn:
        logger.error("DB_SECRET_ARN environment variable not set")
        return None

    try:
        # Initialize client and verify access
        client = _get_secrets_manager_client(region)
        if not _describe_secret(client, secret_arn):
            return None

        # Get and parse the secret
        logger.info("Getting secret value...")
        response = client.get_secret_value(SecretId=secret_arn)

        if "SecretString" not in response:
            logger.error("No SecretString in response")
            return None

        logger.info("Parsing secret JSON...")
        secret = json.loads(response["SecretString"])

        # Extract and validate credentials
        return _extract_credentials_from_secret(secret)

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = f"AWS ClientError ({error_code}) retrieving secret: {str(e)}"
        logger.error(error_msg)
        if "Error" in e.response:
            logger.error(f"Error details: {e.response['Error']}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing secret JSON: {e}")
        if "response" in locals():
            logger.error(f"Raw secret value: {response.get('SecretString', 'No SecretString')}")
        return None
    except Exception as e:
        error_type = type(e).__name__
        logger.error(f"Unexpected error getting database credentials ({error_type}): {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None


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
    logger.info("Attempting to retrieve database credentials...")

    # Track where we're getting credentials from for logging
    cred_source = None
    creds = None

    # 1. Try environment variables first
    try:
        logger.info("Checking for credentials in environment variables...")
        if creds := _get_credentials_from_env():
            cred_source = "environment variables"
            logger.info("Found valid database credentials in environment variables")
    except Exception as e:
        logger.warning("Error getting credentials from environment variables: %s", str(e))

    # 2. Fall back to AWS Secrets Manager if needed
    if not creds and os.environ.get("DB_SECRET_ARN"):
        try:
            logger.info("Attempting to get credentials from AWS Secrets Manager...")
            if new_creds := _get_credentials_from_secrets_manager():
                creds = new_creds
                cred_source = "AWS Secrets Manager"
                logger.info("Successfully retrieved database credentials from AWS Secrets Manager")
        except Exception as e:
            logger.error("Failed to get credentials from AWS Secrets Manager: %s", str(e), exc_info=True)

    # If we have credentials, log and return them
    if creds and cred_source:
        # Log a safe version of the credentials (without password)
        safe_creds = creds.copy()
        if "password" in safe_creds:
            safe_creds["password"] = "********"
        logger.info("Retrieved database credentials from %s: %s", cred_source, safe_creds)
        return creds

    # No credentials found
    error_msg = (
        "Could not find valid database credentials. "
        "Please ensure one of the following is set up correctly:\n"
        "1. Required environment variables: DB_USERNAME, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME\n"
        "2. A valid DB_SECRET_ARN pointing to an AWS Secrets Manager secret with the required fields"
    )
    logger.error(error_msg)
    raise RuntimeError(error_msg)


def _log_environment_vars():
    """Log relevant environment variables for debugging."""
    logger = logging.getLogger(__name__)
    logger.info("Checking environment variables...")
    env_vars = [
        "FLASK_ENV",
        "ENVIRONMENT",
        "DB_SECRET_ARN",
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USERNAME",
        "DB_PASSWORD",
        "AWS_DEFAULT_REGION",
        "AWS_REGION",
        "AWS_LAMBDA_FUNCTION_NAME",
        "LAMBDA_TASK_ROOT",
    ]

    for var in env_vars:
        if var in os.environ:
            if any(s in var for s in ["PASSWORD", "SECRET", "KEY"]):
                logger.info(f"{var}: {'*' * 8}")
            else:
                logger.info(f"{var}: {os.environ[var]}")
        else:
            logger.info(f"{var}: Not set")


def _get_database_url_from_creds() -> Optional[str]:
    """Get database URL from credentials."""
    logger = logging.getLogger(__name__)
    try:
        logger.info("Attempting to get database credentials...")
        creds = get_db_credentials()
        logger.info("Successfully retrieved database credentials")

        safe_url = (
            f"postgresql+psycopg2://{creds['username']}:{'*'*8}@" f"{creds['host']}:{creds['port']}/{creds['dbname']}"
        )
        logger.info(f"Constructed database URL: {safe_url}")

        return (
            f"postgresql+psycopg2://{creds['username']}:{creds['password']}@"
            f"{creds['host']}:{creds['port']}/{creds['dbname']}"
        )
    except Exception as e:
        logger.warning("Failed to get database credentials: %s", str(e), exc_info=True)
        return None


def _get_sqlite_url() -> str:
    """Get SQLite database URL for development.

    Returns:
        str: SQLite database URL

    Raises:
        RuntimeError: If SQLite database setup fails
    """
    logger = logging.getLogger(__name__)
    logger.warning("No production database configuration found, falling back to SQLite for development")
    try:
        db_dir = os.path.join(os.path.dirname(__file__), "instance")
        os.makedirs(db_dir, exist_ok=True)
        db_file = os.path.join(db_dir, "meal_expenses.db")
        sqlite_url = f"sqlite:///{db_file}?check_same_thread=False"
        logger.warning(f"Using SQLite database at: {sqlite_url}")
        return sqlite_url
    except Exception as e:
        error_msg = f"Failed to set up SQLite database: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise RuntimeError(error_msg) from e


def _handle_production_error() -> None:
    """Handle production environment error when database configuration is missing."""
    error_msg = (
        "Database configuration is required in production. "
        "Please set DATABASE_URL or configure database credentials. "
        f"Environment: {os.environ.get('FLASK_ENV', 'not set')}"
    )
    logger = logging.getLogger(__name__)
    logger.error(error_msg)
    if "current_app" in globals() and hasattr(current_app, "logger"):
        current_app.logger.error(error_msg)
    raise RuntimeError(error_msg)


def _is_production_environment() -> bool:
    """Check if the application is running in production environment."""
    return os.environ.get("FLASK_ENV") == "production" or os.environ.get("ENVIRONMENT") == "production"


def _log_environment_info() -> None:
    """Log information about the current environment."""
    logger = logging.getLogger(__name__)
    logger.info(f"Environment: {'production' if _is_production_environment() else 'development'}")
    logger.info(f"AWS Lambda: {'LAMBDA_TASK_ROOT' in os.environ}")
    logger.info(f"Current working directory: {os.getcwd()}")
    _log_environment_vars()


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
    logger = logging.getLogger(__name__)
    logger.info("Constructing database URL...")
    _log_environment_info()

    # 1. Check for explicit DATABASE_URL first
    if db_url := os.getenv("DATABASE_URL"):
        logger.info("Using DATABASE_URL from environment")
        return _ensure_proper_db_url(db_url)

    # 2. Try to get credentials from environment or Secrets Manager
    if db_url := _get_database_url_from_creds():
        return db_url

    # 3. Fall back to SQLite for development only
    if not _is_production_environment():
        return _get_sqlite_url()

    # 4. Handle production error case
    _handle_production_error()


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

    # Start with default engine options
    engine_options = {}

    # Only apply connection pooling for non-SQLite databases
    if not db_uri.startswith("sqlite"):
        # Get base engine options from app.config (set by config.py)
        engine_options = app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {})

    # Apply SQLite specific configuration if using SQLite
    if db_uri.startswith("sqlite"):
        engine_options.update(
            {
                "connect_args": {"check_same_thread": False},
                "poolclass": StaticPool,
            }
        )
        _configure_sqlite(app)  # This function also sets PRAGMA foreign_keys=ON

    # Set the final engine options in the app config
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
    # Load environment variables from .env file if it exists
    from pathlib import Path

    from dotenv import load_dotenv

    # Look for .env file in the root directory
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
        print(f"Loaded environment variables from {env_path}")

    if config_obj is None:
        # Load configuration from environment variable or use default
        config_name = os.getenv("FLASK_ENV", "development")
        config_obj = config[config_name]

    if isinstance(config_obj, str):
        config_obj = config[config_obj]

    app.config.from_object(config_obj)

    # Load environment variables into app config
    app.config.update(
        GOOGLE_PLACES_API_KEY=os.getenv("GOOGLE_PLACES_API_KEY"),
        GOOGLE_MAPS_API_KEY=os.getenv("GOOGLE_MAPS_API_KEY"),
        SECRET_KEY=os.getenv("SECRET_KEY", "dev"),
    )

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

    # Import models to ensure they are registered with SQLAlchemy
    from app.auth import models as auth_models  # noqa: F401
    from app.expenses import init_default_categories  # noqa: F401
    from app.expenses import models as expense_models  # noqa: F401
    from app.expenses.models import Category  # noqa: F401
    from app.restaurants import models as restaurant_models  # noqa: F401

    # Create database tables
    with app.app_context():
        db.create_all()

    # Initialize and configure login manager
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    # Initialize login manager for authentication
    from app.auth.models import init_login_manager

    init_login_manager(login_manager)

    # Ensure login manager is registered in app.extensions
    if "login_manager" not in app.extensions:
        app.extensions["login_manager"] = login_manager

    # Register template filters
    from . import template_filters

    template_filters.init_app(app)
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

    # CSRF token context processor
    @app.context_processor
    def inject_template_vars():
        return {"config": app.config, "csrf_token": generate_csrf}  # Return the function, don't call it

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
    """Register all blueprints with the application.

    Args:
        app: The Flask application instance
    """
    from .api import bp as api_bp
    from .auth import bp as auth_bp
    from .expenses import bp as expenses_bp
    from .health import bp as health_bp
    from .main import bp as main_bp
    from .reports import bp as reports_bp
    from .restaurants import bp as restaurants_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(expenses_bp, url_prefix="/expenses")
    app.register_blueprint(restaurants_bp, url_prefix="/restaurants")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(api_bp, url_prefix="/api/v1")
    app.register_blueprint(health_bp, url_prefix="/health")

    # Only register blueprints that haven't been registered by their init_app
    blueprints_to_register = []

    for bp, url_prefix in blueprints_to_register:
        if bp.name not in app.blueprints:
            app.register_blueprint(bp, url_prefix=url_prefix)
            app.logger.info(f"Registered blueprint: {bp.name} at {url_prefix}")
        else:
            app.logger.debug(f"Blueprint {bp.name} already registered")


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
