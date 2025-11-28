#!/usr/bin/env python3
"""Remote administration client for Lambda-deployed Meal Expense Tracker.

This script allows you to perform administrative operations on the deployed
application via Lambda function invocations, providing CLI-like functionality
for AWS deployments.

Usage:
    python scripts/remote_admin.py [OPTIONS] COMMAND [ARGS]

Examples:
    # List available operations
    python scripts/remote_admin.py list-operations

    # List all users
    python scripts/remote_admin.py list-users

    # List only admin users
    python scripts/remote_admin.py list-users --admin-only

    # Create a new user
    python scripts/remote_admin.py create-user --username newuser --email user@example.com --password secretpass123

    # Create admin user with confirmation
    python scripts/remote_admin.py --confirm create-user --username admin --email admin@example.com --password admin123 --admin

    # Get system statistics
    python scripts/remote_admin.py system-stats

    # Update user
    python scripts/remote_admin.py --confirm update-user --user-id 1 --admin

    # Recent activity
    python scripts/remote_admin.py recent-activity --days 30

    # Validate restaurants
    python scripts/remote_admin.py validate-restaurants --user-id 1
    python scripts/remote_admin.py validate-restaurants --username admin --dry-run
    python scripts/remote_admin.py validate-restaurants --all-users --fix-mismatches
    python scripts/remote_admin.py validate-restaurants --restaurant-id 123
    python scripts/remote_admin.py validate-restaurants --find-place-id --dry-run
    python scripts/remote_admin.py validate-restaurants --find-place-id --closest --dry-run

    # Run migrations
    python scripts/remote_admin.py run-migrations --dry-run
    python scripts/remote_admin.py --confirm run-migrations

    # Fix migration history for existing tables (if you get "already exists" errors)
    python scripts/remote_admin.py --confirm run-migrations --fix-history

    # Run migrations with specific target revision
    python scripts/remote_admin.py --confirm run-migrations --target-revision 7943db7ca196

    # Initialize database (with confirmation)
    python scripts/remote_admin.py --confirm init-db --sample-data

    # Force recreate database with sample data
    python scripts/remote_admin.py --confirm init-db --force --sample-data
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional, cast

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


class RemoteAdminClient:
    """Client for remote administration via Lambda."""

    def __init__(self, function_name: str, region: str = "us-east-1"):
        self.function_name = function_name
        self.region = region
        self.lambda_client: Any = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize the Lambda client."""
        try:
            self.lambda_client = boto3.client("lambda", region_name=self.region)
            # Test credentials
            self.lambda_client.get_account_settings()
        except NoCredentialsError:
            print("❌ Error: AWS credentials not configured.")
            print("Please configure your AWS credentials using:")
            print("  - aws configure")
            print("  - Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)")
            print("  - IAM roles (if running on EC2)")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error initializing AWS client: {e}")
            sys.exit(1)

    def invoke_operation(
        self, operation_name: str, parameters: dict[str, Any], confirm: bool = False
    ) -> dict[str, Any]:
        """Invoke an admin operation on the Lambda function."""
        payload = {"admin_operation": operation_name, "parameters": parameters, "confirm": confirm}

        try:
            response = self.lambda_client.invoke(
                FunctionName=self.function_name, InvocationType="RequestResponse", Payload=json.dumps(payload)
            )

            # Parse response
            response_payload = json.loads(response["Payload"].read())

            if response.get("FunctionError"):
                return {"success": False, "message": f"Lambda function error: {response_payload}"}

            # Parse the body if it's a Lambda API Gateway response
            if "body" in response_payload:
                body_data = json.loads(response_payload["body"])
                return cast(dict[str, Any], body_data)

            return cast(dict[str, Any], response_payload)

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ResourceNotFound":
                return {
                    "success": False,
                    "message": f"Lambda function '{self.function_name}' not found in region '{self.region}'",
                }
            elif error_code == "AccessDenied":
                return {
                    "success": False,
                    "message": "Access denied. Check your AWS permissions for Lambda:InvokeFunction",
                }
            else:
                return {"success": False, "message": f"AWS Error: {e.response['Error']['Message']}"}
        except Exception as e:
            return {"success": False, "message": f"Unexpected error: {str(e)}"}

    def list_operations(self) -> dict[str, Any]:
        """List available admin operations."""
        return self.invoke_operation("list_operations", {})

    def format_response(self, response: dict[str, Any], verbose: bool = False) -> str:
        """Format response for display."""
        if not response.get("success"):
            return f"❌ {response.get('message', 'Operation failed')}"

        message = response.get("message", "Operation completed")
        output = [f"✅ {message}"]

        data = response.get("data")
        if data:
            if verbose:
                output.append(f"\n📊 Data: {json.dumps(data, indent=2, default=str)}")
            else:
                self._format_data_output(data, output)

        return "\n".join(output)

    def _format_data_output(self, data: dict[str, Any], output: list[str]) -> None:
        """Format data output for specific data types."""
        if "users" in data and isinstance(data["users"], list):
            self._format_users_output(data["users"], output)
        elif "operations" in data:
            self._format_operations_output(data["operations"], output)
        elif "validation_results" in data:
            self._format_validation_results_output(data, output)
        elif any(key in data for key in ["users", "content", "system"]):
            self._format_stats_output(data, output)

    def _format_users_output(self, users: list[dict[str, Any]], output: list[str]) -> None:
        """Format users list output."""
        output.append(f"\n👥 Users ({len(users)}):")
        for user in users[:10]:  # Show first 10
            admin_badge = " 👑" if user.get("is_admin") else ""
            active_badge = " ✅" if user.get("is_active") else " ❌"
            output.append(f"  • {user.get('username', 'N/A')} ({user.get('email', 'N/A')}){admin_badge}{active_badge}")
        if len(users) > 10:
            output.append(f"  ... and {len(users) - 10} more")

    def _format_operations_output(self, operations: Any, output: list[str]) -> None:
        """Format operations list output."""
        if isinstance(operations, dict):
            output.append(f"\n🛠️  Available Operations ({len(operations)}):")
            for name, info in operations.items():
                confirm_badge = " ⚠️" if info.get("requires_confirmation") else ""
                output.append(f"  • {name}: {info.get('description', 'No description')}{confirm_badge}")
        elif isinstance(operations, list):
            output.append(f"\n🛠️  Available Operations ({len(operations)}):")
            for op in operations:
                if isinstance(op, dict):
                    name = op.get("name", "Unknown")
                    description = op.get("description", "No description")
                    confirm_badge = " ⚠️" if op.get("requires_confirmation") else ""
                    output.append(f"  • {name}: {description}{confirm_badge}")
                else:
                    output.append(f"  • {op}")
        else:
            output.append(f"\n🛠️  Operations: {operations}")

    def _format_stats_output(self, data: dict[str, Any], output: list[str]) -> None:
        """Format system stats output."""
        if "users" in data:
            stats = data["users"]
            output.append(
                f"\n👥 Users: {stats.get('total', 0)} total, {stats.get('active', 0)} active, {stats.get('admin', 0)} admin"
            )
        if "content" in data:
            stats = data["content"]
            output.append(f"📝 Content: {stats.get('restaurants', 0)} restaurants, {stats.get('expenses', 0)} expenses")

    def _format_validation_results_output(self, data: dict[str, Any], output: list[str]) -> None:
        """Format restaurant validation results output."""
        validation_results = data.get("validation_results", [])
        summary = data.get("summary", {})

        output.append(f"\n🍽️  Restaurant Validation Results ({len(validation_results)} restaurants):")

        # Show individual results
        self._format_individual_validation_results(validation_results, output)

        # Show summary
        self._format_validation_summary(summary, output)

    def _format_individual_validation_results(
        self, validation_results: list[dict[str, Any]], output: list[str]
    ) -> None:
        """Format individual validation results."""
        for result in validation_results[:5]:  # Show first 5
            restaurant_name = result.get("name", "Unknown")
            restaurant_id = result.get("id", "N/A")
            username = result.get("username", "N/A")
            google_place_id = result.get("google_place_id", "N/A")
            full_address = result.get("full_address", "N/A")
            status = result.get("status", "unknown")

            status_icon = self._get_status_icon(status)
            output.append(f"\n🍽️  {restaurant_name} (ID: {restaurant_id})")
            output.append(f"   User: {username}")
            output.append(f"   Google Place ID: {google_place_id}")
            output.append(f"   Full Address: {full_address}")
            output.append(f"   {status_icon} {status.title()}")

            # Show mismatches if any
            mismatches = result.get("mismatches", [])
            if mismatches:
                output.append("   ⚠️  Mismatches found:")
                for mismatch in mismatches:
                    output.append(f"      - {mismatch}")

            # Show address comparison if available
            address_comparison = result.get("address_comparison", {})
            if address_comparison:
                self._format_address_comparison(address_comparison, output)

            # Show Google data if available
            google_data = result.get("google_data", {})
            if google_data:
                self._format_google_data(google_data, output)

            # Show if fixed
            if result.get("fixed"):
                output.append("      🔧 Fixed")
            elif result.get("would_fix") and result.get("dry_run"):
                output.append("      🔧 Would fix (dry run)")

        if len(validation_results) > 5:
            output.append(f"  ... and {len(validation_results) - 5} more restaurants")

    def _format_address_comparison(self, address_comparison: dict[str, Any], output: list[str]) -> None:
        """Format address comparison output."""
        stored = address_comparison.get("stored_address", {})
        google = address_comparison.get("google_address", {})

        output.append("   📍 Address Comparison:")
        output.append("      Stored Address:")
        output.append(f"         Street: {stored.get('street', 'N/A')}")
        if stored.get("unit"):
            output.append(f"         Unit: {stored['unit']}")
        output.append(f"         City: {stored.get('city', 'N/A')}")
        output.append(f"         State: {stored.get('state', 'N/A')}")
        output.append(f"         ZIP: {stored.get('zip', 'N/A')}")
        output.append(f"         Country: {stored.get('country', 'N/A')}")

        output.append("      Google Address:")
        output.append(f"         Street: {google.get('street', 'N/A')}")
        if google.get("unit"):
            output.append(f"         Unit: {google['unit']}")
        output.append(f"         City: {google.get('city', 'N/A')}")
        output.append(f"         State: {google.get('state', 'N/A')}")
        output.append(f"         ZIP: {google.get('zip', 'N/A')}")
        output.append(f"         Country: {google.get('country', 'N/A')}")

    def _format_google_data(self, google_data: dict[str, Any], output: list[str]) -> None:
        """Format Google Places data output."""
        self._format_google_basic_info(google_data, output)
        self._format_google_service_info(google_data, output)

    def _format_google_basic_info(self, google_data: dict[str, Any], output: list[str]) -> None:
        """Format basic Google Places information."""
        if google_data.get("google_address"):
            output.append(f"   🗺️  Google Address: {google_data['google_address']}")

        if google_data.get("google_status"):
            output.append(f"   📊 Status: {google_data['google_status']}")
        if google_data.get("google_rating"):
            output.append(f"   ⭐ Google Rating: {google_data['google_rating']}/5.0")
        if google_data.get("google_phone"):
            output.append(f"   📞 Phone: {google_data['google_phone']}")
        if google_data.get("google_website"):
            output.append(f"   🌐 Website: {google_data['google_website']}")
        if google_data.get("google_price_level"):
            price_level = google_data["google_price_level"]
            price_symbols = "💰" * price_level if isinstance(price_level, int) else price_level
            output.append(f"   💲 Price Level: {price_symbols}")
        if google_data.get("types"):
            types_data = google_data["types"]
            if isinstance(types_data, list):
                types_str = ", ".join(types_data[:3])  # Show first 3 types
            else:
                types_str = str(types_data)
            output.append(f"   🏷️  Types: {types_str}")

    def _format_google_service_info(self, google_data: dict[str, Any], output: list[str]) -> None:
        """Format Google service level information."""
        if google_data.get("google_service_level"):
            service_level, confidence = google_data["google_service_level"]
            if service_level != "unknown":
                output.append(f"   🍽️  Service Level: {service_level.title()} (confidence: {confidence:.2f})")

    def _get_status_icon(self, status: str) -> str:
        """Get status icon for validation result."""
        if status == "valid":
            return "✅"
        elif status == "invalid":
            return "❌"
        else:
            return "⚠️"

    def _format_validation_summary(self, summary: dict[str, Any], output: list[str]) -> None:
        """Format validation summary."""
        if not summary:
            return

        output.append("\n📊 Summary:")

        # Restaurant counts
        total_restaurants = summary.get("total_restaurants", 0)
        missing_google_id = summary.get("missing_google_id", 0)
        with_google_id = summary.get("with_google_id", 0)

        output.append(f"   🍽️  Total restaurants: {total_restaurants}")
        output.append(f"   🌐 With Google Place ID: {with_google_id}")
        output.append(f"   📍 Missing Google Place ID: {missing_google_id}")

        # Validation results
        output.append(f"   ✅ Valid: {summary.get('valid_count', 0)}")
        output.append(f"   ❌ Invalid: {summary.get('invalid_count', 0)}")
        output.append(f"   ⚠️  Cannot validate: {summary.get('error_count', 0)}")

        # Mismatch count
        mismatch_count = summary.get("mismatch_count", 0)
        if mismatch_count > 0:
            output.append(f"   🔄 With mismatches: {mismatch_count}")

        # Fixed count
        if summary.get("fixed_count", 0) > 0:
            if summary.get("dry_run"):
                output.append(f"   🔧 Would fix: {summary.get('fixed_count', 0)} restaurants")
            else:
                output.append(f"   🔧 Fixed: {summary.get('fixed_count', 0)} restaurants")


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        description="Remote administration for Lambda-deployed Meal Expense Tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--function-name",
        "-f",
        default="meal-expense-tracker-dev",
        help="Lambda function name (default: meal-expense-tracker-dev)",
    )
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region (default: us-east-1)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output with full data")
    parser.add_argument("--confirm", "-c", action="store_true", help="Confirm operations that require confirmation")

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List operations
    subparsers.add_parser("list-operations", help="List all available admin operations")

    # List users
    list_users_parser = subparsers.add_parser("list-users", help="List system users")
    list_users_parser.add_argument("--admin-only", action="store_true", help="Show only admin users")
    list_users_parser.add_argument("--limit", type=int, default=100, help="Limit number of results")

    # Create user
    create_user_parser = subparsers.add_parser("create-user", help="Create a new user")
    create_user_parser.add_argument("--username", required=True, help="Username for new user")
    create_user_parser.add_argument("--email", required=True, help="Email for new user")
    create_user_parser.add_argument("--password", required=True, help="Password for new user")
    create_user_parser.add_argument("--admin", action="store_true", help="Make user an admin")
    create_user_parser.add_argument("--inactive", action="store_true", help="Create user as inactive")

    # Update user
    update_user_parser = subparsers.add_parser("update-user", help="Update an existing user")
    update_user_parser.add_argument("--user-id", type=int, help="User ID to update")
    update_user_parser.add_argument("--email", help="Find user by email")
    update_user_parser.add_argument("--username", help="Find user by username")
    update_user_parser.add_argument("--new-email", help="New email address")
    update_user_parser.add_argument("--new-username", help="New username")
    update_user_parser.add_argument("--password", help="New password")
    update_user_parser.add_argument("--admin", action="store_true", help="Make user admin")
    update_user_parser.add_argument("--no-admin", action="store_true", help="Remove admin privileges")
    update_user_parser.add_argument("--active", action="store_true", help="Activate user")
    update_user_parser.add_argument("--inactive", action="store_true", help="Deactivate user")

    # System stats
    subparsers.add_parser("system-stats", help="Get system statistics")

    # Recent activity
    activity_parser = subparsers.add_parser("recent-activity", help="Get recent system activity")
    activity_parser.add_argument("--days", type=int, default=7, help="Number of days to look back")
    activity_parser.add_argument("--limit", type=int, default=50, help="Limit number of results")

    # Initialize database
    init_db_parser = subparsers.add_parser("init-db", help="Initialize database schema and create default data")
    init_db_parser.add_argument("--force", action="store_true", help="Force recreation of existing database")
    init_db_parser.add_argument(
        "--sample-data", action="store_true", help="Create sample data (admin user and default categories)"
    )

    # Database maintenance
    db_parser = subparsers.add_parser("db-maintenance", help="Perform database maintenance")
    db_parser.add_argument(
        "--operation", choices=["analyze", "vacuum"], default="analyze", help="Maintenance operation to perform"
    )

    # Validate restaurants
    validate_restaurants_parser = subparsers.add_parser(
        "validate-restaurants", help="Validate restaurant information using Google Places API"
    )
    validate_restaurants_parser.add_argument("--user-id", type=int, help="Specific user ID to validate restaurants for")
    validate_restaurants_parser.add_argument(
        "--username", type=str, help="Specific username to validate restaurants for"
    )
    validate_restaurants_parser.add_argument(
        "--all-users", action="store_true", help="Validate restaurants for all users"
    )
    validate_restaurants_parser.add_argument("--restaurant-id", type=int, help="Validate a specific restaurant by ID")
    validate_restaurants_parser.add_argument(
        "--fix-mismatches", action="store_true", help="Automatically fix name/address mismatches from Google"
    )
    validate_restaurants_parser.add_argument(
        "--update-service-levels",
        action="store_true",
        help="Update service levels for restaurants without Google Place IDs",
    )
    validate_restaurants_parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be fixed without making changes"
    )
    validate_restaurants_parser.add_argument(
        "--find-place-id", action="store_true", help="Find Google Place ID matches for restaurants without one"
    )
    validate_restaurants_parser.add_argument(
        "--closest", action="store_true", help="Automatically select closest match when multiple options are found"
    )

    # Run migrations
    migrate_parser = subparsers.add_parser("run-migrations", help="Run database migrations safely")
    migrate_parser.add_argument(
        "--dry-run", action="store_true", help="Show what migrations would be applied without running them"
    )
    migrate_parser.add_argument("--target-revision", type=str, help="Specific migration revision to run to (optional)")
    migrate_parser.add_argument(
        "--fix-history",
        action="store_true",
        help="Fix migration history for existing tables (use when you get 'already exists' errors)",
    )

    # Stamp alembic version
    stamp_parser = subparsers.add_parser("stamp", help="Stamp the database to a specific Alembic revision")
    stamp_parser.add_argument(
        "--revision",
        type=str,
        required=True,
        help="Target revision to stamp to (e.g., 42985d8e0812)",
    )

    return parser


