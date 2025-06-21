"""Script to check database connectivity and list tables.

This script provides functionality to test database connectivity and inspect
the database schema by listing all tables and their columns. It supports
multiple methods of database connection configuration including direct
environment variables and AWS Secrets Manager.
"""

import json
import logging
import os
import sys
from typing import Dict

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine
from sqlalchemy.engine.reflection import Inspector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Type aliases
SecretDict = Dict[str, str]  # Type for database secret dictionary


def _get_secret_dict(secret_arn: str) -> SecretDict:
    """Retrieve database credentials from AWS Secrets Manager.

    Args:
        secret_arn: ARN of the secret in AWS Secrets Manager

    Returns:
        SecretDict: Dictionary containing database connection parameters with
        standard keys

    Raises:
        ValueError: If required keys are missing from the secret
        ClientError: For AWS client errors
        json.JSONDecodeError: If secret value is not valid JSON
    """
    try:
        # Initialize AWS Secrets Manager client
        session = boto3.Session()
        client = session.client("secretsmanager")

        # Get the secret value
        logger.debug("Retrieving secret from ARN: %s", secret_arn)
        secret = client.get_secret_value(SecretId=secret_arn)
        secret_dict: Dict[str, str] = json.loads(secret["SecretString"])

        # Log available keys for debugging
        logger.debug("Available secret keys: %s", ", ".join(secret_dict.keys()))

        # Map of possible key variations to standard keys
        key_mapping = {
            # Standard keys (no prefix)
            "username": ["username", "user", "dbuser", "db_username"],
            "password": ["password", "pass", "dbpassword", "db_password"],
            "host": ["host", "hostname", "endpoint", "dbhost", "db_host"],
            "port": ["port", "dbport", "db_port"],
            "dbname": ["dbname", "database", "name", "db", "db_name", "db_database"],
        }

        # Also check for db_ prefixed versions
        for std_key in list(key_mapping.keys()):
            key_mapping[std_key].extend([f"db_{std_key}"])

        # Find the actual key for each standard key
        result = {}
        for std_key, possible_keys in key_mapping.items():
            # Look for each possible key variation
            for key in possible_keys:
                if key in secret_dict:
                    result[std_key] = secret_dict[key]
                    break
            else:
                # If we get here, no variation of the key was found
                raise ValueError(f"Could not find any of {possible_keys} in secret")

        # Ensure port is a string
        if "port" in result and not isinstance(result["port"], str):
            result["port"] = str(result["port"])

        logger.debug(
            "Resolved secret keys: %s",
            ", ".join(
                f"{k}:{'*' * len(v) if 'pass' in k else v}" for k, v in result.items()
            ),
        )

        return result

    except (ClientError, json.JSONDecodeError) as e:
        logger.error("Error retrieving secret from AWS: %s", str(e), exc_info=True)
        raise
    except Exception as e:
        logger.error("Unexpected error processing secret: %s", str(e), exc_info=True)
        raise


def get_db_uri() -> str:
    """Get database URI from environment variables.

    Priority order:
    1. DATABASE_URL environment variable
    2. AWS Secrets Manager (if DB_SECRET_ARN is set)
    3. Individual DB_* environment variables

    Returns:
        str: Database connection URI

    Raises:
        ValueError: If required environment variables are missing
        Exception: For AWS Secrets Manager or other errors
    """
    load_dotenv()

    # 1. Check for direct database URL
    if db_url := os.getenv("DATABASE_URL"):
        logger.debug("Using DATABASE_URL from environment")
        return db_url

    # 2. Check for AWS Secrets Manager
    if secret_arn := os.getenv("DB_SECRET_ARN"):
        logger.debug("Using DB_SECRET_ARN from environment")
        try:
            secret_dict = _get_secret_dict(secret_arn)
            return (
                f"postgresql://{secret_dict['username']}:"
                f"{secret_dict['password']}@{secret_dict['host']}:"
                f"{secret_dict['port']}/{secret_dict['dbname']}"
            )
        except Exception as e:
            logger.error("Failed to get database URI from secret: %s", str(e))
            raise

    # 3. Fallback to individual environment variables
    required_vars = ["DB_USERNAME", "DB_PASSWORD", "DB_HOST", "DB_NAME"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.error(msg)
        raise ValueError(msg)

    logger.debug("Using individual DB_* environment variables")
    return (
        f"postgresql://{os.getenv('DB_USERNAME')}:"
        f"{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:"
        f"{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}"
    )


def _test_database_connection(engine: Engine) -> None:
    """Test database connection by executing a simple query.

    Args:
        engine: SQLAlchemy engine instance

    Raises:
        SQLAlchemyError: If connection test fails
    """
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def _log_database_schema(inspector: Inspector) -> None:
    """Log database schema information.

    Args:
        inspector: SQLAlchemy inspector instance
    """
    tables = inspector.get_table_names()
    logger.info(
        "Found %d table(s): %s",
        len(tables),
        ", ".join(sorted(tables)) if tables else "No tables found",
    )

    for table_name in sorted(tables):
        columns = [col["name"] for col in inspector.get_columns(table_name)]
        logger.info("Table '%s' columns: %s", table_name, ", ".join(columns))


def check_database() -> bool:
    """Check database connection and list tables.

    Returns:
        bool: True if database check was successful, False otherwise
    """
    try:
        db_uri = get_db_uri()
        logger.info("Connecting to database: %s", db_uri.split("@")[-1])

        engine = create_engine(db_uri)
        inspector = inspect(engine)

        _test_database_connection(engine)
        _log_database_schema(inspector)

        return True

    except SQLAlchemyError as e:
        logger.error("Database error: %s", str(e), exc_info=True)
        return False
    except Exception as e:
        logger.error("Unexpected error: %s", str(e), exc_info=True)
        return False


def main() -> int:
    """Run the database check and return appropriate exit code.

    Returns:
        int: 0 on success, 1 on failure
    """
    try:
        success = check_database()
        logger.info("Database check %s", "succeeded" if success else "failed")
        return 0 if success else 1
    except Exception as e:
        logger.critical("Fatal error during database check: %s", str(e), exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
