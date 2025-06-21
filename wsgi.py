"""WSGI entry point for the Meal Expense Tracker application.

This module serves as the entry point for both local development and
AWS Lambda deployment.
For AWS Lambda, this module provides the handler function that AWS Lambda invokes.
For local development, it can be run directly with `python wsgi.py`.
"""

import logging
import os
import sys
import time
import site
from pathlib import Path

# Ensure the app directory is in the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.join(current_dir, "app")

# Add the current directory and app directory to Python path
for path in [current_dir, app_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Import app components after path configuration
from app import create_app, db, setup_logger  # noqa: E402
from flask import jsonify  # noqa: E402
from sqlalchemy import text

# Configure logging after imports to ensure all loggers are properly configured
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    force=True,  # Override any existing handlers
)
logger = logging.getLogger(__name__)


def _create_app_with_env(env):
    """Helper to create app with given environment."""
    return create_app(env)


def _setup_app_context(app):
    """Set up application context including logging and database."""
    with app.app_context():
        setup_logger(app)

        # Initialize database and verify connection
        _initialize_database(app)

        # Register routes and handlers
        register_routes(app)
        register_error_handlers(app)
        check_database_migrations(app)


def configure_application():
    """Create and configure the Flask application.

    This function is separated to ensure all configurations are properly set
    before the application starts handling requests.

    Returns:
        Flask: The configured Flask application instance
    """
    try:
        # Import os here to ensure it's in scope
        import os  # noqa: F811

        # Determine the environment
        env = os.environ.get("FLASK_ENV", "development")
        logger.info("Starting application in %s environment", env)

        # Log environment variables for debugging (excluding sensitive data)
        logger.debug(
            "Environment variables: %s",
            {
                k: v
                for k, v in os.environ.items()
                if not any(s in k.lower() for s in ["key", "secret", "pass", "token"])
            },
        )

        app = _create_app_with_env(env)
        _setup_app_context(app)
        return app

    except ImportError as e:
        logger.critical(f"Failed to import module: {str(e)}", exc_info=True)
        # List contents of app directory for debugging
        try:
            app_dir = os.path.join(os.path.dirname(__file__), "app")
            if os.path.exists(app_dir):
                logger.info(f"Contents of app directory: {os.listdir(app_dir)}")
            else:
                logger.error(f"App directory not found at: {app_dir}")
        except Exception as debug_e:
            logger.error(f"Error listing app directory: {str(debug_e)}")
        raise
    except Exception as e:
        logger.critical(f"Failed to configure application: {str(e)}", exc_info=True)
        raise