def _handle_list_operations(client: RemoteAdminClient) -> dict[str, Any]:
    """Handle list-operations command."""
    return client.list_operations()


def _handle_list_users(client: RemoteAdminClient, args: argparse.Namespace) -> dict[str, Any]:
    """Handle list-users command."""
    params = {"admin_only": args.admin_only, "limit": args.limit}
    return client.invoke_operation("list_users", params)


def _handle_create_user(client: RemoteAdminClient, args: argparse.Namespace) -> dict[str, Any]:
    """Handle create-user command."""
    params = {
        "username": args.username,
        "email": args.email,
        "password": args.password,
        "admin": args.admin,
        "active": not args.inactive,
    }
    return client.invoke_operation("create_user", params, args.confirm)


def _add_identity_params(params: dict[str, Any], args: argparse.Namespace) -> None:
    """Add identity parameters to params dictionary."""
    if args.user_id:
        params["user_id"] = args.user_id
    if args.email:
        params["email"] = args.email
    if args.username:
        params["username"] = args.username


def _add_update_params(params: dict[str, Any], args: argparse.Namespace) -> None:
    """Add update parameters to params dictionary."""
    if args.new_email:
        params["new_email"] = args.new_email
    if args.new_username:
        params["new_username"] = args.new_username
    if args.password:
        params["password"] = args.password


