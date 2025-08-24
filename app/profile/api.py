"""User Profile API Routes."""

from typing import Any, Dict, Tuple, Union

from flask import request
from flask_login import current_user, login_required
from marshmallow import ValidationError

from app.profile import services

from . import bp
from .schemas import PasswordChangeSchema, UserSchema

user_schema = UserSchema()
password_change_schema = PasswordChangeSchema()

# Type aliases
JsonResponse = Union[Dict[str, Any], Tuple[Dict[str, Any], int]]


def _make_response(data: Dict[str, Any], status: int = 200) -> Tuple[Dict[str, Any], int]:
    """Helper to create a consistent response format.

    Args:
        data: The response data
        status: HTTP status code

    Returns:
        A tuple of (response_data, status_code)
    """
    return data, status


@bp.route("/profile", methods=["GET"])
@login_required
def get_profile() -> Tuple[Dict[str, Any], int]:
    """Get the current user's profile.

    Returns:
        Tuple containing the user's profile data and status code
    """
    return _make_response(user_schema.dump(current_user))


@bp.route("/profile", methods=["PUT"])
@login_required
def update_profile() -> Tuple[Dict[str, Any], int]:
    """Update the current user's profile.

    Returns:
        Tuple containing the updated profile data and status code
    """
    try:
        data: Dict[str, Any] = user_schema.load(request.get_json() or {})
    except ValidationError as err:
        return _make_response({"error": "Validation failed", "details": err.messages}, 400)

    updated_user = services.update_user_profile(current_user, data)
    return _make_response(user_schema.dump(updated_user))


@bp.route("/profile/change-password", methods=["POST"])
@login_required
def change_password() -> Tuple[Dict[str, Any], int]:
    """Change the current user's password.

    Returns:
        Tuple containing the status message and status code
    """
    try:
        data: Dict[str, str] = password_change_schema.load(request.get_json() or {})
    except ValidationError as err:
        return _make_response({"error": "Validation failed", "details": err.messages}, 400)

    old_password: str = data.get("old_password", "")
    new_password: str = data.get("new_password", "")
    success: bool
    message: str
    success, message = services.change_user_password(current_user, old_password, new_password)

    if success:
        return _make_response({"status": "success", "message": message})
    return _make_response({"status": "error", "message": message}, 400)
