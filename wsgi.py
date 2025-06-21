"""WSGI entry point for the Meal Expense Tracker application.

This module serves as the entry point for both local development and
AWS Lambda deployment. It handles application initialization,
database configuration, and request routing.
"""

import logging
import os
import sys

# Add the project directory to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import app components after path configuration
from flask import Flask, jsonify  # noqa: E402
from sqlalchemy import text  # noqa: E402
from app.extensions import db  # noqa: E402

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """Create and configure the Flask application.

    This function initializes the Flask application using the application factory
    pattern from the main application package. This ensures consistent
    initialization of all extensions and blueprints.

    Returns:
        Flask: The configured Flask application instance
    """
    from app import create_app as app_factory

    # Create the application using the application factory
    app = app_factory()

    # Add health check endpoint (if not already added by the app factory)
    if not hasattr(app, "health_check_added"):

        @app.route("/health")
        def health_check():
            """Health check endpoint for load balancers and monitoring."""
            try:
                db.session.execute(text("SELECT 1"))
                return jsonify({"status": "healthy"}), 200
            except Exception as e:
                logger.error("Health check failed: %s", e)
                return jsonify({"status": "unhealthy", "error": str(e)}), 500

        # Mark that we've added the health check
        app.health_check_added = True

    # Add error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({"error": "Internal server error"}), 500

    return app


# Create the application instance
# This is used by WSGI servers and local development
app = create_app()
application = app  # Standard WSGI interface


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
            logger.error("Failed to import awsgi: %s", str(e))
            return None


def lambda_handler(event, context):
    """AWS Lambda handler function.

    Handles both API Gateway events (REST and HTTP APIs) and direct Lambda invocations.
    """
    # Log the incoming event for debugging
    logger.info("Received Lambda event: %s", event)

    # Handle different event formats
    if not isinstance(event, dict):
        logger.error("Invalid event type: %s", type(event).__name__)
        return {
            "statusCode": 400,
            "body": "Bad Request: Invalid event format",
            "headers": {"Content-Type": "application/json"},
        }

    # Check if this is an HTTP API v2.0 event
    if event.get("version") == "2.0":
        event = {
            "httpMethod": event.get("requestContext", {})
            .get("http", {})
            .get("method", "GET"),
            "path": event.get("rawPath", "/"),
            "queryStringParameters": event.get("queryStringParameters", {}),
            "headers": event.get("headers", {}),
            "body": event.get("body", ""),
            "isBase64Encoded": event.get("isBase64Encoded", False),
        }
    # Check if this is a direct Lambda invocation without HTTP context
    elif "httpMethod" not in event and "requestContext" in event:
        # This might be a direct Lambda invocation or custom event
        logger.warning("Event missing httpMethod, assuming direct invocation")
        return {
            "statusCode": 200,
            "body": "Direct Lambda invocation successful",
            "headers": {"Content-Type": "application/json"},
        }
    # Check if this is a scheduled event or other AWS event
    elif "httpMethod" not in event and "source" in event:
        logger.info("Processing non-HTTP Lambda event: %s", event.get("source"))
        return {
            "statusCode": 200,
            "body": f"Processed {event.get('source')} event",
            "headers": {"Content-Type": "application/json"},
        }

    # Get AWSGI response handler
    handler = _get_awsgi_response()
    if not handler:
        logger.error("Failed to load AWSGI handler")
        return {
            "statusCode": 500,
            "body": "Internal Server Error: awsgi package not found",
            "headers": {"Content-Type": "application/json"},
        }

    try:
        # Handle the request using awsgi
        return handler(app, event, context, base64_content_types={"image/png"})
    except KeyError as e:
        logger.error("Missing required field in event: %s", str(e))
        return {
            "statusCode": 400,
            "body": f"Bad Request: Missing required field - {str(e)}",
            "headers": {"Content-Type": "application/json"},
        }
    except Exception as e:
        logger.error("Error processing request: %s", str(e), exc_info=True)
        return {
            "statusCode": 500,
            "body": "Internal Server Error: Failed to process request",
            "headers": {"Content-Type": "application/json"},
        }


def main():
    """Run the application locally.

    This is the entry point for local development using `python wsgi.py`
    """
    # Configure host and port from environment or use defaults
    host = os.environ.get("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_RUN_PORT", "5000"))

    # Set debug mode based on environment
    debug = os.environ.get("FLASK_ENV") == "development"

    # Log startup information
    logger.info("Starting local development server at http://%s:%s", host, port)
    logger.info("Debug mode: %s", "on" if debug else "off")

    # Run the application
    app.run(host=host, port=port, debug=debug, use_reloader=debug)


if __name__ == "__main__":
    # Run the application directly for local development
    main()
