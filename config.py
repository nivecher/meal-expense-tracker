"""Application configuration."""

import os


class Config:
    """Base configuration class."""

    SECRET_KEY = os.environ.get("SECRET_KEY") or "a-hard-to-guess-string"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_recycle": 280}
    DEBUG = False
    TESTING = False

    # Google Maps API Configuration
    GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("DEV_DATABASE_URL") or "sqlite:///" + os.path.join(
        os.path.abspath(os.path.dirname(__file__)), "instance/app-dev.db"
    )
    WTF_CSRF_ENABLED = False


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL") or "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    # Disable rate limiting in tests
    RATELIMIT_ENABLED = False
    # Use in-memory storage for rate limiting
    RATELIMIT_STORAGE_URL = "memory://"


class ProductionConfig(Config):
    """Production configuration for AWS Lambda."""

    # Use class variables instead of instance variables
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")

    def __init__(self):
        # In Lambda, we should use a proper database like RDS or Aurora
        if not self.SQLALCHEMY_DATABASE_URI:
            # If no DATABASE_URL is set, fall back to SQLite in /tmp (not recommended for production)
            db_path = "/tmp/app-prod.db"
            self.SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
            self.SQLALCHEMY_ENGINE_OPTIONS = {
                "pool_recycle": 280,
                "connect_args": {"timeout": 15, "check_same_thread": False},
            }
        else:
            # For PostgreSQL/RDS, set appropriate engine options
            self.SQLALCHEMY_ENGINE_OPTIONS = {
                "pool_pre_ping": True,
                "pool_recycle": 300,
                "pool_size": 5,
                "max_overflow": 10,
                "pool_timeout": 30,
                "connect_args": {"connect_timeout": 10},
            }


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
