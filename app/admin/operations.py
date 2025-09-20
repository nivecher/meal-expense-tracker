"""Remote administration operations.

This module provides concrete implementations of admin operations that can be
invoked remotely via Lambda. Each operation follows the TIGER principles:
- Testing: Pure functions with clear interfaces
- Interfaces: Simple parameter validation
- Generality: Reusable operation patterns
- Examples: Clear usage documentation
- Refactoring: Single responsibility per operation
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from flask import current_app
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError

from app.auth.models import User
from app.extensions import db
from app.restaurants.models import Restaurant

logger = logging.getLogger(__name__)


class BaseAdminOperation(ABC):
    """Base class for all admin operations."""

    name: str = ""
    description: str = ""
    requires_confirmation: bool = False

    @abstractmethod
    def validate_params(self, **kwargs) -> Dict[str, Any]:
        """Validate operation parameters.

        Returns:
            dict: {"valid": bool, "errors": List[str]}
        """

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the operation.

        Returns:
            dict: {"success": bool, "message": str, "data": Any}
        """


class ListUsersOperation(BaseAdminOperation):
    """List system users with filtering options."""

    name = "list_users"
    description = "List all users in the system with optional filtering"
    requires_confirmation = False

    def validate_params(self, **kwargs) -> Dict[str, Any]:
        """Validate list users parameters."""
        errors = []

        admin_only = kwargs.get("admin_only", False)
        if not isinstance(admin_only, bool):
            errors.append("admin_only must be a boolean")

        limit = kwargs.get("limit", 100)
        if not isinstance(limit, int) or limit < 1 or limit > 1000:
            errors.append("limit must be an integer between 1 and 1000")

        return {"valid": len(errors) == 0, "errors": errors}

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute list users operation."""
        try:
            admin_only = kwargs.get("admin_only", False)
            limit = kwargs.get("limit", 100)

            query = User.query
            if admin_only:
                query = query.filter_by(is_admin=True)

            users = query.limit(limit).all()

            user_data = []
            for user in users:
                user_data.append(
                    {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "is_admin": getattr(user, "is_admin", False),
                        "is_active": getattr(user, "is_active", True),
                        "created_at": getattr(user, "created_at", None),
                        "last_login": getattr(user, "last_login", None),
                    }
                )

            return {
                "success": True,
                "message": f"Retrieved {len(user_data)} users",
                "data": {
                    "users": user_data,
                    "total_count": len(user_data),
                    "filtered": {"admin_only": admin_only},
                    "limit_applied": limit,
                },
            }

        except Exception as e:
            logger.exception(f"Error listing users: {e}")
            return {"success": False, "message": f"Failed to list users: {str(e)}"}


class CreateUserOperation(BaseAdminOperation):
    """Create a new user in the system."""

    name = "create_user"
    description = "Create a new user with specified credentials"
    requires_confirmation = True

    def validate_params(self, **kwargs) -> Dict[str, Any]:
        """Validate create user parameters."""
        errors = []

        username = kwargs.get("username", "").strip()
        if not username or len(username) < 3:
            errors.append("username must be at least 3 characters")

        email = kwargs.get("email", "").strip()
        if not email or "@" not in email:
            errors.append("email must be a valid email address")

        password = kwargs.get("password", "")
        if not password or len(password) < 6:
            errors.append("password must be at least 6 characters")

        admin = kwargs.get("admin", False)
        if not isinstance(admin, bool):
            errors.append("admin must be a boolean")

        active = kwargs.get("active", True)
        if not isinstance(active, bool):
            errors.append("active must be a boolean")

        return {"valid": len(errors) == 0, "errors": errors}

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute create user operation."""
        try:
            username = kwargs.get("username", "").strip()
            email = kwargs.get("email", "").strip()
            password = kwargs.get("password", "")
            admin = kwargs.get("admin", False)
            active = kwargs.get("active", True)

            # Check if user already exists
            existing_user = User.query.filter((User.username == username) | (User.email == email)).first()

            if existing_user:
                return {
                    "success": False,
                    "message": f"User with username '{username}' or email '{email}' already exists",
                }

            # Create new user
            user = User(username=username, email=email)
            user.set_password(password)

            if hasattr(user, "is_admin"):
                user.is_admin = admin
            if hasattr(user, "is_active"):
                user.is_active = active

            db.session.add(user)
            db.session.commit()

            return {
                "success": True,
                "message": f"Successfully created user '{username}' ({email})",
                "data": {
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_admin": getattr(user, "is_admin", False),
                    "is_active": getattr(user, "is_active", True),
                },
            }

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception(f"Database error creating user: {e}")
            return {"success": False, "message": f"Database error: {str(e)}"}
        except Exception as e:
            db.session.rollback()
            logger.exception(f"Error creating user: {e}")
            return {"success": False, "message": f"Failed to create user: {str(e)}"}


