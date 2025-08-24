"""AWS Lambda handler for Meal Expense Tracker API.

This module handles API Gateway v2.0 (HTTP API) events and routes them
to the Flask application. It also provides database migration capabilities.
"""

import json
import logging
import os
from typing import Any, Dict, Optional, TypedDict, Union, cast

import awsgi
from flask import Flask
from flask.wrappers import Response as FlaskResponse

from app import create_app

# Type definitions


class ApiGatewayResponse(TypedDict):
    statusCode: int
    body: str
    headers: Dict[str, str]
    isBase64Encoded: bool


class LambdaContext:
    function_name: str
    function_version: str
    invoked_function_arn: str
    memory_limit_in_mb: int
    aws_request_id: str
    log_group_name: str
    log_stream_name: str
    identity: Any
    client_context: Any


# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global variable to hold the Flask application instance
_APP_INSTANCE: Optional[Flask] = None


def get_or_create_app() -> Flask:
    """Get or create the Flask application instance with proper configuration.

    Implements the singleton pattern to ensure we only create one Flask app instance
    per Lambda container, which is important for performance.

    Returns:
        Flask: The configured Flask application instance
    """
    global _APP_INSTANCE

    if _APP_INSTANCE is None:
        try:
            _APP_INSTANCE = create_app()
            logger.info("Created new Flask application instance")
        except Exception as e:
            logger.exception("Failed to create Flask application")
            raise RuntimeError(f"Failed to initialize application: {str(e)}")

    return _APP_INSTANCE


def handle_migration(app: Flask) -> Dict[str, Any]:
    """Handle database migration operation.

    Args:
        app: Flask application instance

    Returns:
        Dict with operation results
    """
    from flask_migrate import upgrade

    try:
        with app.app_context():
            upgrade()
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Database migrations applied successfully"}),
                "headers": {"Content-Type": "application/json"},
            }
    except Exception as e:
        logger.exception("Database migration failed")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Database migration failed: {str(e)}"}),
            "headers": {"Content-Type": "application/json"},
        }


def handle_database_operation(operation: str, **kwargs: Any) -> ApiGatewayResponse:
    """Handle database operations like migrations.

    Args:
        operation: Operation to perform (currently only 'migrate' is supported)
        **kwargs: Additional operation-specific arguments

    Returns:
        Dict with operation results in API Gateway format
    """
    app = get_or_create_app()

    if operation == "migrate":
        result = handle_migration(app)
        # Ensure the response matches ApiGatewayResponse type
        return {
            "statusCode": result["statusCode"],
            "body": result["body"],
            "headers": result["headers"],
            "isBase64Encoded": False,
        }
    else:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": f"Unsupported operation: {operation}"}),
            "headers": {"Content-Type": "application/json"},
            "isBase64Encoded": False,
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle Lambda events from API Gateway v2.0 (HTTP API).

    Args:
        event: The Lambda event
        context: The Lambda context object (not used but required by Lambda)

    Returns:
        dict: Response in API Gateway v2.0 format
    """
    _ = context  # Mark as unused

    # Handle direct invocation for database operations
    if "operation" in event:
        operation = str(event["operation"])
        db_response = handle_database_operation(operation, **event)
        # Convert ApiGatewayResponse to Dict[str, Any] for return
        return {
            "statusCode": db_response["statusCode"],
            "body": db_response["body"],
            "headers": db_response["headers"],
            "isBase64Encoded": db_response["isBase64Encoded"],
        }

    # Handle HTTP API v2.0 events
    app = get_or_create_app()

    try:
        # Use awsgi for HTTP request handling
        response = awsgi.response(
            app, event, context, base64_content_types={"image/png", "image/jpg", "application/octet-stream"}
        )

        # Ensure CORS headers are set
        headers = response.get("headers", {})
        if not isinstance(headers, dict):
            headers = {}

        # Ensure all header keys are strings
        headers = {str(k): str(v) for k, v in headers.items()}

        # Add CORS headers
        headers.update(
            {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            }
        )

        # Ensure response has all required fields
        api_response: Dict[str, Any] = {
            "statusCode": response.get("statusCode", 500),
            "body": response.get("body", ""),
            "headers": headers,
            "isBase64Encoded": response.get("isBase64Encoded", False),
        }

        return api_response

    except Exception as e:
        logger.exception("Error handling request: %s", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"}),
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "isBase64Encoded": False,
        }
