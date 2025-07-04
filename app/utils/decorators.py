"""Custom decorators for the application."""

# Standard library imports
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, cast

# Third-party imports
from flask import flash, jsonify, redirect, request, url_for
from flask.typing import ResponseReturnValue
from sqlalchemy.exc import SQLAlchemyError

# Type variable for function type
F = TypeVar("F", bound=Callable[..., Any])


def db_transaction(
    success_message: Optional[str] = None,
    error_message: Optional[str] = "An error occurred. Please try again.",
) -> Callable[[F], F]:
    """Decorator to handle database transactions with success/error messages.

    Args:
        success_message: Optional success message to flash
        error_message: Optional error message to flash

    Returns:
        Decorated function
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> ResponseReturnValue:
            from flask import current_app

            from app import db

            try:
                result = func(*args, **kwargs)
                db.session.commit()
                if success_message:
                    flash(success_message, "success")
                return result
            except SQLAlchemyError as e:
                db.session.rollback()
                current_app.logger.error(f"Database error in {func.__name__}: {str(e)}")
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return jsonify({"status": "error", "message": error_message}), 500
                flash(error_message, "danger")
                # Return to the previous page or home if referrer is not available
                return redirect(request.referrer or url_for("main.index"))
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error in {func.__name__}: {str(e)}")
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return jsonify({"status": "error", "message": error_message}), 500
                flash(error_message, "danger")
                return redirect(request.referrer or url_for("main.index"))

        return cast(F, wrapper)

    return decorator
