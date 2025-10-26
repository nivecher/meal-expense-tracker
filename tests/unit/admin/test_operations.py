"""Tests for admin operations to improve coverage."""

from app.admin.operations import get_operation_info, list_operations


class TestOperationsAPI:
    """Test the new operations API."""

    def test_list_operations(self):
        """Test that operations can be listed."""
        operations = list_operations()
        assert isinstance(operations, dict)
        assert "list_users" in operations
        assert "create_user" in operations

    def test_get_operation_info(self):
        """Test getting operation information."""
        info = get_operation_info("list_users")
        assert info is not None
        assert "description" in info
        assert "requires_confirmation" in info
        assert "validate" in info
        assert "execute" in info

    def test_get_operation_info_invalid(self):
        """Test getting info for non-existent operation."""
        info = get_operation_info("non_existent")
        assert info is None


class TestListUsersOperation:
    """Test list users operation."""

    def test_validate_params_valid(self):
        """Test parameter validation with valid input."""
        info = get_operation_info("list_users")
        validate_func = info["validate"]
        result = validate_func(limit=10, offset=0)
        assert isinstance(result, dict)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_validate_params_default(self):
        """Test parameter validation with default values."""
        info = get_operation_info("list_users")
        validate_func = info["validate"]
        result = validate_func()
        assert isinstance(result, dict)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_validate_params_invalid_limit(self):
        """Test parameter validation with invalid limit."""
        info = get_operation_info("list_users")
        validate_func = info["validate"]
        result = validate_func(limit=0)
        assert result["valid"] is False
        assert "limit must be an integer between 1 and 1000" in result["errors"]

    def test_validate_params_invalid_admin_only(self):
        """Test parameter validation with invalid admin_only."""
        info = get_operation_info("list_users")
        validate_func = info["validate"]
        result = validate_func(admin_only="invalid")
        assert result["valid"] is False
        assert "admin_only must be a boolean" in result["errors"]

    def test_operation_description(self):
        """Test operation description."""
        info = get_operation_info("list_users")
        description = info["description"]
        assert isinstance(description, str)
        assert len(description) > 0


class TestCreateUserOperation:
    """Test create user operation."""

    def test_validate_params_valid(self):
        """Test parameter validation with valid input."""
        info = get_operation_info("create_user")
        validate_func = info["validate"]
        result = validate_func(username="testuser", email="test@example.com", password="password123")
        assert isinstance(result, dict)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_validate_params_missing_required(self):
        """Test parameter validation with missing required fields."""
        info = get_operation_info("create_user")
        validate_func = info["validate"]
        result = validate_func(username="testuser")  # Missing email and password
        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_operation_description(self):
        """Test operation description."""
        info = get_operation_info("create_user")
        description = info["description"]
        assert isinstance(description, str)
        assert len(description) > 0
