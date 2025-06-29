"""WSGI entry point for the Meal Expense Tracker application.

This module serves as the entry point for both local development and
AWS Lambda deployment. It handles application initialization,
database configuration, and request routing.

It supports:
- API Gateway events (REST and HTTP APIs)
- Direct Lambda invocations
- Database operations (migrations, resets, status)
- Local development server
"""

from __future__ import annotations

# Standard library imports
import io
import json
import logging
import os
import sys
import traceback
from types import SimpleNamespace
from typing import Any, Dict, Optional

# Third-party imports
from flask import Flask

# Local application imports
from app import create_app

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def _get_nested(dct: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Safely get nested dictionary values."""
    for key in keys:
        try:
            dct = dct[key]
        except (KeyError, TypeError):
            return default
    return dct


def _process_headers(headers: Optional[Dict[str, str]]) -> Dict[str, str]:
    """Process and normalize HTTP headers."""
    processed = {}
    if not headers:
        return processed

    for key, value in headers.items():
        header_key = "-".join(word.capitalize() for word in key.split("-"))
        processed[header_key] = value
    return processed


def _build_request_context(
    request_context: Dict[str, Any], headers: Dict[str, str], http_method: str, path: str
) -> Dict[str, Any]:
    """Build v1.0 compatible request context."""
    return {
        "httpMethod": http_method,
        "path": path,
        "resourcePath": path,
        "requestId": _get_nested(request_context, "requestId", default=""),
        "apiId": _get_nested(request_context, "apiId", default=""),
        "resourceId": _get_nested(request_context, "resourceId", default=""),
        "accountId": _get_nested(request_context, "accountId", default=""),
        "stage": _get_nested(request_context, "stage", default="$default"),
        "identity": {
            "sourceIp": _get_nested(request_context, "identity", "sourceIp", default=""),
            "userAgent": headers.get("User-Agent", ""),
        },
    }


def _create_minimal_event() -> Dict[str, Any]:
    """Create a minimal valid API Gateway v1.0 event."""
    return {
        "httpMethod": "GET",
        "path": "/",
        "resource": "$default",
        "queryStringParameters": {},
        "multiValueQueryStringParameters": {},
        "headers": {},
        "multiValueHeaders": {},
        "pathParameters": {},
        "stageVariables": {},
        "requestContext": {},
        "body": "",
        "isBase64Encoded": False,
    }


def _normalize_http_api_v2_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize HTTP API v2.0 event to v1.0 format.

    Args:
        event: The API Gateway v2.0 event

    Returns:
        dict: Normalized event in v1.0 format
    """
    try:
        normalized = json.loads(json.dumps(event))
        request_context = normalized.get("requestContext", {})
        http_context = request_context.get("http", {})

        http_method = http_context.get("method", "GET").upper()
        path = normalized.get("rawPath", "/")
        headers = _process_headers(normalized.get("headers"))

        request_context_v1 = _build_request_context(request_context, headers, http_method, path)

        normalized.update(
            {
                "httpMethod": http_method,
                "path": path,
                "resource": normalized.get("routeKey", "$default"),
                "queryStringParameters": normalized.get("queryStringParameters") or {},
                "multiValueQueryStringParameters": normalized.get("queryStringParameters") or {},
                "headers": headers,
                "multiValueHeaders": {k: [v] for k, v in headers.items()},
                "pathParameters": normalized.get("pathParameters") or {},
                "stageVariables": normalized.get("stageVariables") or {},
                "requestContext": request_context_v1,
                "body": normalized.get("body", "") or "",
                "isBase64Encoded": normalized.get("isBase64Encoded", False),
            }
        )

        logger.debug("Normalized event: %s", json.dumps(normalized, default=str, indent=2))
        return normalized

    except Exception as e:
        logger.error("Error normalizing API Gateway v2.0 event: %s", str(e), exc_info=True)
        return _create_minimal_event()


# Create the application instance
# This is used by WSGI servers and local development

# Add the project directory to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


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


def handle_database_operation(app, operation, **kwargs):
    """Handle database operations like migrations and resets.

    Args:
        app: Flask application instance
        operation: Operation to perform ('migrate', 'reset', 'status')
        **kwargs: Additional operation-specific arguments

    Returns:
        dict: Operation result with status code and message
    """
    with app.app_context():
        try:
            from migrate_db import reset_database, run_migrations

            if operation == "migrate":
                logger.info("Running database migrations")
                run_migrations()
                return {
                    "statusCode": 200,
                    "body": json.dumps(
                        {
                            "status": "success",
                            "message": "Migrations completed successfully",
                        }
                    ),
                    "headers": {"Content-Type": "application/json"},
                }

            elif operation == "reset":
                logger.warning("Resetting database")
                reset_database()
                return {
                    "statusCode": 200,
                    "body": json.dumps({"status": "success", "message": "Database reset completed"}),
                    "headers": {"Content-Type": "application/json"},
                }

            elif operation == "status":
                from sqlalchemy import inspect

                from app.extensions import db

                inspector = inspect(db.engine)
                tables = inspector.get_table_names()
                return {
                    "statusCode": 200,
                    "body": json.dumps(
                        {
                            "status": "success",
                            "tables": tables,
                            "alembic_version": (
                                db.session.execute("SELECT version_num FROM alembic_version").scalar()
                                if "alembic_version" in tables
                                else None
                            ),
                        }
                    ),
                    "headers": {"Content-Type": "application/json"},
                }

            else:
                return {
                    "statusCode": 400,
                    "body": json.dumps(
                        {
                            "status": "error",
                            "message": f"Unknown operation: {operation}",
                        }
                    ),
                    "headers": {"Content-Type": "application/json"},
                }

        except Exception as e:
            error_msg = f"Database operation '{operation}' failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            return {
                "statusCode": 500,
                "body": json.dumps({"status": "error", "message": error_msg}),
                "headers": {"Content-Type": "application/json"},
            }


