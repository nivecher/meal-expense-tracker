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
import json
import logging
import os
import sys
import traceback
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Tuple

# Third-party imports
from flask import Flask
from flask_wtf.csrf import generate_csrf
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


def _get_awsgi_response() -> Callable:
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


def handle_database_operation(app, operation, **kwargs) -> dict:
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


def handle_api_gateway_event(app, event, context) -> dict:
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
    """[DEPRECATED] Transform API Gateway v2.0 (HTTP API) event to v1.0 (REST API) format.

    This function is kept for backward compatibility but no longer performs any transformation
    as we now handle API Gateway v2.0 events directly.
    """
    logger.warning(
        "_transform_v2_to_v1_event is deprecated and will be removed in a future version. "
        "The application now handles API Gateway v2.0 events directly."
    )
    return event


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


def _process_wsgi_headers(response_headers: List[Tuple[str, str]]) -> Dict[str, str]:
    """Process WSGI response headers into a normalized dictionary.

    Args:
        response_headers: List of (header_name, value) tuples from WSGI

    Returns:
        Dict of normalized headers with lowercase keys
    """
    headers: Dict[str, str] = {}
    for name, value in response_headers:
        name = name.lower()
        if name in headers:
            # Handle duplicate headers by joining with comma
            headers[name] = ", ".join([headers[name], value])
        else:
            headers[name] = value
    return headers


def _create_wsgi_start_response(response_data: List[Dict[str, Any]]) -> Callable[..., None]:
    """Create a start_response function for WSGI applications.

    Args:
        response_data: List containing a single response dict to be modified

    Returns:
        A start_response function for WSGI applications
    """

    def start_response(status: str, response_headers: List[Tuple[str, str]], exc_info: Optional[Any] = None) -> None:
        """WSGI start_response callback function."""
        # Parse the status code from the status string (e.g., "200 OK" -> 200)
        status_code = int(status.split()[0]) if status else 500
        response_data[0]["statusCode"] = status_code
        response_data[0]["headers"] = _process_wsgi_headers(response_headers)

    return start_response


def _handle_awsgi_request(environ: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle a WSGI request and return the response.

    This function processes a WSGI environment and returns a response
    in the format expected by API Gateway.

    Args:
        environ: The WSGI environment dictionary
        context: The Lambda context object

    Returns:
        dict: Response object for API Gateway
    """

    try:

        app = get_or_create_app()  # TODO is this needed here?

        # Log request details for debugging
        logger.info(
            "Processing %s request for %s",
            environ.get("REQUEST_METHOD", "UNKNOWN"),
            environ.get("PATH_INFO", "/"),
        )

        # Store response data in a list to allow modification in the start_response closure
        response_data: List[Dict[str, Any]] = [{"statusCode": 200, "headers": {}, "body": "", "isBase64Encoded": False}]

        # Create start_response function
        start_response = _create_wsgi_start_response(response_data)

        def process_response_body(response_body: Any) -> str:
            """Convert WSGI response body to a string.
            Args:
                response_body: The response body from WSGI app

            Returns:
                str: The response body as a string
            """
            if isinstance(response_body, (list, tuple)):
                return "".join(
                    chunk.decode("utf-8") if isinstance(chunk, bytes) else str(chunk) for chunk in response_body
                )
            if isinstance(response_body, bytes):
                return response_body.decode("utf-8")
            if isinstance(response_body, str):
                return response_body
            return str(response_body or "")

        # Process the request through the WSGI app
        response_body = app(environ, start_response)
        response = response_data[0]
        try:
            # Process response body and ensure proper formatting
            response["body"] = process_response_body(response_body)

            # Ensure required fields are present and properly typed
            response["statusCode"] = int(response.get("statusCode", 200))
            response.setdefault("headers", {})
            response["isBase64Encoded"] = bool(response.get("isBase64Encoded", False))

            # Ensure headers are strings
            response["headers"] = {str(k): str(v) for k, v in response["headers"].items()}

            return response

        except Exception as e:
            logger.exception("Error processing response")
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {"error": "Internal Server Error", "message": "Error processing response", "details": str(e)}
                ),
                "isBase64Encoded": False,
            }

    except Exception as e:
        logger.exception("Error in _handle_awsgi_request")
        return _create_error_response(e, 500, context)


def _handle_http_api_v2_event(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle API Gateway v2.0 (HTTP API) events directly.

    Args:
        event: Lambda event object from API Gateway v2.0
        context: Lambda context object

    Returns:
        dict: Response object for API Gateway
    """
    get_or_create_app()

    # Create WSGI environment from v2.0 event
    environ = create_wsgi_environ(event, context)

    # Process the request
    response = _handle_awsgi_request(environ, context)

    # Ensure the response has the required fields
    if not isinstance(response, dict):
        return _create_error_response(ValueError("Invalid response format from application"), 500, context)

    # Ensure required fields are present
    response.setdefault("statusCode", 200)
    response.setdefault("headers", {})
    response.setdefault("isBase64Encoded", False)

    # Add CORS headers if not already present
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, X-CSRFToken, X-Requested-With",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Max-Age": "3600",
    }

    # Only add CORS headers if not already set
    for header, value in cors_headers.items():
        if header not in response["headers"]:
            response["headers"][header] = value

    return response


