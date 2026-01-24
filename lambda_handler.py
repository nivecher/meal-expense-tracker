"""AWS Lambda handler with enhanced error handling and structured logging.

This module provides a Lambda handler that wraps the Flask application
with comprehensive error handling, structured logging, and CloudWatch
integration for easier debugging.
"""

import json
import logging
import os
import sys
import traceback
from typing import Any, cast

# Try to import AWS X-Ray SDK for tracing
try:
    from aws_xray_sdk.core import patch_all, xray_recorder

    XRAY_AVAILABLE = True
    # Patch libraries for X-Ray tracing
    patch_all()
except ImportError:
    XRAY_AVAILABLE = False
    xray_recorder = None

# Configure structured logging for CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Create a structured formatter for JSON logs
class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured CloudWatch logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add extra fields from record
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "lambda_request_id"):
            log_data["lambda_request_id"] = record.lambda_request_id
        if hasattr(record, "path"):
            log_data["path"] = record.path
        if hasattr(record, "method"):
            log_data["method"] = record.method
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        return json.dumps(log_data)


# Configure handler with structured formatter
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(StructuredFormatter())
logger.addHandler(handler)

# Prevent duplicate logs
logger.propagate = False


def _extract_request_context(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Extract request context from Lambda event and context."""
    request_context = {
        "lambda_request_id": getattr(context, "request_id", None) if context else None,
        "function_name": getattr(context, "function_name", None) if context else None,
        "function_version": getattr(context, "function_version", None) if context else None,
        "memory_limit_mb": getattr(context, "memory_limit_in_mb", None) if context else None,
        "remaining_time_ms": getattr(context, "get_remaining_time_in_millis", lambda: None)(),
    }

    # Extract API Gateway request context
    if "requestContext" in event:
        api_context = event["requestContext"]
        request_context.update(
            {
                "api_request_id": api_context.get("requestId"),
                "api_stage": api_context.get("stage"),
                "api_path": api_context.get("path"),
                "api_method": api_context.get("httpMethod") or api_context.get("http", {}).get("method"),
                "api_source_ip": api_context.get("identity", {}).get("sourceIp")
                or api_context.get("http", {}).get("sourceIp"),
                "api_user_agent": api_context.get("identity", {}).get("userAgent")
                or api_context.get("http", {}).get("userAgent"),
            }
        )

    # Extract X-Ray trace ID if available
    trace_id = os.environ.get("_X_AMZN_TRACE_ID")
    if trace_id:
        request_context["xray_trace_id"] = trace_id.split(";")[0] if ";" in trace_id else trace_id

    return request_context


def _log_request_start(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Log the start of a request with context."""
    request_context = _extract_request_context(event, context)

    path = event.get("path", event.get("rawPath", "/"))
    method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method", "UNKNOWN")

    logger.info(
        "Lambda request started",
        extra={
            "request_id": request_context.get("api_request_id"),
            "lambda_request_id": request_context.get("lambda_request_id"),
            "path": path,
            "method": method,
            "source_ip": request_context.get("api_source_ip"),
            "user_agent": request_context.get("api_user_agent"),
            "xray_trace_id": request_context.get("xray_trace_id"),
        },
    )

    return request_context


def _log_request_end(
    request_context: dict[str, Any],
    status_code: int,
    duration_ms: float,
    error: Exception | None = None,
) -> None:
    """Log the end of a request with results."""
    extra = {
        "request_id": request_context.get("api_request_id"),
        "lambda_request_id": request_context.get("lambda_request_id"),
        "path": request_context.get("api_path"),
        "method": request_context.get("api_method"),
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "xray_trace_id": request_context.get("xray_trace_id"),
    }

    if error:
        logger.error(
            f"Lambda request failed: {str(error)}",
            exc_info=error,
            extra=extra,
        )
    elif status_code >= 500:
        logger.error(
            f"Lambda request returned error status: {status_code}",
            extra=extra,
        )
    elif status_code >= 400:
        logger.warning(
            f"Lambda request returned client error: {status_code}",
            extra=extra,
        )
    else:
        logger.info(
            "Lambda request completed successfully",
            extra=extra,
        )


def _create_error_response(
    status_code: int,
    error_message: str,
    error_type: str | None = None,
    traceback_str: str | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Create a standardized error response."""
    response = {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "X-Request-ID": request_id or "unknown",
        },
        "body": json.dumps(
            {
                "error": error_message,
                "error_type": error_type or "InternalServerError",
                "request_id": request_id,
            }
        ),
        "isBase64Encoded": False,
    }

    # Include traceback in non-production environments
    if traceback_str and os.environ.get("ENVIRONMENT", "prod") != "prod":
        body_str = response["body"]
        if isinstance(body_str, str):
            error_body = json.loads(body_str)
            error_body["traceback"] = traceback_str.split("\n")
            response["body"] = json.dumps(error_body)

    return response


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda handler with enhanced error handling and logging.

    Args:
        event: Lambda event dictionary containing API Gateway request data
        context: Lambda context object

    Returns:
        API Gateway compatible response dictionary
    """
    import time

    start_time = time.time()
    request_context = _log_request_start(event, context)
    request_id = request_context.get("api_request_id") or request_context.get("lambda_request_id")

    # Start X-Ray segment if available
    if XRAY_AVAILABLE and xray_recorder:
        segment = xray_recorder.begin_segment(name="lambda_handler")
        segment.put_metadata("request_context", request_context)
        segment.put_metadata("event", event)
        segment.put_annotation("function_name", request_context.get("function_name", "unknown"))
        segment.put_annotation("path", request_context.get("api_path", "/"))
        segment.put_annotation("method", request_context.get("api_method", "UNKNOWN"))
    else:
        segment = None

    try:
        # Run initialization (including migrations) once per container
        try:
            from lambda_init import initialize_lambda

            init_result = initialize_lambda()
            if not init_result.get("success"):
                logger.warning(f"Lambda initialization reported issues: {init_result.get('message')}")
        except Exception as init_error:
            logger.warning(f"Lambda initialization failed: {init_error}")

        # Use WSGI adapter directly (Mangum has compatibility issues with Flask)
        # Mangum tries to use Flask as ASGI but Flask is WSGI-only
        from wsgi import application

        # Handle admin operations (invoked via Lambda payload)
        if event.get("admin_operation"):
            from app.admin.lambda_admin import handle_admin_request

            admin_response = handle_admin_request(application, event)
            duration_ms = (time.time() - start_time) * 1000
            status_code = admin_response.get("statusCode", 200)
            _log_request_end(request_context, status_code, duration_ms)

            if segment:
                segment.put_annotation("status_code", status_code)
                segment.put_metadata("response", {"status_code": status_code, "duration_ms": duration_ms})
                xray_recorder.end_segment()

            return admin_response

        response: dict[str, Any]
        import base64
        from io import BytesIO

        path = event.get("rawPath", "/")
        method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
        query_string = event.get("rawQueryString", "")
        headers = event.get("headers", {})
        body = event.get("body", "")

        # Handle cookies - HTTP API v2 may pass cookies in array or Cookie header
        cookies = event.get("cookies", [])
        # Check for Cookie header (case-insensitive)
        has_cookie_header = any(key.lower() == "cookie" for key in headers.keys())
        if cookies and not has_cookie_header:
            # Convert cookies array to Cookie header format
            cookie_header = "; ".join(cookies)
            headers["cookie"] = cookie_header

        # Handle body
        # API Gateway may base64 encode binary data (like multipart/form-data with files)
        # Check both lowercase and original case for Content-Type (API Gateway may normalize headers)
        content_type = headers.get("content-type", headers.get("Content-Type", headers.get("CONTENT-TYPE", "")))
        is_multipart = "multipart/form-data" in content_type.lower() if content_type else False

        if body and event.get("isBase64Encoded", False):
            body_bytes = base64.b64decode(body)
        elif body and is_multipart and isinstance(body, str):
            # For multipart/form-data, API Gateway might send as base64 string even if not marked
            # Try to decode if it looks like base64
            try:
                body_bytes = base64.b64decode(body)
            except Exception:
                # Not base64, treat as regular string
                body_bytes = body.encode("utf-8")
        elif body:
            body_bytes = body.encode("utf-8") if isinstance(body, str) else body
        else:
            body_bytes = b""

        # Extract host from headers for proper cookie domain handling
        host = headers.get("host", headers.get("Host", "lambda"))
        # Remove port if present (e.g., "example.com:443" -> "example.com")
        if ":" in host:
            host = host.split(":")[0]

        # Create WSGI environment
        # Preserve original Content-Type for multipart/form-data (includes boundary)
        content_type_header = headers.get("content-type", headers.get("Content-Type", ""))
        environ = {
            "REQUEST_METHOD": method,
            "PATH_INFO": path,
            "QUERY_STRING": query_string,
            "CONTENT_TYPE": content_type_header,  # Preserve original with boundary for multipart
            "CONTENT_LENGTH": str(len(body_bytes)),
            "SERVER_NAME": host,  # Use actual host for proper cookie domain
            "SERVER_PORT": "443",
            "HTTP_HOST": host,  # Also set HTTP_HOST header
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "https",
            "wsgi.input": BytesIO(body_bytes),
            "wsgi.errors": sys.stderr,
            "wsgi.multithread": False,
            "wsgi.multiprocess": False,
            "wsgi.run_once": False,
        }

        # Add headers (including Cookie header)
        # Note: CONTENT_TYPE and CONTENT_LENGTH are already set above
        for key, value in headers.items():
            key_upper = key.upper().replace("-", "_")
            # Skip CONTENT_TYPE and CONTENT_LENGTH (already set in environ)
            if key_upper not in ("CONTENT_TYPE", "CONTENT_LENGTH"):
                environ[f"HTTP_{key_upper}"] = value

        # Call Flask application
        with application.request_context(environ):
            flask_response = application.full_dispatch_request()

        # Convert to API Gateway format
        # Extract cookies from Set-Cookie headers for HTTP API v2
        response_headers = {}
        cookies = []
        cors_headers = {}
        for key, value in flask_response.headers:
            if key.lower() == "set-cookie":
                cookies.append(value)
            elif key.lower().startswith("access-control-"):
                cors_headers[key] = value
                response_headers[key] = value
            else:
                response_headers[key] = value

        response = {
            "statusCode": flask_response.status_code,
            "headers": response_headers,
            "body": flask_response.get_data(as_text=True),
            "isBase64Encoded": False,
        }

        # HTTP API v2 uses cookies array, not Set-Cookie headers
        if cookies:
            response["cookies"] = cookies

        # Calculate duration and log
        duration_ms = (time.time() - start_time) * 1000
        status_code = response.get("statusCode", 200)
        _log_request_end(request_context, status_code, duration_ms)

        # Add X-Ray annotations
        if segment:
            segment.put_annotation("status_code", status_code)
            segment.put_metadata("response", {"status_code": status_code, "duration_ms": duration_ms})
            xray_recorder.end_segment()

        return response

    except Exception as e:
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log the error with full context
        error_type = type(e).__name__
        error_message = str(e)
        traceback_str = traceback.format_exc()

        logger.error(
            f"Unhandled exception in Lambda handler: {error_type}: {error_message}",
            exc_info=True,
            extra={
                "request_id": request_id,
                "lambda_request_id": request_context.get("lambda_request_id"),
                "error_type": error_type,
                "error_message": error_message,
                "duration_ms": round(duration_ms, 2),
                "xray_trace_id": request_context.get("xray_trace_id"),
            },
        )

        # Log request completion with error
        _log_request_end(request_context, 500, duration_ms, error=e)

        # Add X-Ray error annotations
        if segment:
            segment.put_annotation("error", True)
            segment.put_annotation("error_type", error_type)
            segment.put_annotation("status_code", 500)
            segment.put_metadata(
                "error",
                {
                    "type": error_type,
                    "message": error_message,
                    "traceback": traceback_str.split("\n") if traceback_str else None,
                },
            )
            xray_recorder.end_segment()

        # Return error response
        return _create_error_response(
            status_code=500,
            error_message="Internal server error",
            error_type=error_type,
            traceback_str=traceback_str,
            request_id=request_id,
        )
