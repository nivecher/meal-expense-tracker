"""Lambda-based administration handler.

This module provides the Lambda function handler for remote administration operations.
It integrates with the existing Lambda handler to provide admin functionality.
"""

import json
import logging
from typing import Any, Dict

from flask import Flask

from .operations import AdminOperationRegistry

logger = logging.getLogger(__name__)


class LambdaAdminHandler:
    """Handler for Lambda-based admin operations."""

    def __init__(self, app: Flask):
        self.app = app

    def handle_admin_operation(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an admin operation from a Lambda event.

        Expected event format:
        {
            "admin_operation": "operation_name",
            "parameters": {
                "param1": "value1",
                "param2": "value2"
            },
            "confirm": true  # Required for operations that need confirmation
        }

        Returns:
            Dict with operation results in Lambda response format
        """
        try:
            operation_name = event.get("admin_operation")
            if not operation_name:
                return self._error_response("Missing 'admin_operation' in request")

            parameters = event.get("parameters", {})
            confirm = event.get("confirm", False)

            # Get the operation class
            operation_class = AdminOperationRegistry.get_operation(operation_name)
            if not operation_class:
                available_ops = list(AdminOperationRegistry.list_operations().keys())
                return self._error_response(
                    f"Unknown operation: {operation_name}. Available: {', '.join(available_ops)}"
                )

            # Create operation instance
            operation = operation_class()

            # Validate parameters
            validation = operation.validate_params(**parameters)
            if not validation["valid"]:
                return self._error_response(f"Invalid parameters: {', '.join(validation.get('errors', []))}")

            # Check confirmation requirement
            if operation.requires_confirmation and not confirm:
                return {
                    "statusCode": 200,
                    "body": json.dumps(
                        {
                            "success": False,
                            "message": f"Operation '{operation_name}' requires confirmation. Add 'confirm': true to proceed.",
                            "operation": operation_name,
                            "description": operation.description,
                            "requires_confirmation": True,
                        }
                    ),
                    "headers": {"Content-Type": "application/json"},
                }

            # Execute operation within Flask app context
            with self.app.app_context():
                result = operation.execute(**parameters)

            # Return formatted response
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {**result, "operation": operation_name, "timestamp": self._get_timestamp()},
                    default=str,
                ),
                "headers": {"Content-Type": "application/json"},
            }

        except Exception as e:
            logger.exception(f"Error in admin operation: {e}")
            return self._error_response(f"Internal error: {str(e)}")

    def list_available_operations(self) -> Dict[str, Any]:
        """List all available admin operations."""
        operations = AdminOperationRegistry.list_operations()

        # Get detailed info for each operation
        detailed_ops = {}
        for name, description in operations.items():
            operation_class = AdminOperationRegistry.get_operation(name)
            if operation_class:
                detailed_ops[name] = {
                    "description": description,
                    "requires_confirmation": operation_class.requires_confirmation,
                }

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "success": True,
                    "message": f"Available operations: {len(detailed_ops)}",
                    "data": {"operations": detailed_ops, "total_count": len(detailed_ops)},
                    "timestamp": self._get_timestamp(),
                }
            ),
            "headers": {"Content-Type": "application/json"},
        }

    def _error_response(self, message: str) -> Dict[str, Any]:
        """Create a standardized error response."""
        return {
            "statusCode": 400,
            "body": json.dumps({"success": False, "message": message, "timestamp": self._get_timestamp()}),
            "headers": {"Content-Type": "application/json"},
        }

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat()


def handle_admin_request(app: Flask, event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle admin requests in Lambda function.

    This function should be called from the main Lambda handler when an admin operation is detected.
    """
    admin_handler = LambdaAdminHandler(app)

    # Check if this is a list operations request
    if event.get("admin_operation") == "list_operations":
        return admin_handler.list_available_operations()

    # Handle specific admin operation
    return admin_handler.handle_admin_operation(event)
