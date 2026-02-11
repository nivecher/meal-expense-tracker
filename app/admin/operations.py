"""Remote administration operations.

Simplified admin operations using direct functions instead of complex class hierarchies.
Each operation returns a consistent interface for easy remote invocation.
"""

from collections.abc import Callable
import logging
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    pass

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.auth.models import User
from app.extensions import db

logger = logging.getLogger(__name__)


# Operation definitions: name -> (description, requires_confirmation, validate_func, execute_func)
OPERATIONS: dict[str, dict[str, Any]] = {}


def register_operation(
    name: str,
    description: str,
    requires_confirmation: bool,
    validate_func: Callable[..., Any],
    execute_func: Callable[..., Any],
) -> None:
    """Register an admin operation."""
    OPERATIONS[name] = {
        "description": description,
        "requires_confirmation": requires_confirmation,
        "validate": validate_func,
        "execute": execute_func,
    }


def get_operation_info(name: str) -> dict[str, Any] | None:
    """Get operation information."""
    return OPERATIONS.get(name)


def list_operations() -> dict[str, str]:
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

register_operation(
    "update_user",
    "Update an existing user (email/username/password/admin/active)",
    True,
    lambda **kwargs: _validate_update_user(**kwargs),
    lambda **kwargs: _execute_update_user(**kwargs),
)

register_operation(
    "run_migrations",
    "Run database migrations safely (optionally dry-run or fix history)",
    True,
    lambda **kwargs: _validate_run_migrations(**kwargs),
    lambda **kwargs: _execute_run_migrations(**kwargs),
)


def _validate_list_users(**kwargs: Any) -> dict[str, Any]:
    """Validate list users parameters."""
    errors = []

    admin_only = kwargs.get("admin_only", False)
    if not isinstance(admin_only, bool):
        errors.append("admin_only must be a boolean")

    limit = kwargs.get("limit", 100)
    if not isinstance(limit, int) or limit < 1 or limit > 1000:
        errors.append("limit must be an integer between 1 and 1000")

    return {"valid": len(errors) == 0, "errors": errors}


def _execute_list_users(**kwargs: Any) -> dict[str, Any]:
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


def _validate_create_user(**kwargs: Any) -> dict[str, Any]:
    """Validate create user parameters."""
    errors = []

    username = kwargs.get("username", "").strip()
    if not username or len(username) < 3:
        errors.append("username must be at least 3 characters")

    email = kwargs.get("email", "").strip()
    if not email or "@" not in email:
        errors.append("email must be a valid email address")

    password = kwargs.get("password", "")
    if not password or len(password) < 8:
        errors.append("password must be at least 8 characters")

    admin = kwargs.get("admin", False)
    if not isinstance(admin, bool):
        errors.append("admin must be a boolean")

    active = kwargs.get("active", True)
    if not isinstance(active, bool):
        errors.append("active must be a boolean")

    return {"valid": len(errors) == 0, "errors": errors}


def _validate_update_user(**kwargs: Any) -> dict[str, Any]:
    """Validate update user parameters."""
    errors: list[str] = []

    user_id = kwargs.get("user_id")
    if user_id is not None and (not isinstance(user_id, int) or user_id < 1):
        errors.append("user_id must be a positive integer")

    email = kwargs.get("email")
    if email is not None and (not isinstance(email, str) or not email.strip()):
        errors.append("email must be a non-empty string")

    username = kwargs.get("username")
    if username is not None and (not isinstance(username, str) or not username.strip()):
        errors.append("username must be a non-empty string")

    if user_id is None and not email and not username:
        errors.append("Must provide one identifier: user_id, email, or username")

    new_email = kwargs.get("new_email")
    if new_email is not None and (not isinstance(new_email, str) or not new_email.strip()):
        errors.append("new_email must be a non-empty string")
    elif isinstance(new_email, str) and new_email and "@" not in new_email:
        errors.append("new_email must be a valid email address")

    new_username = kwargs.get("new_username")
    if new_username is not None and (not isinstance(new_username, str) or not new_username.strip()):
        errors.append("new_username must be a non-empty string")
    elif isinstance(new_username, str) and new_username and len(new_username.strip()) < 3:
        errors.append("new_username must be at least 3 characters")

    password = kwargs.get("password")
    if password is not None and (not isinstance(password, str) or len(password) < 8):
        errors.append("password must be a string at least 8 characters long")

    admin = kwargs.get("admin")
    if admin is not None and not isinstance(admin, bool):
        errors.append("admin must be a boolean")

    active = kwargs.get("active")
    if active is not None and not isinstance(active, bool):
        errors.append("active must be a boolean")

    if not any([new_email, new_username, password, admin is not None, active is not None]):
        errors.append("No updates specified (provide at least one field to change)")

    return {"valid": len(errors) == 0, "errors": errors}


