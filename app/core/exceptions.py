"""Custom exceptions for the Meal Expense Tracker application."""

from http import HTTPStatus
from typing import Any, Dict, Optional

from flask import jsonify


class AppError(Exception):
    """Base exception class for application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to a dictionary for JSON response."""
        rv = dict(self.payload or {})
        rv["message"] = self.message
        rv["status"] = "error"
        return rv

    def to_response(self):
        """Convert exception to a Flask response."""
        response = jsonify(self.to_dict())
        response.status_code = self.status_code
        return response


class ValidationError(AppError):
    """Raised when input validation fails."""

    def __init__(self, message: str, errors: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            status_code=HTTPStatus.BAD_REQUEST,
            payload={"errors": errors or {}},
        )


class DatabaseError(AppError):
    """Raised for database-related errors."""

    def __init__(self, message: str, sql_error: Optional[str] = None) -> None:
        super().__init__(
            message=message,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            payload={"sql_error": sql_error} if sql_error else {},
        )


class NotFoundError(AppError):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str, id_: Any) -> None:
        super().__init__(
            message=f"{resource} with id {id_} not found",
            status_code=HTTPStatus.NOT_FOUND,
            payload={"resource": resource, "id": id_},
        )


class UnauthorizedError(AppError):
    """Raised when authentication is required or invalid."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(
            message=message,
            status_code=HTTPStatus.UNAUTHORIZED,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenError(AppError):
    """Raised when the user doesn't have permission to access a resource."""

    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(
            message=message,
            status_code=HTTPStatus.FORBIDDEN,
        )