def handle_api_gateway_event(app, event, context):
    """Handle API Gateway events and return the appropriate response.

    Args:
        app: Flask application instance
        event: Lambda event from API Gateway
        context: Lambda context object

    Returns:
        dict: Response formatted for API Gateway
    """
    # Get the AWSGI response handler for normal API requests
    get_response = _get_awsgi_response()

    # Set up request context
    with app.app_context():
        try:
            # Log the incoming event structure for debugging
            logger.debug("Raw API Gateway event: %s", json.dumps(event, default=str))

            # Normalize the event format for different API Gateway versions
            if event.get("version") == "2.0":
                # HTTP API v2.0 format
                logger.debug("Processing HTTP API v2.0 event")
                event = _normalize_http_api_v2_event(event)
            elif "httpMethod" in event:
                # REST API v1.0 format
                logger.debug("Processing REST API v1.0 event")
            else:
                # Unknown API Gateway format
                logger.error("Unknown API Gateway event format")
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Invalid API Gateway event format"}),
                    "headers": {"Content-Type": "application/json"},
                }

            # Call the WSGI app and get the response
            response = get_response(
                event,
                context,
                base64_content_types=app.config.get("BINARY_CONTENT_TYPES", []),
            )

            # Log the response for debugging
            logger.debug("API Gateway response: %s", json.dumps(response, default=str))
            return response

        except json.JSONDecodeError as e:
            logger.error("JSON decode error in API Gateway event: %s", str(e))
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Invalid JSON in request"}),
                "headers": {"Content-Type": "application/json"},
            }
        except Exception as e:
            logger.error("Error handling API Gateway event: %s", str(e))
            logger.error(traceback.format_exc())
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "error": "Internal server error",
                        "request_id": (context.aws_request_id if hasattr(context, "aws_request_id") else None),
                    }
                ),
                "headers": {
                    "Content-Type": "application/json",
                    "x-amzn-ErrorType": "InternalServerError",
                },
            }


