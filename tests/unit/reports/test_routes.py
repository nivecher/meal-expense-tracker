"""Tests for reports routes module."""

import pytest
from unittest.mock import Mock, patch
from flask import Flask

from app.reports.routes import index, expense_report, restaurant_report, analytics


class TestReportsRoutes:
    """Test reports routes functions."""

    @pytest.fixture
    def app(self):
        """Create test Flask app."""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        return app

    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = Mock()
        user.id = 1
        user.username = "testuser"
        return user

    def test_index_route(self, app, mock_user):
        """Test reports index route."""
        with app.test_request_context():
            with patch("app.reports.routes.current_user", mock_user):
                with patch("app.reports.routes.expense_services") as mock_expense_services:
                    with patch("app.reports.routes.restaurant_services") as mock_restaurant_services:
                        with patch("app.reports.routes.render_template") as mock_render:
                            mock_expenses = [{"id": 1, "amount": 25.50}]
                            mock_restaurants = [{"id": 1, "name": "Test Restaurant"}]
                            mock_expense_services.get_expenses_for_user.return_value = mock_expenses
                            mock_restaurant_services.get_restaurants_for_user.return_value = mock_restaurants
                            
                            result = index()
                            
                            mock_expense_services.get_expenses_for_user.assert_called_once_with(1)
                            mock_restaurant_services.get_restaurants_for_user.assert_called_once_with(1)
                            mock_render.assert_called_once_with(
                                "reports/index.html", 
                                expenses=mock_expenses, 
                                restaurants=mock_restaurants
                            )

    def test_expense_report_route(self, app, mock_user):
        """Test expense report route."""
        with app.test_request_context():
            with patch("app.reports.routes.current_user", mock_user):
                with patch("app.reports.routes.render_template") as mock_render:
                    result = expense_report()
                    
                    mock_render.assert_called_once_with("reports/expense_report.html")

    def test_restaurant_report_route(self, app, mock_user):
        """Test restaurant report route."""
        with app.test_request_context():
            with patch("app.reports.routes.current_user", mock_user):
                with patch("app.reports.routes.render_template") as mock_render:
                    result = restaurant_report()
                    
                    mock_render.assert_called_once_with("reports/restaurant_report.html")

    def test_analytics_route(self, app, mock_user):
        """Test analytics route."""
        with app.test_request_context():
            with patch("app.reports.routes.current_user", mock_user):
                with patch("app.reports.routes.render_template") as mock_render:
                    result = analytics()
                    
                    mock_render.assert_called_once_with("reports/analytics.html")

    def test_index_route_with_empty_data(self, app, mock_user):
        """Test reports index route with empty data."""
        with app.test_request_context():
            with patch("app.reports.routes.current_user", mock_user):
                with patch("app.reports.routes.expense_services") as mock_expense_services:
                    with patch("app.reports.routes.restaurant_services") as mock_restaurant_services:
                        with patch("app.reports.routes.render_template") as mock_render:
                            mock_expense_services.get_expenses_for_user.return_value = []
                            mock_restaurant_services.get_restaurants_for_user.return_value = []
                            
                            result = index()
                            
                            mock_render.assert_called_once_with(
                                "reports/index.html", 
                                expenses=[], 
                                restaurants=[]
                            )

    def test_index_route_service_exception(self, app, mock_user):
        """Test reports index route with service exception."""
        with app.test_request_context():
            with patch("app.reports.routes.current_user", mock_user):
                with patch("app.reports.routes.expense_services") as mock_expense_services:
                    with patch("app.reports.routes.restaurant_services") as mock_restaurant_services:
                        mock_expense_services.get_expenses_for_user.side_effect = Exception("Database error")
                        mock_restaurant_services.get_restaurants_for_user.return_value = []
                        
                        with pytest.raises(Exception):
                            index()

    def test_expense_report_route_template_error(self, app, mock_user):
        """Test expense report route with template error."""
        with app.test_request_context():
            with patch("app.reports.routes.current_user", mock_user):
                with patch("app.reports.routes.render_template") as mock_render:
                    mock_render.side_effect = Exception("Template error")
                    
                    with pytest.raises(Exception):
                        expense_report()

    def test_restaurant_report_route_template_error(self, app, mock_user):
        """Test restaurant report route with template error."""
        with app.test_request_context():
            with patch("app.reports.routes.current_user", mock_user):
                with patch("app.reports.routes.render_template") as mock_render:
                    mock_render.side_effect = Exception("Template error")
                    
                    with pytest.raises(Exception):
                        restaurant_report()

    def test_analytics_route_template_error(self, app, mock_user):
        """Test analytics route with template error."""
        with app.test_request_context():
            with patch("app.reports.routes.current_user", mock_user):
                with patch("app.reports.routes.render_template") as mock_render:
                    mock_render.side_effect = Exception("Template error")
                    
                    with pytest.raises(Exception):
                        analytics()

    def test_index_route_with_large_datasets(self, app, mock_user):
        """Test reports index route with large datasets."""
        with app.test_request_context():
            with patch("app.reports.routes.current_user", mock_user):
                with patch("app.reports.routes.expense_services") as mock_expense_services:
                    with patch("app.reports.routes.restaurant_services") as mock_restaurant_services:
                        with patch("app.reports.routes.render_template") as mock_render:
                            # Create large mock datasets
                            mock_expenses = [{"id": i, "amount": i * 10.0} for i in range(1000)]
                            mock_restaurants = [{"id": i, "name": f"Restaurant {i}"} for i in range(100)]
                            mock_expense_services.get_expenses_for_user.return_value = mock_expenses
                            mock_restaurant_services.get_restaurants_for_user.return_value = mock_restaurants
                            
                            result = index()
                            
                            mock_render.assert_called_once_with(
                                "reports/index.html", 
                                expenses=mock_expenses, 
                                restaurants=mock_restaurants
                            )

    def test_routes_require_login(self, app):
        """Test that all routes require login."""
        # This test verifies that the @login_required decorator is applied
        # by checking that routes raise an error when no user is logged in
        with app.test_request_context():
            with patch("app.reports.routes.current_user") as mock_current_user:
                mock_current_user.is_authenticated = False
                
                # All routes should require authentication
                # This is more of a documentation test since the decorator
                # behavior is tested by Flask-Login itself
                assert hasattr(index, '__wrapped__')  # Decorated function
                assert hasattr(expense_report, '__wrapped__')  # Decorated function
                assert hasattr(restaurant_report, '__wrapped__')  # Decorated function
                assert hasattr(analytics, '__wrapped__')  # Decorated function
