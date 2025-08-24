#!/usr/bin/env python3
import logging
import os
import sys
from typing import Any, Dict, Optional, Tuple, cast

import boto3
import psycopg2
from botocore.config import Config
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_rds_auth_token(host: str, port: int, username: str, region: str) -> str:
    """Generate an IAM authentication token for RDS."""
    try:
        client = boto3.client("rds", region_name=region)
        auth_token = client.generate_db_auth_token(DBHostname=host, Port=port, DBUsername=username, Region=region)
        return str(auth_token)
    except Exception as e:
        logger.error(f"Error generating auth token: {e}")
        sys.exit(1)


def get_env_var(name: str, default: str) -> str:
    """Safely get environment variable with type checking."""
    value = os.environ.get(name, default)
    if not isinstance(value, str):
        raise ValueError(f"Environment variable {name} must be a string")
    return value


def get_env_int(name: str, default: int) -> int:
    """Safely get environment variable as integer with type checking."""
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as e:
        raise ValueError(f"Environment variable {name} must be an integer") from e


def test_rds_connection() -> None:
    # Configuration - Update these values
    config: Dict[str, Any] = {
        "host": get_env_var("RDS_HOST", "your-rds-endpoint.rds.amazonaws.com"),
        "port": get_env_int("RDS_PORT", 5432),
        "dbname": get_env_var("RDS_DBNAME", "mealtracker"),
        "user": get_env_var("RDS_USER", "db_mealtracker"),
        "region": get_env_var("RDS_REGION", "us-east-1"),
        "sslmode": get_env_var("RDS_SSLMODE", "require"),
    }

    try:
        # Get IAM authentication token
        logger.info("Generating IAM authentication token...")
        password = get_rds_auth_token(config["host"], config["port"], config["user"], config["region"])

        # Create connection string
        conn_str = (
            f"host={config['host']} port={config['port']} "
            f"dbname={config['dbname']} user={config['user']} "
            f"password={password} sslmode={config['sslmode']}"
        )

        # Connect to the database
        logger.info("Attempting to connect to the database...")
        conn = psycopg2.connect(conn_str)

        # Create a cursor
        cur = conn.cursor()

        # Execute a simple query
        cur.execute("SELECT version();")
        db_version_row = cur.fetchone()
        if not db_version_row or not db_version_row[0]:
            raise ValueError("Failed to fetch database version")
        logger.info(f"Connected to PostgreSQL version: {db_version_row[0]}")

        # Check current user and database
        cur.execute("SELECT current_user, current_database(), current_timestamp;")
        user_info = cur.fetchone()
        if not user_info or len(user_info) != 3:
            raise ValueError("Failed to fetch user and database information")
        user, db, timestamp = user_info
        logger.info(f"Current User: {user}, Database: {db}, Time: {timestamp}")

        # Close the cursor and connection
        cur.close()
        conn.close()
        logger.info("Connection closed successfully")

    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    load_dotenv()
    test_rds_connection()