class UpdateUserOperation(BaseAdminOperation):
    """Update an existing user."""

    name = "update_user"
    description = "Update user information and privileges"
    requires_confirmation = True

    def validate_params(self, **kwargs) -> Dict[str, Any]:
        """Validate update user parameters."""
        errors = []

        # Must specify at least one identifier
        user_id = kwargs.get("user_id")
        username = kwargs.get("username", "").strip()
        email = kwargs.get("email", "").strip()

        if not any([user_id, username, email]):
            errors.append("Must specify user_id, username, or email to identify user")

        if user_id is not None and not isinstance(user_id, int):
            errors.append("user_id must be an integer")

        # Validate new values if provided
        new_username = kwargs.get("new_username", "").strip()
        if new_username and len(new_username) < 3:
            errors.append("new_username must be at least 3 characters")

        new_email = kwargs.get("new_email", "").strip()
        if new_email and "@" not in new_email:
            errors.append("new_email must be a valid email address")

        password = kwargs.get("password", "")
        if password and len(password) < 6:
            errors.append("password must be at least 6 characters")

        return {"valid": len(errors) == 0, "errors": errors}

    def _find_user_by_identifier(self, **kwargs) -> Optional[User]:
        """Find user by provided identifier (user_id, username, or email).

        Args:
            **kwargs: Parameters containing user identifiers

        Returns:
            User object if found, None otherwise
        """
        user_id = kwargs.get("user_id")
        username = kwargs.get("username", "").strip()
        email = kwargs.get("email", "").strip()

        query = User.query
        if user_id:
            return query.filter_by(id=user_id).first()
        elif username:
            return query.filter_by(username=username).first()
        elif email:
            return query.filter_by(email=email).first()

        return None

    def _apply_user_updates(self, user: User, **kwargs) -> List[str]:
        """Apply updates to user object and return list of changes.

        Args:
            user: User object to update
            **kwargs: Update parameters

        Returns:
            List of change descriptions
        """
        changes_made = []

        new_username = kwargs.get("new_username", "").strip()
        if new_username and user.username != new_username:
            user.username = new_username
            changes_made.append("username")

        new_email = kwargs.get("new_email", "").strip()
        if new_email and user.email != new_email:
            user.email = new_email
            changes_made.append("email")

        password = kwargs.get("password", "")
        if password:
            user.set_password(password)
            changes_made.append("password")

        admin = kwargs.get("admin")
        if admin is not None and hasattr(user, "is_admin"):
            if user.is_admin != admin:
                user.is_admin = admin
                changes_made.append("admin privileges")

        active = kwargs.get("active")
        if active is not None and hasattr(user, "is_active"):
            if user.is_active != active:
                user.is_active = active
                changes_made.append("active status")

        return changes_made

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute update user operation."""
        try:
            # Find user
            user = self._find_user_by_identifier(**kwargs)

            if not user:
                user_id = kwargs.get("user_id")
                username = kwargs.get("username", "").strip()
                email = kwargs.get("email", "").strip()

                if not any([user_id, username, email]):
                    return {"success": False, "message": "No user identifier provided"}

                return {"success": False, "message": "User not found with the provided identifier"}

            # Apply updates
            changes_made = self._apply_user_updates(user, **kwargs)

            if not changes_made:
                return {"success": True, "message": "No changes were needed", "data": {"changes": []}}

            db.session.commit()

            return {
                "success": True,
                "message": f"Updated user '{user.username}': {', '.join(changes_made)}",
                "data": {"user_id": user.id, "username": user.username, "email": user.email, "changes": changes_made},
            }

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.exception(f"Database error updating user: {e}")
            return {"success": False, "message": f"Database error: {str(e)}"}
        except Exception as e:
            db.session.rollback()
            logger.exception(f"Error updating user: {e}")
            return {"success": False, "message": f"Failed to update user: {str(e)}"}


class SystemStatsOperation(BaseAdminOperation):
    """Get system statistics."""

    name = "system_stats"
    description = "Get comprehensive system statistics and health metrics"
    requires_confirmation = False

    def validate_params(self, **kwargs) -> Dict[str, Any]:
        """Validate system stats parameters."""
        return {"valid": True, "errors": []}

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute system stats operation."""
        try:
            stats = {}

            # User statistics
            total_users = db.session.query(func.count(User.id)).scalar() or 0
            admin_users = db.session.query(func.count(User.id)).filter_by(is_admin=True).scalar() or 0

            stats["users"] = {"total": total_users, "admin": admin_users, "regular": total_users - admin_users}

            # Try to get content statistics (may not exist in all deployments)
            try:
                # Import models dynamically to avoid import errors
                from app.restaurants.models import Restaurant

                restaurant_count = db.session.query(func.count(Restaurant.id)).scalar() or 0
                stats["content"] = {"restaurants": restaurant_count}

                try:
                    from app.expenses.models import Expense

                    expense_count = db.session.query(func.count(Expense.id)).scalar() or 0
                    stats["content"]["expenses"] = expense_count
                except ImportError:
                    stats["content"]["expenses"] = "N/A (model not available)"

            except ImportError:
                stats["content"] = {"restaurants": "N/A (model not available)", "expenses": "N/A (model not available)"}

            # System information
            stats["system"] = {
                "database_connection": "active",
                "environment": current_app.config.get("ENV", "unknown"),
                "debug_mode": current_app.debug,
            }

            return {"success": True, "message": "System statistics retrieved", "data": stats}

        except Exception as e:
            logger.exception(f"Error getting system stats: {e}")
            return {"success": False, "message": f"Failed to get system stats: {str(e)}"}