def _validate_run_migrations(**kwargs: Any) -> dict[str, Any]:
    """Validate run migrations parameters."""
    errors = []

    dry_run = kwargs.get("dry_run", False)
    if not isinstance(dry_run, bool):
        errors.append("dry_run must be a boolean")

    fix_history = kwargs.get("fix_history", False)
    if not isinstance(fix_history, bool):
        errors.append("fix_history must be a boolean")

    target_revision = kwargs.get("target_revision")
    if target_revision is not None and not isinstance(target_revision, str):
        errors.append("target_revision must be a string")

    return {"valid": len(errors) == 0, "errors": errors}


def _execute_create_user(**kwargs: Any) -> dict[str, Any]:
    """Execute create user operation."""
    try:
        username = kwargs.get("username", "").strip()
        email = kwargs.get("email", "").strip()
        password = kwargs.get("password", "")
        admin = kwargs.get("admin", False)
        active = kwargs.get("active", True)

        # Check if user already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            return {
                "success": False,
                "message": f"User with username '{username}' or email '{email}' already exists",
            }

        # Create new user
        user = User(username=username, email=email, is_admin=bool(admin), is_active=bool(active))
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
                "is_admin": user.is_admin,
                "is_active": user.is_active,
            },
        }

    except IntegrityError as e:
        db.session.rollback()
        logger.exception(f"Integrity error creating user: {e}")
        return {"success": False, "message": f"Integrity error: {str(e)}"}
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.exception(f"Database error creating user: {e}")
        return {"success": False, "message": f"Database error: {str(e)}"}
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Error creating user: {e}")
        return {"success": False, "message": f"Failed to create user: {str(e)}"}


def _find_user_for_update(user_id: int | None, email: str | None, username: str | None) -> User | None:
    """Find a user by id/email/username, optionally cross-checking identifiers."""
    if user_id is not None:
        user = db.session.get(User, user_id)
        if user is None:
            return None
        if email and user.email != email:
            return None
        if username and user.username != username:
            return None
        return user

    if email:
        user = User.query.filter_by(email=email).first()
        if user and username and user.username != username:
            return None
        return user

    if username:
        user = User.query.filter_by(username=username).first()
        return user

    return None


def _username_available(new_username: str, user_id: int) -> bool:
    """Check if username is available (excluding the current user)."""
    return User.query.filter(User.username == new_username, User.id != user_id).first() is None


def _email_available(new_email: str, user_id: int) -> bool:
    """Check if email is available (excluding the current user)."""
    return User.query.filter(User.email == new_email, User.id != user_id).first() is None


