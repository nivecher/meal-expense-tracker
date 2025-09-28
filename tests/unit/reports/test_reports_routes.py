"""Tests for reports routes module."""

import pytest
from flask import Flask

from app.reports.routes import analytics, expense_report, index, restaurant_report


class TestReportsRoutes:
    """Test reports routes functions."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        app.config["SECRET_KEY"] = "test_secret_key"
        return app

    def test_index_route_decorator_presence(self):
        """Test that index route has the @login_required decorator."""
        assert hasattr(index, "__wrapped__")

    def test_expense_report_route_decorator_presence(self):
        """Test that expense_report route has the @login_required decorator."""
        assert hasattr(expense_report, "__wrapped__")

    def test_restaurant_report_route_decorator_presence(self):
        """Test that restaurant_report route has the @login_required decorator."""
        assert hasattr(restaurant_report, "__wrapped__")

    def test_analytics_route_decorator_presence(self):
        """Test that analytics route has the @login_required decorator."""
        assert hasattr(analytics, "__wrapped__")

    def test_routes_import_correctly(self):
        """Test that all routes can be imported correctly."""
        assert index is not None
        assert expense_report is not None
        assert restaurant_report is not None
        assert analytics is not None

    def test_routes_are_callable(self):
        """Test that all routes are callable functions."""
        assert callable(index)
        assert callable(expense_report)
        assert callable(restaurant_report)
        assert callable(analytics)

    def test_routes_module_structure(self):
        """Test that the routes module has expected structure."""
        from app.reports import routes

        assert hasattr(routes, "index")
        assert hasattr(routes, "expense_report")
        assert hasattr(routes, "restaurant_report")
        assert hasattr(routes, "analytics")

    def test_routes_blueprint_registration(self):
        """Test that routes are properly registered with blueprint."""
        from app.reports import bp

        assert bp is not None
        assert hasattr(bp, "name")
        assert bp.name == "reports"

    def test_route_functions_have_docstrings(self):
        """Test that route functions have proper documentation."""
        assert index.__doc__ is not None
        assert "Show the reports dashboard" in index.__doc__

        assert expense_report.__doc__ is not None
        assert "Generate an expense report" in expense_report.__doc__

        assert restaurant_report.__doc__ is not None
        assert "Generate a restaurant report" in restaurant_report.__doc__

        assert analytics.__doc__ is not None
        assert "Show analytics dashboard" in analytics.__doc__
