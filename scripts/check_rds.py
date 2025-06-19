#!/usr/bin/env python3
"""
Script to verify RDS database connection and initialization.

This script can be used in your deployment pipeline to ensure the database
is properly configured before deploying the application.
"""
import os
import sys
import logging
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_database_connection(db_url):
    """Check if we can connect to the database."""
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # Simple query to check connection
            result = conn.execute("SELECT version();")
            version = result.scalar()
            logger.info("Successfully connected to database. Version: %s", version)
            return True
    except SQLAlchemyError as e:
        logger.error("Failed to connect to database: %s", str(e))
        return False


def check_tables(engine):
    """Check if required tables exist in the database."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    required_tables = {"user", "expense", "restaurant", "alembic_version"}
    missing_tables = required_tables - set(tables)

    if missing_tables:
        logger.warning("Missing tables: %s", ", ".join(missing_tables))
        return False

    logger.info("All required tables exist in the database.")
    return True


def main():
    """Main function to check database connection and tables."""
    # Get database URL from environment or use default
    db_url = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        "postgresql://postgres:postgres@localhost:5432/meal_expense_tracker",
    )

    db_display = db_url.split("@")[-1] if "@" in db_url else db_url
    logger.info("Checking database connection to: %s", db_display)

    if not check_database_connection(db_url):
        logger.error("Database connection check failed.")
        sys.exit(1)

    # If connection is successful, check tables
    try:
        engine = create_engine(db_url)
        if not check_tables(engine):
            logger.warning(
                "Some required tables are missing. You may need to run migrations."
            )
            # Don't fail if tables are missing, as migrations might be applied later
    except SQLAlchemyError as e:
        logger.error("Error checking database tables: %s", str(e))
        sys.exit(1)

    logger.info("Database check completed successfully.")
    sys.exit(0)


if __name__ == "__main__":
    main()