def _execute_update_user(**kwargs: Any) -> dict[str, Any]:
    """Execute update user operation."""
    try:
        user_id = kwargs.get("user_id")
        email = kwargs.get("email")
        username = kwargs.get("username")
        new_email = kwargs.get("new_email")
        new_username = kwargs.get("new_username")
        password = kwargs.get("password")
        admin = kwargs.get("admin")
        active = kwargs.get("active")

        user = _find_user_for_update(user_id, email, username)
        if user is None:
            return {"success": False, "message": "User not found (or identifiers do not match the same user)"}

        changes: list[str] = []

        if isinstance(new_username, str):
            new_username = new_username.strip()
            if new_username and new_username != user.username:
                if not _username_available(new_username, user.id):
                    return {"success": False, "message": f"Username '{new_username}' is already taken"}
                user.username = new_username
                changes.append("username")

        if isinstance(new_email, str):
            new_email = new_email.strip()
            if new_email and new_email != user.email:
                if not _email_available(new_email, user.id):
                    return {"success": False, "message": f"Email '{new_email}' is already in use"}
                user.email = new_email
                changes.append("email")

        if isinstance(password, str) and password:
            user.set_password(password)
            changes.append("password")

        if isinstance(admin, bool) and admin != user.is_admin:
            user.is_admin = admin
            changes.append("is_admin")

        if isinstance(active, bool) and active != user.is_active:
            user.is_active = active
            changes.append("is_active")

        if not changes:
            return {
                "success": True,
                "message": f"No changes applied to user '{user.username}'",
                "data": {
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_admin": user.is_admin,
                    "is_active": user.is_active,
                    "changed_fields": [],
                },
            }

        db.session.commit()

        return {
            "success": True,
            "message": f"Successfully updated user '{user.username}' ({user.email})",
            "data": {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "is_active": user.is_active,
                "changed_fields": changes,
            },
        }

    except IntegrityError as e:
        db.session.rollback()
        logger.exception(f"Integrity error updating user: {e}")
        return {"success": False, "message": f"Integrity error: {str(e)}"}
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.exception(f"Database error updating user: {e}")
        return {"success": False, "message": f"Database error: {str(e)}"}
    except Exception as e:
        db.session.rollback()
        logger.exception(f"Error updating user: {e}")
        return {"success": False, "message": f"Failed to update user: {str(e)}"}


def _execute_run_migrations(**kwargs: Any) -> dict[str, Any]:
    """Execute run migrations operation."""
    try:
        from app.utils.migration_manager import migration_manager

        dry_run = kwargs.get("dry_run", False)
        fix_history = kwargs.get("fix_history", False)
        target_revision = kwargs.get("target_revision")

        if fix_history:
            fix_result = migration_manager.fix_migration_history()
            if not fix_result.get("success"):
                return {
                    "success": False,
                    "message": f"Failed to fix migration history: {fix_result.get('error')}",
                    "data": fix_result,
                }

        result = migration_manager.run_migrations(dry_run=dry_run, target_revision=target_revision)
        return {**result, "data": result.get("data", {})}
    except Exception as e:
        logger.exception(f"Error running migrations: {e}")
        return {"success": False, "message": f"Failed to run migrations: {str(e)}"}


# Legacy compatibility - AdminOperationRegistry for backward compatibility
class AdminOperationRegistry:
    """Registry for all available admin operations."""

    @classmethod
    def get_operation(cls, op_name: str) -> type[Any] | None:
        """Get operation class by name."""
        op_info = OPERATIONS.get(op_name)
        # Explicit None check for type narrowing (replaces assert that would be stripped in -O mode)
        if op_info is None:
            return None
        # After None check, op_info is guaranteed to be Dict[str, Any]
        op_info_dict: dict[str, Any] = op_info

        # Create a compatibility class
        class LegacyOperation:
            name = op_name
            description = op_info_dict["description"]
            requires_confirmation = op_info_dict["requires_confirmation"]

            def validate_params(self, **kwargs: Any) -> dict[str, Any]:
                return cast(dict[str, Any], op_info_dict["validate"](**kwargs))

            def execute(self, **kwargs: Any) -> dict[str, Any]:
                return cast(dict[str, Any], op_info_dict["execute"](**kwargs))

        return LegacyOperation

    @classmethod
    def list_operations(cls) -> dict[str, str]:
        """List all available operations with descriptions."""
        return list_operations()

    @classmethod
    def register_operation(cls, name: str, operation_class: type[Any]) -> None:
        """Register a new operation."""
        # For backward compatibility, we don't actually register here
        # since we're using the function-based approach


# Legacy compatibility - BaseAdminOperation class
class BaseAdminOperation:
    """Legacy base class for backward compatibility."""
