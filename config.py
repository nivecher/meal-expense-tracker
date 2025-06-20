import os
import json
import boto3
import logging
from botocore.exceptions import ClientError
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


def get_secret(secret_arn=None, region_name="us-west-2"):
    """Retrieve secret from AWS Secrets Manager.

    Args:
        secret_arn (str): The ARN of the secret in AWS Secrets Manager
        region_name (str): AWS region where the secret is stored

    Returns:
        dict: The secret value as a dictionary, or None if retrieval fails
    """
    if not secret_arn:
        return None

    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)

    try:
        response = client.get_secret_value(SecretId=secret_arn)
    except ClientError as e:
        logging.error(f"Error retrieving secret: {e}")
        return None

    if "SecretString" in response:
        return json.loads(response["SecretString"])
    return None


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"

    def _get_database_uri(self):
        """Dynamically construct the database URI based on the environment.

        Returns:
            str: A valid database connection string

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        # Check for explicit DATABASE_URL first
        if "DATABASE_URL" in os.environ:
            db_url = os.environ["DATABASE_URL"]
            if not db_url:
                raise ValueError("DATABASE_URL environment variable is empty")
            return db_url

        # In Lambda environment, use RDS connection
        if "AWS_LAMBDA_FUNCTION_NAME" in os.environ:
            db_url = self._get_rds_connection_uri()
            if not db_url:
                raise ValueError(
                    "Failed to construct RDS connection URI. "
                    "Check DB_HOST, DB_NAME, DB_USERNAME, and "
                    "DB_SECRET_ARN environment variables."
                )
            return db_url

        # Default to SQLite for local development
        db_path = os.path.join(basedir, "instance/meal_expenses.db")
        return f"sqlite:///{db_path}"

    def _get_rds_connection_uri(self):
        """
        Construct RDS connection URI using environment variables and Secrets Manager.

        Returns:
            str: PostgreSQL connection string or None if configuration is incomplete

        Raises:
            ValueError: If required configuration is missing or invalid
        """
        # Get required environment variables
        db_secret_arn = os.environ.get("DB_SECRET_ARN")

        # Validate required variables
        missing_vars = []
        if not db_secret_arn:
            missing_vars.append("DB_SECRET_ARN")

        if missing_vars:
            logging.error(
                f"Missing required database configuration: {', '.join(missing_vars)}"
            )
            return None

        # Get database password from Secrets Manager
        region = os.environ.get("AWS_REGION", "us-east-1")
        try:
            secret = get_secret(db_secret_arn, region)
            if not secret or "db_password" not in secret:
                logging.error(
                    f"Failed to retrieve or invalid database password from secret: "
                    f"{db_secret_arn}"
                )
                return None

            db_password = secret["db_password"]
            db_user = secret["db_user"]
            db_host = secret["db_host"]
            db_port = secret["db_port"]
            db_name = secret["db_name"]
            if not db_password:
                logging.error("Database password is empty in secret")
                return None

            # Construct and return the connection string
            connection_uri = (
                f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            )
            logging.info(
                f"Successfully constructed database connection URI for "
                f"{db_user}@{db_host}:{db_port}/{db_name}"
            )
            return connection_uri

        except Exception as e:
            logging.error(
                f"Error constructing database connection URI: {str(e)}", exc_info=True
            )
            return None

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")

    @classmethod
    def init_app(cls, app):
        """Initialize configuration for the Flask app.

        Args:
            app: The Flask application instance

        Raises:
            ValueError: If database configuration is invalid
        """
        config = cls()

        try:
            # Get database URI and validate it
            db_uri = config._get_database_uri()
            if not db_uri:
                raise ValueError(
                    "Failed to determine database URI. Check logs for details."
                )

            # Set SQLAlchemy configuration
            app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
            app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
                "pool_pre_ping": True,
                "pool_recycle": 300,  # Recycle connections after 5 minutes
            }

            # Load remaining configuration
            app.config.from_object(cls)
            app.config.from_prefixed_env()

            # Log database configuration (without password)
            if "sqlite" not in db_uri.lower():
                safe_uri = db_uri.split("@")[-1] if "@" in db_uri else db_uri
                logging.info(f"Database connection configured for: {safe_uri}")

            # Skip directory creation in Lambda environment
            if "AWS_LAMBDA_FUNCTION_NAME" not in os.environ:
                # Ensure instance folder exists (only in non-Lambda environments)
                os.makedirs(os.path.join(basedir, "instance"), exist_ok=True)

        except Exception as e:
            logging.error(
                f"Failed to initialize application configuration: {str(e)}",
                exc_info=True,
            )
            raise


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
