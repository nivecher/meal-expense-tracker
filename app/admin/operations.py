"""Remote administration operations.

Simplified admin operations using direct functions instead of complex class hierarchies.
Each operation returns a consistent interface for easy remote invocation.
"""

import logging
from typing import Any, Dict, Optional

from sqlalchemy.exc import SQLAlchemyError

from app.auth.models import User
from app.extensions import db

logger = logging.getLogger(__name__)


# Operation definitions: name -> (description, requires_confirmation, validate_func, execute_func)
OPERATIONS = {}


def register_operation(name: str, description: str, requires_confirmation: bool, validate_func, execute_func):
    """Register an admin operation."""
    OPERATIONS[name] = {
        "description": description,
        "requires_confirmation": requires_confirmation,
        "validate": validate_func,
        "execute": execute_func,
    }


def get_operation_info(name: str) -> Optional[Dict[str, Any]]:
    """Get operation information."""
    return OPERATIONS.get(name)


def list_operations() -> Dict[str, str]:
    """List all available operations with descriptions."""
    return {name: info["description"] for name, info in OPERATIONS.items()}


# Register all operations
register_operation(
    "list_users",
    "List all users in the system with optional filtering",
    False,
    lambda **kwargs: _validate_list_users(**kwargs),
    lambda **kwargs: _execute_list_users(**kwargs),
)

register_operation(
    "create_user",
    "Create a new user with specified credentials",
    True,
    lambda **kwargs: _validate_create_user(**kwargs),
    lambda **kwargs: _execute_create_user(**kwargs),
)


def _validate_list_users(**kwargs) -> Dict[str, Any]:
    """Validate list users parameters."""
    errors = []

    admin_only = kwargs.get("admin_only", False)
    if not isinstance(admin_only, bool):
        errors.append("admin_only must be a boolean")

    limit = kwargs.get("limit", 100)
    if not isinstance(limit, int) or limit < 1 or limit > 1000:
        errors.append("limit must be an integer between 1 and 1000")

    return {"valid": len(errors) == 0, "errors": errors}


def _execute_list_users(**kwargs) -> Dict[str, Any]:
    """Execute list users operation."""
    try:
        admin_only = kwargs.get("admin_only", False)
        limit = kwargs.get("limit", 100)

        query = User.query
        if admin_only:
            query = query.filter_by(is_admin=True)

        users = query.limit(limit).all()

        user_data = []
        for user in users:
            user_data.append(
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_admin": getattr(user, "is_admin", False),
                    "is_active": getattr(user, "is_active", True),
                    "created_at": getattr(user, "created_at", None),
                    "last_login": getattr(user, "last_login", None),
                }
            )

        return {
            "success": True,
            "message": f"Retrieved {len(user_data)} users",
            "data": {
                "users": user_data,
                "total_count": len(user_data),
                "filtered": {"admin_only": admin_only},
                "limit_applied": limit,
            },
        }

    except Exception as e:
        logger.exception(f"Error listing users: {e}")
        return {"success": False, "message": f"Failed to list users: {str(e)}"}


def _validate_create_user(**kwargs) -> Dict[str, Any]:
    """Validate create user parameters."""
    errors = []

    username = kwargs.get("username", "").strip()
    if not username or len(username) < 3:
        errors.append("username must be at least 3 characters")

    email = kwargs.get("email", "").strip()
    if not email or "@" not in email:
        errors.append("email must be a valid email address")

    password = kwargs.get("password", "")
    if not password or len(password) < 6:
        errors.append("password must be at least 6 characters")

    return {"valid": len(errors) == 0, "errors": errors}


def _execute_create_user(**kwargs) -> Dict[str, Any]:
    """Execute create user operation."""
    try:
        username = kwargs.get("username", "").strip()
        email = kwargs.get("email", "").strip()
        password = kwargs.get("password", "")

        # Check if user already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            return {
                "success": False,
                "message": f"User with username '{username}' or email '{email}' already exists",
            }

        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        return {
            "success": True,
            "message": f"Successfully created user '{username}' ({email})",
            "data": {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
            },
        }

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.exception(f"Database error creating user: {e}")
        return {"success": False, "message": f"Database error: {str(e)}"}
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Error creating user: {e}")
        return {"success": False, "message": f"Failed to create user: {str(e)}"}


# Legacy compatibility - AdminOperationRegistry for backward compatibility
class AdminOperationRegistry:
    """Registry for all available admin operations."""

    @classmethod
    def get_operation(cls, op_name: str):
        """Get operation class by name."""
        op_info = OPERATIONS.get(op_name)
        if not op_info:
            return None

        # Create a compatibility class
        class LegacyOperation:
            name = op_name
            description = op_info["description"]
            requires_confirmation = op_info["requires_confirmation"]

            def validate_params(self, **kwargs):
                return op_info["validate"](**kwargs)

            def execute(self, **kwargs):
                return op_info["execute"](**kwargs)

        return LegacyOperation

    @classmethod
    def list_operations(cls):
        """List all available operations with descriptions."""
        return list_operations()

    @classmethod
    def register_operation(cls, name: str, operation_class):
        """Register a new operation."""
        # For backward compatibility, we don't actually register here
        # since we're using the function-based approach


# Legacy compatibility - BaseAdminOperation class
class BaseAdminOperation:
    """Legacy base class for backward compatibility."""
