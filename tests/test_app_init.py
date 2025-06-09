import json
import sys
import importlib
from unittest.mock import patch, MagicMock

from app import create_app, version, get_db_credentials


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
            "SERVER_NAME": "localhost:5001",
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
        assert app.config["GOOGLE_MAPS_API_KEY"] == "test-key"
        assert app.config["SERVER_NAME"] == "localhost:5001"
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
    monkeypatch.setenv("FLASK_ENV", "development")

    if "app" in sys.modules:
        importlib.reload(sys.modules["app"])

    credentials = get_db_credentials()
    assert credentials == {
        "username": "sqlite_user",
        "password": "sqlite_password",
        "database_url": "sqlite:///instance/meal_expenses.db",
    }


def test_get_db_credentials_aws_secrets(monkeypatch):
    """Test getting DB credentials from AWS Secrets Manager."""
    monkeypatch.setenv("FLASK_ENV", "production")

    mock_secret = {"username": "awsuser", "password": "awspass"}

    secret_arn = "arn:aws:secretsmanager:us-east-1:123456789012:secret:db-credentials"
    test_env_vars = {
        "AWS_REGION": "us-east-1",
        "DB_SECRET_ARN": secret_arn,
        "DB_HOST": "db-host",
        "DB_NAME": "dbname",
    }

    for key, value in test_env_vars.items():
        monkeypatch.setenv(key, value)

    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretString": json.dumps(mock_secret)
    }

    with patch("boto3.client", return_value=mock_client) as mock_boto3:
        if "app" in sys.modules:
            del sys.modules["app"]

        from app import get_db_credentials

        credentials = get_db_credentials()

        mock_boto3.assert_called_once_with("secretsmanager", region_name="us-east-1")
        mock_client.get_secret_value.assert_called_once_with(SecretId=secret_arn)

        assert credentials == {
            "username": "awsuser",
            "password": "awspass",
            "database_url": "postgresql://awsuser:awspass@db-host/dbname",
        }
