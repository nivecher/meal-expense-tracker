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
import base64
import io
import json
import logging
import os
import sys
import traceback
from types import SimpleNamespace
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

import awsgi

# Third-party imports
from flask import Flask
from flask import Response as FlaskResponse
from sqlalchemy import text

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
    processed: Dict[str, str] = {}
    if not headers:
        return processed

    for key, value in headers.items():
        header_key = "-".join(word.capitalize() for word in key.split("-"))
        processed[header_key] = value
    return processed


def _build_request_context(
    request_context: Dict[str, Any], headers: Dict[str, str], http_method: str, path: str
) -> Dict[str, Any]:
    """Build v1.0 compatible request context from API Gateway events.

    Handles both REST API (v1.0) and HTTP API (v2.0) event formats.

    Args:
        request_context: The request context from the API Gateway event
        headers: The request headers
        http_method: The HTTP method (GET, POST, etc.)
        path: The request path

    Returns:
        dict: A v1.0 compatible request context
    """
    # Handle API Gateway v2.0 (HTTP API) format
    if "http" in request_context:
        return {
            "httpMethod": http_method,
            "path": path,
            "resourcePath": path,
            "requestId": request_context.get("requestId", ""),
            "apiId": request_context.get("apiId", ""),
            "domainName": request_context.get("domainName", ""),
            "domainPrefix": request_context.get("domainPrefix", ""),
            "extendedRequestId": request_context.get("extendedRequestId", ""),
            "requestTime": request_context.get("time", ""),
            "requestTimeEpoch": request_context.get("timeEpoch", 0),
            "identity": {
                "sourceIp": request_context.get("http", {}).get("sourceIp", ""),
                "userAgent": headers.get("User-Agent", ""),
                "user": request_context.get("authorizer", {}).get("principalId", ""),
            },
            "authorizer": request_context.get("authorizer", {}),
            "protocol": request_context.get("http", {}).get("protocol", "HTTP/1.1"),
            "stage": request_context.get("stage", "$default"),
        }

    # Handle API Gateway v1.0 (REST API) format
    return {
        "httpMethod": http_method,
        "path": path,
        "resourcePath": path,
        "requestId": request_context.get("requestId", ""),
        "apiId": request_context.get("apiId", ""),
        "resourceId": request_context.get("resourceId", ""),
        "accountId": request_context.get("accountId", ""),
        "stage": request_context.get("stage", "$default"),
        "domainName": request_context.get("domainName", ""),
        "domainPrefix": request_context.get("domainPrefix", ""),
        "extendedRequestId": request_context.get("extendedRequestId", ""),
        "requestTime": request_context.get("requestTime", ""),
        "requestTimeEpoch": request_context.get("requestTimeEpoch", 0),
        "identity": {
            "sourceIp": _get_nested(request_context, "identity", "sourceIp", default=""),
            "user": _get_nested(request_context, "identity", "user", default=""),
            "cognitoIdentityPoolId": _get_nested(request_context, "identity", "cognitoIdentityPoolId", default=None),
            "cognitoIdentityId": _get_nested(request_context, "identity", "cognitoIdentityId", default=None),
            "cognitoAuthenticationType": _get_nested(
                request_context, "identity", "cognitoAuthenticationType", default=None
            ),
            "cognitoAuthenticationProvider": _get_nested(
                request_context, "identity", "cognitoAuthenticationProvider", default=None
            ),
            "userArn": _get_nested(request_context, "identity", "userArn", default=None),
            "userAgent": _get_nested(request_context, "identity", "userAgent", default=""),
            "caller": _get_nested(request_context, "identity", "caller", default=None),
            "accessKey": _get_nested(request_context, "identity", "accessKey", default=None),
        },
        "authorizer": request_context.get("authorizer", {}),
        "protocol": request_context.get("protocol", "HTTP/1.1"),
        "apiKey": request_context.get("identity", {}).get("apiKey", None),
        "apiKeyId": request_context.get("identity", {}).get("apiKeyId", None),
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
                                db.session.execute(text("SELECT version_num FROM alembic_version")).scalar()
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
    """Transform API Gateway v2.0 (HTTP API) event to v1.0 (REST API) format.

    This function handles the conversion between the two API Gateway event formats
    to maintain compatibility with existing application code.

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

    This function processes incoming API Gateway events and converts them into
    WSGI-compatible requests that can be handled by the Flask application.

    Args:
        event: Lambda event object from API Gateway
        context: Lambda context object

    Returns:
        dict: Response object for API Gateway
    """
    try:
        # Get or create the Flask app instance
        app = get_or_create_app()

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
            "QUERY_STRING": (
                "&".join(
                    f"{k}={v}"
                    for k, vs in event.get("queryStringParameters", {}).items()
                    for v in ([vs] if isinstance(vs, str) else vs)
                )
                if event.get("queryStringParameters")
                else ""
            ),
            "CONTENT_TYPE": event.get("headers", {}).get("Content-Type", ""),
            "CONTENT_LENGTH": str(len(event.get("body", "") or "")),
            "SERVER_NAME": event.get("headers", {}).get("Host", "localhost"),
            "SERVER_PORT": event.get("headers", {}).get("X-Forwarded-Port", "80"),
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "https" if event.get("isBase64Encoded", False) else "http",
            "wsgi.input": io.BytesIO(
                (event.get("body") or "").encode("utf-8")
                if not event.get("isBase64Encoded", False)
                else base64.b64decode(event["body"])
            ),
            "wsgi.errors": sys.stderr,
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
            "SERVER_PROTOCOL": "HTTP/1.1",
            "REMOTE_ADDR": event.get("requestContext", {}).get("identity", {}).get("sourceIp", ""),
            "HTTP_USER_AGENT": event.get("headers", {}).get("User-Agent", ""),
            "HTTP_ACCEPT": event.get("headers", {}).get("Accept", "*/*"),
        }

        # Add all headers to the WSGI environment with HTTP_ prefix
        for key, value in (event.get("headers") or {}).items():
            if key.lower() == "content-length":
                environ["CONTENT_LENGTH"] = value
            elif key.lower() == "content-type":
                environ["CONTENT_TYPE"] = value
            else:
                header_name = "HTTP_" + key.upper().replace("-", "_")
                environ[header_name] = value
            environ[key] = value

        # Call the WSGI app using a list to store response data
        # Using a list to store the dict for modification in closure
        response_data: List[Dict[str, Any]] = [{"statusCode": 200, "headers": {}, "body": "", "isBase64Encoded": False}]

        def start_response(
            status: str, response_headers: List[Tuple[str, str]], exc_info: Optional[Any] = None
        ) -> None:
            response_data[0]["statusCode"] = int(status.split()[0])
            response_data[0]["headers"] = dict(response_headers)
            return None

        # Use the Flask application's WSGI app to handle the request
        response_body = app(environ, start_response)
        response_data[0]["body"] = "".join(
            chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk for chunk in response_body
        )
        response_data[0]["isBase64Encoded"] = False
        # Extract the response data from the list
        response = response_data[0]

        # Ensure the response has the required fields
        if "statusCode" not in response:
            response = {
                "statusCode": 500,
                "body": json.dumps(
                    {"error": "Internal Server Error", "message": "No status code returned from application"}
                ),
                "headers": {"Content-Type": "application/json"},
                "isBase64Encoded": False,
            }

        return response

    except Exception as e:
        logger.error("Error processing request: %s", str(e), exc_info=True)
        return _create_error_response(e, 500, context)


