"""Application configuration.

This module provides environment-specific configuration settings for the application.
"""

import os
from pathlib import Path
from typing import Any, Dict


class Config:
    """Base configuration with settings common to all environments."""

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-key-change-in-production")

    # Flask settings
    DEBUG: bool = False
    TESTING: bool = False

    # Database settings
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: Dict[str, Any] = {
        "pool_pre_ping": True,
        "pool_recycle": 300,  # 5 minutes
    }

    # Session settings
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"
    SESSION_PERMANENT: bool = True
    PERMANENT_SESSION_LIFETIME: int = 3600  # 1 hour in seconds

    # Google Maps API
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    GOOGLE_MAPS_MAP_ID: str = os.getenv("GOOGLE_MAPS_MAP_ID", "")

    def __init__(self) -> None:
        """Initialize configuration."""
        # Set environment if not set
        os.environ.setdefault("FLASK_ENV", "development")

        # Configure database URI
        self.SQLALCHEMY_DATABASE_URI = self._get_database_uri()

        # Configure session
        self._configure_session()

    def _get_database_uri(self) -> str:
        """Get the appropriate database URI for the current environment."""
        # Handle Heroku-style database URLs
        if "DATABASE_URL" in os.environ:
            uri = os.environ["DATABASE_URL"]
            if uri.startswith("postgres://"):
                uri = uri.replace("postgres://", "postgresql://", 1)
            return uri

        # Default to SQLite in development
        instance_path = Path(__file__).parent / "instance"
        instance_path.mkdir(exist_ok=True)
        return f'sqlite:///{instance_path}/app-{os.getenv("FLASK_ENV")}.db'

    def _configure_session(self) -> None:
        """Configure session settings based on environment."""
        if os.getenv("FLASK_ENV") == "production":
            self._configure_production_session()
        else:
            self._configure_development_session()

    def _configure_production_session(self) -> None:
        """Configure production session settings with DynamoDB."""
        self.SESSION_TYPE = "dynamodb"
        self.SESSION_DYNAMODB_TABLE = os.getenv("SESSION_TABLE_NAME", "flask_sessions")
        self.SESSION_DYNAMODB_REGION = os.getenv("AWS_REGION", "us-east-1")
        self.SESSION_DYNAMODB_ENDPOINT_URL = os.getenv("SESSION_DYNAMODB_ENDPOINT")
        self.SESSION_USE_SIGNER = True

    def _configure_development_session(self) -> None:
        """Configure development session settings with filesystem."""
        self.SESSION_TYPE = "filesystem"
        # Use tempfile for secure temporary directory
        import tempfile

        self.SESSION_FILE_DIR = tempfile.mkdtemp(prefix="flask_session_")
        self.SESSION_FILE_THRESHOLD = 100


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG: bool = True
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_HTTPONLY: bool = False


class TestingConfig(Config):
    """Testing configuration."""

    TESTING: bool = True
    DEBUG: bool = True
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_HTTPONLY: bool = False


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG: bool = False
    TESTING: bool = False


def get_config() -> Config:
    """Get the appropriate configuration based on environment."""
    env = os.getenv("FLASK_ENV", "development").lower()

    configs = {
        "development": DevelopmentConfig,
        "testing": TestingConfig,
        "production": ProductionConfig,
    }

    config_class = configs.get(env, DevelopmentConfig)
    return config_class()