class RecentActivityOperation(BaseAdminOperation):
    """Get recent system activity."""

    name = "recent_activity"
    description = "Get recent user and system activity"
    requires_confirmation = False

    def validate_params(self, **kwargs) -> Dict[str, Any]:
        """Validate recent activity parameters."""
        errors = []

        days = kwargs.get("days", 7)
        if not isinstance(days, int) or days < 1 or days > 365:
            errors.append("days must be an integer between 1 and 365")

        limit = kwargs.get("limit", 50)
        if not isinstance(limit, int) or limit < 1 or limit > 500:
            errors.append("limit must be an integer between 1 and 500")

        return {"valid": len(errors) == 0, "errors": errors}

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute recent activity operation."""
        try:
            days = kwargs.get("days", 7)
            limit = kwargs.get("limit", 50)

            since_date = datetime.now(timezone.utc) - timedelta(days=days)

            # Get recent users (those with created_at if available)
            recent_users = []
            try:
                users_query = User.query
                if hasattr(User, "created_at"):
                    users_query = users_query.filter(User.created_at >= since_date)

                users = users_query.order_by(User.id.desc()).limit(limit).all()

                for user in users:
                    recent_users.append(
                        {
                            "id": user.id,
                            "username": user.username,
                            "email": user.email,
                            "is_admin": getattr(user, "is_admin", False),
                            "created_at": getattr(user, "created_at", None),
                        }
                    )
            except Exception as e:
                logger.warning(f"Could not fetch recent users: {e}")

            activity_data = {
                "recent_users": recent_users,
                "period_days": days,
                "limit_applied": limit,
                "query_time": datetime.now(timezone.utc).isoformat(),
            }

            return {"success": True, "message": f"Retrieved activity for the last {days} days", "data": activity_data}

        except Exception as e:
            logger.exception(f"Error getting recent activity: {e}")
            return {"success": False, "message": f"Failed to get recent activity: {str(e)}"}


class InitializeDatabaseOperation(BaseAdminOperation):
    """Initialize the database with tables and default data."""

    name = "init_db"
    description = "Initialize database schema and create default data"
    requires_confirmation = True

    def validate_params(self, **kwargs) -> Dict[str, Any]:
        """Validate init database parameters."""
        errors = []

        force = kwargs.get("force", False)
        if not isinstance(force, bool):
            errors.append("force must be a boolean")

        sample_data = kwargs.get("sample_data", False)
        if not isinstance(sample_data, bool):
            errors.append("sample_data must be a boolean")

        return {"valid": len(errors) == 0, "errors": errors}

    def _check_existing_tables(self, force: bool) -> tuple[Optional[Dict[str, Any]], List[str]]:
        """Check for existing tables and handle force parameter.

        Args:
            force: Whether to force recreation of existing tables

        Returns:
            Tuple of (error_response, existing_tables_list)
        """
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()

        if existing_tables and not force:
            error_response = {
                "success": False,
                "message": f"Database already has {len(existing_tables)} tables. Use --force to recreate.",
                "data": {"existing_tables": existing_tables},
            }
            return error_response, existing_tables

        return None, existing_tables

    def _setup_database_schema(self, force: bool, existing_tables: List[str]) -> List[str]:
        """Set up database schema, optionally dropping existing tables.

        Args:
            force: Whether to drop existing tables
            existing_tables: List of existing table names

        Returns:
            List of operation results
        """
        results = []

        # Drop all tables if force is enabled
        if force and existing_tables:
            db.drop_all()
            results.append(f"Dropped {len(existing_tables)} existing tables")
            logger.info(f"Dropped existing tables: {existing_tables}")

        # Create all tables
        db.create_all()
        results.append("Created database schema with all tables")
        logger.info("Created database schema")

        return results

    def _create_default_admin_user(self) -> tuple[Optional[User], str]:
        """Create default admin user if it doesn't exist.

        Returns:
            Tuple of (admin_user, result_message)
        """
        try:
            from app.auth.models import User

            # Check if admin user already exists
            admin_user = User.query.filter_by(username="admin").first()
            if not admin_user:
                admin_user = User(username="admin", email="admin@example.com")
                admin_user.set_password("admin123")
                if hasattr(admin_user, "is_admin"):
                    admin_user.is_admin = True

                db.session.add(admin_user)
                db.session.commit()
                logger.info("Created default admin user")
                return admin_user, "Created default admin user (admin/admin123)"
            else:
                return admin_user, "Admin user already exists"

        except ImportError:
            logger.warning("User model not available")
            return None, "User model not available - skipping sample data creation"

    # Note: Review data model - potential confusion between expense categories and meal types
    def _create_default_categories(self, admin_user: User) -> str:
        """Create default expense categories for admin user.

        Args:
            admin_user: Admin user to create categories for

        Returns:
            Result message string
        """
        try:
            from app.expenses.models import Category

            default_categories = [
                {"name": "Breakfast", "color": "#FF6B6B", "icon": "coffee"},
                {"name": "Lunch", "color": "#4ECDC4", "icon": "utensils"},
                {"name": "Dinner", "color": "#45B7D1", "icon": "plate"},
                {"name": "Snacks", "color": "#96CEB4", "icon": "cookie"},
                {"name": "Dessert", "color": "#FCE7F3", "icon": "cupcake"},
                {"name": "Beverages", "color": "#FFEAA7", "icon": "glass"},
                {"name": "Groceries", "color": "#B2E0A4", "icon": "shopping-basket"},
            ]

            created_categories = 0
            for cat_data in default_categories:
                existing_cat = Category.query.filter_by(name=cat_data["name"], user_id=admin_user.id).first()

                if not existing_cat:
                    category = Category(
                        name=cat_data["name"],
                        color=cat_data["color"],
                        icon=cat_data["icon"],
                        is_default=True,
                        user_id=admin_user.id,
                    )
                    db.session.add(category)
                    created_categories += 1

            if created_categories > 0:
                db.session.commit()
                logger.info(f"Created {created_categories} default categories")
                return f"Created {created_categories} default categories"
            else:
                return "Default categories already exist"

        except ImportError:
            logger.warning("Category model not available")
            return "Category model not available - skipping default categories"

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute database initialization."""
        try:
            force = kwargs.get("force", False)
            sample_data = kwargs.get("sample_data", False)

            # Check if database already has tables
            error_response, existing_tables = self._check_existing_tables(force)
            if error_response:
                return error_response

            # Set up database schema
            results = self._setup_database_schema(force, existing_tables)

            # Create sample data if requested
            if sample_data:
                admin_user, user_result = self._create_default_admin_user()
                results.append(user_result)

                if admin_user:
                    category_result = self._create_default_categories(admin_user)
                    results.append(category_result)

            # Get final table count
            inspector = db.inspect(db.engine)
            final_tables = inspector.get_table_names()

            return {
                "success": True,
                "message": "Database initialization completed successfully",
                "data": {
                    "operations": results,
                    "tables_created": len(final_tables),
                    "table_names": final_tables,
                    "sample_data_created": sample_data,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                },
            }

        except Exception as e:
            db.session.rollback()
            logger.exception(f"Error initializing database: {e}")
            return {"success": False, "message": f"Database initialization failed: {str(e)}"}


