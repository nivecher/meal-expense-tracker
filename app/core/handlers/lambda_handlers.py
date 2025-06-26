"""Lambda event handlers for the Meal Expense Tracker application."""

import logging
from typing import Any, Dict

from flask import Flask

from app.core.exceptions import AppError

logger = logging.getLogger(__name__)


def handle_lambda_event(app: Flask, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle different types of Lambda events and route them to appropriate handlers.

    Args:
        app: Flask application instance
        event: Lambda event object
        context: Lambda context object

    Returns:
        dict: Response appropriate for the event type
    """
    try:
        # Handle API Gateway events
        if "httpMethod" in event or "requestContext" in event:
            from .api_gateway import handle_api_gateway_event

            return handle_api_gateway_event(app, event, context)

        # Handle direct invocations
        if "operation" in event:
            return handle_direct_invocation(app, event)

        # Handle scheduled events (CloudWatch Events/EventBridge)
        if event.get("source") == "aws.events" and event.get("detail-type") == "Scheduled Event":
            return handle_scheduled_event(event)

        # Handle S3 events
        if "Records" in event and len(event["Records"]) > 0 and "s3" in event["Records"][0]:
            return handle_s3_event(event)

        # Unsupported event type
        logger.warning("Unsupported event type: %s", event.get("source", "unknown"))
        return {
            "statusCode": 400,
            "body": "Unsupported event type",
        }

    except Exception as e:
        logger.exception("Error handling Lambda event")
        if isinstance(e, AppError):
            return e.to_dict()

        return {
            "statusCode": 500,
            "body": "Internal server error",
        }


def handle_direct_invocation(app: Flask, event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle direct Lambda invocations for database operations.

    Args:
        app: Flask application instance
        event: Direct invocation event

    Returns:
        dict: Response for the direct invocation
    """
    operation = event.get("operation")

    if operation == "migrate":
        return handle_database_operation(app, "migrate")
    elif operation == "reset":
        return handle_database_operation(app, "reset")
    elif operation == "status":
        return handle_database_operation(app, "status")
    else:
        return {
            "statusCode": 400,
            "body": f"Unsupported operation: {operation}",
        }


def handle_database_operation(app: Flask, operation: str) -> Dict[str, Any]:
    """Handle database operations like migrations and resets.

    Args:
        app: Flask application instance
        operation: Operation to perform ('migrate', 'reset', 'status')

    Returns:
        dict: Operation result with status code and message
    """
    with app.app_context():
        try:
            if operation == "migrate":
                from migrate_db import run_migrations

                run_migrations()
                return {"status": "success", "message": "Migrations completed successfully"}

            elif operation == "reset":
                from migrate_db import reset_database

                reset_database()
                return {"status": "success", "message": "Database reset completed"}

            elif operation == "status":
                from sqlalchemy import inspect

                from app.extensions import db

                inspector = inspect(db.engine)
                tables = inspector.get_table_names()
                return {
                    "status": "success",
                    "tables": tables,
                    "table_count": len(tables),
                }

            else:
                return {"status": "error", "message": f"Unknown operation: {operation}"}

        except Exception as e:
            logger.exception(f"Database operation '{operation}' failed")
            return {
                "status": "error",
                "message": f"Database operation failed: {str(e)}",
                "error": str(e),
            }


def handle_scheduled_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle scheduled events (CloudWatch Events/EventBridge).

    Args:
        event: Scheduled event

    Returns:
        dict: Response for the scheduled event
    """
    logger.info("Processing scheduled event: %s", event.get("id"))
    # Add your scheduled event handling logic here
    return {"status": "success", "message": "Scheduled event processed"}


def handle_s3_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle S3 events.

    Args:
        event: S3 event

    Returns:
        dict: Response for the S3 event
    """
    logger.info("Processing S3 event: %s", event.get("Records", [{}])[0].get("eventName"))
    # Add your S3 event handling logic here
    return {"status": "success", "message": "S3 event processed"}
