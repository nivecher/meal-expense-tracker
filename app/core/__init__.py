"""Core functionality for the Meal Expense Tracker application.

This package contains the core components of the application, including:
- Exception classes
- Request handlers
- Utility functions
- Common utilities
"""

from .exceptions import (
    AppError,
    DatabaseError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from .handlers.api_gateway import handle_api_gateway_event
from .handlers.lambda_handlers import handle_lambda_event
from .utils.logging import StructuredLogger, configure_logging, get_logger

__all__ = [
    # Core functionality
    "handle_lambda_event",
    "handle_api_gateway_event",
    # Logging
    "configure_logging",
    "get_logger",
    "StructuredLogger",
    # Exceptions
    "AppError",
    "ValidationError",
    "DatabaseError",
    "NotFoundError",
    "UnauthorizedError",
    "ForbiddenError",
]
