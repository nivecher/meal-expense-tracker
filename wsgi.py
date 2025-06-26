"""
WSGI entry point for the Meal Expense Tracker application.

This module serves as the entry point for both local development and
AWS Lambda deployment. It handles application initialization,
request/response transformations, environment configuration,
and database operations.
"""

import json
import os
import sys
import traceback
from typing import Any, Dict, Optional, Tuple

# Third-party imports
from werkzeug.wsgi import ClosingIterator

# Local application imports
from app import create_app
from app.core import configure_logging, get_logger
from migrate_db import handle_database_operation

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Create Flask application
app = create_app()


def _get_default_headers() -> Dict[str, str]:
    """Return default CORS and content type headers."""
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Requested-With",
        "Access-Control-Max-Age": "3600",
    }


def _get_wsgi_environ(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Convert API Gateway event to WSGI environment.

    Args:
        event: API Gateway Lambda event
        context: Lambda context object

    Returns:
        WSGI environment dictionary
    """
    # Default environment
    environ = {
        "REQUEST_METHOD": event.get("httpMethod", "GET"),
        "SCRIPT_NAME": "",
        "PATH_INFO": event.get("path", "/"),
        "QUERY_STRING": "&".join(f"{k}={v}" for k, v in (event.get("queryStringParameters") or {}).items()) or "",
        "REMOTE_ADDR": event.get("requestContext", {}).get("identity", {}).get("sourceIp", "127.0.0.1"),
        "CONTENT_LENGTH": str(len(event.get("body", "") or "")),
        "HTTP": "on",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.version": (1, 0),
        "wsgi.input": None,
        "wsgi.errors": sys.stderr,
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
    }

    # Add headers
    for key, value in (event.get("headers") or {}).items():
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


def _handle_lambda_event(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle Lambda event from API Gateway.

    Args:
        event: Lambda event from API Gateway
        context: Lambda context object

    Returns:
        API Gateway compatible response
    """
    request_id = context.aws_request_id if context else "local"
    logger.info(
        {
            "message": "Processing request",
            "request_id": request_id,
            "http_method": event.get("httpMethod"),
            "path": event.get("path"),
            "query_params": event.get("queryStringParameters", {}),
        }
    )

    # Create WSGI environment
    environ = _get_wsgi_environ(event, context)

    # Create response variables
    response_headers = {}
    response_body = []
    status_code = 200

    # Define response start callback
    def start_response(status, headers, exc_info=None):
        nonlocal status_code
        status_code = int(status.split()[0])
        for header, value in headers:
            response_headers[header] = value
        return response_body.append

    try:
        # Create WSGI iterator
        wsgi_input = None
        if event.get("body"):
            if event.get("isBase64Encoded", False):
                import base64

                wsgi_input = [base64.b64decode(event["body"])]
            else:
                wsgi_input = [event["body"].encode("utf-8")]

        environ["wsgi.input"] = wsgi_input[0] if wsgi_input else None

        # Process request
        result = app(environ, start_response)
        response_body = []

        # Handle streaming responses
        if isinstance(result, ClosingIterator):
            response_body = [b"".join(result)]
        else:
            response_body = [b"".join(result)]

        # Ensure CORS headers are set
        headers = {**_get_default_headers(), **response_headers}

        # Build response
        return {
            "statusCode": status_code,
            "headers": headers,
            "body": response_body[0].decode("utf-8") if response_body else "",
            "isBase64Encoded": False,
        }

    except Exception as e:
        logger.error(
            {
                "message": "Error processing request",
                "request_id": request_id,
                "error": str(e),
                "stack_trace": traceback.format_exc(),
            }
        )

        return {
            "statusCode": 500,
            "headers": _get_default_headers(),
            "body": json.dumps(
                {"error": "Internal Server Error", "request_id": request_id, "message": "An unexpected error occurred."}
            ),
            "isBase64Encoded": False,
        }


def _handle_database_operation(operation: str, **kwargs) -> Tuple[int, Dict[str, Any]]:
    """Handle database operations by delegating to migrate_db module.

    Args:
        operation: Operation to perform ('migrate', 'upgrade', 'downgrade', 'show', 'history', 'current')
        **kwargs: Additional operation-specific arguments

    Returns:
        tuple: (status_code, response_dict)
    """
    return handle_database_operation(operation, **kwargs)


def _handle_direct_invocation(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle direct Lambda invocation (not from API Gateway)."""
    request_id = context.aws_request_id if context else "local"
    logger.info(
        {
            "message": "Direct Lambda invocation",
            "request_id": request_id,
            "event_type": event.get("detail-type", "direct"),
        }
    )

    # Handle database operations if specified in the event
    if "db_operation" in event:
        operation = event["db_operation"]
        logger.info(f"Processing database operation: {operation}")

        # Extract operation arguments
        kwargs = {k: v for k, v in event.items() if k not in ["db_operation", "request_id"]}

        status_code, result = _handle_database_operation(operation, **kwargs)

        return {
            "statusCode": status_code,
            "headers": _get_default_headers(),
            "body": json.dumps({"operation": operation, "request_id": request_id, **result}),
        }

    # Default response for other direct invocations
    return {
        "statusCode": 200,
        "headers": _get_default_headers(),
        "body": json.dumps(
            {
                "message": "Direct invocation successful",
                "request_id": request_id,
                "available_operations": ["migrate", "upgrade", "downgrade", "show", "history", "current"],
            }
        ),
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda handler function.

    This is the entry point for AWS Lambda. It handles:
    - API Gateway events (both REST and HTTP APIs)
    - Direct Lambda invocations
    - Scheduled events
    - Database operations (migrations, etc.)
    - Other AWS event sources

    For database operations, you can invoke the Lambda directly with an event like:
    {
        "db_operation": "migrate",
        "message": "Initial migration"
    }

    Available operations:
    - migrate [message]: Create a new migration
    - upgrade [revision]: Upgrade to a later version (default: 'head')
    - downgrade <revision>: Revert to a previous version
    - show: Show the current revision
    - history: Show the revision history
    - current: Show the current revision

    Args:
        event: Lambda event
        context: Lambda context object

    Returns:
        Response for API Gateway or direct invocation
    """
    try:
        # Check if this is a direct database operation
        if isinstance(event, dict) and "db_operation" in event:
            return _handle_direct_invocation(event, context)

        # Check if this is an API Gateway event
        if "httpMethod" in event and "path" in event:
            # Handle database operations through API if needed
            if event.get("path") == "/_db" and event.get("httpMethod") == "POST":
                try:
                    body = json.loads(event.get("body", "{}"))
                    if "db_operation" in body:
                        return _handle_direct_invocation(body, context)
                except json.JSONDecodeError:
                    pass
            return _handle_lambda_event(event, context)

        # Handle direct invocation for other cases
        return _handle_direct_invocation(event, context)

    except Exception as e:
        request_id = context.aws_request_id if context else "unknown"
        logger.error(
            {
                "message": "Unhandled exception in lambda_handler",
                "request_id": request_id,
                "error": str(e),
                "stack_trace": traceback.format_exc(),
                "event": event,
            }
        )

        return {
            "statusCode": 500,
            "headers": _get_default_headers(),
            "body": json.dumps(
                {
                    "error": "Internal Server Error",
                    "request_id": request_id,
                    "message": "An unhandled exception occurred.",
                }
            ),
            "isBase64Encoded": False,
        }


def _process_headers(headers: Optional[Dict[str, str]]) -> Dict[str, str]:
    """Process and normalize headers from API Gateway event.

    Args:
        headers: Headers from API Gateway event

    Returns:
        Normalized headers dictionary
    """
    if not headers:
        return {}

    # Convert all header keys to lowercase for case-insensitive comparison
    return {k.lower(): v for k, v in headers.items()}


def _normalize_http_api_v2_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize HTTP API v2.0 event to v1.0 format.

    Args:
        event: The API Gateway v2.0 event

    Returns:
        dict: Normalized event in v1.0 format
    """
    try:
        normalized = event.copy()
        request_context = normalized.get("requestContext", {})
        http_context = request_context.get("http", {})

        http_method = http_context.get("method", "GET").upper()
        path = normalized.get("rawPath", "/")
        headers = _process_headers(normalized.get("headers"))

        # Build request context in v1.0 format
        request_context_v1 = {
            "accountId": request_context.get("accountId", ""),
            "apiId": request_context.get("apiId"),
            "httpMethod": http_method,
            "identity": {
                "sourceIp": http_context.get("sourceIp"),
                "userAgent": http_context.get("userAgent"),
            },
            "path": path,
            "requestId": request_context.get("requestId"),
            "requestTime": request_context.get("time"),
            "resourcePath": normalized.get("routeKey", "$default"),
            "stage": request_context.get("stage"),
        }

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

        logger.debug("Normalized event: %s", normalized)
        return normalized

    except Exception as e:
        logger.error("Error normalizing API Gateway v2.0 event: %s", str(e), exc_info=True)
        raise


def main() -> None:
    """Run the application locally.

    This is the entry point for local development using `python wsgi.py`
    """
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

    # Log startup information
    logger.info("Starting development server on http://%s:%s", host, port)
    logger.info("Debug mode: %s", "ON" if debug else "OFF")

    # Run the Flask development server
    app.run(host=host, port=port, debug=debug, use_reloader=debug)


if __name__ == "__main__":
    # Run the application directly for local development
    main()
