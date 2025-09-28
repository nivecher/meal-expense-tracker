"""Application configuration.

This module provides simplified, environment-specific configuration settings for the application.
Uses signed cookies for sessions across all environments for simplicity and reliability.
"""

import os
from pathlib import Path


class Config:
    """Base configuration with settings common to all environments."""

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-key-change-in-production")

    # Flask settings
    DEBUG: bool = False
    TESTING: bool = False

    # Database settings
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,  # 5 minutes
    }

    # Session settings - Simplified to use signed cookies everywhere
    SESSION_PERMANENT: bool = True
    PERMANENT_SESSION_LIFETIME: int = 3600  # 1 hour in seconds
    SESSION_COOKIE_NAME: str = "session"
    SESSION_COOKIE_PATH: str = "/"
    SESSION_USE_SIGNER: bool = True
    
    # Google Maps API
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    GOOGLE_MAPS_MAP_ID: str = os.getenv("GOOGLE_MAPS_MAP_ID", "")

    # Application settings
    APP_NAME: str = os.getenv("APP_NAME", "Meal Expense Tracker")

    # Email configuration (AWS SES only)
    MAIL_ENABLED: bool = os.getenv("MAIL_ENABLED", "false").lower() == "true"
    MAIL_DEFAULT_SENDER: str = os.getenv("MAIL_DEFAULT_SENDER", "noreply@nivecher.com")
    AWS_SES_REGION: str = os.getenv("AWS_SES_REGION", "us-east-1")

    def __init__(self) -> None:
        """Initialize configuration."""
        # Set environment if not set
        os.environ.setdefault("FLASK_ENV", "development")

        # Configure database URI
        self.SQLALCHEMY_DATABASE_URI = self._get_database_uri()
        
        # Configure simplified session and cookie security
        self._configure_session_security()

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

    def _configure_session_security(self) -> None:
        """Configure session and cookie security settings.
        
        Simplified approach: Use signed cookies for all environments with
        environment-appropriate security settings.
        """
        # Detect if we're in a secure environment (Lambda/production)
        is_lambda = os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None
        is_production = os.getenv("FLASK_ENV", "development").lower() == "production"
        is_secure_env = is_lambda or is_production
        
        # Configure cookie security based on environment
        if is_secure_env:
            # Production/Lambda: Secure settings for HTTPS
            self.SESSION_COOKIE_SECURE = True
            self.SESSION_COOKIE_HTTPONLY = True
            self.SESSION_COOKIE_SAMESITE = "Lax"
            self.SESSION_COOKIE_DOMAIN = None  # Let Flask handle domain detection
        else:
            # Development: Allow HTTP for local development
            self.SESSION_COOKIE_SECURE = False  # Allow HTTP for localhost
            self.SESSION_COOKIE_HTTPONLY = True  # Still secure from XSS
            self.SESSION_COOKIE_SAMESITE = "Lax"
            self.SESSION_COOKIE_DOMAIN = None


class DevelopmentConfig(Config):
    """Development configuration."""
    
    DEBUG: bool = True


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