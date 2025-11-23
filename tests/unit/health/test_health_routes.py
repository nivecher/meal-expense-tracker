"""Tests for health check endpoints."""

from unittest.mock import Mock, patch

from flask import url_for
from sqlalchemy.exc import SQLAlchemyError

from app.health.routes import check


class TestHealthRoutes:
    """Test health check endpoints."""

    def test_health_check_success(self, client, app):
        """Test successful health check."""
        with app.app_context():
            with patch("app.health.routes.db.session.execute") as mock_execute:
                mock_execute.return_value = None

                with patch("app.health.routes.datetime") as mock_datetime:
                    mock_now = Mock()
                    mock_now.isoformat.return_value = "2024-01-01T12:00:00+00:00"
                    mock_datetime.now.return_value = mock_now

                    response = client.get(url_for("health.check"))

                    assert response.status_code == 200
                    data = response.get_json()
                    assert data["status"] == "ok"
                    assert data["database"] == "connected"
                    assert data["version"] is not None
                    assert data["timestamp"] == "2024-01-01T12:00:00+00:00"

    def test_health_check_database_error(self, client, app):
        """Test health check when database connection fails."""
        with app.app_context():
            with patch("app.health.routes.db.session.execute") as mock_execute:
                mock_execute.side_effect = SQLAlchemyError("Connection failed")

                with patch("app.health.routes.datetime") as mock_datetime:
                    mock_now = Mock()
                    mock_now.isoformat.return_value = "2024-01-01T12:00:00+00:00"
                    mock_datetime.now.return_value = mock_now

                    response = client.get(url_for("health.check"))

                    assert response.status_code == 200
                    data = response.get_json()
                    assert data["status"] == "ok"
                    assert data["database"] == "error: Connection failed"
                    assert data["version"] is not None
                    assert data["timestamp"] == "2024-01-01T12:00:00+00:00"

    def test_health_check_database_generic_error(self, client, app):
        """Test health check when database raises a generic exception."""
        with app.app_context():
            with patch("app.health.routes.db.session.execute") as mock_execute:
                mock_execute.side_effect = Exception("Generic database error")

                with patch("app.health.routes.datetime") as mock_datetime:
                    mock_now = Mock()
                    mock_now.isoformat.return_value = "2024-01-01T12:00:00+00:00"
                    mock_datetime.now.return_value = mock_now

                    response = client.get(url_for("health.check"))

                    assert response.status_code == 200
                    data = response.get_json()
                    assert data["status"] == "ok"
                    assert data["database"] == "error: Generic database error"
                    assert data["version"] is not None
                    assert data["timestamp"] == "2024-01-01T12:00:00+00:00"

    def test_health_check_logs_database_error(self, client, app):
        """Test that database errors are logged."""
        with app.app_context():
            with patch("app.health.routes.db.session.execute") as mock_execute:
                mock_execute.side_effect = SQLAlchemyError("Connection failed")

                with patch("app.health.routes.logger") as mock_logger:
                    response = client.get(url_for("health.check"))

                    assert response.status_code == 200
                    # Verify error was logged
                    mock_logger.error.assert_called_once()
                    log_call = mock_logger.error.call_args[0][0]
                    assert "Database connection error" in log_call
                    assert "Connection failed" in log_call

    def test_health_check_version_included(self, client, app):
        """Test that version information is included in response."""
        with app.app_context():
            with patch("app.health.routes.db.session.execute") as mock_execute:
                mock_execute.return_value = None

                response = client.get(url_for("health.check"))

                assert response.status_code == 200
                data = response.get_json()
                assert "version" in data
                assert data["version"] is not None

    def test_health_check_timestamp_format(self, client, app):
        """Test that timestamp is in ISO format."""
        with app.app_context():
            with patch("app.health.routes.db.session.execute") as mock_execute:
                mock_execute.return_value = None

                response = client.get(url_for("health.check"))

                assert response.status_code == 200
                data = response.get_json()
                assert "timestamp" in data
                # Should be ISO format timestamp
                timestamp = data["timestamp"]
                assert "T" in timestamp
                assert "+" in timestamp or "Z" in timestamp

    def test_health_check_response_structure(self, client, app):
        """Test that response has all expected fields."""
        with app.app_context():
            with patch("app.health.routes.db.session.execute") as mock_execute:
                mock_execute.return_value = None

                response = client.get(url_for("health.check"))

                assert response.status_code == 200
                data = response.get_json()

                # Check all expected fields are present
                expected_fields = ["status", "version", "timestamp", "database"]
                for field in expected_fields:
                    assert field in data, f"Missing field: {field}"

    def test_health_check_status_always_ok(self, client, app):
        """Test that status is always 'ok' even when database fails."""
        with app.app_context():
            with patch("app.health.routes.db.session.execute") as mock_execute:
                mock_execute.side_effect = Exception("Database down")

                response = client.get(url_for("health.check"))

                assert response.status_code == 200
                data = response.get_json()
                # Status should always be "ok" - the endpoint itself is working
                assert data["status"] == "ok"

    def test_health_check_database_query(self, client, app):
        """Test that the correct database query is executed."""
        with app.app_context():
            with patch("app.health.routes.db.session.execute") as mock_execute:
                mock_execute.return_value = None

                response = client.get(url_for("health.check"))

                assert response.status_code == 200
                # Verify the correct SQL query was executed
                mock_execute.assert_called_once()
                call_args = mock_execute.call_args[0][0]
                assert "SELECT 1" in str(call_args)

    def test_health_check_function_directly(self, app):
        """Test the health check function directly without Flask client."""
        with app.app_context():
            with patch("app.health.routes.db.session.execute") as mock_execute:
                mock_execute.return_value = None

                with patch("app.health.routes.datetime") as mock_datetime:
                    mock_now = Mock()
                    mock_now.isoformat.return_value = "2024-01-01T12:00:00+00:00"
                    mock_datetime.now.return_value = mock_now

                    # Call the function directly
                    response = check()

                    assert response.status_code == 200
                    data = response.get_json()
                    assert data["status"] == "ok"
                    assert data["database"] == "connected"
