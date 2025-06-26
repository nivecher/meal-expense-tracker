"""API Gateway event handler for the Meal Expense Tracker application."""

from typing import Any, Dict

from flask import Flask, Response

from app.core.exceptions import AppError


def _get_nested(dct: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Safely get nested dictionary values."""
    for key in keys:
        try:
            dct = dct[key]
        except (KeyError, TypeError):
            return default
    return dct


def _build_request_context(
    request_context: Dict[str, Any], headers: Dict[str, str], http_method: str, path: str
) -> Dict[str, Any]:
    """Build v1.0 compatible request context."""
    return {
        "httpMethod": http_method,
        "path": path,
        "requestContext": {
            "httpMethod": http_method,
            "path": path,
            "requestId": request_context.get("requestId", ""),
            "accountId": request_context.get("accountId", ""),
            "apiId": request_context.get("apiId", ""),
            "stage": request_context.get("stage", "$default"),
            "domainPrefix": request_context.get("domainName", "").split(".")[0],
            "requestTime": request_context.get("time", ""),
            "requestTimeEpoch": request_context.get("timeEpoch", 0),
            "identity": {"sourceIp": _get_nested(request_context, "http", "sourceIp") or ""},
        },
    }


def handle_api_gateway_event(app: Flask, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle an API Gateway event.

    Args:
        app: The Flask application
        event: The API Gateway event
        context: The Lambda context

    Returns:
        API Gateway response
    """
    try:
        # Normalize the event
        normalized_event = normalize_api_gateway_event(event)

        # Process the request using aws_wsgi
        response = aws_wsgi.response(
            app, normalized_event, context, base64_content_types={"image/png", "image/jpeg", "application/octet-stream"}
        )

        return response
    except Exception as e:
        app.logger.exception("Error processing API Gateway event")
        if isinstance(e, AppError):
            return e.to_dict()
        return {
            "statusCode": 500,
            "body": "Internal Server Error",
            "isBase64Encoded": False,
        }


def _transform_v2_to_v1_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Transform API Gateway v2.0 event to v1.0 format.

    Args:
        event: API Gateway v2.0 event

    Returns:
        dict: Transformed event in v1.0 format
    """
    request_context = event.get("requestContext", {})
    http = request_context.get("http", {})

    # Build the base event
    transformed = {
        "httpMethod": http.get("method", ""),
        "path": event.get("rawPath", ""),
        "resource": event.get("routeKey", ""),
        "requestContext": {
            "requestId": request_context.get("requestId", ""),
            "httpMethod": http.get("method", ""),
            "path": event.get("rawPath", ""),
            "accountId": request_context.get("accountId", ""),
            "apiId": request_context.get("apiId", ""),
            "stage": request_context.get("stage", "$default"),
            "requestTime": request_context.get("time", ""),
            "requestTimeEpoch": request_context.get("timeEpoch", 0),
            "identity": {
                "sourceIp": request_context.get("http", {}).get("sourceIp", ""),
                "userAgent": request_context.get("http", {}).get("userAgent", ""),
            },
        },
        "headers": event.get("headers", {}),
        "queryStringParameters": event.get("queryStringParameters") or {},
        "pathParameters": event.get("pathParameters") or {},
        "body": event.get("body"),
        "isBase64Encoded": event.get("isBase64Encoded", False),
    }

    # Add multiValueHeaders if present
    if "multiValueHeaders" in event:
        transformed["multiValueHeaders"] = event["multiValueHeaders"]
    else:
        transformed["multiValueHeaders"] = {k: [v] for k, v in event.get("headers", {}).items()}

    # Add multiValueQueryStringParameters if present
    if "multiValueQueryStringParameters" in event:
        transformed["multiValueQueryStringParameters"] = event["multiValueQueryStringParameters"]
    elif "queryStringParameters" in event:
        transformed["multiValueQueryStringParameters"] = {k: [v] for k, v in event["queryStringParameters"].items()}

    return transformed
