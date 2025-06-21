#!/usr/bin/env python3
"""
Script to verify the database schema after migration.
This script should be run after the initial migration to verify the schema was created correctly.
"""
import sys
import logging
from sqlalchemy import inspect, create_engine
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def verify_schema():
    """Verify the database schema matches expectations."""
    try:
        # Initialize config
        config = Config()

        # Get database URL
        db_url = config.SQLALCHEMY_DATABASE_URI
        if not db_url:
            logger.error("DATABASE_URL not set in environment")
            return False

        logger.info(f"Connecting to database: {db_url.split('@')[-1]}")

        # Create engine
        engine = create_engine(db_url)

        # Get inspector
        inspector = inspect(engine)

        # Get all tables
        tables = inspector.get_table_names()
        logger.info(
            f"Found tables: {', '.join(tables) if tables else 'No tables found'}"
        )

        # Verify required tables exist
        required_tables = {"user"}
        missing_tables = required_tables - set(tables)

        if missing_tables:
            logger.error(f"Missing required tables: {', '.join(missing_tables)}")
            return False

        # Verify alembic_version table exists (indicates migrations were run)
        if "alembic_version" not in tables:
            logger.warning(
                "alembic_version table not found - migrations may not have been applied"
            )

        # Verify columns in user table
        user_columns = {col["name"] for col in inspector.get_columns("user")}
        required_columns = {"id", "username", "password_hash"}
        missing_columns = required_columns - user_columns

        if missing_columns:
            logger.error(
                f"Missing required columns in user table: {', '.join(missing_columns)}"
            )
            return False

        logger.info("Schema verification successful")
        return True

    except Exception as e:
        logger.error(f"Error verifying schema: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    success = verify_schema()
    sys.exit(0 if success else 1)