def _add_boolean_flags(params: dict[str, Any], args: argparse.Namespace) -> None:
    """Add boolean flag parameters to params dictionary."""
    if args.admin:
        params["admin"] = True
    if args.no_admin:
        params["admin"] = False
    if args.active:
        params["active"] = True
    if args.inactive:
        params["active"] = False


def _build_update_user_params(args: argparse.Namespace) -> dict[str, Any]:
    """Build parameters for update-user command."""
    params: dict[str, Any] = {}
    _add_identity_params(params, args)
    _add_update_params(params, args)
    _add_boolean_flags(params, args)
    return params


def _handle_update_user(client: RemoteAdminClient, args: argparse.Namespace) -> dict[str, Any]:
    """Handle update-user command."""
    params = _build_update_user_params(args)
    return client.invoke_operation("update_user", params, args.confirm)


def _handle_system_stats(client: RemoteAdminClient) -> dict[str, Any]:
    """Handle system-stats command."""
    return client.invoke_operation("system_stats", {})


def _handle_recent_activity(client: RemoteAdminClient, args: argparse.Namespace) -> dict[str, Any]:
    """Handle recent-activity command."""
    params = {"days": args.days, "limit": args.limit}
    return client.invoke_operation("recent_activity", params)


def _handle_init_db(client: RemoteAdminClient, args: argparse.Namespace) -> dict[str, Any]:
    """Handle init-db command."""
    params = {
        "force": args.force,
        "sample_data": args.sample_data,
    }
    return client.invoke_operation("init_db", params, args.confirm)


