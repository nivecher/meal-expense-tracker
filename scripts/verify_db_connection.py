#!/usr/bin/env python3
"""Test database connection and migrations locally.

This script helps verify that the database connection and migrations work
correctly before deploying to AWS Lambda.
"""

import argparse
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_database_connection():
    """Test the database connection using the application's configuration."""
    try:
        from sqlalchemy import text

        from app import create_app, db

        # Create the Flask application
        app = create_app()

        with app.app_context():
            # Test database connection
            logger.info("Testing database connection...")
            db.session.execute(text("SELECT 1"))
            db.session.commit()
            logger.info("✅ Database connection successful!")

            # Get database URL (masking password)
            db_url = app.config.get("SQLALCHEMY_DATABASE_URI", "")
            if db_url and "@" in db_url:
                # Mask password in the URL
                parts = db_url.split("@", 1)
                if "//" in parts[0]:
                    safe_db_url = f"{parts[0].split('//')[0]}//***@{parts[1]}"
                    logger.info("Connected to database: %s", safe_db_url)
            return True

    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        logger.exception("Full error details:")
        return False


def run_migrations():
    """Run database migrations using the application's configuration."""
    try:
        from app import create_app
        from migrate_db import run_migrations as run_migrations_func

        # Create the Flask application
        app = create_app()

        with app.app_context():
            logger.info("Running database migrations...")
            run_migrations_func()
            logger.info("✅ Database migrations completed successfully!")
            return True

    except Exception as e:
        logger.error("❌ Database migrations failed: %s", str(e))
        logger.exception("Full error details:")
        return False


def main():
    """Main function to test database connection and migrations."""
    parser = argparse.ArgumentParser(description="Test database connection and migrations")
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Run database migrations after testing the connection",
    )
    args = parser.parse_args()

    # Test database connection
    if not test_database_connection():
        return 1

    # Run migrations if requested
    if args.migrate:
        if not run_migrations():
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
