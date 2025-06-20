"""Application configuration.

This module handles all configuration for the application, including:
- Environment variable loading
- Database connection management
- AWS service configuration

Environment variables take precedence over .env file values.
"""

import os
import json
import boto3
import logging
import urllib.parse
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
# Note: In Lambda, environment variables should be set via the Lambda configuration
basedir = os.path.abspath(os.path.dirname(__file__))
if os.path.exists(os.path.join(basedir, ".env")) and not os.environ.get(
    "AWS_LAMBDA_FUNCTION_NAME"
):
    load_dotenv(os.path.join(basedir, ".env"))

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_secret(secret_arn, region_name=None):
    """Retrieve a secret from AWS Secrets Manager.

    Args:
        secret_arn (str): The ARN of the secret to retrieve
        region_name (str, optional): AWS region name. If not provided, will use AWS_REGION or us-east-1

    Returns:
        dict: The secret value as a dictionary

    Raises:
        ValueError: If secret_arn is not provided or secret retrieval fails
    """
    if not secret_arn:
        raise ValueError("Secret ARN is required")

    region = region_name or os.environ.get("AWS_REGION", "us-east-1")

    try:
        session = boto3.session.Session()
        client = session.client(service_name="secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=secret_arn)

        if "SecretString" not in response:
            raise ValueError("No SecretString in response from Secrets Manager")

        return json.loads(response["SecretString"])

    except ClientError as e:
        logger.error(f"Error retrieving secret from Secrets Manager: {e}")
        raise ValueError(f"Failed to retrieve secret: {str(e)}")
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing secret JSON: {e}")
        raise ValueError("Invalid JSON in secret value")


class Config:
    """Base configuration class with settings common to all environments."""

    # Application settings
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"
    DEBUG = False
    TESTING = False

    # Database settings
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_timeout": 30,
        "pool_size": 5,
        "max_overflow": 10,
    }

    def _get_database_uri(self):
        """Dynamically construct the database URI based on the environment.

        Priority order for database configuration:
        1. DATABASE_URL environment variable (direct override)
        2. RDS connection via Secrets Manager (AWS Lambda)
        3. Direct environment variables (DB_*)
        4. SQLite (development default)

        Returns:
            str: A valid SQLAlchemy database URI

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        # Log which environment we're running in
        env_type = (
            "AWS Lambda" if os.environ.get("AWS_LAMBDA_FUNCTION_NAME") else "Local"
        )
        logger.info(f"Running in {env_type} environment")

        # 1. Check for explicit DATABASE_URL (highest priority)
        if db_url := os.environ.get("DATABASE_URL"):
            logger.info("Using DATABASE_URL from environment")
            return db_url

        # 2. In Lambda, use RDS connection via Secrets Manager
        if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            logger.info("Running in AWS Lambda environment, attempting RDS connection")
            try:
                db_url = self._get_rds_connection_uri()
                logger.info("Successfully constructed RDS connection URI")
                return db_url
            except Exception as e:
                logger.error("Failed to initialize RDS connection", exc_info=True)
                # In production, you might want to fail fast
                if os.environ.get("FLASK_ENV") == "production":
                    raise
                logger.warning(
                    "Falling back to direct DB config due to RDS connection error"
                )

        # 3. Check for direct DB environment variables
        db_host = os.environ.get("DB_HOST")
        if db_host:
            # Build connection string from individual components
            db_config = {
                "username": os.environ.get("DB_USERNAME"),
                "password": os.environ.get("DB_PASSWORD"),
                "host": db_host,
                "port": os.environ.get("DB_PORT", "5432"),
                "dbname": os.environ.get("DB_NAME"),
            }

            if all(db_config.values()):
                logger.info("Using direct DB environment variables for connection")
                return (
                    "postgresql://{username}:{password}@{host}:{port}/{dbname}".format(
                        username=db_config["username"],
                        password=urllib.parse.quote_plus(db_config["password"]),
                        host=db_config["host"],
                        port=db_config["port"],
                        dbname=db_config["dbname"],
                    )
                )

        # 4. Default to SQLite for local development as last resort
        if os.environ.get("FLASK_ENV") == "production":
            raise ValueError(
                "Database configuration is required in production. "
                "Please set DATABASE_URL or DB_* environment variables."
            )

        logger.warning("No database configuration found, defaulting to SQLite")
        db_path = os.path.join(basedir, "instance/meal_expenses.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return f"sqlite:///{db_path}"

    def _get_rds_connection_uri(self):
        """Construct a PostgreSQL connection string from AWS Secrets Manager.

        Returns:
            str: PostgreSQL connection string

        Raises:
            ValueError: If secret retrieval fails or required fields are missing
        """
        db_secret_arn = os.environ.get("DB_SECRET_ARN")
        if not db_secret_arn:
            raise ValueError("DB_SECRET_ARN environment variable is not set")

        logger.info(f"Retrieving database secret from ARN: {db_secret_arn}")

        try:
            # Get secret from AWS Secrets Manager
            secret = get_secret(db_secret_arn)

            # Extract and validate required fields
            required_fields = {
                "db_username": "DB username",
                "db_password": "DB password",
                "db_host": "DB host",
                "db_port": "DB port",
                "db_name": "DB name",
            }

            # Validate all required fields exist and are non-empty
            missing = []
            for field in required_fields:
                if not secret.get(field):
                    missing.append(field)

            if missing:
                raise ValueError(
                    f"Missing or empty required secret fields: {', '.join(missing)}"
                )

            # Construct connection string with URL-encoded password
            connection_uri = (
                f"postgresql://{secret['db_username']}:"
                f"{urllib.parse.quote_plus(secret['db_password'])}"
                f"@{secret['db_host']}:{secret['db_port']}/{secret['db_name']}"
            )

            # Log a masked version for security
            logger.info(
                f"Constructed database connection to {secret['db_host']} "
                f"for database {secret['db_name']}"
            )

            return connection_uri

        except Exception as e:
            logger.error("Failed to construct RDS connection URI", exc_info=True)
            raise ValueError(f"Failed to construct database connection: {str(e)}")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")

    @classmethod
    def init_app(cls, app):
        """Initialize configuration for the Flask app.

        This method is called by create_app() after the app is created.
        It sets up the database connection and other app configurations.

        Args:
            app: The Flask application instance

        Raises:
            ValueError: If database configuration is invalid
        """
        config = cls()

        try:
            # Get database URI and validate it
            db_uri = config._get_database_uri()

            # Configure SQLAlchemy
            app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
            app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

            # Log database configuration (masking sensitive information)
            if db_uri.startswith("postgresql"):
                # Extract just the host and database name for logging
                parts = db_uri.split("@")
                safe_uri = parts[-1].split("?")[0] if "?" in parts[-1] else parts[-1]
                logger.info(f"Database connection configured for: {safe_uri}")
            else:
                logger.info(f"Using database: {db_uri.split('://')[0]}")

            # Create instance directory for SQLite if needed
            if db_uri.startswith("sqlite") and not os.environ.get(
                "AWS_LAMBDA_FUNCTION_NAME"
            ):
                db_path = db_uri.split("sqlite:///")[-1]
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
                logger.info(f"SQLite database will be created at: {db_path}")

        except Exception as e:
            logger.critical(
                "Failed to initialize application configuration", exc_info=True
            )
            raise ValueError(f"Failed to initialize application: {str(e)}")


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    pass


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
