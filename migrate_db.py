"""Database migration utility for both local and Lambda environments."""

import logging
import os
import sys
import traceback
from typing import Any, Dict, List, Optional, Tuple, Union

from flask import Flask, current_app
from flask_migrate import Migrate
from flask_migrate import current as flask_current
from flask_migrate import downgrade as flask_downgrade
from flask_migrate import history as flask_history
from flask_migrate import init as flask_init
from flask_migrate import migrate as flask_migrate
from flask_migrate import show as flask_show
from flask_migrate import stamp as flask_stamp
from flask_migrate import upgrade as flask_upgrade
from sqlalchemy import inspect, text

# Import db from extensions to avoid circular imports
from app.extensions import db

logger = logging.getLogger(__name__)

# Initialize Flask application and Migrate extension
app: Optional[Flask] = None
migrate: Optional[Migrate] = None


def init_app(flask_app: Optional[Flask] = None) -> None:
    """Initialize the Flask application for migrations.

    Args:
        flask_app: Optional Flask application instance. If not provided, a new one will be created.
    """
    global app, migrate

    if flask_app is None:
        from app import create_app

        app = create_app()
    else:
        app = flask_app

    migrate = Migrate(app, db)

    # Ensure we have a valid app context
    if app.app_context() is None:
        app.app_context().push()


def _get_safe_db_url(db_url: str) -> str:
    """Get a safe version of the database URL for logging.

    Args:
        db_url: The database URL to sanitize

    Returns:
        str: A safe version of the database URL with sensitive information redacted
    """
    if not db_url:
        return "Not configured"
    if "@" not in db_url:
        return "***"

    # Mask password in the URL
    parts = db_url.split("@", 1)
    if "//" in parts[0]:
        return f"{parts[0].split('//')[0]}//***@{parts[1]}"
    return "***"


def _check_database_connection() -> bool:
    """Check if database is accessible.

    Returns:
        bool: True if database is accessible, False otherwise
    """
    try:
        db.session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        current_app.logger.error(f"Database connection failed: {str(e)}")
        return False


def _log_migration_history() -> None:
    """Log the current migration history."""
    try:
        with current_app.app_context():
            history_revs = flask_history()
            current_app.logger.info("Available migrations:")
            for rev in history_revs:
                current_app.logger.info("  %s: %s", rev.revision, rev.doc)
    except Exception as e:
        current_app.logger.warning("Could not get migration history: %s", str(e))


def _check_existing_tables() -> bool:
    """Check if tables already exist in the database.

    Returns:
        bool: True if tables exist, False otherwise
    """
    try:
        inspector = inspect(db.engine)
        return bool(inspector.get_table_names())
    except Exception as e:
        logger.error("Error checking existing tables: %s", str(e))
        return False


def run_migrations(flask_app: Optional[Flask] = None) -> bool:
    """Run database migrations.

    Args:
        flask_app: Optional Flask application instance

    Returns:
        bool: True if migrations were successful or not needed, False otherwise
    """
    global app, migrate

    try:
        # Initialize app if not already done
        if app is None:
            if flask_app is None:
                from app import create_app  # pylint: disable=import-outside-toplevel

                app = create_app()
            else:
                app = flask_app
            init_app(app)

        if migrate is None:
            logger.error("Migrate not initialized")
            return False

        with app.app_context():
            # Check if migrations directory exists
            migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
            if not os.path.exists(migrations_dir):
                logger.info("Initializing migrations...")
                flask_init()

            # Check if this is a fresh database
            if not _check_existing_tables():
                logger.info("No existing tables found. Creating initial database...")
                db.create_all()
                flask_stamp()
                return True

            # Run migrations if needed
            flask_upgrade()
            logger.info("Database migrations completed successfully.")
            return True

    except Exception as e:
        logger.error("Database migration failed: %s", str(e))
        logger.debug(traceback.format_exc())
        return False


