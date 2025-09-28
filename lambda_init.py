"""
Lambda Initialization Script

This script handles Lambda startup tasks including database migrations,
health checks, and initialization validation.
"""

import json
import logging
import os
import time
from typing import Any, Dict, Optional

from sqlalchemy import text

from app import create_app
from app.utils.migration_manager import migration_manager

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global state tracking
_INITIALIZATION_STATE = {
    "initialized": False,
    "migration_attempted": False,
    "migration_successful": False,
    "last_migration_error": None,
    "initialization_time": None,
}


def _validate_environment() -> Dict[str, Any]:
    """Validate required environment variables and configuration."""
    required_vars = [
        "DATABASE_URL",
        "SECRET_KEY",
    ]

    optional_vars = [
        "AUTO_MIGRATE",
        "FLASK_ENV",
        "LOG_LEVEL",
        "GOOGLE_MAPS_API_KEY",
    ]

    validation_result = {
        "valid": True,
        "missing_required": [],
        "missing_optional": [],
        "warnings": [],
    }

    # Check required variables
    for var in required_vars:
        if not os.environ.get(var):
            validation_result["missing_required"].append(var)
            validation_result["valid"] = False

    # Check optional variables
    for var in optional_vars:
        if not os.environ.get(var):
            validation_result["missing_optional"].append(var)

    # Environment-specific validations
    if os.environ.get("FLASK_ENV") == "production":
        if not os.environ.get("GOOGLE_MAPS_API_KEY"):
            validation_result["warnings"].append("Google Maps API key missing in production")

    return validation_result


def _test_database_connection(app) -> Dict[str, Any]:
    """Test database connectivity and basic operations."""
    try:
        with app.app_context():
            from app.extensions import db

            # Test basic connection
            db.session.execute(text("SELECT 1"))
            db.session.commit()

            # Test if we can access the database
            from sqlalchemy import inspect

            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            return {
                "success": True,
                "message": "Database connection successful",
                "tables_found": len(tables),
                "tables": tables,
            }

    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return {
            "success": False,
            "message": f"Database connection failed: {str(e)}",
            "error": str(e),
        }


def _run_startup_migrations(app) -> Dict[str, Any]:
    """Run database migrations during Lambda startup."""
    if _INITIALIZATION_STATE["migration_attempted"]:
        logger.info("Migration already attempted in this container")
        return {
            "success": _INITIALIZATION_STATE["migration_successful"],
            "message": "Migration already attempted",
            "skipped": True,
        }

    _INITIALIZATION_STATE["migration_attempted"] = True

    try:
        with app.app_context():
            # Initialize migration manager
            migration_manager.init_app(app)

            # Run auto-migration
            result = migration_manager.auto_migrate()

            if result["success"]:
                _INITIALIZATION_STATE["migration_successful"] = True
                logger.info(f"Startup migration successful: {result['message']}")
            else:
                _INITIALIZATION_STATE["last_migration_error"] = result.get("error")
                logger.error(f"Startup migration failed: {result['message']}")

            return result

    except Exception as e:
        error_msg = f"Migration execution failed: {str(e)}"
        _INITIALIZATION_STATE["last_migration_error"] = error_msg
        logger.exception(error_msg)
        return {
            "success": False,
            "message": error_msg,
            "error": str(e),
        }


