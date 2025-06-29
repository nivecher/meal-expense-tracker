"""Database migration utility for both local and Lambda environments."""

import logging
import os
import traceback

from flask import current_app
from flask_migrate import current, history
from flask_migrate import upgrade as _upgrade
from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db

logger = logging.getLogger(__name__)


def _get_safe_db_url(db_url):
    """Get a safe version of the database URL for logging."""
    if not db_url:
        return "Not configured"
    if "@" not in db_url:
        return "***"

    # Mask password in the URL
    parts = db_url.split("@", 1)
    if "//" in parts[0]:
        return f"{parts[0].split('//')[0]}//***@{parts[1]}"
    return "***"


def _check_database_connection():
    """Check if database is accessible."""
    try:
        db.session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        current_app.logger.error(f"Database connection failed: {str(e)}")
        return False


def _log_migration_history():
    """Log the current migration history."""
    try:
        history_revs = history()
        current_app.logger.info("Available migrations:")
        for rev in history_revs:
            current_app.logger.info(f"  - {rev.revision}: {rev.doc}")
    except Exception as e:
        current_app.logger.warning(f"Could not get migration history: {str(e)}")


def _check_existing_tables():
    """Check if tables already exist in the database."""
    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()
    return existing_tables and "restaurant" in existing_tables


def run_migrations():
    """Run database migrations.

    Returns:
        bool: True if migrations were successful or not needed, False otherwise
    """
    app = create_app()

    with app.app_context():
        try:
            # Log database URL (masking password)
            db_url = app.config.get("SQLALCHEMY_DATABASE_URI", "")
            current_app.logger.info(f"Database URL: {_get_safe_db_url(db_url)}")

            # Ensure the migrations directory exists
            migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
            current_app.logger.info(f"Migrations directory: {migrations_dir}")

            if not os.path.exists(migrations_dir):
                raise RuntimeError(f"Migrations directory not found at {migrations_dir}")

            # Check database connection
            current_app.logger.info("Testing database connection...")
            if not _check_database_connection():
                raise RuntimeError("Failed to connect to the database")

            # Log current migration state
            current_rev = current()
            current_app.logger.info(f"Current database revision: {current_rev}")

            # Log available migrations
            _log_migration_history()

            # Check if tables already exist
            if _check_existing_tables():
                current_app.logger.warning("Tables already exist in the database. Skipping migrations.")
                current_app.logger.info("If you need to run migrations, please reset the database first.")
                return True

            # Run migrations
            current_app.logger.info("Running database migrations...")
            try:
                upgrade()
                current_app.logger.info("Database migrations completed successfully")
                return True
            except Exception as e:
                if "already exists" in str(e):
                    current_app.logger.warning(
                        "Some tables already exist. " "Database may be in an inconsistent state."
                    )
                    current_app.logger.info(
                        "If you need to reset the database, please run: " "flask db downgrade base && flask db upgrade"
                    )
                    return True
                raise

        except Exception as e:
            logger.error(f"Error in migrations: {str(e)}", exc_info=True)
            if current_app.debug:
                logger.error("Full traceback:\n" + traceback.format_exc())
            return False
        raise


def upgrade():
    """Run database upgrade."""
    _upgrade()


def reset_database():
    """Reset the database by dropping all tables and running migrations.

    This function is used by the Lambda function to reset the database to a clean state.
    """
    from flask_migrate import downgrade

    app = create_app()

    with app.app_context():
        try:
            logger.warning("Dropping all database tables...")
            db.drop_all()

            # Reset migrations to base
            logger.info("Resetting migrations to base...")
            try:
                downgrade(revision="base")
            except Exception as e:
                logger.warning(f"Could not reset to base: {str(e)}")

            # Run migrations
            logger.info("Running migrations...")
            upgrade()

            logger.info("Database reset complete")
            return True

        except Exception as e:
            logger.error(f"Error resetting database: {str(e)}", exc_info=True)
            if app.debug:
                logger.error("Full traceback:\n" + traceback.format_exc())
            return False


if __name__ == "__main__":
    # Add command line interface for reset
    import argparse

    parser = argparse.ArgumentParser(description="Database migration utility")
    parser.add_argument("--reset", action="store_true", help="Reset the database")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if args.reset:
        reset_database()
    else:
        run_migrations()
