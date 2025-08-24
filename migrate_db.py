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
        # Test the connection with a simple query
        db.session.execute(text("SELECT 1"))
        db.session.commit()
        return True
    except Exception as e:
        current_app.logger.error(f"Database connection failed: {str(e)}")
        current_app.logger.error(traceback.format_exc())
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


def _setup_sqlite_database(db_url):
    """Handle SQLite-specific setup including directory creation and PRAGMAs."""
    if not db_url or not isinstance(db_url, str) or not db_url.startswith("sqlite://"):
        current_app.logger.warning(f"Invalid or non-SQLite database URL: {db_url}")
        return False

    try:
        # Extract and prepare the database path
        db_path = db_url.replace("sqlite:///", "")
        db_dir = os.path.dirname(db_path)

        # Ensure the directory exists and is writable
        if db_dir and not os.path.exists(db_dir):
            current_app.logger.info(f"Creating database directory: {db_dir}")
            os.makedirs(db_dir, mode=0o755, exist_ok=True)

        # Verify directory is writable
        if not os.access(os.path.dirname(db_path) or ".", os.W_OK):
            current_app.logger.error(f"Database directory is not writable: {os.path.dirname(db_path) or '.'}")
            return False

        current_app.logger.info(f"Database will be created at: {db_path}")

        # Set SQLite PRAGMAs for better performance
        current_app.logger.info("Configuring SQLite PRAGMAs...")
        try:
            with db.engine.connect() as conn:
                conn.execute(text("PRAGMA journal_mode=WAL"))
                conn.execute(text("PRAGMA synchronous=NORMAL"))
                conn.execute(text("PRAGMA busy_timeout=5000"))  # 5 second timeout
                conn.commit()
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to set SQLite PRAGMAs: {str(e)}")
            current_app.logger.error(traceback.format_exc())
            return False

    except Exception as e:
        current_app.logger.error(f"Error setting up SQLite database: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return False


def _setup_database_connection(db_url):
    """Set up the database connection and handle SQLite-specific setup."""
    current_app.logger.info("Testing database connection...")
    if _check_database_connection():
        return True

    # For SQLite, try to create the database file
    if db_url and db_url.startswith("sqlite://"):
        try:
            db_path = db_url.replace("sqlite:///", "")
            current_app.logger.info(f"Attempting to create SQLite database at: {db_path}")
            with open(db_path, "a", encoding="utf-8") as f:
                f.write("")  # Create empty file
            os.chmod(db_path, 0o666)  # Make sure it's writable
            current_app.logger.info("Created empty SQLite database file")

            # Try connecting again
            return _check_database_connection()

        except Exception as e:
            current_app.logger.error(f"Failed to create SQLite database file: {str(e)}")
            current_app.logger.error(traceback.format_exc())

    return False


def _verify_migrations():
    """Verify and log current migration state."""
    current_rev = current()
    current_app.logger.info(f"Current database revision: {current_rev}")
    _log_migration_history()
    return current_rev


def _execute_migrations():
    """Execute the database migrations with proper error handling.

    Returns:
        tuple: (success: bool, error: str or None)
    """
    current_app.logger.info("Running database migrations...")
    try:
        # Get the current revision before upgrade
        current_rev = current()
        current_app.logger.info(f"Current database revision before upgrade: {current_rev}")

        # Get the latest revision available
        import subprocess

        result = subprocess.run(["flask", "db", "heads"], capture_output=True, text=True, check=True)
        head = result.stdout.strip()
        current_app.logger.info(f"Latest available migration: {head}")

        # Run the upgrade
        _upgrade()

        # Verify the upgrade was successful
        new_rev = current()
        if new_rev == current_rev and current_rev != head:
            error_msg = f"Migration failed - still at revision {current_rev}, " f"expected {head}"
            current_app.logger.error(error_msg)
            return False, error_msg

        current_app.logger.info("Database migrations completed successfully.")
        return True, None

    except Exception as e:
        error_msg = f"Error executing migrations: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())

        # Check for common migration issues
        error_msg = str(e)
        if "already exists" in error_msg:
            error_msg = (
                "Table already exists. Database may be in an inconsistent state. "
                "Try running 'flask db downgrade base && flask db upgrade'"
            )
            current_app.logger.warning(error_msg)

        return False, error_msg


def _setup_migration_environment():
    """Set up the migration environment and return database URL.

    Returns:
        str: The database URL being used
    """
    # Log database URL (masking password)
    db_url = current_app.config.get("SQLALCHEMY_DATABASE_URI", "")
    current_app.logger.info(f"Database URL: {_get_safe_db_url(db_url)}")

    # Ensure the migrations directory exists
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    if not os.path.exists(migrations_dir):
        raise RuntimeError(f"Migrations directory not found at {migrations_dir}")
    current_app.logger.info(f"Using migrations from: {migrations_dir}")

    # Handle SQLite-specific setup
    if db_url.startswith("sqlite://") and not _setup_sqlite_database(db_url):
        current_app.logger.error("SQLite database setup failed")
        raise RuntimeError("SQLite database setup failed")

    return db_url


def _handle_migration_success(initial_rev):
    """Handle successful migration completion.

    Args:
        initial_rev (str): The revision before migrations were run
    """
    final_rev = current()
    if final_rev != initial_rev:
        current_app.logger.info(f"Database upgraded from {initial_rev} to {final_rev}")
    else:
        current_app.logger.info("Database is already at the latest revision.")

    # Verify all migrations were applied
    import subprocess

    result = subprocess.run(["flask", "db", "heads"], capture_output=True, text=True, check=True)
    head = result.stdout.strip()
    if final_rev != head:
        current_app.logger.warning(
            f"Database is at revision {final_rev} but the latest is {head}. "
            "Some migrations may not have been applied."
        )


def _handle_migration_failure(error):
    """Handle migration failure with appropriate logging and error messages.

    Args:
        error (str): The error message

    Raises:
        RuntimeError: Always raises with the error message
    """
    current_app.logger.error(f"Migration failed: {error}")

    # If we're in development, provide helpful reset instructions
    if current_app.debug:
        current_app.logger.warning(
            "To reset the database in development, you can run: " "flask db downgrade base && flask db upgrade"
        )

    raise RuntimeError(f"Migration failed: {error}")


def run_migrations():
    """Run database migrations.

    Returns:
        bool: True if migrations were successful or not needed, False otherwise
    """
    app = create_app()

    with app.app_context():
        try:
            # Set up migration environment
            db_url = _setup_migration_environment()

            # Set up database connection
            if not _setup_database_connection(db_url):
                raise RuntimeError("Failed to connect to the database after setup")

            # Check if tables already exist
            if _check_existing_tables():
                msg = "Tables already exist in the database. " "Skipping migrations. Reset the database if needed."
                current_app.logger.warning(msg)
                return True

            # Execute migrations
            initial_rev = _verify_migrations()
            success, error = _execute_migrations()

            if not success:
                _handle_migration_failure(error)

            _handle_migration_success(initial_rev)
            return True

        except Exception as e:
            current_app.logger.error(f"Error running migrations: {str(e)}")
            current_app.logger.error(traceback.format_exc())
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