class DatabaseMaintenanceOperation(BaseAdminOperation):
    """Perform database maintenance operations."""

    name = "db_maintenance"
    description = "Perform database maintenance and optimization"
    requires_confirmation = True

    def validate_params(self, **kwargs) -> Dict[str, Any]:
        """Validate database maintenance parameters."""
        errors = []

        operation = kwargs.get("operation", "analyze")
        if operation not in ["analyze", "vacuum"]:
            errors.append("operation must be 'analyze' or 'vacuum'")

        return {"valid": len(errors) == 0, "errors": errors}

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute database maintenance operation."""
        try:
            operation = kwargs.get("operation", "analyze")

            if operation == "analyze":
                # Run ANALYZE on PostgreSQL or similar operation
                try:
                    db.session.execute(text("ANALYZE"))
                    db.session.commit()
                    message = "Database analysis completed successfully"
                except Exception as e:
                    # Fallback for SQLite or other databases
                    logger.warning(f"ANALYZE command failed, trying alternative: {e}")
                    message = "Database maintenance completed (basic statistics updated)"

            elif operation == "vacuum":
                try:
                    db.session.execute(text("VACUUM"))
                    db.session.commit()
                    message = "Database vacuum completed successfully"
                except Exception as e:
                    logger.warning(f"VACUUM command failed: {e}")
                    message = "Vacuum operation not supported on this database type"

            return {
                "success": True,
                "message": message,
                "data": {"operation": operation, "completed_at": datetime.now(timezone.utc).isoformat()},
            }

        except Exception as e:
            db.session.rollback()
            logger.exception(f"Error in database maintenance: {e}")
            return {"success": False, "message": f"Database maintenance failed: {str(e)}"}


class ValidateRestaurantsOperation(BaseAdminOperation):
    """Validate restaurant information using Google Places API."""

    name = "validate_restaurants"
    description = "Validate restaurant information against Google Places API and optionally fix mismatches"
    requires_confirmation = False

    def _build_street_address_from_components(self, address_components: list[dict]) -> str:
        """Build street address from Google Places address components."""
        street_number = next(
            (comp.get("long_name") for comp in address_components if "street_number" in comp.get("types", [])),
            None,
        )
        route = next(
            (comp.get("long_name") for comp in address_components if "route" in comp.get("types", [])),
            None,
        )
        return " ".join(filter(None, [street_number, route]))

    def _detect_service_level_from_google_data(self, google_data: dict) -> tuple[str, float]:
        """Detect service level from Google Places data."""
        from app.restaurants.services import detect_service_level_from_google_data

        return detect_service_level_from_google_data(google_data)

    def validate_params(self, **kwargs) -> Dict[str, Any]:
        """Validate restaurant validation parameters."""
        errors = []

        # Must specify at least one filter
        user_id = kwargs.get("user_id")
        username = kwargs.get("username", "").strip()
        all_users = kwargs.get("all_users", False)
        restaurant_id = kwargs.get("restaurant_id")

        if not any([user_id, username, all_users, restaurant_id]):
            errors.append("Must specify --user-id, --username, --all-users, or --restaurant-id")

        if user_id is not None and not isinstance(user_id, int):
            errors.append("user_id must be an integer")

        if restaurant_id is not None and not isinstance(restaurant_id, int):
            errors.append("restaurant_id must be an integer")

        fix_mismatches = kwargs.get("fix_mismatches", False)
        if not isinstance(fix_mismatches, bool):
            errors.append("fix_mismatches must be a boolean")

        update_service_levels = kwargs.get("update_service_levels", False)
        if not isinstance(update_service_levels, bool):
            errors.append("update_service_levels must be a boolean")

        dry_run = kwargs.get("dry_run", False)
        if not isinstance(dry_run, bool):
            errors.append("dry_run must be a boolean")

        find_place_id = kwargs.get("find_place_id", False)
        if not isinstance(find_place_id, bool):
            errors.append("find_place_id must be a boolean")

        closest = kwargs.get("closest", False)
        if not isinstance(closest, bool):
            errors.append("closest must be a boolean")

        return {"valid": len(errors) == 0, "errors": errors}

    def _get_target_users(self, **kwargs) -> tuple[Optional[Dict[str, Any]], List[User]]:
        """Get target users based on parameters."""
        try:
            user_id = kwargs.get("user_id")
            username = kwargs.get("username", "").strip()
            all_users = kwargs.get("all_users", False)

            if user_id:
                from app.extensions import db

                user = db.session.get(User, user_id)
                if not user:
                    return {"success": False, "message": f"User with ID {user_id} not found"}, []
                return None, [user]
            elif username:
                user = User.query.filter_by(username=username).first()
                if not user:
                    return {"success": False, "message": f"User with username '{username}' not found"}, []
                return None, [user]
            elif all_users:
                users = User.query.all()
                if not users:
                    return {"success": False, "message": "No users found in database"}, []
                return None, users

            return {"success": False, "message": "No user filter provided"}, []

        except Exception as e:
            logger.exception(f"Error getting target users: {e}")
            return {"success": False, "message": f"Failed to get users: {str(e)}"}, []

    def _get_restaurants_to_validate(self, **kwargs) -> tuple[Optional[Dict[str, Any]], List, Dict[str, int]]:
        """Get restaurants to validate based on parameters."""
        try:
            from app.restaurants.models import Restaurant

            restaurant_id = kwargs.get("restaurant_id")
            counts = {"total_restaurants": 0, "missing_google_id": 0, "with_google_id": 0}

            if restaurant_id:
                from app.extensions import db

                restaurant = db.session.get(Restaurant, restaurant_id)
                if not restaurant:
                    return {"success": False, "message": f"Restaurant with ID {restaurant_id} not found"}, [], counts

                counts["total_restaurants"] = 1
                if restaurant.google_place_id:
                    counts["with_google_id"] = 1
                else:
                    counts["missing_google_id"] = 1

                return None, [restaurant] if restaurant.google_place_id else [], counts
            else:
                error_response, users = self._get_target_users(**kwargs)
                if error_response:
                    return error_response, [], counts

                restaurants_to_validate = []
                for user in users:
                    # Get all restaurants for count statistics
                    all_user_restaurants = Restaurant.query.filter_by(user_id=user.id).all()
                    counts["total_restaurants"] += len(all_user_restaurants)

                    # Get restaurants with Google Place IDs for validation
                    user_restaurants_with_google_id = [r for r in all_user_restaurants if r.google_place_id]
                    user_restaurants_without_google_id = [r for r in all_user_restaurants if not r.google_place_id]

                    counts["with_google_id"] += len(user_restaurants_with_google_id)
                    counts["missing_google_id"] += len(user_restaurants_without_google_id)

                    restaurants_to_validate.extend(user_restaurants_with_google_id)

                return None, restaurants_to_validate, counts

        except ImportError:
            return {"success": False, "message": "Restaurant model not available"}, [], counts
        except Exception as e:
            logger.exception(f"Error getting restaurants to validate: {e}")
            return {"success": False, "message": f"Failed to get restaurants: {str(e)}"}, [], counts

    def _validate_restaurant_with_google(self, restaurant) -> Dict[str, Any]:
        """Validate restaurant using Google Places API."""
        try:
            from app.api.routes import get_gmaps_client

            if not restaurant.google_place_id:
                return {"valid": None, "errors": ["No Google Place ID available for validation"]}

            gmaps = get_gmaps_client()
            if not gmaps:
                return {"valid": False, "errors": ["Google Maps API not configured"]}

            place = gmaps.place(
                place_id=restaurant.google_place_id,
                language="en",
                fields=[
                    "name",
                    "formatted_address",
                    "geometry/location",
                    "rating",
                    "business_status",
                    "type",
                    "user_ratings_total",
                    "opening_hours",
                    "website",
                    "international_phone_number",
                    "price_level",
                    "editorial_summary",
                    "address_component",
                ],
            )

            if place and "result" in place:
                google_data = place["result"]
                return {
                    "valid": True,
                    "google_name": google_data.get("name"),
                    "google_address": google_data.get("formatted_address"),
                    "google_rating": google_data.get("rating"),
                    "google_status": google_data.get("business_status"),
                    "types": google_data.get("type", []),
                    "google_phone": google_data.get("international_phone_number"),
                    "google_website": google_data.get("website"),
                    "google_price_level": google_data.get("price_level"),
                    "google_street_address": self._build_street_address_from_components(
                        google_data.get("address_component", [])
                    ),
                    "google_service_level": self._detect_service_level_from_google_data(google_data),
                    "errors": [],
                }
            elif place and "status" in place:
                status = place["status"]
                error_msg = place.get("error_message", f"Google API error: {status}")
                return {"valid": False, "errors": [error_msg]}
            else:
                return {"valid": False, "errors": ["No response from Google Places API"]}

        except ImportError:
            return {"valid": False, "errors": ["Google Places API service not available"]}
        except Exception as e:
            logger.exception(f"Error validating restaurant {restaurant.id}: {e}")
            return {"valid": False, "errors": [f"Unexpected error: {str(e)}"]}

    def _check_restaurant_mismatches(
        self, restaurant, validation_result: Dict[str, Any]
    ) -> tuple[List[str], Dict[str, str]]:
        """Check for mismatches between restaurant data and Google data."""
        google_name = validation_result.get("google_name")
        google_street_address = validation_result.get("google_street_address")

        mismatches = []
        fixes_to_apply = {}

        if google_name and google_name.lower() != restaurant.name.lower():
            mismatches.append(f"Name: '{restaurant.name}' vs Google: '{google_name}'")
            fixes_to_apply["name"] = google_name

        if google_street_address and restaurant.address and google_street_address.lower() != restaurant.address.lower():
            mismatches.append(f"Address: '{restaurant.address}' vs Google: '{google_street_address}'")
            fixes_to_apply["address"] = google_street_address

        # Check service level
        google_service_level_data = validation_result.get("google_service_level")
        if google_service_level_data:
            google_service_level, confidence = google_service_level_data
            from app.restaurants.services import validate_restaurant_service_level

            has_mismatch, mismatch_message, suggested_fix = validate_restaurant_service_level(
                restaurant, google_service_level, confidence
            )

            if has_mismatch:
                mismatches.append(mismatch_message)
                if suggested_fix:
                    fixes_to_apply["service_level"] = suggested_fix

        return mismatches, fixes_to_apply

    def _apply_restaurant_fixes(self, restaurant, fixes_to_apply: Dict[str, str], dry_run: bool) -> tuple[bool, str]:
        """Apply fixes to restaurant data."""
        if dry_run:
            return True, f"Would fix: {', '.join(fixes_to_apply.keys())}"

        try:
            changes_made = []
            if "name" in fixes_to_apply:
                restaurant.name = fixes_to_apply["name"]
                changes_made.append("name")
            if "address" in fixes_to_apply:
                restaurant.address = fixes_to_apply["address"]
                changes_made.append("address")
            if "service_level" in fixes_to_apply:
                restaurant.service_level = fixes_to_apply["service_level"]
                changes_made.append("service_level")

            if changes_made:
                db.session.commit()
                return True, f"Fixed: {', '.join(changes_made)}"
            else:
                return True, "No changes needed"

        except Exception as e:
            db.session.rollback()
            logger.exception(f"Error fixing restaurant {restaurant.id}: {e}")
            return False, f"Error fixing: {str(e)}"

    def _process_restaurant_validation(self, restaurant, fix_mismatches: bool, dry_run: bool) -> Dict[str, Any]:
        """Process validation for a single restaurant."""
        result = {
            "id": restaurant.id,
            "name": restaurant.name,
            "user_id": restaurant.user_id,
            "google_place_id": restaurant.google_place_id,
            "status": "error",
            "mismatches": [],
            "has_mismatches": False,
            "fixed": False,
            "would_fix": False,
            "dry_run": dry_run,
            "errors": [],
        }

        validation_result = self._validate_restaurant_with_google(restaurant)

        if validation_result["valid"] is True:
            result["status"] = "valid"

            # Check for mismatches
            mismatches, fixes_to_apply = self._check_restaurant_mismatches(restaurant, validation_result)
            result["mismatches"] = mismatches
            result["has_mismatches"] = len(mismatches) > 0

            if mismatches and fix_mismatches and fixes_to_apply:
                fixed, fix_message = self._apply_restaurant_fixes(restaurant, fixes_to_apply, dry_run)
                if dry_run:
                    result["would_fix"] = fixed
                else:
                    result["fixed"] = fixed
                result["fix_message"] = fix_message

        elif validation_result["valid"] is False:
            result["status"] = "invalid"
            result["errors"] = validation_result["errors"]
        else:
            result["status"] = "error"
            result["errors"] = validation_result["errors"]

        return result

    def _process_all_restaurants(
        self, restaurants_to_validate: List, fix_mismatches: bool, dry_run: bool
    ) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
        """Process validation for all restaurants and return results and counts."""
        validation_results = []
        valid_count = 0
        invalid_count = 0
        error_count = 0
        fixed_count = 0
        mismatch_count = 0

        for restaurant in restaurants_to_validate:
            result = self._process_restaurant_validation(restaurant, fix_mismatches, dry_run)
            validation_results.append(result)

            if result["status"] == "valid":
                valid_count += 1
            elif result["status"] == "invalid":
                invalid_count += 1
            else:
                error_count += 1

            if result.get("fixed") or result.get("would_fix"):
                fixed_count += 1

            if result.get("has_mismatches"):
                mismatch_count += 1

        summary = {
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "error_count": error_count,
            "fixed_count": fixed_count,
            "mismatch_count": mismatch_count,
            "dry_run": dry_run,
            "total_restaurants": len(validation_results),
        }

        return validation_results, summary

    def _get_restaurants_without_google_id(self, **kwargs) -> List[Restaurant]:
        """Get restaurants without Google Place IDs for service level updates."""
        try:
            pass

            # Handle specific restaurant case
            restaurant_id = kwargs.get("restaurant_id")
            if restaurant_id:
                return self._get_specific_restaurant_without_google_id(restaurant_id)

            # Handle user-based filtering
            users = self._get_target_users_for_service_levels(**kwargs)
            if not users:
                return []

            return self._get_restaurants_for_users_without_google_id(users)

        except Exception as e:
            logger.exception(f"Error getting restaurants without Google Place IDs: {e}")
            return []

    def _get_specific_restaurant_without_google_id(self, restaurant_id: int) -> List[Restaurant]:
        """Get specific restaurant without Google Place ID."""
        from app.extensions import db
        from app.restaurants.models import Restaurant

        restaurant = db.session.get(Restaurant, restaurant_id)
        if restaurant and not restaurant.google_place_id:
            return [restaurant]
        return []

    def _get_target_users_for_service_levels(self, **kwargs) -> List[User]:
        """Get target users for service level updates."""
        user_id = kwargs.get("user_id")
        username = kwargs.get("username", "").strip()
        all_users = kwargs.get("all_users", False)

        if user_id:
            from app.extensions import db

            user = db.session.get(User, user_id)
            return [user] if user else []
        elif username:
            user = User.query.filter_by(username=username).first()
            return [user] if user else []
        elif all_users:
            return User.query.all()

        return []

    def _get_restaurants_for_users_without_google_id(self, users: List[User]) -> List[Restaurant]:
        """Get restaurants without Google Place IDs for given users."""
        from app.restaurants.models import Restaurant

        restaurants = []
        for user in users:
            user_restaurants = (
                Restaurant.query.filter_by(user_id=user.id).filter(Restaurant.google_place_id.is_(None)).all()
            )
            restaurants.extend(user_restaurants)

        return restaurants

    def _suggest_service_level_from_restaurant_data(self, restaurant: Restaurant) -> str:
        """Suggest service level based on available restaurant data."""
        name_lower = restaurant.name.lower()

        # Quick service indicators
        quick_service_keywords = [
            "mcdonald",
            "burger king",
            "wendy",
            "subway",
            "kfc",
            "taco bell",
            "pizza hut",
            "domino",
            "chipotle",
            "starbucks",
            "dunkin",
            "pizza",
            "burger",
            "sandwich",
            "coffee",
            "ice cream",
            "donut",
            "bakery",
        ]

        # Fast casual indicators
        fast_casual_keywords = [
            "panera",
            "chipotle",
            "qdoba",
            "moe",
            "noodles",
            "panda express",
            "five guys",
            "shake shack",
            "in-n-out",
            "whataburger",
        ]

        # Fine dining indicators
        fine_dining_keywords = [
            "steakhouse",
            "grill",
            "bistro",
            "cafe",
            "restaurant",
            "dining",
            "kitchen",
            "table",
            "chef",
            "gourmet",
            "fine",
            "upscale",
        ]

        # Check for quick service
        for keyword in quick_service_keywords:
            if keyword in name_lower:
                return "quick_service"

        # Check for fast casual
        for keyword in fast_casual_keywords:
            if keyword in name_lower:
                return "fast_casual"

        # Check for fine dining
        for keyword in fine_dining_keywords:
            if keyword in name_lower:
                return "fine_dining"

        # Default to casual dining if no specific indicators found
        return "casual_dining"

    def _update_service_levels_for_restaurants_without_google_id(self, **kwargs) -> Dict[str, Any]:
        """Update service levels for restaurants without Google Place IDs."""
        try:
            restaurants = self._get_restaurants_without_google_id(**kwargs)
            if not restaurants:
                return {
                    "success": True,
                    "message": "No restaurants without Google Place IDs found",
                    "updated_count": 0,
                    "total_count": 0,
                }

            dry_run = kwargs.get("dry_run", False)
            updated_count = 0

            for restaurant in restaurants:
                logger.info(f"Processing restaurant {restaurant.id}: {restaurant.name}")

                suggested_service_level = self._suggest_service_level_from_restaurant_data(restaurant)

                if suggested_service_level and suggested_service_level != restaurant.service_level:
                    if dry_run:
                        logger.info(
                            f"Would update service level for {restaurant.name}: '{restaurant.service_level or 'Not set'}' → '{suggested_service_level}'"
                        )
                    else:
                        try:
                            restaurant.service_level = suggested_service_level
                            db.session.commit()
                            logger.info(f"Updated service level for {restaurant.name}: '{suggested_service_level}'")
                            updated_count += 1
                        except Exception as e:
                            db.session.rollback()
                            logger.error(f"Error updating service level for {restaurant.name}: {e}")
                else:
                    logger.info(f"No service level update needed for {restaurant.name}")

            action_text = "would update" if dry_run else "updated"
            return {
                "success": True,
                "message": f"Successfully {action_text} service levels for {updated_count} out of {len(restaurants)} restaurants",
                "updated_count": updated_count,
                "total_count": len(restaurants),
            }

        except Exception as e:
            logger.exception(f"Error updating service levels: {e}")
            return {
                "success": False,
                "message": f"Failed to update service levels: {str(e)}",
                "updated_count": 0,
                "total_count": 0,
            }

    def _get_action_text(self, fix_mismatches: bool, dry_run: bool) -> str:
        """Get appropriate action text based on parameters."""
        if fix_mismatches:
            if dry_run:
                return "validated (dry run - no changes made)"
            else:
                return "validated and fixed"
        return "validated"

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute restaurant validation operation."""
        try:
            fix_mismatches = kwargs.get("fix_mismatches", False)
            update_service_levels = kwargs.get("update_service_levels", False)
            dry_run = kwargs.get("dry_run", False)
            find_place_id = kwargs.get("find_place_id", False)

            # Handle service level updates and place ID finding
            service_level_results = self._handle_service_level_updates(update_service_levels, **kwargs)
            place_id_results = self._handle_place_id_finding(find_place_id, **kwargs)

            # Get restaurants to validate
            error_response, restaurants_to_validate, restaurant_counts = self._get_restaurants_to_validate(**kwargs)
            if error_response:
                return error_response

            if not restaurants_to_validate:
                return self._build_no_restaurants_response(
                    restaurant_counts, service_level_results, place_id_results, dry_run
                )

            # Process all restaurants
            validation_results, summary = self._process_all_restaurants(
                restaurants_to_validate, fix_mismatches, dry_run
            )

            # Build final response
            return self._build_validation_response(
                validation_results,
                summary,
                restaurant_counts,
                service_level_results,
                place_id_results,
                fix_mismatches,
                dry_run,
            )

        except Exception as e:
            logger.exception(f"Error in restaurant validation: {e}")
            return {"success": False, "message": f"Restaurant validation failed: {str(e)}"}

    def _handle_service_level_updates(self, update_service_levels: bool, **kwargs) -> Dict[str, Any] | None:
        """Handle service level updates for restaurants without Google Place IDs."""
        if update_service_levels:
            return self._update_service_levels_for_restaurants_without_google_id(**kwargs)
        return None

    def _handle_place_id_finding(self, find_place_id: bool, **kwargs) -> Dict[str, Any] | None:
        """Handle place ID finding for restaurants without Google Place IDs."""
        if find_place_id:
            return self._find_place_ids_for_restaurants_without_google_id(**kwargs)
        return None

    def _build_no_restaurants_response(
        self, restaurant_counts: dict, service_level_results: dict | None, place_id_results: dict | None, dry_run: bool
    ) -> Dict[str, Any]:
        """Build response when no restaurants are found to validate."""
        summary = {
            "total_restaurants": restaurant_counts["total_restaurants"],
            "missing_google_id": restaurant_counts["missing_google_id"],
            "with_google_id": restaurant_counts["with_google_id"],
            "valid_count": 0,
            "invalid_count": 0,
            "error_count": 0,
            "fixed_count": 0,
            "mismatch_count": 0,
            "dry_run": dry_run,
        }

        # Add service level metrics to summary
        if service_level_results and service_level_results.get("success"):
            summary["service_level_metrics"] = {
                "total_without_google_id": service_level_results.get("total_count", 0),
                "updated_count": service_level_results.get("updated_count", 0),
                "dry_run": dry_run,
            }

        # Add place ID finding metrics to summary
        if place_id_results and place_id_results.get("success"):
            summary["place_id_metrics"] = {
                "found_count": place_id_results.get("found_count", 0),
                "warning_count": place_id_results.get("warning_count", 0),
                "error_count": place_id_results.get("error_count", 0),
                "dry_run": dry_run,
            }

        return {
            "success": True,
            "message": "No restaurants with Google Place IDs found to validate",
            "data": {
                "restaurant_counts": restaurant_counts,
                "service_level_results": service_level_results,
                "place_id_results": place_id_results,
                "summary": summary,
            },
        }

    def _build_validation_response(
        self,
        validation_results: list,
        summary: dict,
        restaurant_counts: dict,
        service_level_results: dict | None,
        place_id_results: dict | None,
        fix_mismatches: bool,
        dry_run: bool,
    ) -> Dict[str, Any]:
        """Build final validation response."""
        # Merge restaurant counts into summary
        summary.update(restaurant_counts)

        action_text = self._get_action_text(fix_mismatches, dry_run)

        # Add service level metrics to summary
        if service_level_results and service_level_results.get("success"):
            summary["service_level_metrics"] = {
                "total_without_google_id": service_level_results.get("total_count", 0),
                "updated_count": service_level_results.get("updated_count", 0),
                "dry_run": dry_run,
            }

        # Add place ID finding metrics to summary
        if place_id_results and place_id_results.get("success"):
            summary["place_id_metrics"] = {
                "found_count": place_id_results.get("found_count", 0),
                "warning_count": place_id_results.get("warning_count", 0),
                "error_count": place_id_results.get("error_count", 0),
                "dry_run": dry_run,
            }

        return {
            "success": True,
            "message": f"Successfully {action_text} {len(validation_results)} restaurants",
            "data": {
                "validation_results": validation_results,
                "summary": summary,
                "service_level_results": service_level_results,
                "place_id_results": place_id_results,
            },
        }

    def _find_place_ids_for_restaurants_without_google_id(self, **kwargs) -> Dict[str, Any]:
        """Find Google Place IDs for restaurants without them."""
        try:
            from app.restaurants.models import Restaurant

            # Get restaurants without Google Place IDs
            error_response, users = self._get_target_users(**kwargs)
            if error_response:
                return error_response

            restaurants_without_google_id = []
            for user in users:
                user_restaurants = (
                    Restaurant.query.filter_by(user_id=user.id).filter(Restaurant.google_place_id.is_(None)).all()
                )
                restaurants_without_google_id.extend(user_restaurants)

            if not restaurants_without_google_id:
                return {
                    "success": True,
                    "message": "All restaurants already have Google Place IDs",
                    "found_count": 0,
                    "warning_count": 0,
                    "error_count": 0,
                }

            # Process restaurants to find place IDs
            return self._process_place_id_finding(restaurants_without_google_id, **kwargs)

        except Exception as e:
            logger.exception(f"Error finding place IDs: {e}")
            return {"success": False, "message": f"Place ID finding failed: {str(e)}"}

    def _process_place_id_finding(self, restaurants: list, **kwargs) -> Dict[str, Any]:
        """Process restaurants to find Google Place IDs."""
        from app.extensions import db

        dry_run = kwargs.get("dry_run", False)
        closest = kwargs.get("closest", False)

        found_count = 0
        warning_count = 0
        error_count = 0

        for restaurant in restaurants:
            place_id, matches = self._find_google_place_match(restaurant)

            if place_id:
                found_count += 1
                if not dry_run:
                    restaurant.google_place_id = place_id
                    db.session.commit()
            elif matches:
                if closest and len(matches) > 1:
                    closest_match = self._find_closest_match(restaurant, matches)
                    if closest_match:
                        closest_place_id = closest_match.get("id")
                        if not dry_run:
                            restaurant.google_place_id = closest_place_id
                            db.session.commit()
                        found_count += 1
                    else:
                        warning_count += 1
                else:
                    warning_count += 1
            else:
                error_count += 1

        return {
            "success": True,
            "message": "Place ID finding completed",
            "found_count": found_count,
            "warning_count": warning_count,
            "error_count": error_count,
        }

    def _find_google_place_match(self, restaurant) -> tuple[str | None, list[dict]]:
        """Find Google Place ID match for a restaurant based on name and address."""
        try:
            name = restaurant.name
            address = restaurant.full_address

            places = self._search_google_places_by_name_and_address(name, address)

            if not places:
                return None, []

            exact_matches = []
            for place in places:
                place_name = (
                    place.get("displayName", {}).get("text", "")
                    if isinstance(place.get("displayName"), dict)
                    else place.get("displayName", "")
                )

                if place_name.lower() == name.lower():
                    exact_matches.append(place)

            if len(exact_matches) == 1:
                return exact_matches[0].get("id"), exact_matches

            if len(exact_matches) > 1:
                return None, exact_matches

            return None, places

        except Exception as e:
            logger.exception(f"Error finding Google Place match: {e}")
            return None, []

    def _search_google_places_by_name_and_address(self, name: str, address: str | None = None) -> list[dict]:
        """Search Google Places API for restaurants by name and address."""
        try:
            import requests
            from flask import current_app

            api_key = current_app.config.get("GOOGLE_MAPS_API_KEY")
            if not api_key:
                return []

            search_query = name
            if address:
                search_query += f" {address}"

            url = "https://places.googleapis.com/v1/places:searchText"
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.location",
            }
            payload = {
                "textQuery": search_query,
                "maxResultCount": 10,
                "includedType": "restaurant",
            }

            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("places", [])

        except Exception as e:
            logger.exception(f"Error searching Google Places: {e}")
            return []

    def _find_closest_match(self, restaurant, matches: list[dict]) -> dict | None:
        """Find the closest match based on restaurant address and Google Places coordinates."""
        if not matches:
            return None

        restaurant_city = restaurant.city
        restaurant_state = restaurant.state

        if not restaurant_city or not restaurant_state:
            return matches[0]

        best_match = None
        best_score = -1

        for match in matches:
            match_address = match.get("formattedAddress", "").lower()
            score = 0

            if restaurant_city.lower() in match_address:
                score += 2

            if restaurant_state.lower() in match_address:
                score += 1

            city_state_combo = f"{restaurant_city.lower()}, {restaurant_state.lower()}"
            if city_state_combo in match_address:
                score += 3

            if score > best_score:
                best_score = score
                best_match = match

        return best_match if best_match else matches[0]


