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

            # Validate session configuration for Lambda environment
            _validate_session_config(_APP_INSTANCE)

        except Exception as e:
            logger.exception("Failed to create Flask application")
            raise RuntimeError(f"Failed to initialize application: {str(e)}")

    return _APP_INSTANCE


def _convert_apigw_v2_to_v1(event: Dict[str, Any]) -> Dict[str, Any]:
    """Convert API Gateway v2.0 event format to v1.0 format for awsgi compatibility.

    Args:
        event: API Gateway v2.0 event

    Returns:
        API Gateway v1.0 compatible event
    """
    request_context = event.get("requestContext", {})
    http_context = request_context.get("http", {})

    # Convert v2.0 event to v1.0 format
    v1_event = {
        "httpMethod": http_context.get("method", "GET"),
        "path": event.get("rawPath", "/"),
        "pathParameters": event.get("pathParameters"),
        "queryStringParameters": event.get("queryStringParameters"),
        "headers": event.get("headers", {}),
        "body": event.get("body"),
        "isBase64Encoded": event.get("isBase64Encoded", False),
        "requestContext": {
            "requestId": request_context.get("requestId", ""),
            "stage": request_context.get("stage", ""),
            "resourcePath": event.get("rawPath", "/"),
            "httpMethod": http_context.get("method", "GET"),
            "requestTime": request_context.get("time", ""),
            "protocol": http_context.get("protocol", "HTTP/1.1"),
            "resourceId": request_context.get("resourceId", ""),
            "accountId": request_context.get("accountId", ""),
            "apiId": request_context.get("apiId", ""),
            "identity": request_context.get("identity", {}),
        },
        "multiValueHeaders": {},
        "multiValueQueryStringParameters": {},
    }

    # Convert headers to multiValueHeaders format if needed
    if isinstance(v1_event["headers"], dict):
        v1_event["multiValueHeaders"] = {k: [v] for k, v in v1_event["headers"].items()}

    # Convert query parameters to multiValue format if needed
    if isinstance(v1_event["queryStringParameters"], dict):
        v1_event["multiValueQueryStringParameters"] = {k: [v] for k, v in v1_event["queryStringParameters"].items()}

    return v1_event


def _validate_session_config(app: Flask) -> None:
    """Validate session configuration for Lambda deployment.

    Ensures that DynamoDB session configuration is properly set up
    for the Lambda environment.

    Args:
        app: Flask application instance

    Raises:
        RuntimeError: If session configuration is invalid
    """
    session_type = app.config.get("SESSION_TYPE")

    if session_type == "dynamodb":
        required_configs = {
            "SESSION_TABLE_NAME": os.environ.get("SESSION_TABLE_NAME"),
            "AWS_REGION": os.environ.get("AWS_REGION"),
        }

        missing_configs = [key for key, value in required_configs.items() if not value]

        if missing_configs:
            error_msg = f"Missing required session environment variables for Lambda: {', '.join(missing_configs)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        # Log session configuration for debugging
        logger.info("Lambda session configuration validated:")
        logger.info("  Type: %s", session_type)
        logger.info("  Table: %s", required_configs["SESSION_TABLE_NAME"])
        logger.info("  Region: %s", required_configs["AWS_REGION"])

        # Test DynamoDB table existence in Lambda environment
        try:
            import boto3

            dynamodb = boto3.resource("dynamodb", region_name=required_configs["AWS_REGION"])
            table = dynamodb.Table(required_configs["SESSION_TABLE_NAME"])
            table.load()  # This will fail if table doesn't exist
            logger.info("DynamoDB session table verified: %s", required_configs["SESSION_TABLE_NAME"])
        except Exception as e:
            logger.error("DynamoDB session table validation failed: %s", str(e))
            logger.error("Ensure the DynamoDB table exists before Lambda deployment")
            # This is critical - raise the error to prevent Flask-Session from trying to create table
            raise RuntimeError(f"DynamoDB session table '{required_configs['SESSION_TABLE_NAME']}' is not accessible")

    elif session_type == "filesystem":
        logger.warning("Using filesystem sessions in Lambda - this may cause issues with session persistence")
    elif session_type is None:
        logger.info("Using Flask's default signed cookie sessions (ideal for Lambda)")

    else:
        logger.info("Session configuration validated for type: %s", session_type)


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
    """Handle Lambda events from API Gateway v1.0 (REST API) or v2.0 (HTTP API).

    Args:
        event: The Lambda event
        context: The Lambda context object (not used but required by Lambda)

    Returns:
        dict: Response in appropriate API Gateway format
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

    # Handle HTTP API events (both v1.0 and v2.0 formats)
    app = get_or_create_app()

    try:
        # Convert API Gateway v2.0 format to v1.0 format if needed
        # v2.0 uses 'requestContext.http.method' while v1.0 uses 'httpMethod'
        if "httpMethod" not in event and "requestContext" in event:
            http_context = event.get("requestContext", {})
            if "http" in http_context:
                # API Gateway v2.0 format - convert to v1.0
                event = _convert_apigw_v2_to_v1(event)
                logger.info("Converted API Gateway v2.0 event to v1.0 format")

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