def _perform_health_check(app) -> Dict[str, Any]:
    """Perform comprehensive health check."""
    health_status = {
        "healthy": True,
        "checks": {},
        "timestamp": time.time(),
    }

    try:
        # Environment validation
        env_validation = _validate_environment()
        health_status["checks"]["environment"] = {
            "valid": env_validation["valid"],
            "missing_required": env_validation["missing_required"],
            "warnings": env_validation["warnings"],
        }

        if not env_validation["valid"]:
            health_status["healthy"] = False

        # Database connectivity
        db_test = _test_database_connection(app)
        health_status["checks"]["database"] = db_test

        if not db_test["success"]:
            health_status["healthy"] = False

        # Migration status
        health_status["checks"]["migration"] = {
            "attempted": _INITIALIZATION_STATE["migration_attempted"],
            "successful": _INITIALIZATION_STATE["migration_successful"],
            "last_error": _INITIALIZATION_STATE["last_migration_error"],
        }

        # Application initialization
        health_status["checks"]["app_initialization"] = {
            "initialized": _INITIALIZATION_STATE["initialized"],
            "initialization_time": _INITIALIZATION_STATE["initialization_time"],
        }

    except Exception as e:
        logger.exception("Health check failed")
        health_status["healthy"] = False
        health_status["checks"]["error"] = str(e)

    return health_status


def initialize_lambda() -> Dict[str, Any]:
    """
    Initialize Lambda function with all startup tasks.

    This function should be called once per Lambda container lifecycle.
    """
    if _INITIALIZATION_STATE["initialized"]:
        logger.info("Lambda already initialized")
        return {
            "success": True,
            "message": "Lambda already initialized",
            "skipped": True,
        }

    start_time = time.time()
    logger.info("Starting Lambda initialization...")

    try:
        # Step 1: Validate environment
        logger.info("Validating environment...")
        env_validation = _validate_environment()
        if not env_validation["valid"]:
            error_msg = f"Environment validation failed: {env_validation['missing_required']}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "validation": env_validation,
            }

        # Step 2: Create Flask app
        logger.info("Creating Flask application...")
        app = create_app()

        # Step 3: Test database connection
        logger.info("Testing database connection...")
        db_test = _test_database_connection(app)
        if not db_test["success"]:
            error_msg = f"Database connection failed: {db_test['message']}"
            logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "database_test": db_test,
            }

        # Step 4: Run migrations if enabled
        auto_migrate = os.environ.get("AUTO_MIGRATE", "false").lower() == "true"
        if auto_migrate:
            logger.info("Running startup migrations...")
            migration_result = _run_startup_migrations(app)
            if not migration_result["success"] and not migration_result.get("skipped"):
                # Log error but don't fail initialization for migration issues
                logger.warning(f"Migration failed but continuing: {migration_result['message']}")
        else:
            logger.info("Auto-migration disabled")

        # Step 5: Mark as initialized
        _INITIALIZATION_STATE["initialized"] = True
        _INITIALIZATION_STATE["initialization_time"] = time.time() - start_time

        logger.info(f"Lambda initialization completed in {_INITIALIZATION_STATE['initialization_time']:.2f}s")

        return {
            "success": True,
            "message": "Lambda initialization completed successfully",
            "initialization_time": _INITIALIZATION_STATE["initialization_time"],
            "migration_result": (
                migration_result if auto_migrate else {"skipped": True, "message": "Auto-migration disabled"}
            ),
            "database_test": db_test,
        }

    except Exception as e:
        logger.exception("Lambda initialization failed")
        return {
            "success": False,
            "message": f"Lambda initialization failed: {str(e)}",
            "error": str(e),
        }


def get_initialization_status() -> Dict[str, Any]:
    """Get current initialization status."""
    return {
        "state": _INITIALIZATION_STATE.copy(),
        "health": _perform_health_check(create_app()) if _INITIALIZATION_STATE["initialized"] else None,
    }


def force_migration_retry() -> Dict[str, Any]:
    """Force a retry of migrations (useful for debugging)."""
    _INITIALIZATION_STATE["migration_attempted"] = False
    _INITIALIZATION_STATE["migration_successful"] = False
    _INITIALIZATION_STATE["last_migration_error"] = None

    app = create_app()
    return _run_startup_migrations(app)


# Export functions for use in lambda_handler
__all__ = [
    "initialize_lambda",
    "get_initialization_status",
    "force_migration_retry",
    "_perform_health_check",
]
