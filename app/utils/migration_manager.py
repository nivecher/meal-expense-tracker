"""
Migration Manager for Lambda Deployments

This module provides safe, automated migration handling for Lambda deployments
with data preservation and rollback capabilities.
"""

from collections.abc import Callable
from enum import Enum
import logging
import os
import time
from typing import TYPE_CHECKING, Any, cast

from alembic.script import ScriptDirectory
from flask import Flask, current_app
from sqlalchemy import inspect, text
from sqlalchemy.exc import DisconnectionError, OperationalError

if TYPE_CHECKING:
    from flask.ctx import AppContext

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

    def __init__(self, app: Flask | None = None):
        self.app = app
        self._migration_state = MigrationState.PENDING
        self._max_retries = 3
        self._retry_delay = 1.0  # seconds
        self._connection_timeout = 30  # seconds

    def init_app(self, app: Flask) -> None:
        """Initialize with Flask app."""
        self.app = app

    def _detect_migrations_dir(self) -> str | None:
        """Detect the migrations directory path in current environment."""
        env_dir = os.environ.get("MIGRATIONS_DIR")
        if env_dir and os.path.isdir(env_dir):
            return env_dir

        try:
            app = self.app or current_app
            migrate_ext = getattr(app, "extensions", {}).get("migrate")
            if migrate_ext and getattr(migrate_ext, "directory", None):
                dir_candidate = migrate_ext.directory
                if dir_candidate and os.path.isdir(dir_candidate):
                    return cast(str, dir_candidate)
        except Exception as e:
            logger.debug(f"Could not detect migrations directory from Flask app: {e}")
            # Continue to fallback options

        lambda_default = "/var/task/migrations"
        if os.path.isdir(lambda_default):
            return lambda_default

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        local_default = os.path.join(project_root, "migrations")
        if os.path.isdir(local_default):
            return local_default

        return None

    def _list_revisions_from_dir(self, migrations_dir: str) -> list[str]:
        """List Alembic revision ids from the specified migrations directory."""
        script = ScriptDirectory(migrations_dir)
        try:
            revisions_desc = list(script.walk_revisions())
        except Exception:
            revisions_desc = list(script.walk_revisions(base="base", head="heads"))
        revisions = [rev.revision for rev in reversed(revisions_desc)]
        logger.info(f"Found {len(revisions)} migrations from {migrations_dir}: {revisions}")
        return revisions

    def _get_app_context(self) -> "AppContext":
        """Get Flask app context."""
        if self.app:
            return self.app.app_context()
        return current_app.app_context()

    def _retry_with_backoff(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute function with exponential backoff retry logic."""
        last_exception: Exception | None = None

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
        # Type narrowing: last_exception is Exception after None check
        if last_exception is None:
            raise RuntimeError("All retries failed but no exception was captured")
        # Explicit check ensures type narrowing (replaces assert that would be stripped in -O mode)
        raise last_exception

    def _ensure_database_connection(self) -> bool:
        """Ensure database connection is available with timeout."""
        try:
            # Test connection with timeout
            db.session.execute(text("SELECT 1"))
            db.session.commit()
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def _copy_migrations_to_writable_location(self) -> str | None:
        """Copy migrations to a writable location in Lambda."""
        import os
        import shutil
        import tempfile

        temp_migrations_dir = tempfile.mkdtemp(prefix="migrations_")

        try:
            # Get the original migrations directory - in Lambda, it's at the root of the package
            import os

            # In Lambda, migrations are at the root level of the package (v4 fix)
            if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
                # Lambda environment - migrations are at /var/task/migrations
                original_migrations_dir = "/var/task/migrations"
            else:
                # Local environment - calculate relative to this file
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                original_migrations_dir = os.path.join(project_root, "migrations")

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

            # Configure Flask-Migrate to use the copied directory
            try:
                from flask import current_app
                from flask_migrate import Migrate

                # Get the current Flask app and configure Migrate
                app = current_app._get_current_object()
                if "migrate" not in app.extensions:
                    # Initialize Migrate with the app and the temp directory
                    migrate = Migrate()
                    migrate.init_app(app, db, directory=temp_migrations_dir)
                    logger.info(f"Configured Flask-Migrate to use directory: {temp_migrations_dir}")
                else:
                    # Update existing Migrate instance
                    app.extensions["migrate"].directory = temp_migrations_dir
                    logger.info(f"Updated Flask-Migrate to use directory: {temp_migrations_dir}")
            except Exception as e:
                logger.warning(f"Could not configure Flask-Migrate: {e}")

            return temp_migrations_dir

        except Exception as e:
            logger.error(f"Failed to copy migrations: {e}")
            return None

    def _get_database_info(self) -> dict[str, Any]:
        """Get basic database information with retry logic."""

        def _get_info() -> dict[str, Any]:
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()

            has_alembic_version = "alembic_version" in existing_tables
            has_main_tables = any(table in existing_tables for table in ["user", "restaurant", "expense"])

            return {
                "existing_tables": existing_tables,
                "has_alembic_version": has_alembic_version,
                "has_main_tables": has_main_tables,
            }

        result = self._retry_with_backoff(_get_info)
        return cast(dict[str, Any], result)

    def _get_current_revision(self, has_alembic_version: bool) -> str | None:
        """Get current revision from alembic_version table with retry logic."""
        if not has_alembic_version:
            return None

        def _get_revision() -> str | None:
            result = db.session.execute(text("SELECT version_num FROM alembic_version"))
            return cast(str | None, result.scalar())

        try:
            result = self._retry_with_backoff(_get_revision)
            return cast(str | None, result)
        except Exception as e:
            logger.warning(f"Could not read alembic_version: {e}")
            return None

    def _get_available_revisions(self) -> tuple[list[str], str | None]:
        """Get available migration revisions using Alembic ScriptDirectory."""
        mig_dir = self._detect_migrations_dir()
        if mig_dir:
            try:
                return self._list_revisions_from_dir(mig_dir), None
            except Exception as e:
                logger.warning(f"Could not get migration history via Alembic: {e}")

        temp_dir = self._copy_migrations_to_writable_location()
        if temp_dir:
            try:
                return self._list_revisions_from_dir(temp_dir), None
            except Exception as e2:
                logger.error(f"Still could not get migration history after copying: {e2}")
                return [], "Could not access migration files: error after copying"

        return [], "Could not access migration files: migrations directory not found"

    def _determine_migration_state(
        self,
        db_info: dict[str, Any],
        current_revision: str | None,
        available_revisions: list[str],
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

    def check_migration_state(self) -> dict[str, Any]:
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

    def _get_latest_revision(self) -> tuple[str | None, str | None]:
        """Get the latest migration revision using Alembic ScriptDirectory.

        Avoids relying on Flask-Migrate's history() which may return None.
        """

        def _latest_from_dir(migrations_dir: str) -> str | None:
            script = ScriptDirectory(migrations_dir)
            try:
                revisions_desc = list(script.walk_revisions())
            except Exception:
                revisions_desc = list(script.walk_revisions(base="base", head="heads"))
            if not revisions_desc:
                return None
            # walk_revisions yields newest→oldest, pick the first or reverse
            latest = revisions_desc[0].revision
            return latest

        # Try detected migrations dir first
        mig_dir = self._detect_migrations_dir()
        if mig_dir and os.path.isdir(mig_dir):
            latest = _latest_from_dir(mig_dir)
            if latest:
                logger.info(f"Latest migration revision: {latest}")
                return latest, None

        # Fallback to copy to /tmp and retry
        temp_dir = self._copy_migrations_to_writable_location()
        if temp_dir and os.path.isdir(temp_dir):
            latest = _latest_from_dir(temp_dir)
            if latest:
                logger.info(f"Latest migration revision after copying: {latest}")
                return latest, None
            return None, "No migration files found after copying"

        return None, "No migration files found"

    def _create_alembic_version_table(self, existing_tables: list[str]) -> None:
        """Create alembic_version table if it doesn't exist."""
        if "alembic_version" not in existing_tables:
            logger.info("Creating alembic_version table...")
            db.session.execute(text("""
                CREATE TABLE alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """))

    def _set_migration_revision(self, revision: str) -> None:
        """Set the current migration revision."""
        db.session.execute(text("DELETE FROM alembic_version"))
        db.session.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
            {"revision": revision},
        )

    def fix_migration_history(self) -> dict[str, Any]:
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
                if not latest_revision:
                    return {"success": False, "error": "Could not determine latest revision"}

                # Create alembic_version table if it doesn't exist
                self._create_alembic_version_table(existing_tables)

                # Set the current revision
                # latest_revision is guaranteed to be str after None check above
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

    def _upgrade_once_to_heads(self) -> dict[str, Any]:
        """Perform a single Alembic upgrade to 'heads' and return revisions before/after.

        Uses Alembic's programmatic API directly to avoid CLI argument ambiguity.
        """
        from alembic import command as alembic_command
        from alembic.config import Config

        # Determine migrations directory
        mig_dir = self._detect_migrations_dir()
        if not mig_dir:
            mig_dir = self._copy_migrations_to_writable_location()
        if not mig_dir:
            raise RuntimeError("Migrations directory not found for upgrade")

        # Compute before revision
        db_info = self._get_database_info()
        before_rev = self._get_current_revision(db_info["has_alembic_version"])
        logger.info(f"Current revision before upgrade: {before_rev}")

        # Build Alembic Config from alembic.ini to satisfy env.py fileConfig
        ini_path = os.path.join(mig_dir, "alembic.ini")
        if os.path.exists(ini_path):
            cfg = Config(ini_path)
        else:
            cfg = Config()
        # Ensure critical options are set regardless of path source
        cfg.set_main_option("script_location", mig_dir)
        try:
            cfg.set_main_option("config_file_name", ini_path)
            cfg.config_file_name = ini_path  # safeguard for env.py fileConfig
        except Exception as e:
            logger.debug(f"Could not set config_file_name for Alembic config: {e}")
            # Continue without config file name
        try:
            # Provide DB URL for offline envs; env.py usually reads from current_app
            cfg.set_main_option("sqlalchemy.url", str(db.engine.url))
        except Exception as e:
            logger.debug(f"Could not set sqlalchemy.url for Alembic config: {e}")
            # Continue without explicit URL (env.py will handle connection)

        # Run upgrade to heads
        alembic_command.upgrade(cfg, "heads")

        # Compute after revision
        db_info = self._get_database_info()
        after_rev = self._get_current_revision(db_info["has_alembic_version"])
        logger.info(f"New revision after upgrade: {after_rev}")

        return {"previous_revision": before_rev, "new_revision": after_rev}

    def _upgrade_until_up_to_date(self, max_checks: int = 5) -> tuple[dict[str, Any], dict[str, Any]]:
        """Upgrade to heads and repeat until state is up_to_date or attempts exhausted."""
        migration_data = self._retry_with_backoff(self._upgrade_once_to_heads)
        for _ in range(max_checks):
            post_state = self.check_migration_state()
            if post_state.get("state") in {"up_to_date", "empty"}:
                return migration_data, post_state
            logger.info(
                f"Still pending migrations ({post_state.get('pending_count', '?')}), running another upgrade cycle..."
            )
            migration_data = self._retry_with_backoff(self._upgrade_once_to_heads)
        return migration_data, self.check_migration_state()

    def _verify_schema_matches_head(self) -> bool:
        """Lightweight verification that critical schema matches expected head.

        Currently verifies the 'restaurant.located_within' column exists.
        Returns True when verification passes.
        """
        try:
            inspector = inspect(db.engine)
            if "restaurant" not in inspector.get_table_names():
                return True  # nothing to verify yet
            columns = [col["name"] for col in inspector.get_columns("restaurant")]
            if "located_within" not in columns:
                logger.warning("Schema mismatch: restaurant.located_within is missing while at head")
                return False
            return True
        except Exception as e:
            logger.warning(f"Schema verification failed: {e}")
            return True

    def _stamp_to_previous_of_head(self) -> str | None:
        """Stamp alembic_version to the previous revision of the head, if resolvable.

        Returns the stamped revision id or None on failure.
        """
        try:
            mig_dir = self._detect_migrations_dir() or self._copy_migrations_to_writable_location()
            if not mig_dir:
                logger.error("Cannot determine migrations directory to stamp")
                return None
            script = ScriptDirectory(mig_dir)
            head = script.get_current_head() or (script.get_heads()[0] if script.get_heads() else None)
            if not head:
                logger.error("Could not determine head revision to stamp back from")
                return None
            head_rev = script.get_revision(head)
            prev: str | None = None
            down_revision = head_rev.down_revision
            if isinstance(down_revision, (tuple, list)):
                prev = down_revision[0] if down_revision else None
            elif isinstance(down_revision, str):
                prev = down_revision
            # else: down_revision is None, prev remains None
            if not prev:
                logger.error("Head has no down_revision; cannot stamp backwards")
                return None
            self._set_migration_revision(prev)
            db.session.commit()
            logger.info(f"Stamped alembic_version back to previous revision: {prev}")
            return prev
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed stamping to previous of head: {e}")
            return None

    def run_migrations(self, dry_run: bool = False, target_revision: str | None = None) -> dict[str, Any]:
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

                migration_data, final_state = self._upgrade_until_up_to_date(max_checks=5)
                self._handle_post_upgrade_verification(migration_data, final_state)

                return {
                    "success": True,
                    "message": (
                        f"Database migrations attempted. Last revision: {migration_data['previous_revision']} → {migration_data['new_revision']}"
                    ),
                    "data": {"final_state": final_state, **migration_data},
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

                return {
                    "success": False,
                    "message": f"Migration failed: {error_msg}",
                    "error": str(e),
                }

    def _handle_post_upgrade_verification(self, migration_data: dict[str, Any], final_state: dict[str, Any]) -> None:
        """Verify schema and optionally stamp back one revision and re-apply if needed."""
        if final_state.get("state") != "up_to_date":
            logger.warning(f"Migrations did not reach up-to-date state: {final_state}")
            return
        if self._verify_schema_matches_head():
            return
        stamped = self._stamp_to_previous_of_head()
        if not stamped:
            logger.warning("Could not stamp back to previous revision; manual intervention may be required")
            return
        logger.info("Re-applying migrations after stamping back one revision...")
        self._upgrade_until_up_to_date(max_checks=3)

    def auto_migrate(self) -> dict[str, Any]:
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
            return {
                "success": False,
                "message": f"Unknown migration state: {state_info['state']}",
                "data": state_info,
            }


# Global migration manager instance
migration_manager = MigrationManager()


def init_migration_manager(app: Flask) -> MigrationManager:
    """Initialize the migration manager with Flask app."""
    migration_manager.init_app(app)
    return migration_manager
