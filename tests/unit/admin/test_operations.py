"""Tests for admin operations to improve coverage."""

import pytest

from app.admin.operations import (
    BaseAdminOperation,
    ListUsersOperation,
    SystemStatsOperation,
)


class TestBaseAdminOperation:
    """Test the base admin operation class."""

    def test_base_operation_interface(self):
        """Test that base operation defines required interface."""
        # This tests the abstract base class interface
        assert hasattr(BaseAdminOperation, "validate_params")
        assert hasattr(BaseAdminOperation, "execute")
        assert hasattr(BaseAdminOperation, "description")

        # Verify it's abstract
        with pytest.raises(TypeError):
            BaseAdminOperation()


class TestSystemStatsOperation:
    """Test system statistics operation."""

    def test_validate_params_valid(self):
        """Test parameter validation with valid input."""
        op = SystemStatsOperation()
        result = op.validate_params()
        assert isinstance(result, dict)

    def test_description_property(self):
        """Test operation description."""
        op = SystemStatsOperation()
        description = op.description
        assert isinstance(description, str)
        assert len(description) > 0


class TestListUsersOperation:
    """Test list users operation."""

    def test_validate_params_valid(self):
        """Test parameter validation with valid input."""
        op = ListUsersOperation()
        result = op.validate_params(limit=10, offset=0)
        assert isinstance(result, dict)

    def test_validate_params_default(self):
        """Test parameter validation with default values."""
        op = ListUsersOperation()
        result = op.validate_params()
        assert isinstance(result, dict)

    def test_description_property(self):
        """Test operation description."""
        op = ListUsersOperation()
        description = op.description
        assert isinstance(description, str)
        assert len(description) > 0
