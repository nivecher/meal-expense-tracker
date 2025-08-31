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


def _get_allowed_domains(headers: Dict[str, str]) -> list[str]:
    """Get allowed domains for referrer validation."""
    allowed_domains = os.getenv("ALLOWED_REFERRER_DOMAINS", "").split(",")
    if not allowed_domains or allowed_domains == [""]:
        host = headers.get("Host") or headers.get("host", "")
        if host:
            allowed_domains = [f"https://{host}"]
            if "execute-api" in host or "lambda-url" in host or "amazonaws.com" in host:
                allowed_domains.extend([f"https://{host}", f"http://{host}"])
        else:
            allowed_domains = ["http://localhost:5000", "https://localhost:5000"]
    return allowed_domains


def _should_skip_referrer_validation(event: Dict[str, Any]) -> bool:
    """Check if referrer validation should be skipped."""
    http_method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method", "")

    # Skip for OPTIONS, GET requests
    if http_method in ["OPTIONS", "GET"]:
        return True

    # Skip for admin/database operations
    if "admin_operation" in event or "operation" in event:
        return True

    return False


def _is_referrer_allowed(referer: str, allowed_domains: list[str]) -> bool:
    """Check if referrer is allowed."""
    if not referer:
        return True  # Allow requests without referrer

    # Check against allowed domains
    for domain in allowed_domains:
        if referer.startswith(domain.strip()):
            return True

    # Additional check for AWS domains
    if "amazonaws.com" in referer:
        return True

    return False


def _validate_referrer(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validate the referrer header for security."""
    if _should_skip_referrer_validation(event):
        return None

    headers = event.get("headers", {})
    referer = headers.get("Referer") or headers.get("referer", "")
    allowed_domains = _get_allowed_domains(headers)

    if _is_referrer_allowed(referer, allowed_domains):
        if referer:
            logging.info(f"Referrer validation passed: {referer}")
        return None

    # Log but don't block for now
    logging.warning(f"Invalid referrer: {referer}. Allowed domains: {allowed_domains}")
    return None  # Don't block during development


def _enhance_security_headers(headers: Dict[str, str]) -> None:
    """Ensure security headers are properly set for Lambda environment."""
    # Essential security headers
    if "X-Content-Type-Options" not in headers:
        headers["X-Content-Type-Options"] = "nosniff"

    # Remove deprecated headers
    headers.pop("Pragma", None)
    headers.pop("X-Frame-Options", None)

    # Ensure CSP header for HTML responses
    content_type = headers.get("Content-Type", "")
    if "html" in content_type and "Content-Security-Policy" not in headers:
        headers["Content-Security-Policy"] = (
            "frame-ancestors 'none'; default-src 'self'; script-src 'self' 'unsafe-inline' "
            "https://cdn.jsdelivr.net https://code.jquery.com https://maps.googleapis.com "
            "https://maps.gstatic.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net "
            "https://cdnjs.cloudflare.com https://fonts.googleapis.com; font-src 'self' "
            "https://cdn.jsdelivr.net https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https: blob:; connect-src 'self' https://maps.googleapis.com "
            "https://places.googleapis.com; object-src 'none'; base-uri 'self';"
        )


def _fix_cache_control_headers(headers: Dict[str, str]) -> None:
    """Fix cache-control header conflicts and ensure proper caching."""
    cache_control = headers.get("Cache-Control", "")
    content_type = headers.get("Content-Type", "")

    # Remove conflicting directives
    if "no-cache" in cache_control and "max-age" in cache_control:
        if "html" in content_type:
            headers["Cache-Control"] = "no-cache"
        elif any(ext in content_type for ext in ["css", "javascript", "image", "font/"]):
            headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            headers["Cache-Control"] = "public, max-age=3600"

    # Set proper cache control if missing
    if not cache_control:
        if "html" in content_type:
            headers["Cache-Control"] = "no-cache"
        elif any(ext in content_type for ext in ["css", "javascript", "image", "font/"]):
            headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            headers["Cache-Control"] = "public, max-age=3600"


def _handle_database_operation(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle database operations with enhanced headers."""
    operation = str(event["operation"])
    db_response = handle_database_operation(operation, **event)
    db_headers = db_response.get("headers", {})
    _enhance_security_headers(db_headers)
    _fix_cache_control_headers(db_headers)
    return {
        "statusCode": db_response["statusCode"],
        "body": db_response["body"],
        "headers": db_headers,
        "isBase64Encoded": db_response["isBase64Encoded"],
    }


def _handle_admin_operation(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle admin operations with enhanced headers."""
    from app.admin.lambda_admin import handle_admin_request

    app = get_or_create_app()
    admin_response = handle_admin_request(app, event)
    if isinstance(admin_response, dict) and "headers" in admin_response:
        _enhance_security_headers(admin_response["headers"])
        _fix_cache_control_headers(admin_response["headers"])
    return admin_response


def _handle_cors_preflight() -> Dict[str, Any]:
    """Handle CORS preflight OPTIONS requests."""
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-CSRFToken, X-Requested-With",
            "Access-Control-Allow-Credentials": "false",
            "Access-Control-Max-Age": "86400",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "public, max-age=86400",
        },
        "body": "",
        "isBase64Encoded": False,
    }


def _process_awsgi_response(response: Dict[str, Any]) -> Dict[str, str]:
    """Process and enhance AWSGI response headers."""
    headers = response.get("headers", {})
    if not isinstance(headers, dict):
        headers = {}

    headers = {str(k): str(v) for k, v in headers.items()}
    headers.update(
        {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-CSRFToken, X-Requested-With",
            "Access-Control-Allow-Credentials": "false",
        }
    )

    _enhance_security_headers(headers)
    _fix_cache_control_headers(headers)
    return headers


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
        return _handle_database_operation(event)

    # Handle admin operations
    if "admin_operation" in event:
        return _handle_admin_operation(event)

    # Validate referrer for security (before processing HTTP requests)
    referrer_error = _validate_referrer(event)
    if referrer_error:
        return referrer_error

    # Handle HTTP API events (both v1.0 and v2.0 formats)
    app = get_or_create_app()

    try:
        # Handle CORS preflight requests for OPTIONS method
        http_method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")
        if http_method == "OPTIONS":
            return _handle_cors_preflight()
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

        # Process and enhance response headers
        headers = _process_awsgi_response(response)

        return {
            "statusCode": response.get("statusCode", 500),
            "body": response.get("body", ""),
            "headers": headers,
            "isBase64Encoded": response.get("isBase64Encoded", False),
        }

    except Exception as e:
        logger.exception("Error handling request: %s", str(e))
        error_headers = {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-cache",
        }
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"}),
            "headers": error_headers,
            "isBase64Encoded": False,
        }
