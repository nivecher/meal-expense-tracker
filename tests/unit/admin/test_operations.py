"""Tests for admin operations to improve coverage."""

import uuid

from app.admin.operations import get_operation_info, list_operations
from app.auth.models import User


class TestOperationsAPI:
    """Test the new operations API."""

    def test_list_operations(self) -> None:
        """Test that operations can be listed."""
        operations = list_operations()
        assert isinstance(operations, dict)
        assert "list_users" in operations
        assert "create_user" in operations
        assert "update_user" in operations

    def test_get_operation_info(self) -> None:
        """Test getting operation information."""
        info = get_operation_info("list_users")
        assert info is not None
        assert "description" in info
        assert "requires_confirmation" in info
        assert "validate" in info
        assert "execute" in info

    def test_get_operation_info_invalid(self) -> None:
        """Test getting info for non-existent operation."""
        info = get_operation_info("non_existent")
        assert info is None


class TestListUsersOperation:
    """Test list users operation."""

    def test_validate_params_valid(self) -> None:
        """Test parameter validation with valid input."""
        info = get_operation_info("list_users")
        validate_func = info["validate"]
        result = validate_func(limit=10, offset=0)
        assert isinstance(result, dict)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_validate_params_default(self) -> None:
        """Test parameter validation with default values."""
        info = get_operation_info("list_users")
        validate_func = info["validate"]
        result = validate_func()
        assert isinstance(result, dict)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_validate_params_invalid_limit(self) -> None:
        """Test parameter validation with invalid limit."""
        info = get_operation_info("list_users")
        validate_func = info["validate"]
        result = validate_func(limit=0)
        assert result["valid"] is False
        assert "limit must be an integer between 1 and 1000" in result["errors"]

    def test_validate_params_invalid_admin_only(self) -> None:
        """Test parameter validation with invalid admin_only."""
        info = get_operation_info("list_users")
        validate_func = info["validate"]
        result = validate_func(admin_only="invalid")
        assert result["valid"] is False
        assert "admin_only must be a boolean" in result["errors"]

    def test_operation_description(self) -> None:
        """Test operation description."""
        info = get_operation_info("list_users")
        description = info["description"]
        assert isinstance(description, str)
        assert len(description) > 0


class TestCreateUserOperation:
    """Test create user operation."""

    def test_validate_params_valid(self) -> None:
        """Test parameter validation with valid input."""
        info = get_operation_info("create_user")
        validate_func = info["validate"]
        result = validate_func(username="testuser", email="test@example.com", password="password123")
        assert isinstance(result, dict)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_validate_params_missing_required(self) -> None:
        """Test parameter validation with missing required fields."""
        info = get_operation_info("create_user")
        validate_func = info["validate"]
        result = validate_func(username="testuser")  # Missing email and password
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_validate_params_invalid_flags(self) -> None:
        """Test parameter validation with invalid flags."""
        info = get_operation_info("create_user")
        validate_func = info["validate"]
        result = validate_func(
            username="testuser",
            email="test@example.com",
            password="password123",
            admin="yes",
            active="no",
        )
        assert result["valid"] is False
        assert "admin must be a boolean" in result["errors"]
        assert "active must be a boolean" in result["errors"]

    def test_operation_description(self) -> None:
        """Test operation description."""
        info = get_operation_info("create_user")
        description = info["description"]
        assert isinstance(description, str)
        assert len(description) > 0


class TestUpdateUserOperation:
    """Test update user operation."""

    def test_validate_requires_identifier(self) -> None:
        """Test update validation requires an identifier."""
        info = get_operation_info("update_user")
        validate_func = info["validate"]
        result = validate_func(admin=True)
        assert result["valid"] is False
        assert "Must provide one identifier: user_id, email, or username" in result["errors"]

    def test_validate_requires_changes(self) -> None:
        """Test update validation requires a change to apply."""
        info = get_operation_info("update_user")
        validate_func = info["validate"]
        result = validate_func(user_id=1)
        assert result["valid"] is False
        assert "No updates specified (provide at least one field to change)" in result["errors"]


class TestAdminOperationsExecute:
    """Test execute paths for admin operations."""

    def test_create_user_sets_admin_and_active(self, session) -> None:
        """Create user should honor admin/active flags."""
        username = f"remote_{uuid.uuid4().hex[:8]}"
        email = f"{username}@example.com"

        info = get_operation_info("create_user")
        execute_func = info["execute"]
        result = execute_func(
            username=username,
            email=email,
            password="password123",
            admin=True,
            active=False,
        )
        assert result["success"] is True

        user = session.query(User).filter_by(username=username).first()
        assert user is not None
        assert user.is_admin is True
        assert user.is_active is False

    def test_update_user_can_promote_to_admin(self, session) -> None:
        """Update user should be able to toggle admin."""
        username = f"user_{uuid.uuid4().hex[:8]}"
        email = f"{username}@example.com"

        user = User(username=username, email=email, is_admin=False, is_active=True)
        user.set_password("password123")
        session.add(user)
        session.commit()
        session.refresh(user)

        info = get_operation_info("update_user")
        execute_func = info["execute"]
        result = execute_func(user_id=user.id, admin=True)
        assert result["success"] is True

        session.refresh(user)
        assert user.is_admin is True