def handle_database_operation(operation: str, **kwargs) -> Tuple[int, Dict[str, Any]]:
    """Handle database operations like migrations and resets.

    Args:
        operation: Operation to perform ('migrate', 'upgrade', 'downgrade', 'show', 'history', 'current')
        **kwargs: Additional operation-specific arguments

    Returns:
        tuple: (status_code, response_dict)
    """
    global app

    # Initialize app if not already done
    if app is None:
        from app import create_app

        app = create_app()
        init_app(app)

    if migrate is None:
        return 500, {"error": "Database not initialized"}

    try:
        with app.app_context():
            if operation == "migrate":
                message = kwargs.get("message", "auto migration")
                flask_migrate(message=message)
                return 200, {"status": "success", "message": f"Migration created: {message}"}
            elif operation == "upgrade":
                revision = kwargs.get("revision", "head")
                flask_upgrade(revision=revision)
                return 200, {"status": "success", "message": f"Upgraded to revision: {revision}"}
            elif operation == "downgrade":
                revision = kwargs.get("revision")
                if not revision:
                    return 400, {"status": "error", "message": "Revision is required for downgrade"}
                flask_downgrade(revision=revision)
                return 200, {"status": "success", "message": f"Downgraded to revision: {revision}"}
            elif operation == "show":
                current_rev = flask_current()
                return 200, {"status": "success", "current": current_rev}
            elif operation == "history":
                history_revs = flask_history()
                return 200, {"status": "success", "history": [str(rev) for rev in history_revs]}
            elif operation == "current":
                current_rev = flask_current()
                return 200, {"status": "success", "current": current_rev}
            else:
                return 400, {"status": "error", "message": f"Unknown operation: {operation}"}
    except Exception as e:
        logger.error("Database operation failed: %s", str(e))
        logger.debug(traceback.format_exc())
        return 500, {"status": "error", "message": str(e)}


def upgrade_db(revision: str = "head") -> None:
    """Run database upgrade.

    Args:
        revision: Target revision (default: 'head')
    """
    global app
    if app is None:
        from app import create_app

        app = create_app()
        init_app(app)

    with app.app_context():
        flask_upgrade(revision=revision)


def reset_database() -> bool:
    """Reset the database by dropping all tables and running migrations.

    This function is used by the Lambda function to reset the database to a clean state.

    Returns:
        bool: True if reset was successful, False otherwise
    """
    global app

    # Initialize app if not already done
    if app is None:
        from app import create_app

        app = create_app()
        init_app(app)

    try:
        with app.app_context():
            # Drop all tables
            db.reflect()
            db.drop_all()

            # Remove the migrations directory if it exists
            migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
            if os.path.exists(migrations_dir):
                import shutil

                shutil.rmtree(migrations_dir)

            # Recreate the database
            db.create_all()

            # Reinitialize migrations
            flask_init()
            flask_migrate(message="Initial migration")
            flask_upgrade()

            logger.info("Database reset successfully")
            return True
    except Exception as e:
        logger.error("Failed to reset database: %s", str(e))
        logger.debug(traceback.format_exc())
        return False


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    import argparse
    import json

    parser = argparse.ArgumentParser(description="Database migration utility")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Create a new migration")
    migrate_parser.add_argument("message", help="Migration message")

    # Upgrade command
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade database")
    upgrade_parser.add_argument("--revision", default="head", help="Revision to upgrade to (default: head)")

    # Downgrade command
    downgrade_parser = subparsers.add_parser("downgrade", help="Downgrade database")
    downgrade_parser.add_argument("revision", help="Revision to downgrade to")

    # Show command
    subparsers.add_parser("show", help="Show current revision")

    # History command
    subparsers.add_parser("history", help="Show revision history")

    # Current command
    subparsers.add_parser("current", help="Show current revision")

    # Reset command
    subparsers.add_parser("reset", help="Reset database (drop all tables and re-run migrations)")

    # Run migrations command
    subparsers.add_parser("run-migrations", help="Run pending migrations")

    args = parser.parse_args()

    try:
        if args.command == "migrate":
            status, result = handle_database_operation("migrate", message=args.message)
        elif args.command == "upgrade":
            status, result = handle_database_operation("upgrade", revision=args.revision)
        elif args.command == "downgrade":
            status, result = handle_database_operation("downgrade", revision=args.revision)
        elif args.command == "show":
            status, result = handle_database_operation("show")
        elif args.command == "history":
            status, result = handle_database_operation("history")
        elif args.command == "current":
            status, result = handle_database_operation("current")
        elif args.command == "reset":
            success = reset_database()
            if success:
                print("Database reset successfully")
                sys.exit(0)
            print("Failed to reset database", file=sys.stderr)
            sys.exit(1)
        elif args.command == "run-migrations":
            success = run_migrations()
            if success:
                print("Migrations completed successfully")
                sys.exit(0)
            print("Migrations failed", file=sys.stderr)
            sys.exit(1)
        else:
            parser.print_help()
            sys.exit(1)

        print(json.dumps(result, indent=2))
        sys.exit(0 if status == 200 else 1)

    except Exception as e:
        logger.error("Error: %s", str(e))
        logger.debug(traceback.format_exc())
        sys.exit(1)
