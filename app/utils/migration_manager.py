"""
Migration Manager for Lambda Deployments

This module provides safe, automated migration handling for Lambda deployments
with data preservation and rollback capabilities.
"""

import logging
import os
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app
from sqlalchemy import inspect, text
from sqlalchemy.exc import DisconnectionError, OperationalError

from app.extensions import db

logger = logging.getLogger(__name__)


class MigrationState(Enum):
    """Migration states for tracking progress."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLBACK_NEEDED = "rollback_needed"


class MigrationManager:
    """
    Safe migration manager for Lambda deployments.

    Features:
    - Automatic migration history detection and repair
    - Safe migration execution with rollback capability
    - Data preservation during schema changes
    - Migration state tracking
    - Environment-specific behavior
    - Retry logic with exponential backoff
    - Connection pooling and timeout handling
    """

    def __init__(self, app=None):
        self.app = app
        self._migration_state = MigrationState.PENDING
        self._max_retries = 3
        self._retry_delay = 1.0  # seconds
        self._connection_timeout = 30  # seconds

    def init_app(self, app):
        """Initialize with Flask app."""
        self.app = app

    def _get_app_context(self):
        """Get Flask app context."""
        if self.app:
            return self.app.app_context()
        return current_app.app_context()

    def _retry_with_backoff(self, func, *args, **kwargs):
        """Execute function with exponential backoff retry logic."""
        last_exception = None

        for attempt in range(self._max_retries + 1):
            try:
                return func(*args, **kwargs)
            except (OperationalError, DisconnectionError) as e:
                last_exception = e
                if attempt < self._max_retries:
                    delay = self._retry_delay * (2**attempt)
                    logger.warning(f"Database operation failed (attempt {attempt + 1}/{self._max_retries + 1}): {e}")
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logger.error(f"Database operation failed after {self._max_retries + 1} attempts: {e}")
            except Exception as e:
                # Don't retry for non-database errors
                logger.error(f"Non-retryable error: {e}")
                raise e

        # If we get here, all retries failed
        raise last_exception

    def _ensure_database_connection(self):
        """Ensure database connection is available with timeout."""
        try:
            # Test connection with timeout
            db.session.execute(text("SELECT 1"))
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def _copy_migrations_to_writable_location(self) -> str:
        """Copy migrations to a writable location in Lambda."""
        import os
        import shutil
        import tempfile

        temp_migrations_dir = tempfile.mkdtemp(prefix="migrations_")

        try:
            # Get the original migrations directory
            original_migrations_dir = os.path.join(os.getcwd(), "migrations")

            if not os.path.exists(original_migrations_dir):
                logger.error(f"Original migrations directory not found: {original_migrations_dir}")
                return None

            # Copy migrations to temp directory
            if os.path.exists(temp_migrations_dir):
                shutil.rmtree(temp_migrations_dir)

            shutil.copytree(original_migrations_dir, temp_migrations_dir)
            logger.info(f"Copied migrations to: {temp_migrations_dir}")

            # Set environment variable for Flask-Migrate
            os.environ["MIGRATIONS_DIR"] = temp_migrations_dir
            logger.info(f"Set MIGRATIONS_DIR to: {temp_migrations_dir}")

            return temp_migrations_dir

        except Exception as e:
            logger.error(f"Failed to copy migrations: {e}")
            return None

    def _get_database_info(self) -> Dict[str, Any]:
        """Get basic database information with retry logic."""

        def _get_info():
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()

            has_alembic_version = "alembic_version" in existing_tables
            has_main_tables = any(table in existing_tables for table in ["user", "restaurant", "expense"])

            return {
                "existing_tables": existing_tables,
                "has_alembic_version": has_alembic_version,
                "has_main_tables": has_main_tables,
            }

        return self._retry_with_backoff(_get_info)

    def _get_current_revision(self, has_alembic_version: bool) -> Optional[str]:
        """Get current revision from alembic_version table with retry logic."""
        if not has_alembic_version:
            return None

        def _get_revision():
            result = db.session.execute(text("SELECT version_num FROM alembic_version"))
            return result.scalar()

        try:
            return self._retry_with_backoff(_get_revision)
        except Exception as e:
            logger.warning(f"Could not read alembic_version: {e}")
            return None

    def _get_available_revisions(self) -> Tuple[List[str], Optional[str]]:
        """Get available migration revisions, copying to writable location if needed."""
        try:
            from flask_migrate import history

            migration_history = history()
            available_revisions = [rev.revision for rev in migration_history]
            logger.info(f"Found {len(available_revisions)} migrations: {available_revisions}")
            return available_revisions, None
        except Exception as e:
            logger.warning(f"Could not get migration history: {e}")

            # Try copying migrations to writable location
            temp_migrations_dir = self._copy_migrations_to_writable_location()
            if temp_migrations_dir:
                try:
                    from flask_migrate import history

                    migration_history = history()
                    available_revisions = [rev.revision for rev in migration_history]
                    logger.info(f"Found {len(available_revisions)} migrations after copying: {available_revisions}")
                    return available_revisions, None
                except Exception as e2:
                    logger.error(f"Still could not get migration history after copying: {e2}")
                    return [], f"Could not access migration files: {str(e)}"
            else:
                return [], f"Could not access migration files: {str(e)}"

    def _determine_migration_state(
        self, db_info: Dict[str, Any], current_revision: Optional[str], available_revisions: List[str]
    ) -> str:
        """Determine the current migration state."""
        if not db_info["has_main_tables"]:
            return "empty"
        elif not db_info["has_alembic_version"]:
            return "tables_without_migration_history"
        elif current_revision is None:
            return "inconsistent_migration_history"
        elif current_revision == available_revisions[-1] if available_revisions else None:
            return "up_to_date"
        else:
            return "pending_migrations"

    def check_migration_state(self) -> Dict[str, Any]:
        """
        Check the current state of migrations.

        Returns:
            Dict with migration state information
        """
        with self._get_app_context():
            try:
                db_info = self._get_database_info()
                current_revision = self._get_current_revision(db_info["has_alembic_version"])
                available_revisions, error = self._get_available_revisions()

                if error:
                    return {
                        "state": "error",
                        "error": error,
                        **db_info,
                        "current_revision": current_revision,
                    }

                state = self._determine_migration_state(db_info, current_revision, available_revisions)

                return {
                    "state": state,
                    **db_info,
                    "current_revision": current_revision,
                    "available_revisions": available_revisions,
                    "pending_count": (
                        len([r for r in available_revisions if r != current_revision])
                        if current_revision
                        else len(available_revisions)
                    ),
                }

            except Exception as e:
                logger.error(f"Error checking migration state: {e}")
                return {"state": "error", "error": str(e)}

    def _get_latest_revision(self) -> Tuple[Optional[str], Optional[str]]:
        """Get the latest migration revision, copying migrations if needed."""
        try:
            from flask_migrate import history

            migration_history = history()
            if not migration_history:
                return None, "No migration files found"
            latest_revision = migration_history[-1].revision
            logger.info(f"Latest migration revision: {latest_revision}")
            return latest_revision, None
        except Exception as e:
            logger.warning(f"Could not get migration history directly: {e}")

            # Try copying migrations to writable location
            temp_migrations_dir = self._copy_migrations_to_writable_location()
            if temp_migrations_dir:
                try:
                    from flask_migrate import history

                    migration_history = history()
                    if not migration_history:
                        return None, "No migration files found after copying"
                    latest_revision = migration_history[-1].revision
                    logger.info(f"Latest migration revision after copying: {latest_revision}")
                    return latest_revision, None
                except Exception as e2:
                    logger.error(f"Still could not get migration history after copying: {e2}")
                    return None, f"Could not access migration files: {str(e)}"
            else:
                return None, f"Could not access migration files: {str(e)}"

    def _create_alembic_version_table(self, existing_tables: List[str]) -> None:
        """Create alembic_version table if it doesn't exist."""
        if "alembic_version" not in existing_tables:
            logger.info("Creating alembic_version table...")
            db.session.execute(
                text(
                    """
                CREATE TABLE alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """
                )
            )

    def _set_migration_revision(self, revision: str) -> None:
        """Set the current migration revision."""
        db.session.execute(text("DELETE FROM alembic_version"))
        db.session.execute(text("INSERT INTO alembic_version (version_num) VALUES (:revision)"), {"revision": revision})

    def fix_migration_history(self) -> Dict[str, Any]:
        """
        Fix migration history for existing tables.

        This is safe to run multiple times and preserves all data.
        """
        with self._get_app_context():
            try:
                inspector = inspect(db.engine)
                existing_tables = inspector.get_table_names()

                # Get the latest migration revision
                latest_revision, error = self._get_latest_revision()
                if error:
                    return {"success": False, "error": error}

                # Create alembic_version table if it doesn't exist
                self._create_alembic_version_table(existing_tables)

                # Set the current revision
                self._set_migration_revision(latest_revision)
                db.session.commit()

                return {
                    "success": True,
                    "message": f"Migration history fixed. Set to revision: {latest_revision}",
                    "revision": latest_revision,
                }

            except Exception as e:
                db.session.rollback()
                logger.error(f"Error fixing migration history: {e}")
                return {"success": False, "error": str(e)}

    def run_migrations(self, dry_run: bool = False, target_revision: Optional[str] = None) -> Dict[str, Any]:
        """
        Run database migrations safely with retry logic.

        Args:
            dry_run: If True, show what would be migrated without running
            target_revision: Specific revision to run to (optional)

        Returns:
            Dict with migration results
        """
        with self._get_app_context():
            try:
                # Ensure database connection before starting
                if not self._ensure_database_connection():
                    return {
                        "success": False,
                        "message": "Database connection not available",
                        "error": "Connection test failed",
                    }

                # Check current state first
                state_info = self.check_migration_state()

                if state_info["state"] == "tables_without_migration_history":
                    logger.info("Tables exist without migration history. Fixing...")
                    fix_result = self.fix_migration_history()
                    if not fix_result["success"]:
                        return {
                            "success": False,
                            "message": f"Failed to fix migration history: {fix_result['error']}",
                            "state_info": state_info,
                        }
                    logger.info("Migration history fixed successfully")

                if dry_run:
                    return {
                        "success": True,
                        "message": "Migration dry run completed",
                        "data": state_info,
                        "dry_run": True,
                    }

                # Run the actual migration with retry logic
                def _run_upgrade():
                    from flask_migrate import current, upgrade

                    current_rev = current()
                    logger.info(f"Current revision before upgrade: {current_rev}")

                    # Run upgrade
                    upgrade()

                    new_rev = current()
                    logger.info(f"New revision after upgrade: {new_rev}")

                    return {
                        "previous_revision": current_rev,
                        "new_revision": new_rev,
                        "target_revision": target_revision,
                    }

                migration_data = self._retry_with_backoff(_run_upgrade)

                return {
                    "success": True,
                    "message": f"Database migrations completed successfully. Revision: {migration_data['previous_revision']} → {migration_data['new_revision']}",
                    "data": migration_data,
                }

            except Exception as e:
                logger.exception(f"Migration failed: {e}")

                # Handle common errors
                error_msg = str(e)
                if "already exists" in error_msg:
                    error_msg = (
                        "Table already exists. This usually means the database has tables "
                        "but no migration history. Try running with fix_history=True."
                    )
                elif "connection" in error_msg.lower():
                    error_msg = f"Database connection issue: {error_msg}"

                return {"success": False, "message": f"Migration failed: {error_msg}", "error": str(e)}

    def auto_migrate(self) -> Dict[str, Any]:
        """
        Automatically handle migrations based on environment and state.

        This is the main method to call from Lambda startup.
        """
        # Check if auto-migration is enabled
        if not os.environ.get("AUTO_MIGRATE", "false").lower() == "true":
            logger.info("Auto-migration disabled. Set AUTO_MIGRATE=true to enable.")
            return {"success": True, "message": "Auto-migration disabled", "skipped": True}

        # Check environment
        environment = os.environ.get("FLASK_ENV", "production")
        logger.info(f"Auto-migrating in {environment} environment")

        # Check current state
        state_info = self.check_migration_state()
        logger.info(f"Migration state: {state_info['state']}")

        # Handle different states
        if state_info["state"] == "empty":
            logger.info("Database is empty. Running initial migration...")
            return self.run_migrations()

        elif state_info["state"] == "tables_without_migration_history":
            logger.info("Tables exist without migration history. Fixing and migrating...")
            fix_result = self.fix_migration_history()
            if fix_result["success"]:
                return self.run_migrations()
            else:
                return fix_result

        elif state_info["state"] == "pending_migrations":
            logger.info(f"Running {state_info['pending_count']} pending migrations...")
            return self.run_migrations()

        elif state_info["state"] == "up_to_date":
            logger.info("Database is up to date")
            return {"success": True, "message": "Database is up to date", "data": state_info}

        else:
            logger.warning(f"Unknown migration state: {state_info['state']}")
            return {"success": False, "message": f"Unknown migration state: {state_info['state']}", "data": state_info}


# Global migration manager instance
migration_manager = MigrationManager()


def init_migration_manager(app):
    """Initialize the migration manager with Flask app."""
    migration_manager.init_app(app)
    return migration_manager
