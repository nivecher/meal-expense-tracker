"""Tests for the Flask application initialization and configuration."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

from app import create_app  # noqa: E402


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


def test_get_database_url_local(monkeypatch):
    """Test getting database URL in local development."""
    # Mock environment variables for local development
    env_vars = {"DATABASE_URL": "postgresql://testuser:testpass@localhost:5432/testdb"}

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    # Import here to ensure monkeypatching takes effect
    from app.utils.db_utils import get_database_url

    # Test with DATABASE_URL
    db_url = get_database_url()
    assert db_url == "postgresql://testuser:testpass@localhost:5432/testdb"

    # Test with no database config (should use SQLite)
    for key in env_vars:
        monkeypatch.delenv(key, raising=False)

    db_url = get_database_url()
    assert db_url.startswith("sqlite:///")
    assert "instance/app.db" in db_url


def test_get_database_url_aws_secrets(monkeypatch):
    """Test getting database URL from AWS Secrets Manager."""
    # Mock AWS Secrets Manager response
    secret_value = {
        "username": "testuser",
        "password": "testpass",  # noqa: S105
        "host": "aws-host.rds.amazonaws.com",
        "port": "5432",
        "dbname": "awsdb",
    }

    # Mock environment variable
    secret_arn = "arn:aws:secretsmanager:us-west-2:123456789012:secret:test-secret"
    monkeypatch.setenv("DB_SECRET_ARN", secret_arn)

    # Mock boto3 client and session
    with patch("boto3.session.Session") as mock_session:
        mock_client = MagicMock()
        mock_session.return_value.client.return_value = mock_client
        mock_client.get_secret_value.return_value = {"SecretString": json.dumps(secret_value)}

        # Import here to ensure monkeypatching takes effect
        from app.utils.db_utils import get_database_url

        db_url = get_database_url()

        # Verify the expected database URL format
        expected = "postgresql://testuser:testpass@aws-host.rds.amazonaws.com:5432/awsdb"
        assert db_url == expected

        # Verify the boto3 client was called with the correct parameters
        mock_session.return_value.client.assert_called_once_with(service_name="secretsmanager", region_name="us-east-1")
        mock_client.get_secret_value.assert_called_once_with(SecretId=secret_arn)
