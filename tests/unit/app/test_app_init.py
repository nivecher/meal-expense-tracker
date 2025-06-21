"""Tests for the Flask application initialization and configuration."""

import importlib
import json
import os
import sys
from unittest.mock import MagicMock, patch

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from app import create_app, get_db_credentials, version  # noqa: E402


class TestConfig:
    """Test configuration for the app."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "test-secret-key"
    WTF_CSRF_ENABLED = False


def test_create_app_with_testing_config():
    """Test creating the app with testing configuration."""
    app = create_app(TestConfig)

    assert app.testing is True
    assert app.config["SECRET_KEY"] == "test-secret-key"
    assert app.config["WTF_CSRF_ENABLED"] is False


def test_create_app_with_default_config():
    """Test creating the app with default configuration."""
    # Patch the environment with test values
    with patch.dict(
        "os.environ",
        {
            "FLASK_APP": "app",
            "FLASK_ENV": "development",
            "GOOGLE_MAPS_API_KEY": "test-key",
            "SERVER_NAME": "localhost:5000",
            "DB_USERNAME": "test",
            "DB_PASSWORD": "test",
            "DB_HOST": "localhost",
            "DB_NAME": "testdb",
            "DB_PORT": "5432",
            "AWS_REGION": "us-east-1",
            "DB_SECRET_ARN": "",
            "SECRET_KEY": "test-secret-key",
        },
    ):
        # Create the app
        app = create_app()

        # Verify the app was configured correctly
        assert not app.testing
        # Verify the Google Maps API key is set (don't check the specific value)
        assert "GOOGLE_MAPS_API_KEY" in app.config
        assert isinstance(app.config["GOOGLE_MAPS_API_KEY"], str)
        assert len(app.config["GOOGLE_MAPS_API_KEY"]) > 0

        # SERVER_NAME might be None in default config
        if "SERVER_NAME" in app.config and app.config["SERVER_NAME"] is not None:
            assert isinstance(app.config["SERVER_NAME"], str)
            assert len(app.config["SERVER_NAME"]) > 0

        # SECRET_KEY should be set (either from env or auto-generated)
        assert "SECRET_KEY" in app.config
        # SECRET_KEY can be either bytes or string
        secret_key = app.config["SECRET_KEY"]
        assert isinstance(secret_key, (str, bytes))
        assert len(secret_key) > 0


def test_version_import():
    """Test that version information is properly imported."""
    assert "app" in version
    assert isinstance(version["app"], str)


def test_get_db_credentials_local(monkeypatch):
    """Test getting DB credentials in local development."""
    # Set up test environment variables
    test_env_vars = {
        "FLASK_ENV": "development",
        "DB_USERNAME": "testuser",
        "DB_PASSWORD": "testpass",
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "testdb",
        # Ensure we don't try to use AWS Secrets Manager
        "DB_SECRET_ARN": "",
    }

    # Apply the environment variables
    for key, value in test_env_vars.items():
        monkeypatch.setenv(key, value)

    # Mock the boto3 client to ensure we don't make real AWS calls
    with patch("boto3.client") as mock_boto:
        # Reload the module to pick up the new environment variables
        if "app" in sys.modules:
            importlib.reload(sys.modules["app"])

        # Get the credentials
        credentials = get_db_credentials()

        # Verify boto3 was not called (we should use local env vars)
        mock_boto.assert_not_called()

        # Verify the credentials
        assert credentials == {
            "username": "testuser",
            "password": "testpass",
            "host": "localhost",
            "port": "5432",
            "dbname": "testdb",
        }


def test_get_db_credentials_aws_secrets(monkeypatch):
    """Test getting DB credentials from AWS Secrets Manager."""
    # Set up test environment variables
    secret_arn = "arn:aws:secretsmanager:us-east-1:123456789012:secret:db-credentials"
    test_env_vars = {
        "FLASK_ENV": "production",
        "AWS_REGION": "us-east-1",
        "DB_SECRET_ARN": secret_arn,
    }

    # Set up the mock secret with all required fields
    mock_secret = {
        "username": "awsuser",
        "password": "awspass",
        "host": "db-host",
        "port": "5432",
        "dbname": "testdb",
    }

    # Apply the environment variables
    for key, value in test_env_vars.items():
        monkeypatch.setenv(key, value)

    # Set up the mock AWS client
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretString": json.dumps(mock_secret)
    }

    # Import get_db_credentials at module level to ensure it's available
    from app import get_db_credentials

    # Mock boto3.client to return our mock client
    with patch("boto3.client", return_value=mock_client) as mock_boto3:
        # Reload the module to pick up the new environment variables
        if "app" in sys.modules:
            importlib.reload(sys.modules["app"])
            from app import get_db_credentials as reloaded_get_db_credentials
        else:
            from app import get_db_credentials as reloaded_get_db_credentials

        # Use the reloaded version if available, otherwise use the original
        test_get_db_credentials = reloaded_get_db_credentials or get_db_credentials

        # Get the credentials using the correct function
        credentials = test_get_db_credentials()

        # Verify the credentials
        expected_credentials = {
            "username": "awsuser",
            "password": "awspass",
            "host": "db-host",
            "port": "5432",
            "dbname": "testdb",
        }
        assert credentials == expected_credentials

        # Verify boto3 was called correctly
        mock_boto3.assert_called_once_with("secretsmanager", region_name="us-east-1")
        mock_client.get_secret_value.assert_called_once_with(SecretId=secret_arn)
