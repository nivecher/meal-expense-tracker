"""Test configuration for SQLite in-memory database with SQLAlchemy 2.0."""

from typing import Any, Dict


class TestConfig:
    """Test configuration with SQLite in-memory database for SQLAlchemy 2.0."""

    # Application settings
    SECRET_KEY = "test-secret-key"
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False
    LOGIN_DISABLED = False

    # Database settings for SQLAlchemy 2.0
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:?check_same_thread=False"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SQLAlchemy 2.0 engine options
    SQLALCHEMY_ENGINE_OPTIONS: Dict[str, Any] = {
        "connect_args": {"check_same_thread": False},
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "echo": False,
    }

    # Session configuration
    SQLALCHEMY_SESSION_OPTIONS: Dict[str, Any] = {
        "expire_on_commit": False,
        "autoflush": False,
    }

    # Login manager configuration
    LOGIN_DISABLED = False
    LOGIN_VIEW = "auth.login"
    LOGIN_MESSAGE_CATEGORY = "info"

    # Required for URL generation in tests
    SERVER_NAME = "localhost:5000"
    APPLICATION_ROOT = "/"
    PREFERRED_URL_SCHEME = "http"
