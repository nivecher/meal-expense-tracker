"""Tests for admin __init__.py to improve coverage."""


class TestAdminInit:
    """Test admin module initialization."""

    def test_module_imports(self):
        """Test that module imports work correctly."""
        import app.admin

        # Test that the module has expected attributes
        assert hasattr(app.admin, "__name__")
        assert hasattr(app.admin, "__package__")
        assert hasattr(app.admin, "init_app")
        assert hasattr(app.admin, "LambdaAdminHandler")
        assert hasattr(app.admin, "BaseAdminOperation")
        assert hasattr(app.admin, "AdminOperationRegistry")
        assert hasattr(app.admin, "admin_bp")

    def test_module_imports_all_components(self):
        """Test that all admin components can be imported."""
        from app.admin.lambda_admin import LambdaAdminHandler, handle_admin_request
        from app.admin.operations import (
            AdminOperationRegistry,
            BaseAdminOperation,
            get_operation_info,
            list_operations,
        )
        from app.admin.routes import bp

        # Verify all imports are successful
        assert BaseAdminOperation is not None
        assert get_operation_info is not None
        assert list_operations is not None
        assert AdminOperationRegistry is not None
        assert bp is not None
        assert LambdaAdminHandler is not None
        assert handle_admin_request is not None