def configure_application_logging(app):
    """Configure application-specific logging settings."""
    formatter = setup_logger()
    logger = logging.getLogger()

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Add stderr handler in AWS environment
    if os.environ.get("AWS_EXECUTION_ENV"):
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setFormatter(formatter)
        logger.addHandler(stderr_handler)

    # Configure third-party loggers
    for logger_name in ["botocore", "urllib3", "sqlalchemy"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    app.logger.info("Logging configured")


def register_error_handlers(app):
    """Register error handlers for the Flask application."""

    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 errors."""
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500


def register_routes(app):
    """Register application routes."""

    @app.route("/")
    def root():
        """Root endpoint that returns a welcome message."""
        return (
            jsonify(
                {
                    "status": "healthy",
                    "message": "Meal Expense Tracker API",
                    "version": app.config.get("VERSION", "0.0.0"),
                }
            ),
            200,
        )


def _construct_db_url_from_secret():
    """Construct DB_URL from AWS Secrets Manager secret.

    Returns:
        str: The constructed database URL

    Raises:
        KeyError: If required keys are missing from the secret
        ValueError: If DB_SECRET_ARN is not set
    """
    import boto3
    import json
    import os
    import logging

    logger = logging.getLogger(__name__)

    secret_arn = os.environ.get("DB_SECRET_ARN")
    if not secret_arn:
        raise ValueError("DB_SECRET_ARN environment variable not set")

    try:
        logger.info(f"Retrieving secret from ARN: {secret_arn}")
        client = boto3.client("secretsmanager")
        response = client.get_secret_value(SecretId=secret_arn)
        secret = json.loads(response["SecretString"])

        # Log the available keys for debugging
        logger.info(f"Available secret keys: {list(secret.keys())}")

        # Try different key formats
        username = secret.get("db_username") or secret.get("username")
        password = secret.get("db_password") or secret.get("password")
        host = secret.get("host") or secret.get("db_host")
        port = secret.get("port") or secret.get(
            "db_port", "5432"
        )  # Default PostgreSQL port
        dbname = secret.get("dbname") or secret.get("db_name") or secret.get("database")

        # Validate all required fields are present
        if not all([username, password, host, dbname]):
            missing = []
            if not username:
                missing.append("username")
            if not password:
                missing.append("password")
            if not host:
                missing.append("host")
            if not dbname:
                missing.append("dbname")
            raise KeyError(f"Missing required fields in secret: {', '.join(missing)}")

        # Construct the database URL
        db_url = f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{dbname}"
        logger.info(f"Constructed database URL for host: {host}, database: {dbname}")
        return db_url

    except Exception as e:
        logger.error(f"Failed to construct DB_URL from secret: {str(e)}")
        logger.debug(
            f"Secret content (sensitive data redacted): { {k: '***' for k in secret.keys()} }"
        )
        raise


def check_database_migrations(app):
    """Check and apply database migrations if needed.

    This function will:
    1. Check if migrations are enabled via RUN_MIGRATIONS environment variable
    2. Construct DB_URL from secret if not already set
    3. Verify we're using PostgreSQL
    4. Check if the migrations table exists
    5. Apply any pending migrations
    """
    import traceback

    app.logger.info("=" * 80)
    app.logger.info("STARTING DATABASE MIGRATION CHECK")
    app.logger.info("=" * 80)

    # Only run migrations if explicitly enabled
    migrations_enabled = os.environ.get("RUN_MIGRATIONS", "false").lower() == "true"
    if not migrations_enabled:
        app.logger.info("Skipping database migrations (RUN_MIGRATIONS not enabled)")
        return

    app.logger.info("Database migrations are ENABLED via RUN_MIGRATIONS")
    app.logger.info(f"Current working directory: {os.getcwd()}")
    app.logger.info(f"Python path: {sys.path}")

    # Construct DB_URL from secret if not already set
    if "DB_URL" not in os.environ:
        try:
            app.logger.info("Constructing DB_URL from secret...")
            db_url = _construct_db_url_from_secret()
            os.environ["DB_URL"] = db_url
            app.logger.info("Successfully constructed DB_URL from secret")
        except Exception as e:
            error_msg = f"Failed to construct DB_URL from secret: {str(e)}\n{traceback.format_exc()}"
            app.logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    else:
        app.logger.info("Using existing DB_URL from environment")

    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    app.logger.info(f"Database URI from config: {db_uri}")

    if not db_uri.startswith("postgresql"):
        error_msg = (
            f"Skipping migrations - not using PostgreSQL (found: {db_uri[:20]}...)"
        )
        app.logger.error(error_msg)
        raise RuntimeError(error_msg)

    try:
        # Import here to avoid circular imports
        app.logger.info("Importing Flask-Migrate and extensions...")
        from app.extensions import db  # Changed from relative to absolute import
        from flask_migrate import Migrate
        from alembic import command
        from alembic.config import Config
        import alembic

        app.logger.info(
            f"Using Flask-Migrate version: {getattr(Migrate, '__version__', 'unknown')}"
        )
        app.logger.info(
            f"Using Alembic version: {getattr(alembic, '__version__', 'unknown')}"
        )

        # Initialize Flask-Migrate
        app.logger.info("Initializing Flask-Migrate...")
        migrate = Migrate()
        migrate.init_app(app, db)

        # Initialize SQLAlchemy if not already done
        app.logger.info("Initializing SQLAlchemy...")
        _initialize_sqlalchemy(app)

        # Get engine and inspector
        app.logger.info("Getting database engine and inspector...")
        engine = db.get_engine()
        inspector = db.inspect(engine)

        # Check if alembic_version table exists
        has_alembic_version = inspector.has_table("alembic_version")

        if not has_alembic_version:
            app.logger.warning(
                "ALEMBIC VERSION TABLE NOT FOUND - Fresh database or not yet initialized"
            )
            tables = inspector.get_table_names()
            app.logger.info(f"Current tables in database: {tables}")
            if not tables:
                app.logger.info("Database appears to be completely empty")
        else:
            app.logger.info(
                "Found existing alembic_version table - database has been migrated before"
            )

            # Get current revision from database
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                current_rev = result.scalar()
                app.logger.info(f"Current database revision: {current_rev}")

        # Run migrations with detailed logging
        app.logger.info("=" * 40)
        app.logger.info("STARTING DATABASE MIGRATIONS")
        app.logger.info("=" * 40)

        # Get absolute path to migrations directory
        migrations_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "migrations"
        )
        app.logger.info(f"Using migrations directory: {migrations_dir}")

        # Verify migrations directory exists and contains files
        if not os.path.exists(migrations_dir):
            error_msg = f"Migrations directory not found: {migrations_dir}"
            app.logger.error(error_msg)
            raise RuntimeError(error_msg)

        migration_files = os.listdir(migrations_dir)
        app.logger.info(f"Found {len(migration_files)} items in migrations directory")

        # Run the upgrade with more context
        with app.app_context():
            try:
                # Initialize Alembic config
                alembic_cfg = Config(os.path.join(migrations_dir, "alembic.ini"))
                alembic_cfg.set_main_option("script_location", migrations_dir)
                alembic_cfg.set_main_option("sqlalchemy.url", db_uri)

                # Log current revision before upgrade
                from flask_migrate import current as current_revision

                try:
                    rev = current_revision()
                    app.logger.info(
                        f"Current database revision (before upgrade): {rev}"
                    )
                except Exception as e:
                    app.logger.warning(
                        f"Could not determine current revision: {str(e)}"
                    )

                # Run the upgrade
                app.logger.info("Executing 'flask db upgrade'...")
                command.upgrade(alembic_cfg, "head")
                app.logger.info("Database migrations completed successfully")

                # Verify the upgrade
                try:
                    rev = current_revision()
                    app.logger.info(f"Database now at revision: {rev}")
                except Exception as e:
                    app.logger.warning(f"Could not verify final revision: {str(e)}")

                # Log final table list
                inspector = db.inspect(engine)
                tables = inspector.get_table_names()
                app.logger.info(f"Final tables in database ({len(tables)}): {tables}")

            except Exception as e:
                error_msg = (
                    f"Error during migration: {str(e)}\n{traceback.format_exc()}"
                )
                app.logger.error(error_msg)
                raise RuntimeError(f"Migration failed: {str(e)}") from e

    except Exception as e:
        error_msg = (
            f"FATAL ERROR during database migration: {str(e)}\n{traceback.format_exc()}"
        )
        app.logger.error(error_msg)
        # Reraise with additional context
        raise RuntimeError(f"Database migration failed: {str(e)}") from e

    app.logger.info("=" * 80)
    app.logger.info("DATABASE MIGRATION CHECK COMPLETED SUCCESSFULLY")
    app.logger.info("=" * 80)
    return True


def _verify_database_connection(app, db):
    """Verify database connection with retry logic.

    Args:
        app: Flask application instance
        db: SQLAlchemy database instance

    Returns:
        bool: True if connection is successful, False otherwise
    """
    max_retries = 3
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            app.logger.debug("Attempting to verify database connection...")
            result = db.session.execute(text("SELECT 1"))
            app.logger.debug(
                "Database connection test query result: %s", result.fetchone()
            )
            app.logger.info("Database connection verified")
            return True
        except Exception as e:
            last_error = e
            app.logger.error(
                "Database connection attempt %d failed: %s",
                attempt + 1,
                str(e),
                exc_info=app.config.get("FLASK_ENV") != "production",
            )
            if attempt < max_retries - 1:
                app.logger.warning(
                    "Retrying in %ds... (attempt %d/%d)",
                    retry_delay,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff

    error_msg = f"Failed to verify database connection after {max_retries} attempts: {str(last_error)}"
    if app.config.get("FLASK_ENV") == "production":
        app.logger.critical(error_msg, exc_info=True)
        raise RuntimeError(error_msg) from last_error

    app.logger.warning("%s - Continuing in non-production environment", error_msg)
    return False


def _initialize_sqlalchemy(app):
    """Initialize SQLAlchemy if not already done."""
    if "sqlalchemy" not in app.extensions:
        db.init_app(app)
        logger.debug("Initialized SQLAlchemy with Flask app")
    else:
        logger.debug("SQLAlchemy already initialized for this app")


def _create_tables_if_needed(app):
    """Create database tables in development or testing environments."""
    if app.config.get("FLASK_ENV") not in ["development", "testing"]:
        return

    try:
        logger.debug("Creating database tables...")
        db.create_all()
        logger.info("Database tables created/verified")
    except Exception as e:
        error_msg = f"Failed to create tables: {str(e)}"
        if app.config.get("FLASK_ENV") == "production":
            logger.critical(error_msg)
            raise RuntimeError(error_msg)
        logger.warning("%s - Continuing in non-production environment", error_msg)


def _initialize_database(app):
    """Initialize the database and verify connection.

    Args:
        app: Flask application instance

    Raises:
        RuntimeError: If database initialization fails in production
    """

    try:
        _initialize_sqlalchemy(app)

        # Import db here to avoid circular imports
        from app.extensions import db

        with app.app_context():
            _create_tables_if_needed(app)
            _verify_database_connection(app, db)
            logger.info("Database initialization completed successfully")
    except Exception as e:
        error_msg = f"Failed to initialize database: {str(e)}"
        logger.critical(error_msg, exc_info=True)
        if app.config.get("FLASK_ENV") == "production":
            raise RuntimeError(error_msg) from e
        logger.warning(
            "Continuing with potential database issues in non-production environment"
        )


def create_application(env=None):
    """Create and configure the Flask application.

    Args:
        env (str, optional): The environment to use (development, production, etc.)
                          If not provided, will use FLASK_ENV or default to development.

    Returns:
        Flask: The configured Flask application

    Raises:
        RuntimeError: If application initialization fails
    """
    try:
        # Create the Flask application with the specified environment
        app = create_app(env)

        # Register error handlers
        register_error_handlers(app)

        # Register routes
        register_routes(app)

        # Check and apply database migrations if needed
        check_database_migrations(app)

        # Initialize the database
        _initialize_database(app)

        logger.info("Application initialized successfully")
        return app

    except Exception as e:
        logger.critical("Failed to create application", exc_info=True)
        raise RuntimeError("Failed to initialize the application") from e


# Create the application instance
# This is used by WSGI servers and local development
app = configure_application()
application = app  # Standard WSGI interface


def _transform_http_api_event(event):
    """Transform HTTP API (v2.0) event to REST API format."""
    if "version" not in event or event.get("version") != "2.0" or "httpMethod" in event:
        return event

    request_context = event.get("requestContext", {})
    http_context = request_context.get("http", {})

    return {
        **event,
        "httpMethod": http_context.get("method", "GET"),
        "path": event.get("rawPath", "/"),
        "queryStringParameters": event.get("queryStringParameters", {}),
        "headers": event.get("headers", {}),
        "body": event.get("body", ""),
        "isBase64Encoded": event.get("isBase64Encoded", False),
    }


def _get_awsgi_response():
    """Get the AWSGI response handler, trying multiple import methods."""
    try:
        import awsgi

        return awsgi.response
    except ImportError:
        try:
            from awsgi import response as awsgi_response

            return awsgi_response
        except ImportError as e:
            app.logger.error(f"Failed to import awsgi: {str(e)}")
            return None


def lambda_handler(event, context):
    """AWS Lambda handler function.

    Handles both API Gateway events (REST and HTTP APIs) and direct Lambda invocations.
    """
    app.logger.debug("Received Lambda event")

    # Handle direct Lambda invocation (test event)
    if not event.get("httpMethod") and not event.get("requestContext"):
        app.logger.info("Direct Lambda invocation detected")
        return {
            "statusCode": 200,
            "body": (
                "Lambda function is working! Use API Gateway to access the application."
            ),
            "headers": {"Content-Type": "application/json"},
        }

    # Transform HTTP API v2.0 events to REST API format
    event = _transform_http_api_event(event)

    # Get AWSGI response handler
    awsgi_handler = _get_awsgi_response()
    if not awsgi_handler:
        return {
            "statusCode": 500,
            "body": "Internal Server Error: awsgi package not found",
            "headers": {"Content-Type": "application/json"},
        }

    try:
        return awsgi_handler(app, event, context, base64_content_types={"image/png"})
    except Exception as e:
        app.logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": "Internal Server Error",
            "headers": {"Content-Type": "application/json"},
        }


def main():
    """Run the application locally.

    This is the entry point for local development using `python wsgi.py`
    """
    try:
        port = int(os.environ.get("PORT", 5000))
        host = os.environ.get("HOST", "0.0.0.0")
        debug = os.environ.get("FLASK_ENV") == "development"

        logger.info(f"Starting development server on http://{host}:{port}")
        logger.info(f"Debug mode: {'on' if debug else 'off'}")

        app.run(host=host, port=port, debug=debug, use_reloader=debug)
    except Exception as e:
        app.logger.error(f"Failed to start application: {str(e)}")
        sys.exit(1)


# AWS Lambda Configuration
# This ensures the handler is available for Lambda invocations
if os.environ.get("AWS_EXECUTION_ENV"):
    # Configure Lambda-specific settings
    logger.info("Running in AWS Lambda environment")

    # Ensure all log messages are flushed
    for log_handler in logging.root.handlers:
        log_handler.flush()

    # Export handler for AWS Lambda compatibility
    # This allows the Lambda function to use `wsgi.handler` as the entry point
    handler = lambda_handler  # noqa: F401

# For local development
if __name__ == "__main__":
    # Only run the development server if this file is executed directly
    # and not imported as a module
    main()

# This file serves as both a module and an executable script:
# - As a module: Provides the 'app' and 'application' objects for WSGI servers
# - As a script: Runs the development server for local testing
