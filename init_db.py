#!/usr/bin/env python3
"""Database initialization script for the Meal Expense Tracker.

This script initializes the database and creates all necessary tables.
It can be run directly or imported as a module.
"""

import argparse
import logging
from pathlib import Path
import sys

# Add the project root to the Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def init_default_data() -> None:
    """Initialize default data in the database.

    Note: Categories are now user-specific and created automatically
    when users add their first expense. This function only creates
    the default admin user.
    """
    from app.auth.models import User
    from app.database import db

    # Note: Categories are now user-specific and created automatically when users add expenses
    # This initialization only creates the admin user

    try:

        # Add a default admin user if none exists
        if not db.session.query(User).filter_by(username="admin").first():
            admin = User(username="admin", email="admin@example.com", is_admin=True)
            admin.set_password("admin")
            db.session.add(admin)
            logger.info("Added default admin user")

        db.session.commit()
        logger.info("Successfully initialized default data")

    except Exception as e:
        db.session.rollback()
        logger.error("Error initializing default data: %s", e, exc_info=True)
        raise


def init_db(drop_all: bool = False) -> bool:
    """Initialize the database with all models.

    Args:
        drop_all: If True, drop all tables before creating them

    Returns:
        bool: True if initialization was successful, False otherwise
    """
    from app.database import create_tables, db, drop_tables

    try:
        if drop_all:
            logger.info("Dropping all tables...")
            drop_tables()
            logger.info("All tables dropped")

        # Create all tables
        logger.info("Creating database tables...")
        create_tables()

        # Initialize default data
        logger.info("Initializing default data...")
        init_default_data()

        logger.info("Database initialization completed successfully")
        return True

    except Exception as e:
        logger.error("Error initializing database: %s", str(e), exc_info=True)
        if db.session.is_active:
            db.session.rollback()
        return False


def main() -> None:
    """Main entry point for the database initialization script."""
    parser = argparse.ArgumentParser(description="Initialize the database.")
    parser.add_argument("--reset", action="store_true", help="Drop all tables before creating them")

    args = parser.parse_args()

    print("=" * 80)
    print("Initializing database")
    if args.reset:
        print("WARNING: This will DROP ALL TABLES before creating them!")
        confirm = input("Are you sure you want to continue? (y/N) ")
        if confirm.lower() != "y":
            print("Aborting database initialization.")
            return

    print("-" * 80)

    # Create app and initialize database within app context
    from app import create_app

    app = create_app()

    try:
        with app.app_context():
            success = init_db(args.reset)

        print("=" * 80)
        if success:
            print("\n✅ Database initialized successfully!")
            print("\nYou can now start the application with:")
            print("  flask run")
            if args.reset:
                print("\nDefault admin credentials:")
                print("  Username: admin")
                print("  Password: admin")
                print("\n⚠️  Remember to change the default admin password after first login!")
        else:
            print("\n❌ ERROR: Failed to initialize database. Check the logs for details.")
            sys.exit(1)

    except Exception as e:
        logger.error("Error during database initialization: %s", str(e), exc_info=True)
        print("\n" + "=" * 80)
        print("❌ Database initialization failed with error!")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