def _handle_db_maintenance(client: RemoteAdminClient, args: argparse.Namespace) -> dict[str, Any]:
    """Handle db-maintenance command."""
    params = {"operation": args.operation}
    return client.invoke_operation("db_maintenance", params, args.confirm)


def _handle_validate_restaurants(client: RemoteAdminClient, args: argparse.Namespace) -> dict[str, Any]:
    """Handle validate-restaurants command."""
    params = {}

    # Add identity parameters
    if args.user_id:
        params["user_id"] = args.user_id
    if args.username:
        params["username"] = args.username
    if args.all_users:
        params["all_users"] = args.all_users
    if args.restaurant_id:
        params["restaurant_id"] = args.restaurant_id

    # Add action parameters
    if args.fix_mismatches:
        params["fix_mismatches"] = args.fix_mismatches
    if args.update_service_levels:
        params["update_service_levels"] = args.update_service_levels
    if args.dry_run:
        params["dry_run"] = args.dry_run
    if args.find_place_id:
        params["find_place_id"] = args.find_place_id
    if args.closest:
        params["closest"] = args.closest

    return client.invoke_operation("validate_restaurants", params, args.confirm)


def _handle_run_migrations(client: RemoteAdminClient, args: argparse.Namespace) -> dict[str, Any]:
    """Handle run-migrations command."""
    params = {
        "dry_run": args.dry_run,
        "fix_history": args.fix_history,
    }
    if args.target_revision:
        params["target_revision"] = args.target_revision
    return client.invoke_operation("run_migrations", params, args.confirm)


