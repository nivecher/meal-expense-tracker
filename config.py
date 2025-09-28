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
    APP_NAME: str = os.getenv("APP_NAME", "Meal Expense Tracker")

    # Email configuration (AWS SES only)
    MAIL_ENABLED: bool = os.getenv("MAIL_ENABLED", "false").lower() == "true"
    MAIL_DEFAULT_SENDER: str = os.getenv("MAIL_DEFAULT_SENDER", "noreply@nivecher.com")

    # AWS SES configuration (uses IAM roles by default)
    AWS_SES_REGION: str = os.getenv("AWS_SES_REGION", "us-east-1")

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
        # Use DynamoDB for all environments if SESSION_TYPE is explicitly set to dynamodb
        # or if running in production
        session_type = os.getenv("SESSION_TYPE", "").lower()
        flask_env = os.getenv("FLASK_ENV", "development")
        is_lambda = os.getenv("AWS_LAMBDA_FUNCTION_NAME") is not None

        # For now, use signed cookies in Lambda to avoid table creation issues
        # TODO: Fix DynamoDB session configuration to work with existing tables
        if is_lambda:
            # For Lambda environments, use signed cookies to avoid permission issues
            self._setup_signed_cookie_session()
        elif session_type == "dynamodb" or flask_env == "production":
            self._setup_dynamodb_session()
        else:
            self._setup_filesystem_session()

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

    def _setup_dynamodb_session(self) -> None:
        """Setup DynamoDB session configuration with validation."""
        self.SESSION_TYPE = "dynamodb"

        # Session table configuration with validation
        table_name = os.getenv("SESSION_DYNAMODB_TABLE", "flask_sessions")
        if not table_name or len(table_name.strip()) == 0:
            raise ValueError("SESSION_DYNAMODB_TABLE cannot be empty when using DynamoDB sessions")
        self.SESSION_DYNAMODB_TABLE = table_name.strip()

        # AWS region configuration - use SESSION_DYNAMODB_REGION with fallback to built-in AWS_REGION
        region = os.getenv("SESSION_DYNAMODB_REGION") or os.getenv("AWS_REGION", "us-east-1")
        if not region or len(region.strip()) == 0:
            raise ValueError("SESSION_DYNAMODB_REGION or AWS_REGION must be specified for DynamoDB sessions")
        self.SESSION_DYNAMODB_REGION = region.strip()

        # Explicitly configure DynamoDB to use AWS (not localhost)
        # This prevents Flask-Session from defaulting to localhost:8000
        import boto3
        from botocore.config import Config

        # Create DynamoDB resource with explicit AWS configuration and enhanced retry logic
        boto_config = Config(
            region_name=region.strip(),
            retries={"max_attempts": 5, "mode": "adaptive", "total_max_attempts": 10},
            connect_timeout=10,
            read_timeout=30,
        )

        # Optional endpoint for testing/LocalStack only
        endpoint_url = os.getenv("SESSION_DYNAMODB_ENDPOINT")
        if endpoint_url:
            endpoint_url = endpoint_url.strip()
            if endpoint_url:
                self.SESSION_DYNAMODB_ENDPOINT_URL = endpoint_url
                # For LocalStack/testing, create resource with custom endpoint
                self.SESSION_DYNAMODB = boto3.resource(
                    "dynamodb", endpoint_url=endpoint_url, region_name=region.strip(), config=boto_config
                )
            else:
                # Production: use default AWS endpoints
                self.SESSION_DYNAMODB = boto3.resource("dynamodb", region_name=region.strip(), config=boto_config)
        else:
            # Production: use default AWS endpoints (no localhost fallback)
            self.SESSION_DYNAMODB = boto3.resource("dynamodb", region_name=region.strip(), config=boto_config)

        # Security settings
        self.SESSION_USE_SIGNER = True
        self.SESSION_PERMANENT = True

        # Session timeout configuration (in seconds)
        session_timeout = os.getenv("SESSION_TIMEOUT", "3600")  # Default 1 hour
        try:
            self.SESSION_TIMEOUT = int(session_timeout)
        except ValueError:
            self.SESSION_TIMEOUT = 3600  # Fallback to 1 hour

        # Key prefix for session isolation (optional)
        if key_prefix := os.getenv("SESSION_KEY_PREFIX"):
            self.SESSION_KEY_PREFIX = key_prefix.strip()

        # Cookie settings will be configured by _configure_cookie_security()
        # This ensures consistent behavior across all session types

        # DynamoDB-specific settings
        # Disable automatic table creation - table should exist from Terraform
        self.SESSION_DYNAMODB_AUTO_CREATE = False
        self.SESSION_DYNAMODB_AUTO_DELETE = False

        # Optional custom hash function (default is hashlib.sha1)
        # self.SESSION_DYNAMODB_HASH_FUNCTION = "sha256"  # Uncomment for SHA-256

    def _setup_signed_cookie_session(self) -> None:
        """Setup signed cookie session configuration for Lambda environments.

        Uses Flask's default session interface with signed cookies.
        This is ideal for serverless environments as it requires no external storage.
        """
        # Use Flask's default signed cookie sessions
        self.SESSION_TYPE = None  # This uses Flask's default SecureCookieSessionInterface

        # Cookie settings will be configured by _configure_cookie_security()
        # This ensures consistent behavior across all session types

        self.SESSION_PERMANENT = True
        self.PERMANENT_SESSION_LIFETIME = 3600  # 1 hour

        # Enable session signing
        self.SESSION_USE_SIGNER = True

        # Additional security for serverless
        self.SESSION_COOKIE_NAME = "session"
        # Set explicit domain for API Gateway compatibility
        environment = os.getenv("ENVIRONMENT", "dev")
        if environment == "dev":
            # For development, don't set domain to allow subdomain flexibility
            self.SESSION_COOKIE_DOMAIN = None
        else:
            # For production, set explicit domain
            self.SESSION_COOKIE_DOMAIN = None
        self.SESSION_COOKIE_PATH = "/"

    def _setup_filesystem_session(self) -> None:
        """Setup filesystem session configuration."""
        import tempfile

        from cachelib.file import FileSystemCache

        self.SESSION_TYPE = "filesystem"
        # Use FileSystemCache instance instead of deprecated SESSION_FILE_DIR and SESSION_FILE_THRESHOLD
        session_dir = tempfile.mkdtemp(prefix="flask_session_")
        self.SESSION_CACHELIB = FileSystemCache(session_dir, threshold=100, mode=0o600)


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
