"""WSGI entry point for the Meal Expense Tracker application."""

import os
import sys
import logging
import json
import base64
from typing import Dict, Any, Tuple, Optional
from flask.testing import FlaskClient
from werkzeug.test import TestResponse
from app import create_app

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Initialize the Flask application
app = create_app()


def parse_http_v2_event(event: Dict[str, Any]) -> Tuple[str, str, Dict, Dict, str]:
    """Parse API Gateway HTTP API v2 event format."""
    method = event["requestContext"]["http"]["method"]
    path = event["rawPath"]
    query_params = event.get("queryStringParameters", {}) or {}
    headers = {k.lower(): v for k, v in event.get("headers", {}).items()}
    body = event.get("body", "")

    if event.get("isBase64Encoded", False) and body:
        body = base64.b64decode(body).decode("utf-8")

    return method, path, query_params, headers, body


def parse_rest_api_event(event: Dict[str, Any]) -> Tuple[str, str, Dict, Dict, str]:
    """Parse API Gateway REST API event format."""
    method = event["httpMethod"]
    path = event["path"]
    query_params = event.get("queryStringParameters", {}) or {}
    headers = {k.lower(): v for k, v in event.get("headers", {}).items()}
    body = event.get("body", "")

    if event.get("isBase64Encoded", False) and body:
        body = base64.b64decode(body).decode("utf-8")

    return method, path, query_params, headers, body


def process_request(
    client: FlaskClient,
    method: str,
    path: str,
    query_params: Dict,
    headers: Dict,
    body: str,
) -> TestResponse:
    """Process the HTTP request using Flask test client."""
    headers_list = [(k, v) for k, v in headers.items()]
    return client.open(
        method=method,
        path=path,
        query_string=query_params,
        data=body,
        headers=headers_list,
        content_type=headers.get("content-type"),
    )


def format_response(response: TestResponse) -> Dict[str, Any]:
    """Format the Flask response for API Gateway."""
    response_body = response.get_data(as_text=True)
    content_type = response.content_type or ""

    # Try to parse as JSON if content type is JSON
    if "application/json" in content_type and response_body:
        try:
            response_body = json.loads(response_body)
        except json.JSONDecodeError:
            pass

    # Format response body
    body_content = (
        json.dumps(response_body, default=str)
        if isinstance(response_body, (dict, list))
        else response_body or ""
    )

    # Prepare response headers
    response_headers = dict(response.headers)
    if "content-length" in response_headers:
        response_headers["Content-Length"] = str(len(body_content))

    return {
        "statusCode": response.status_code,
        "headers": response_headers,
        "body": body_content,
    }


def handle_unknown_event(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle unknown event format by trying aws-wsgi as fallback."""
    try:
        import aws_wsgi

        return aws_wsgi.response(app, event, context)
    except ImportError:
        logger.error("aws-wsgi not available for fallback")
        raise
    except Exception as e:
        logger.error("Error in aws-wsgi fallback: %s", str(e), exc_info=True)
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler function.
    Handles both API Gateway HTTP API v2 and REST API events.
    """
    try:
        logger.info("Received event: %s", json.dumps(event, indent=2))

        # Parse the event based on its format
        if event.get("version") == "2.0" and "requestContext" in event:
            method, path, query_params, headers, body = parse_http_v2_event(event)
        elif "httpMethod" in event:
            method, path, query_params, headers, body = parse_rest_api_event(event)
        else:
            return handle_unknown_event(event, context)

        # Process the request
        with app.test_client() as client:
            response = process_request(
                client, method, path, query_params, headers, body
            )
            return format_response(response)

    except Exception as e:
        logger.error("Error processing request: %s", str(e), exc_info=True)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Internal Server Error"}),
        }


# For AWS Lambda
if os.environ.get("AWS_EXECUTION_ENV"):
    handler = lambda_handler


# For local development
if __name__ == "__main__":
    logger.info("Starting application locally...")
    try:
        port = int(os.environ.get("PORT", 5000))
        app.run(debug=True, host="0.0.0.0", port=port)
    except Exception as e:
        logger.error("Failed to run application: %s", str(e), exc_info=True)
        raise