def _process_awsgi_request(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Process AWSGI request and return the response.

    This function handles the request processing for both API Gateway v1.0 (REST API)
    and v2.0 (HTTP API) events, normalizing them to a common format for the application.

    Args:
        event: Lambda event object from API Gateway
        context: Lambda context object

    Returns:
        dict: Response object for API Gateway
    """
    # Get or create the Flask app instance
    app = get_or_create_app()

    # Process the request within the application context
    with app.app_context():
        try:
            # Process the event based on its type
            if "httpMethod" in event:
                # This is an API Gateway v1.0 (REST API) event
                return _handle_awsgi_request(event, context)
            elif "requestContext" in event and "http" in event["requestContext"]:
                # This is an API Gateway v2.0 (HTTP API) event - transform to v1.0 format
                return _handle_awsgi_request(_transform_v2_to_v1_event(event), context)
            else:
                # Handle other event types (e.g., direct Lambda invocation)
                return _handle_event(event, context)

        except ImportError as e:
            error_msg = f"Failed to import required dependencies: {str(e)}"
            logger.exception(error_msg)
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "error": "Internal Server Error",
                        "message": "Server configuration error",
                        "request_id": context.aws_request_id if hasattr(context, "aws_request_id") else None,
                    }
                ),
                "headers": {
                    "Content-Type": "application/json",
                    "X-Request-ID": context.aws_request_id if hasattr(context, "aws_request_id") else "unknown",
                },
                "isBase64Encoded": False,
            }
        except Exception as e:
            logger.error("Error processing AWSGI request: %s", str(e), exc_info=True)
            return _create_error_response(e, 500, context)


# Global variable to store the app instance to enable reuse across Lambda invocations
_APP_INSTANCE = None


def get_or_create_app() -> Flask:
    """Get or create the Flask application instance with proper configuration.

    This function implements the singleton pattern to ensure we only create one
    Flask app instance per Lambda container, which is important for performance.

    Returns:
        Flask: The configured Flask application instance

    Raises:
        RuntimeError: If application initialization fails
    """
    global _APP_INSTANCE

    if _APP_INSTANCE is not None:
        return _APP_INSTANCE

    try:
        logger.info("Initializing Flask application...")

        # Determine the configuration to use
        config_name = "production" if os.environ.get("AWS_EXECUTION_ENV") else None
        logger.info(f"Using configuration: {config_name or 'default'}")

        # Create the Flask application with the appropriate config
        _APP_INSTANCE = create_app(config_name=config_name)

        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler()],
        )

        # Ensure we're in the application context for database initialization
        with _APP_INSTANCE.app_context():
            # Initialize the database with the app
            from app.database import init_database

            init_database(_APP_INSTANCE)

            # Run any pending migrations on cold start if configured
            _run_cold_start_migrations(_APP_INSTANCE)

            logger.info("Successfully initialized Flask application and database")

        return _APP_INSTANCE

    except Exception as e:
        error_msg = f"Failed to initialize application: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise RuntimeError(error_msg) from e


def lambda_handler(event: dict, context: object) -> dict:
    """AWS Lambda handler for the Flask application.

    This is the main entry point for AWS Lambda. It handles:
    - API Gateway v1.0 (REST API) events
    - API Gateway v2.0 (HTTP API) events
    - Application Load Balancer (ALB) events
    - Direct Lambda invocations

    Args:
        event: The Lambda event
        context: The Lambda context

    Returns:
        dict: Response in the format expected by the invoker
    """
    try:
        # Get or create the Flask app instance
        get_or_create_app()

        # Preprocess the event to normalize it
        processed = preprocess_event(event)

        # Log the processed event (redacting sensitive data)
        _log_event(processed)

        # Process the event using the appropriate handler
        if "httpMethod" in processed:
            # This is an API Gateway event
            return _process_awsgi_request(processed, context)
        elif "http" in processed.get("requestContext", {}):
            # This is an API Gateway v2.0 event that wasn't transformed yet
            return _process_awsgi_request(_transform_v2_to_v1_event(processed), context)
        else:
            # Handle other event types (ALB, direct invocation, etc.)
            return _handle_event(processed, context)

    except Exception as e:
        logger.error("Error in lambda_handler: %s", str(e), exc_info=True)
        return _create_error_response(e, 500, context)


def preprocess_event(event: dict) -> dict:
    """Preprocess the Lambda event to handle different formats.

    Handles both API Gateway v1.0 (REST API) and v2.0 (HTTP API) events,
    as well as ALB events and direct Lambda invocations.

    Args:
        event: The incoming Lambda event

    Returns:
        dict: Normalized event in API Gateway v1.0 format
    """
    # If this is an ALB event, return it as-is
    if "requestContext" in event and "elb" in event["requestContext"]:
        return event

    # Check if this is an API Gateway v2.0 (HTTP API) event
    if "version" in event and event["version"] == "2.0":
        return _transform_v2_to_v1_event(event)

    # For API Gateway v1.0 (REST API) or direct Lambda invocations
    # Ensure all required fields are present with appropriate defaults
    processed_event = {
        "httpMethod": event.get("httpMethod", "GET"),
        "path": event.get("path", "/"),
        "resource": event.get("resource", event.get("path", "/")),
        "headers": {k.lower(): v for k, v in event.get("headers", {}).items()},
        "queryStringParameters": event.get("queryStringParameters") or {},
        "pathParameters": event.get("pathParameters") or {},
        "stageVariables": event.get("stageVariables") or {},
        "requestContext": event.get("requestContext", {}),
        "body": event.get("body", ""),
        "isBase64Encoded": event.get("isBase64Encoded", False),
    }

    # Ensure body is a string
    if processed_event["body"] is None:
        processed_event["body"] = ""
    elif isinstance(processed_event["body"], (dict, list)):
        processed_event["body"] = json.dumps(processed_event["body"])

    # Ensure requestContext has required fields
    if not processed_event["requestContext"]:
        processed_event["requestContext"] = {
            "resourcePath": processed_event["path"],
            "httpMethod": processed_event["httpMethod"],
            "requestId": event.get("requestContext", {}).get("requestId", ""),
            "stage": event.get("requestContext", {}).get("stage", "$default"),
        }

    return processed_event


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