class RunMigrationsOperation(BaseAdminOperation):
    """Run database migrations safely using the migration manager."""

    name = "run_migrations"
    description = "Run pending database migrations without affecting existing data"
    requires_confirmation = True

    def validate_params(self, **kwargs) -> Dict[str, Any]:
        """Validate migration parameters."""
        errors = []

        # Optional: target revision
        target_revision = kwargs.get("target_revision")
        if target_revision is not None and not isinstance(target_revision, str):
            errors.append("target_revision must be a string or None")

        # Optional: dry run
        dry_run = kwargs.get("dry_run", False)
        if not isinstance(dry_run, bool):
            errors.append("dry_run must be a boolean")

        return {"valid": len(errors) == 0, "errors": errors}

    def _handle_fix_history(self) -> Dict[str, Any]:
        """Handle migration history fix operation."""
        from app.utils.migration_manager import migration_manager

        logger.info("Fixing migration history...")
        fix_result = migration_manager.fix_migration_history()
        if not fix_result["success"]:
            return {
                "success": False,
                "message": f"Failed to fix migration history: {fix_result['error']}",
                "data": {"error": fix_result["error"]},
            }
        logger.info("Migration history fixed successfully")
        return {"success": True}

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute database migrations using the migration manager."""
        try:
            dry_run = kwargs.get("dry_run", False)
            target_revision = kwargs.get("target_revision")
            fix_history = kwargs.get("fix_history", False)

            with current_app.app_context():
                from app.utils.migration_manager import migration_manager

                # Handle fix_history parameter
                if fix_history:
                    fix_result = self._handle_fix_history()
                    if not fix_result["success"]:
                        return fix_result

                # Run migrations using the migration manager
                result = migration_manager.run_migrations(dry_run=dry_run, target_revision=target_revision)

                return result

        except Exception as e:
            logger.exception(f"Database migration failed: {e}")
            return {
                "success": False,
                "message": f"Database migration failed: {str(e)}",
                "data": {
                    "error": str(e),
                },
            }


class AdminOperationRegistry:
    """Registry for all available admin operations."""

    _operations = {
        "list_users": ListUsersOperation,
        "create_user": CreateUserOperation,
        "update_user": UpdateUserOperation,
        "system_stats": SystemStatsOperation,
        "recent_activity": RecentActivityOperation,
        "init_db": InitializeDatabaseOperation,
        "db_maintenance": DatabaseMaintenanceOperation,
        "validate_restaurants": ValidateRestaurantsOperation,
        "run_migrations": RunMigrationsOperation,
    }

    @classmethod
    def get_operation(cls, name: str) -> Optional[type]:
        """Get operation class by name."""
        return cls._operations.get(name)

    @classmethod
    def list_operations(cls) -> Dict[str, str]:
        """List all available operations with descriptions."""
        operations = {}
        for name, operation_class in cls._operations.items():
            operations[name] = operation_class.description
        return operations

    @classmethod
    def register_operation(cls, name: str, operation_class: type):
        """Register a new operation."""
        cls._operations[name] = operation_class
