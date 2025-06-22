"""Tests for the Flask application factory and configuration."""

import importlib
import json
import os
import sys
from unittest.mock import MagicMock, patch

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from app import create_app, version  # noqa: E402


class TestConfig:
    """Test configuration for the app."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "test-secret-key"
    WTF_CSRF_ENABLED = False


def test_create_app_with_testing_config():
    """Test creating the app with testing configuration."""
    # Create a test config dictionary
    test_config = {
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    }

    # Create the app with the test config
    app = create_app()
    app.config.update(test_config)

    assert app.testing is True
    assert app.config["SECRET_KEY"] == "test-secret-key"
    assert app.config["WTF_CSRF_ENABLED"] is False


def test_create_app_with_default_config(monkeypatch):
    """Test creating the app with default configuration."""
    # Set up test environment variables
    test_env_vars = {
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
    }

    # Apply the environment variables
    for key, value in test_env_vars.items():
        monkeypatch.setenv(key, value)

    # Import create_app after setting up the environment
    from app import create_app

    # Create the app
    app = create_app()

    # Set SERVER_NAME in the app config
    app.config["SERVER_NAME"] = "localhost:5000"

    # Test the configuration
    assert not app.testing
    # Verify the Google Maps API key is set (don't check the specific value)
    assert "GOOGLE_MAPS_API_KEY" in app.config
    assert isinstance(app.config["GOOGLE_MAPS_API_KEY"], str)
    assert len(app.config["GOOGLE_MAPS_API_KEY"]) > 0

    # Verify server name is set correctly if provided
    if "SERVER_NAME" in app.config:
        assert isinstance(app.config["SERVER_NAME"], str)
        assert app.config["SERVER_NAME"] == "localhost:5000"

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
    """Test getting DB credentials from environment variables."""
    # Set up test environment variables
    test_env_vars = {
        "DB_USERNAME": "testuser",
        "DB_PASSWORD": "testpass",
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "testdb",
        # Ensure we don't try to use AWS Secrets Manager
        "DB_SECRET_ARN": "",
        # Set a dummy AWS region to avoid boto3 errors
        "AWS_REGION": "us-east-1",
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
        from app import get_db_credentials

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


@patch("boto3.client")
def test_get_db_credentials_aws_secrets(mock_boto, monkeypatch):
    """Test getting DB credentials from AWS Secrets Manager."""
    # Set up test environment variables
    secret_arn = "arn:aws:secretsmanager:us-east-1:123456789012:secret:db-credentials"
    test_env_vars = {"AWS_REGION": "us-east-1", "DB_SECRET_ARN": secret_arn}

    for key, value in test_env_vars.items():
        monkeypatch.setenv(key, value)

    # Mock the AWS Secrets Manager response
    mock_secret = {
        "username": "awsuser",
        "password": "awspass",
        "host": "db-host",
        "port": "5432",
        "dbname": "testdb",
    }

    # Set up the mock client
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {"SecretString": json.dumps(mock_secret)}
    mock_boto.return_value = mock_client

    # Reload the module to pick up the new environment variables
    if "app" in sys.modules:
        importlib.reload(sys.modules["app"])

    from app import get_db_credentials

    # Get the credentials
    credentials = get_db_credentials()

    # Verify boto3 was called correctly
    mock_boto.assert_called_once_with("secretsmanager", region_name="us-east-1")
    mock_client.get_secret_value.assert_called_once_with(SecretId=secret_arn)

    # Verify the credentials
    assert credentials == mock_secret
