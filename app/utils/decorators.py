"""Custom decorators for the application."""

# Standard library imports
from functools import wraps
from typing import Any, Callable, TypeVar, cast

# Third-party imports
from flask import current_app, flash, jsonify, redirect, request, url_for
from flask.typing import ResponseReturnValue
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

# Type variable for function type
F = TypeVar("F", bound=Callable[..., Any])


def db_transaction(
    success_message: str = "",
    error_message: str = "An error occurred. Please try again.",
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
            from app.extensions import db

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


def admin_required(func: F) -> F:
    """Decorator to ensure the current user is an admin.

    This decorator should be used after the @login_required decorator.
    """

    @wraps(func)
    def decorated_view(*args: Any, **kwargs: Any) -> ResponseReturnValue:
        if not current_user.is_admin:
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for("main.index"))
        return func(*args, **kwargs)

    return cast(F, decorated_view)


def confirm_required(func: F) -> F:
    """Decorator to ensure the current user has confirmed their email.

    This decorator should be used after the @login_required decorator.
    """

    @wraps(func)
    def decorated_view(*args: Any, **kwargs: Any) -> ResponseReturnValue:
        if not current_user.confirmed:
            flash("Please confirm your account to access this page.", "warning")
            return redirect(url_for("auth.unconfirmed"))
        return func(*args, **kwargs)

    return cast(F, decorated_view)
