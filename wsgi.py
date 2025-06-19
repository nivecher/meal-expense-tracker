"""WSGI entry point for the Meal Expense Tracker application.

This module serves as the entry point for both local development
and AWS Lambda deployment.
"""

import os
import sys
import logging
from flask import jsonify
from app import create_app, db


def setup_logger():
    """Set up the root logger with basic configuration."""
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Clear existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Configure basic logging
    logging.basicConfig(
        level=log_level, format=log_format, handlers=[logging.StreamHandler(sys.stdout)]
    )

    return logging.Formatter(log_format)


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


def create_application():
    """Create and configure the Flask application."""
    app = create_app()

    # Configure application components
    configure_application_logging(app)
    register_error_handlers(app)
    register_routes(app)

    # Initialize database
    with app.app_context():
        try:
            db.create_all()  # Create tables if they don't exist
            app.logger.info("Database tables verified/created")
            check_database_migrations(app)
        except Exception as e:
            app.logger.error(f"Error initializing database: {str(e)}")
            raise

    return app


# Create the application
app = create_application()
application = app  # For WSGI servers


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
    """Run the application locally."""
    try:
        port = int(os.environ.get("PORT", 5000))
        host = os.environ.get("HOST", "0.0.0.0")

        app.logger.info(f"Starting Meal Expense Tracker on {host}:{port}")
        app.logger.info(f'Environment: {app.config["ENV"]}')
        app.logger.info(f"Debug mode: {app.debug}")

        app.run(host=host, port=port, debug=app.debug)
    except Exception as e:
        app.logger.error(f"Failed to start application: {str(e)}")
        sys.exit(1)


# For AWS Lambda
if os.environ.get("AWS_EXECUTION_ENV"):
    handler = lambda_handler

# For local development
if __name__ == "__main__":
    main()
