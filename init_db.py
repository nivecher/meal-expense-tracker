#!/usr/bin/env python3
"""Database initialization script for the Meal Expense Tracker application.

This script handles database initialization and migration operations.
It can be used to create the initial database, apply migrations, or reset the database.

Usage:
    python init_db.py [--env ENV] [--reset] [--migrate]

Options:
    --env ENV     Environment to use (development, testing, production) [default: development]
    --reset       Drop all tables and recreate them
    --migrate     Run database migrations after initialization
"""

import argparse
import logging
import sys

from flask import current_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def init_database(env: str = "development", reset: bool = False, migrate: bool = False) -> bool:
    """Initialize the database.

    Args:
        env: Environment to use (development, testing, production)
        reset: If True, drop all tables before creating them
        migrate: If True, run database migrations after initialization

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        from app import create_app, db

        # Create app with specified environment
        app = create_app(env)
        with app.app_context():
            if reset:
                logger.info("Dropping all database tables...")
                db.drop_all()
                logger.info("All tables dropped.")
            logger.info("Creating database tables...")
            db.create_all()
            logger.info("Database tables created successfully!")

            # Initialize default categories
            from app.expenses import init_default_categories

            init_default_categories()
            logger.info("Default categories initialized successfully!")

            if migrate:
                logger.info("Running database migrations...")
                from flask_migrate import upgrade

                upgrade()
                logger.info("Database migrations applied successfully!")
            return True
    except Exception as e:
        logger.error("Error initializing database: %s", str(e))
        if current_app and current_app.debug:
            import traceback

            traceback.print_exc()
        return False


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Initialize the database.")
    parser.add_argument(
        "--env",
        type=str,
        default="development",
        choices=["development", "testing", "production"],
        help="Environment to use (default: development)",
    )
    parser.add_argument("--reset", action="store_true", help="Drop all tables before creating them")
    parser.add_argument("--migrate", action="store_true", help="Run database migrations after initialization")
    return parser.parse_args()


def main():
    """Run the main application logic."""
    # Print header
    print("\n" + "=" * 80)
    print(f"{'Initializing database':^80}")
    print("=" * 80)
    args = parse_arguments()
    print(f"Initializing {args.env} database...")

    if args.reset:
        print("WARNING: This will drop all tables in the database!")
        confirm = input("Are you sure you want to continue? (y/N): ")
        if confirm.lower() != "y":
            print("Operation cancelled.")
            sys.exit(0)

    success = init_database(env=args.env, reset=args.reset, migrate=args.migrate)

    if success:
        print("Database initialized successfully!")
        sys.exit(0)
    else:
        print("Failed to initialize database.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
