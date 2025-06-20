"""WSGI entry point for the Meal Expense Tracker application.

This module serves as the entry point for both local development and
AWS Lambda deployment.
For AWS Lambda, this module provides the handler function that AWS Lambda invokes.
For local development, it can be run directly with `python wsgi.py`.
"""

import logging
import os
import sys

# Add the current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import app components after path configuration
from app import create_app, db, setup_logger  # noqa: E402
from flask import jsonify  # noqa: E402

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
        try:
            # Initialize database and verify connection
            _initialize_database(app)

            # Verify database connection using SQLAlchemy text() for raw SQL
            from sqlalchemy import text

            db.session.execute(text("SELECT 1"))
            logger.info("Successfully connected to the database")

        except Exception as e:
            logger.critical("Database error: %s", str(e), exc_info=True)
            # Re-raise to fail fast in production
            if os.environ.get("FLASK_ENV") == "production":
                raise

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
        app = _create_app_with_env(env)
        _setup_app_context(app)
        try:
            db.session.execute("SELECT 1")
            logger.info("Successfully connected to the database")
        except Exception as e:
            logger.critical(f"Database error: {str(e)}", exc_info=True)
            # Re-raise to fail fast in production
            if os.environ.get("FLASK_ENV") == "production":
                raise
        except ImportError as e:
            logger.critical(f"Failed to import models: {str(e)}", exc_info=True)
            # List contents of app directory for debugging
            try:
                import os

                app_dir = os.path.join(os.path.dirname(__file__), "app")
                if os.path.exists(app_dir):
                    logger.info(f"Contents of app directory: {os.listdir(app_dir)}")
                else:
                    logger.error(f"App directory not found at: {app_dir}")
            except Exception as debug_e:
                logger.error(f"Error listing app directory: {str(debug_e)}")
                raise

        return app

    except Exception as e:
        logger.critical(f"Failed to initialize application: {str(e)}", exc_info=True)
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


def check_database_migrations(app):
    """Check and apply database migrations if needed."""
    if not app.config.get("SQLALCHEMY_DATABASE_URI", "").startswith("postgresql"):
        return

    from sqlalchemy import inspect

    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    table_list = ", ".join(tables) if tables else "None"
    app.logger.info(f"Database contains tables: {table_list}")

    migration_dir = os.path.join(os.path.dirname(__file__), "migrations")
    if os.path.exists(migration_dir):
        try:
            from flask_migrate import upgrade as migration_upgrade

            migration_upgrade()
            app.logger.info("Database migrations applied successfully")
        except Exception as e:
            app.logger.error(f"Error applying database migrations: {str(e)}")
            # Re-raise the exception to fail fast in production
            if os.environ.get("FLASK_ENV") == "production":
                raise
            app.logger.error(f"Error applying database migrations: {str(e)}")
            # Re-raise the exception to fail fast if migrations are required
            raise
            app.logger.warning(f"Could not apply migrations: {str(e)}")


def _initialize_database(app):
    """Initialize the database and verify connection.

    Args:
        app: Flask application instance

    Raises:
        RuntimeError: If database initialization fails
    """
    with app.app_context():
        try:
            # Verify database connection
            app.logger.info("Verifying database connection...")
            db.session.execute(db.text("SELECT 1"))

            # Create tables if they don't exist
            app.logger.info("Creating database tables if they don't exist...")
            db.create_all()

            # Check for pending migrations
            check_database_migrations(app)

            app.logger.info("Database initialization completed successfully")
            return True

        except Exception as e:
            app.logger.error(
                "Database initialization failed: %s", str(e), exc_info=True
            )
            raise RuntimeError(f"Failed to initialize database: {str(e)}") from e


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