def _process_awsgi_request(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Process AWSGI request and return the response.

    This function handles the request processing for API Gateway v2.0 (HTTP API) events.

    Args:
        event: Lambda event object from API Gateway v2.0
        context: Lambda context object

    Returns:
        dict: Response object for API Gateway
    """
    # Get or create the Flask app instance
    app = get_or_create_app()

    # Process the request within the application context
    with app.app_context():
        try:
            # Verify this is a valid HTTP API v2.0 event
            if not ("requestContext" in event and "http" in event["requestContext"]):
                logger.error("Invalid API Gateway v2.0 event format")
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Bad Request", "message": "Invalid API Gateway v2.0 event format"}),
                    "headers": {"Content-Type": "application/json"},
                    "isBase64Encoded": False,
                }

            # Process the v2.0 event directly
            return _handle_http_api_v2_event(event, context)

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


def create_wsgi_environ(event, context) -> dict:
    """Create a WSGI environment from the Lambda event.

    Args:
        event: The Lambda event
        context: The Lambda context

    Returns:
        dict: WSGI environment
    """
    import io
    import json
    import sys

    environ = {
        "REQUEST_METHOD": event.get("httpMethod", "GET"),
        "SCRIPT_NAME": "",
        "PATH_INFO": event.get("path", "/"),
        "QUERY_STRING": (
            "&".join([f"{k}={v}" for k, v in event.get("queryStringParameters", {}).items()])
            if event.get("queryStringParameters")
            else ""
        ),
        "SERVER_NAME": event.get("headers", {}).get("host", "localhost"),
        "SERVER_PORT": "80",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "https" if event.get("headers", {}).get("x-forwarded-proto") == "https" else "http",
        "wsgi.input": (
            io.BytesIO(json.dumps(event.get("body", "")).encode("utf-8"))
            if isinstance(event.get("body"), dict)
            else io.BytesIO(event.get("body", "").encode("utf-8") if event.get("body") else b"")
        ),
        "wsgi.errors": sys.stderr,
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
    }

    # Add headers
    for key, value in event.get("headers", {}).items():
        key = key.upper().replace("-", "_")
        if key not in ("CONTENT_TYPE", "CONTENT_LENGTH"):
            key = f"HTTP_{key}"
        environ[key] = value

    # Add stage variables
    if "stageVariables" in event:
        environ["API_GATEWAY_STAGE_VARIABLES"] = json.dumps(event["stageVariables"])

    # Add request context
    if "requestContext" in event:
        environ["API_GATEWAY_REQUEST_CONTEXT"] = json.dumps(event["requestContext"])

    return environ


def lambda_handler(event: dict, context: object) -> dict:
    """Handle Lambda events from API Gateway v2.0 (HTTP API) with CORS and CSRF support.

    This is the main entry point for AWS Lambda. It handles:
    - API Gateway v2.0 (HTTP API) events
    - Direct Lambda invocations for database operations
    - CORS preflight requests

    Args:
        event: The Lambda event
        context: The Lambda context

    Returns:
        dict: Response in API Gateway v2.0 format
    """
    try:
        # Initialize context and log
        context = _initialize_context(context)
        request_id = getattr(context, "aws_request_id", "local")
        logger.info(f"Processing request {request_id}")

        # Get Flask app instance
        app = get_or_create_app()

        # Handle preflight CORS requests
        if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
            return _create_cors_response()

        # Handle direct Lambda invocations (e.g., for database operations)
        if "operation" in event:
            return _handle_direct_invocation(app, event)

        # Process the request through Flask
        return _process_http_request(app, event, context)

    except Exception as e:
        # Log the error and return a 500 response
        app.logger.exception("Error in lambda_handler")
        return _create_error_response(e, 500, context)


def _create_cors_response(status_code: int = 204) -> dict:
    """Create a CORS response for preflight requests.

    Args:
        status_code: HTTP status code to return

    Returns:
        dict: CORS response in API Gateway v2.0 format
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, X-CSRFToken, X-Requested-With",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "3600",
            "Vary": "Origin",
        },
        "body": "" if status_code == 204 else None,
        "isBase64Encoded": False,
    }