def _handle_stamp(client: RemoteAdminClient, args: argparse.Namespace) -> dict[str, Any]:
    """Handle stamp command."""
    params = {"revision": args.revision}
    return client.invoke_operation("stamp", params, args.confirm)


def _execute_command(client: RemoteAdminClient, args: argparse.Namespace) -> dict[str, Any] | None:
    """Execute the specified command and return the result."""
    command_handlers = {
        "list-operations": lambda: _handle_list_operations(client),
        "list-users": lambda: _handle_list_users(client, args),
        "create-user": lambda: _handle_create_user(client, args),
        "update-user": lambda: _handle_update_user(client, args),
        "system-stats": lambda: _handle_system_stats(client),
        "recent-activity": lambda: _handle_recent_activity(client, args),
        "init-db": lambda: _handle_init_db(client, args),
        "db-maintenance": lambda: _handle_db_maintenance(client, args),
        "validate-restaurants": lambda: _handle_validate_restaurants(client, args),
        "run-migrations": lambda: _handle_run_migrations(client, args),
        "stamp": lambda: _handle_stamp(client, args),
    }

    handler = command_handlers.get(args.command)
    return handler() if handler else None


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize client
    client = RemoteAdminClient(args.function_name, args.region)

    # Execute command
    result = _execute_command(client, args)

    # Display result
    if result:
        if result.get("requires_confirmation") and not args.confirm:
            print(f"⚠️  {result.get('message', 'Operation requires confirmation')}")
            print("Add --confirm to proceed with this operation.")
            return 1

        print(client.format_response(result, args.verbose))
        return 0 if result.get("success") else 1
    else:
        print("❌ No result returned")
        return 1


if __name__ == "__main__":
    sys.exit(main())
