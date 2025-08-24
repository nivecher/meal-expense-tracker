"""API Authentication Routes.

This module handles all authentication-related API endpoints including login and logout.
"""

from typing import Any, Dict, Tuple

from flask import current_app, jsonify, request
from flask_limiter import RateLimitExceeded
from flask_login import current_user, login_user, logout_user
from werkzeug.security import check_password_hash

from app.auth.models import User
from app.extensions import limiter

from . import bp


@bp.route("/auth/login", methods=["POST"])
@limiter.limit("5 per minute")  # Rate limiting to prevent brute force
@limiter.limit("100 per day")  # Daily limit per IP
def api_login() -> Tuple[Dict[str, Any], int]:
    """Handle user login via API.

    Request JSON:
        username (str): The user's username
        password (str): The user's password

    Returns:
        JSON response with status and message
    """
    try:
        data = request.get_json()
        # Input validation
        if not data or "username" not in data or "password" not in data:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "Username and password are required.",
                    }
                ),
                400,
            )

        user = User.query.filter_by(username=data["username"]).first()

        # Debug logging
        current_app.logger.debug(f'Login attempt for user: {data["username"]}')
        current_app.logger.debug(f"User found: {user is not None}")
        if user:
            current_app.logger.debug(f"User active: {user.is_active}")
            current_app.logger.debug(f"Password hash exists: {bool(user.password_hash)}")
            password_matches = check_password_hash(user.password_hash, data["password"])
            current_app.logger.debug(f"Password matches: {password_matches}")

        # Prevent timing attacks with constant-time comparison
        if not user or not check_password_hash(user.password_hash, data["password"]):
            current_app.logger.warning(f'Failed login attempt for username: {data["username"]}')
            return (
                jsonify({"status": "error", "message": "Invalid username or password."}),
                401,
            )

        login_user(user, remember=True)
        current_app.logger.info(f"User {user.username} logged in successfully")
        return jsonify(
            {
                "status": "success",
                "message": "Logged in successfully.",
                "user": {"id": user.id, "username": user.username, "email": user.email},
            }
        )

    except RateLimitExceeded:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Too many login attempts. Please try again later.",
                }
            ),
            429,
        )
    except Exception as e:
        current_app.logger.error(f"Login error: {str(e)}")
        return (
            jsonify({"status": "error", "message": "An error occurred during login."}),
            500,
        )


@bp.route("/auth/logout", methods=["POST"])
@limiter.limit("10 per minute")  # Rate limiting for logout as well
def api_logout():
    """Handle user logout via API.

    Returns:
        JSON response with status and message
    """
    if not current_user.is_authenticated:
        return (
            jsonify({"status": "error", "message": "No user is currently logged in."}),
            400,
        )

    try:
        username = current_user.username
        logout_user()
        current_app.logger.info(f"User {username} logged out successfully")
        return jsonify({"status": "success", "message": "Logged out successfully."})
    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        return (
            jsonify({"status": "error", "message": "An error occurred during logout."}),
            500,
        )