def _ensure_response_format(response: dict, app: Flask) -> dict:
    """Ensure the response is properly formatted with CORS and CSRF headers.

    Args:
        response: The response from the application
        app: Flask application instance

    Returns:
        dict: Formatted response in API Gateway v2.0 format
    """
    # Ensure response is a dictionary
    if not isinstance(response, dict):
        response = {"statusCode": 200, "body": str(response), "headers": {}}

    # Ensure required fields exist
    response.setdefault("statusCode", 200)
    response.setdefault("headers", {})
    response.setdefault("isBase64Encoded", False)

    # Add CSRF token if available (using Flask-WTF)
    if hasattr(app, "extensions") and "csrf" in app.extensions:
        csrf_token = generate_csrf()
        if csrf_token:
            response["headers"]["X-CSRFToken"] = csrf_token

    # Add CORS headers if not already set
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Expose-Headers": "X-CSRFToken",
        "Vary": "Origin",
    }

    for header, value in cors_headers.items():
        if header not in response["headers"]:
            response["headers"][header] = value

    return response


def _process_http_request(app: Flask, event: dict, context: object) -> dict:
    """Process an HTTP request from API Gateway v2.0 (HTTP API).

    This function handles API Gateway v2.0 events directly, processes the request
    through the Flask application, and adds necessary security headers.

    Args:
        app: The Flask application instance
        event: The Lambda event (v2.0 format)
        context: The Lambda context

    Returns:
        dict: The response to return to API Gateway
    """
    try:
        # Log the incoming event (redacting sensitive data)
        _log_event(event)

        # Convert API Gateway v2.0 event to WSGI environment
        environ = create_wsgi_environ(event, context)

        # Process the request through Flask
        with app.request_context(environ):
            # Dispatch the request and get the response
            response = app.full_dispatch_request()

            # Convert response to API Gateway format
            result = {
                "statusCode": response.status_code,
                "headers": dict(response.headers),
                "body": response.get_data(as_text=True),
                "isBase64Encoded": False,
            }

            # Ensure proper CORS and CSRF headers
            return _ensure_response_format(result, app)

    except Exception as e:
        logger.exception("Error processing HTTP request")
        error_response = _create_error_response(e, 500, context)
        return _ensure_response_format(error_response, app)


def main() -> None:
    """Run the application locally.

    This is the entry point for local development using `python wsgi.py`
    """
    # Get the Flask app instance first to ensure config is loaded
    app = get_or_create_app()

    # Configure host and port from environment or use defaults
    host = os.environ.get("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.environ.get("FLASK_RUN_PORT", "5000"))

    # Suppress Werkzeug logs below WARNING level
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    # Log startup information using the app's logger
    logger.info("Starting local development server at http://%s:%s", host, port)
    logger.info("Debug mode: %s", "on" if app.debug else "off")

    # Run the application with reloader disabled to prevent duplicate logs
    app.run(host=host, port=port, debug=app.debug, use_reloader=False)


if __name__ == "__main__":
    # Run the application directly for local development
    main()
