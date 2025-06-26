"""Database utility functions for the application."""

import json
import logging
import os
import re
from typing import Any, Dict


def ensure_proper_db_url(db_url: str) -> str:
    """Ensure the database URL is properly formatted for SQLAlchemy.

    Args:
        db_url: The database URL to check/format

    Returns:
        str: Properly formatted database URL
    """
    logger = logging.getLogger(__name__)

    # Handle PostgreSQL URLs
    if db_url.startswith(("postgresql://", "postgres://")):
        # Convert postgres:// to postgresql+psycopg2://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
        # Ensure psycopg2 is specified
        elif "+psycopg2" not in db_url:
            db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    # Log the URL with sensitive information redacted
    safe_url = re.sub(r":([^/:]+)@", ":***@", db_url) if "@" in db_url else db_url
    logger.debug("Using database URL: %s", safe_url)
    return db_url


def get_db_credentials() -> Dict[str, Any]:
    """Retrieve database credentials from environment variables or AWS Secrets Manager.

    Returns:
        Dict containing database credentials

    Raises:
        RuntimeError: If credentials cannot be retrieved
    """
    logger = logging.getLogger(__name__)

    # Try environment variables first
    env_creds = {
        "username": os.getenv("DB_USERNAME"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT", "5432"),
        "dbname": os.getenv("DB_NAME"),
    }

    if all(env_creds.values()):
        logger.info("Using database credentials from environment variables")
        return env_creds

    # Fall back to AWS Secrets Manager if DB_SECRET_ARN is set
    secret_arn = os.getenv("DB_SECRET_ARN")
    if secret_arn:
        logger.info("DB_SECRET_ARN found, attempting to retrieve credentials from AWS Secrets Manager")
        try:
            return get_credentials_from_secrets_manager(secret_arn)
        except Exception as e:
            logger.error("Failed to get credentials from Secrets Manager: %s", str(e))
            if os.getenv("FLASK_ENV") == "production":
                raise RuntimeError(
                    "Failed to retrieve database credentials from AWS Secrets Manager. "
                    "Please verify that the secret exists and the Lambda has the necessary permissions. "
                    f"Error: {str(e)}"
                ) from e
            raise

    # If we get here, no credentials were found
    error_msg = (
        "Could not find valid database credentials. "
        "Please ensure one of the following is configured:\n"
        "1. Set DB_USERNAME, DB_PASSWORD, DB_HOST, DB_PORT, and DB_NAME environment variables\n"
        "2. Set DB_SECRET_ARN to point to a valid AWS Secrets Manager secret"
    )
    logger.error(error_msg)
    raise RuntimeError(error_msg)


def get_credentials_from_secrets_manager(secret_arn: str) -> Dict[str, str]:
    """Retrieve database credentials from AWS Secrets Manager.

    Args:
        secret_arn: ARN of the secret in AWS Secrets Manager

    Returns:
        Dict containing database credentials

    Raises:
        RuntimeError: If the secret cannot be retrieved or is invalid
    """
    import boto3
    from botocore.exceptions import ClientError

    logger = logging.getLogger(__name__)
    logger.info("Fetching database credentials from AWS Secrets Manager")

    try:
        client = boto3.client("secretsmanager", region_name=os.getenv("AWS_REGION", "us-east-1"))
        response = client.get_secret_value(SecretId=secret_arn)
        secret = json.loads(response["SecretString"])

        # Map secret fields to our expected format
        secret_creds = {
            "username": secret.get("username"),
            "password": secret.get("password"),
            "host": secret.get("host"),
            "port": str(secret.get("port", "5432")),
            "dbname": secret.get("dbname"),
        }

        # Log the retrieved credentials (without password)
        logger.debug("Raw secret values: %s", {k: v if k != "password" else "***" for k, v in secret.items()})

        # Verify we have all required fields
        missing = [k for k, v in secret_creds.items() if not v]
        if missing:
            raise ValueError(f"Missing required fields in secret: {', '.join(missing)}")

        logger.info("Successfully retrieved database credentials from AWS Secrets Manager")
        return secret_creds

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        if error_code == "ResourceNotFoundException":
            error_msg = f"Secret not found with ARN: {secret_arn}"
        elif error_code == "AccessDeniedException":
            error_msg = "Access denied to Secrets Manager. Check IAM permissions."
        else:
            error_msg = f"Failed to retrieve secret: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e
    except (json.JSONDecodeError, KeyError) as e:
        error_msg = f"Invalid secret format in AWS Secrets Manager: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e
