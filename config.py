"""Application configuration.

This module provides environment-specific configuration settings for the application.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """Base configuration with settings common to all environments."""

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-key-change-in-production")

    # Flask settings
    DEBUG: bool = os.getenv("FLASK_DEBUG", "0").lower() == "1"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
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

    # Application settings
    APP_NAME: str = os.getenv("APP_NAME", "meal-expense-tracker")
    SERVER_NAME: str = os.getenv("SERVER_NAME", "localhost:5000")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "dev")

    # File upload settings
    UPLOAD_FOLDER: str = os.path.join(os.path.dirname(__file__), "app", "static", "uploads")
    MAX_CONTENT_LENGTH: int = 5 * 1024 * 1024  # 5MB max file size

    # S3 settings for receipt storage
    # If S3_RECEIPTS_BUCKET is set, S3 is enabled; otherwise use local storage
    S3_RECEIPTS_BUCKET: Optional[str] = os.getenv("S3_RECEIPTS_BUCKET")
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")
    S3_RECEIPTS_PREFIX: str = os.getenv("S3_RECEIPTS_PREFIX", "receipts/")
    S3_URL_EXPIRY: int = int(os.getenv("S3_URL_EXPIRY", "3600"))  # 1 hour default

    # Notification configuration (AWS SNS)
    NOTIFICATIONS_ENABLED: bool = os.getenv("NOTIFICATIONS_ENABLED", "true").lower() == "true"
    SNS_TOPIC_ARN: str = ""  # Will be set in __init__

    def __init__(self) -> None:
        """Initialize configuration."""
        # Set environment if not set
        os.environ.setdefault("FLASK_ENV", "development")

        # Configure database URI
        self.SQLALCHEMY_DATABASE_URI = self._get_database_uri()

        # Configure session
        self._configure_session()

        # Configure SNS topic ARN
        self._configure_sns_topic_arn()

    def _get_database_uri(self) -> str:
        """Get the appropriate database URI for the current environment."""
        # Handle Heroku-style database URLs
        if "DATABASE_URL" in os.environ:
            uri = os.environ["DATABASE_URL"]
            if uri.startswith("postgres://"):
                uri = uri.replace("postgres://", "postgresql://", 1)
            return uri

        # In Lambda environment without DATABASE_URL, fetch from Secrets Manager
        if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            try:
                from app.database import _get_lambda_database_uri

                return _get_lambda_database_uri()
            except Exception:
                # If we can't import or fetch, return placeholder - will be resolved later
                return "postgresql+pg8000://"

        # Default to SQLite in development
        # Skip creating directories in Lambda (read-only filesystem)
        if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            return "sqlite:///:memory:"

        instance_path = Path(__file__).parent / "instance"
        instance_path.mkdir(exist_ok=True)
        return f'sqlite:///{instance_path}/app-{os.getenv("FLASK_ENV")}.db'

    def _configure_session(self) -> None:
        """Configure session settings based on environment."""
        # Use Flask's built-in signed cookie sessions for all environments
        self._setup_signed_cookie_session()

        # Configure secure cookie settings based on HTTPS availability
        self._configure_cookie_security()

    def _configure_cookie_security(self) -> None:
        """Configure cookie security settings based on environment and HTTPS availability."""
        # Detect environment
        is_lambda = os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None
        environment = os.getenv("ENVIRONMENT", "dev")

        # Smart cookie configuration based on environment
        if is_lambda and environment == "dev":
            # Lambda development - use API Gateway compatible settings
            self.SESSION_COOKIE_SECURE = True  # HTTPS required
            self.SESSION_COOKIE_HTTPONLY = True
            self.SESSION_COOKIE_SAMESITE = "Lax"  # Try Lax instead of None for API Gateway
        elif is_lambda:
            # Lambda production - use secure settings
            self.SESSION_COOKIE_SECURE = True
            self.SESSION_COOKIE_HTTPONLY = True
            self.SESSION_COOKIE_SAMESITE = "Lax"
        else:
            # Local development - use standard HTTP settings
            self.SESSION_COOKIE_SECURE = False  # Allow HTTP for localhost
            self.SESSION_COOKIE_HTTPONLY = True
            self.SESSION_COOKIE_SAMESITE = "Lax"  # Standard SameSite for localhost

        # Log the configuration for debugging
        print(
            f"Cookie security: SECURE={self.SESSION_COOKIE_SECURE}, HTTPONLY={self.SESSION_COOKIE_HTTPONLY}, SAMESITE={self.SESSION_COOKIE_SAMESITE}"
        )

    def _configure_sns_topic_arn(self) -> None:
        """Configure SNS topic ARN for notifications."""
        # Try to get from environment first (set by Terraform)
        env_arn = os.getenv("SNS_TOPIC_ARN")
        if env_arn and env_arn != "arn:aws:sns:::notifications":  # Check for placeholder
            self.SNS_TOPIC_ARN = env_arn
            return

        # If not in environment, try to construct it
        try:
            import boto3

            # Get current AWS region and account
            region = os.getenv("AWS_REGION", "us-east-1")
            # Try to get account ID from STS
            sts_client = boto3.client("sts", region_name=region)
            account_id = sts_client.get_caller_identity()["Account"]

            # Construct SNS topic ARN
            app_name = os.getenv("APP_NAME", "meal-expense-tracker").replace("_", "-")
            environment = os.getenv("ENVIRONMENT", "dev")

            self.SNS_TOPIC_ARN = f"arn:aws:sns:{region}:{account_id}:{app_name}-{environment}-notifications"
        except Exception:
            # If we can't construct it, leave as empty string
            self.SNS_TOPIC_ARN = ""

    def _setup_signed_cookie_session(self) -> None:
        """Setup signed cookie session configuration for all environments.

        Uses Flask's default session interface with signed cookies.
        This is ideal for all environments as it requires no external storage.
        """
        # Use Flask's default signed cookie sessions
        self.SESSION_TYPE = None  # This uses Flask's default SecureCookieSessionInterface

        # Cookie settings will be configured by _configure_cookie_security()
        # This ensures consistent behavior across all session types

        self.SESSION_PERMANENT = True
        self.PERMANENT_SESSION_LIFETIME = 3600  # 1 hour

        # Enable session signing
        self.SESSION_USE_SIGNER = True

        # Additional security settings
        self.SESSION_COOKIE_NAME = "session"
        self.SESSION_COOKIE_PATH = "/"


class DevelopmentConfig(Config):
    """Development configuration."""

    # DEBUG: bool = True
    # Cookie security is now automatically configured based on HTTPS availability
    # SESSION_COOKIE_SECURE will be False for HTTP development, True for HTTPS
    # SESSION_COOKIE_HTTPONLY and SESSION_COOKIE_SAMESITE are always enabled for security


class UnitTestConfig(Config):  # noqa: D101
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
        "testing": UnitTestConfig,
        "production": ProductionConfig,
    }

    config_class = configs.get(env, DevelopmentConfig)
    return config_class()