def _handle_direct_invocation(app: Flask, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Handle direct Lambda invocations for database operations.

    Args:
        app: Flask application instance
        event: Lambda event object

    Returns:
        Optional[Dict]: Response from database operation or None if not a direct invocation
    """
    if event.get("run_migrations"):
        logger.info("Handling legacy run_migrations request")
        return handle_database_operation(app, "migrate")

    if "db_operation" in event:
        return handle_database_operation(app, **event)

    return None


def _run_cold_start_migrations(app: Flask) -> None:
    """Run database migrations on Lambda cold start if configured.

    Args:
        app: Flask application instance
    """
    is_lambda = bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
    should_run = is_lambda and os.environ.get("RUN_MIGRATIONS_ON_START", "true").lower() == "true"

    if not should_run:
        logger.debug("Skipping cold start migrations")
        return

    with app.app_context():
        try:
            from migrate_db import run_migrations

            logger.info("Running database migrations on cold start")
            if run_migrations():
                logger.info("Cold start migrations completed successfully")
            else:
                logger.error("Cold start migrations failed")
        except Exception as e:
            logger.error("Database migration failed: %s", str(e), exc_info=True)


def _process_api_gateway_event(app: Flask, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Process API Gateway events and return the response.

    Args:
        app: Flask application instance
        event: Lambda event object
        context: Lambda context object

    Returns:
        Dict: Response for API Gateway
    """
    logger.info("Processing API Gateway event")
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Event details: %s", json.dumps(event, default=str, indent=2))
    return handle_api_gateway_event(app, event, context)


def _create_error_response(error: Exception, status_code: int = 500, context: Optional[Any] = None) -> Dict[str, Any]:
    """Create a standardized error response.

    Args:
        error: Exception that was raised
        status_code: HTTP status code to return
        context: Lambda context object (optional)

    Returns:
        Dict: Formatted error response
    """
    # Generate a unique error ID for tracking
    error_id = f"lambda-{context.aws_request_id}" if context and hasattr(context, "aws_request_id") else "unknown"

    return {
        "statusCode": status_code,
        "body": json.dumps(
            {
                "status": "error",
                "message": "Internal server error",
                "error": str(error),
                "error_id": error_id,
            },
            indent=2,
        ),
        "headers": {"Content-Type": "application/json", "X-Request-ID": error_id or ""},
    }


def _transform_v2_to_v1_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Transform API Gateway v2.0 event to v1.0 format.

    Args:
        event: API Gateway v2.0 event

    Returns:
        dict: Transformed event in v1.0 format
    """
    # If it's already in v1.0 format, return as is
    if "httpMethod" in event:
        return event

    # Get HTTP context with defaults
    http_context = event.get("requestContext", {}).get("http", {})

    # Transform v2.0 to v1.0 format
    transformed = {
        "httpMethod": http_context.get("method", "GET"),
        "path": event.get("rawPath", "/"),
        "resource": event.get("routeKey", "$default"),
        "queryStringParameters": event.get("queryStringParameters") or {},
        "multiValueQueryStringParameters": event.get("queryStringParameters") or {},
        "headers": {k.lower(): v for k, v in event.get("headers", {}).items()},
        "pathParameters": event.get("pathParameters") or {},
        "stageVariables": event.get("stageVariables") or {},
        "requestContext": event.get("requestContext", {}).copy(),
        "body": event.get("body", ""),
        "isBase64Encoded": event.get("isBase64Encoded", False),
    }

    # Add multiValueHeaders if present
    if "multiValueHeaders" in event and event["multiValueHeaders"]:
        transformed["multiValueHeaders"] = {k.lower(): v for k, v in event["multiValueHeaders"].items()}
    # If no multiValueHeaders, create from headers
    elif "headers" in event and event["headers"]:
        multi_headers = {}
        for key, value in transformed["headers"].items():
            multi_headers[key.lower()] = [value]
        transformed["multiValueHeaders"] = multi_headers

    # Ensure required fields in requestContext
    if "requestContext" not in transformed:
        transformed["requestContext"] = {}

    # Add apiId if missing
    if "apiId" not in transformed["requestContext"] and "apiId" in event.get("requestContext", {}):
        transformed["requestContext"]["apiId"] = event["requestContext"]["apiId"]

    # Add requestId if missing
    if "requestId" not in transformed["requestContext"] and "requestId" in event.get("requestContext", {}):
        transformed["requestContext"]["requestId"] = event["requestContext"]["requestId"]

    logger.debug("Transformed v2.0 event to v1.0 format")
    return transformed


def _handle_non_http_event(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Handle non-HTTP Lambda events like direct invocations or scheduled events.

    Args:
        event: Lambda event object

    Returns:
        Optional[Dict]: Response if handled, None if not a non-HTTP event
    """
    if "httpMethod" not in event and "requestContext" in event:
        logger.warning("Event missing httpMethod, assuming direct invocation")
        return {
            "statusCode": 200,
            "body": "Direct Lambda invocation successful",
            "headers": {"Content-Type": "application/json"},
        }

    if "httpMethod" not in event and "source" in event:
        source = event.get("source", "unknown")
        logger.info("Processing non-HTTP Lambda event: %s", source)
        return {
            "statusCode": 200,
            "body": f"Processed {source} event",
            "headers": {"Content-Type": "application/json"},
        }

    return None


def _handle_awsgi_error(context: Any, error_msg: str) -> Dict[str, Any]:
    """Create an error response for AWSGI handler issues.

    Args:
        context: Lambda context object
        error_msg: Error message to include in the response

    Returns:
        dict: Error response
    """
    request_id = context.aws_request_id if context else None
    return {
        "statusCode": 500,
        "body": json.dumps(
            {
                "error": "Internal Server Error",
                "message": error_msg,
                "request_id": request_id,
            }
        ),
        "headers": {
            "Content-Type": "application/json",
            "X-Request-ID": request_id or "unknown",
        },
        "isBase64Encoded": False,
    }


def _initialize_context(context: Any) -> Any:
    """Initialize Lambda context if not provided (for local testing)."""
    if context is None:
        context = SimpleNamespace(
            aws_request_id="local_test",
            function_name="local_test",
            function_version="$LATEST",
            invoked_function_arn="arn:aws:lambda:local:0:function:local_test",
            log_group_name="/aws/lambda/local_test",
            log_stream_name="local_test",
        )
    return context


def _log_event(event: Dict[str, Any]) -> None:
    """Log the incoming event (redacting sensitive data)."""
    event_to_log = dict(event)
    if "body" in event_to_log and event_to_log["body"] and len(event_to_log["body"]) > 100:
        event_to_log["body"] = event_to_log["body"][:100] + "... [truncated]"
    logger.debug("Received event: %s", json.dumps(event_to_log, default=str))


def _handle_event(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle different types of Lambda events."""
    # Handle direct Lambda invocations first (e.g., for database operations)
    db_result = _handle_direct_invocation(app, event)
    if db_result is not None:
        return db_result

    # Handle API Gateway events
    if "httpMethod" in event or "requestContext" in event:
        return _process_api_gateway_event(app, event, context)

    # Handle non-HTTP events (e.g., scheduled events, S3, etc.)
    non_http_result = _handle_non_http_event(event)
    if non_http_result is not None:
        return non_http_result

    # If we get here, the event type is not supported
    error_msg = f"Unsupported event type: {event.get('eventType', 'unknown')}"
    logger.error(error_msg)
    return _create_error_response(ValueError(error_msg), 400, context)


def _handle_awsgi_request(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle AWSGI request processing.

    Args:
        event: Lambda event object
        context: Lambda context object

    Returns:
        dict: Response object for API Gateway
    """
    # Get AWSGI response handler
    handler = _get_awsgi_response()
    if not handler:
        error_msg = "AWSGI handler not available - awsgi package not found"
        logger.error(error_msg)
        return _handle_awsgi_error(context, error_msg)

    try:
        # Log request details for debugging
        logger.info(
            "Processing request: %s %s",
            event.get("httpMethod"),
            event.get("path"),
        )

        # Convert API Gateway event to WSGI environment
        environ = {
            "REQUEST_METHOD": event.get("httpMethod", "GET"),
            "SCRIPT_NAME": "",
            "PATH_INFO": event.get("path", "/"),
            "QUERY_STRING": event.get("queryStringParameters", ""),
            "CONTENT_TYPE": event.get("headers", {}).get("Content-Type", ""),
            "CONTENT_LENGTH": str(len(event.get("body", ""))),
            "SERVER_NAME": "localhost",
            "SERVER_PORT": "80",
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "https" if event.get("isBase64Encoded", False) else "http",
            "wsgi.input": io.BytesIO(event.get("body", "").encode("utf-8") if event.get("body") else b""),
            "wsgi.errors": sys.stderr,
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
        }

        # Add headers to environ
        for key, value in event.get("headers", {}).items():
            key = key.upper().replace("-", "_")
            if key not in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                key = f"HTTP_{key}"
            environ[key] = value

        # Call the WSGI app using a list to store response data
        response_data = [{}]  # Using a list to store the dict for modification in closure

        def start_response(status, response_headers, exc_info=None):
            response_data[0]["statusCode"] = int(status.split()[0])
            response_data[0]["headers"] = dict(response_headers)
            return None

        response_body = handler(app, environ, start_response)
        response_data[0]["body"] = "".join(
            chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk for chunk in response_body
        )
        response_data[0]["isBase64Encoded"] = False
        response_data = response_data[0]  # Extract the dict from the list

        # Ensure the response has the required fields
        if "statusCode" not in response_data:
            response_data["statusCode"] = 500
            response_data["body"] = json.dumps(
                {"error": "Internal Server Error", "message": "No status code returned from application"}
            )
            response_data["headers"] = {"Content-Type": "application/json"}

        return response_data

    except Exception as e:
        logger.error("Error processing request: %s", str(e), exc_info=True)
        return _create_error_response(e, 500, context)


def _process_awsgi_request(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Process AWSGI request and return the response.

    Args:
        event: Lambda event object
        context: Lambda context object

    Returns:
        dict: Response object for API Gateway
    """
    try:
        # Get the AWSGI handler
        awsgi_handler = _get_awsgi_response()
        if not awsgi_handler:
            error_msg = "AWSGI handler not available - awsgi package not found"
            logger.error(error_msg)
            return _handle_awsgi_error(context, error_msg)

        # Process the request using the AWSGI handler
        response = awsgi_handler(app, event, context, base64_content_types={"image/png"})

        # Log successful response (without sensitive data)
        logger.info(
            "Request completed successfully",
            extra={
                "status_code": response.get("statusCode"),
                "response_size": len(json.dumps(response.get("body", ""))),
                "request_id": context.aws_request_id if context else None,
            },
        )
        return response

    except KeyError as e:
        error_msg = f"Bad Request: Missing required field - {str(e)}"
        logger.warning(
            error_msg,
            extra={
                "error_type": "ValidationError",
                "missing_field": str(e),
                "request_id": context.aws_request_id if context else None,
            },
        )
        return {
            "statusCode": 400,
            "body": json.dumps(
                {
                    "error": "Bad Request",
                    "message": error_msg,
                    "request_id": context.aws_request_id if context else None,
                }
            ),
            "headers": {
                "Content-Type": "application/json",
                "X-Request-ID": context.aws_request_id if context else "unknown",
            },
            "isBase64Encoded": False,
        }
    except ImportError as e:
        error_msg = f"Failed to import required dependencies: {str(e)}"
        logger.exception(error_msg)
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "error": "Internal Server Error",
                    "message": "Server configuration error",
                    "request_id": context.aws_request_id if context else None,
                }
            ),
            "headers": {
                "Content-Type": "application/json",
                "X-Request-ID": context.aws_request_id if context else "unknown",
            },
            "isBase64Encoded": False,
        }
    except Exception as e:
        logger.error("Error processing AWSGI request: %s", str(e), exc_info=True)
        return _create_error_response(e, 500, context)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda function handler for the Meal Expense Tracker API.

    This function serves as the entry point for AWS Lambda. It handles:
    - API Gateway events (both REST and HTTP APIs)
    - Direct Lambda invocations for database operations

    Args:
        event: The event dict containing request data
        context: The context object provided by AWS Lambda

    Returns:
        dict: Response object for API Gateway
    """
    # Initialize context and log the incoming event
    context = _initialize_context(context)

    # Log the incoming event (redacting sensitive data)
    _log_event(event)

    try:
        # Transform API Gateway v2.0 (HTTP API) events to v1.0 format if needed
        if event.get("version") == "2.0" or "requestContext" in event and "http" in event.get("requestContext", {}):
            event = _transform_v2_to_v1_event(event)

        # Ensure httpMethod is present for API Gateway events
        if "requestContext" in event and "http" in event.get("requestContext", {}):
            event["httpMethod"] = event["requestContext"]["http"]["method"]

        # Handle AWSGI requests (API Gateway)
        if "httpMethod" in event or "requestContext" in event:
            return _process_awsgi_request(event, context)

        # Handle direct Lambda invocations
        return _handle_event(event, context)

    except Exception as e:
        logger.error("Unhandled exception in Lambda handler: %s", str(e), exc_info=True)
        return _create_error_response(e, 500, context)


def main():
    """Run the application locally.

    This is the entry point for local development using `python wsgi.py`
    """
    # Configure host and port from environment or use defaults
    host = os.environ.get("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_RUN_PORT", "5000"))

    # Set debug mode based on environment
    debug = os.environ.get("FLASK_ENV") == "development"

    # Suppress Werkzeug logs below WARNING level
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    # Log startup information
    logger.info("Starting local development server at http://%s:%s", host, port)
    logger.info("Debug mode: %s", "on" if debug else "off")

    # Run the application
    app.run(host=host, port=port, debug=debug, use_reloader=debug)


if __name__ == "__main__":
    # Run the application directly for local development
    main()
