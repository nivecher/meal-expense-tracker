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

    # Initialize database (with confirmation)
    python scripts/remote_admin.py --confirm init-db --sample-data

    # Force recreate database with sample data
    python scripts/remote_admin.py --confirm init-db --force --sample-data
"""

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


class RemoteAdminClient:
    """Client for remote administration via Lambda."""

    def __init__(self, function_name: str, region: str = "us-east-1"):
        self.function_name = function_name
        self.region = region
        self.lambda_client = None
        self._initialize_client()

    def _initialize_client(self):
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
        self, operation_name: str, parameters: Dict[str, Any], confirm: bool = False
    ) -> Dict[str, Any]:
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
                return json.loads(response_payload["body"])

            return response_payload

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

    def list_operations(self) -> Dict[str, Any]:
        """List available admin operations."""
        return self.invoke_operation("list_operations", {})

    def format_response(self, response: Dict[str, Any], verbose: bool = False) -> str:
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

    def _format_data_output(self, data: Dict[str, Any], output: List[str]) -> None:
        """Format data output for specific data types."""
        if "users" in data and isinstance(data["users"], list):
            self._format_users_output(data["users"], output)
        elif "operations" in data:
            self._format_operations_output(data["operations"], output)
        elif any(key in data for key in ["users", "content", "system"]):
            self._format_stats_output(data, output)

    def _format_users_output(self, users: List[Dict[str, Any]], output: List[str]) -> None:
        """Format users list output."""
        output.append(f"\n👥 Users ({len(users)}):")
        for user in users[:10]:  # Show first 10
            admin_badge = " 👑" if user.get("is_admin") else ""
            active_badge = " ✅" if user.get("is_active") else " ❌"
            output.append(f"  • {user.get('username', 'N/A')} ({user.get('email', 'N/A')}){admin_badge}{active_badge}")
        if len(users) > 10:
            output.append(f"  ... and {len(users) - 10} more")

    def _format_operations_output(self, operations: Any, output: List[str]) -> None:
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

    def _format_stats_output(self, data: Dict[str, Any], output: List[str]) -> None:
        """Format system stats output."""
        if "users" in data:
            stats = data["users"]
            output.append(
                f"\n👥 Users: {stats.get('total', 0)} total, {stats.get('active', 0)} active, {stats.get('admin', 0)} admin"
            )
        if "content" in data:
            stats = data["content"]
            output.append(f"📝 Content: {stats.get('restaurants', 0)} restaurants, {stats.get('expenses', 0)} expenses")


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

    return parser


def _handle_list_operations(client: RemoteAdminClient) -> Dict[str, Any]:
    """Handle list-operations command."""
    return client.list_operations()


def _handle_list_users(client: RemoteAdminClient, args: argparse.Namespace) -> Dict[str, Any]:
    """Handle list-users command."""
    params = {"admin_only": args.admin_only, "limit": args.limit}
    return client.invoke_operation("list_users", params)


def _handle_create_user(client: RemoteAdminClient, args: argparse.Namespace) -> Dict[str, Any]:
    """Handle create-user command."""
    params = {
        "username": args.username,
        "email": args.email,
        "password": args.password,
        "admin": args.admin,
        "active": not args.inactive,
    }
    return client.invoke_operation("create_user", params, args.confirm)


def _add_identity_params(params: Dict[str, Any], args: argparse.Namespace) -> None:
    """Add identity parameters to params dictionary."""
    if args.user_id:
        params["user_id"] = args.user_id
    if args.email:
        params["email"] = args.email
    if args.username:
        params["username"] = args.username


def _add_update_params(params: Dict[str, Any], args: argparse.Namespace) -> None:
    """Add update parameters to params dictionary."""
    if args.new_email:
        params["new_email"] = args.new_email
    if args.new_username:
        params["new_username"] = args.new_username
    if args.password:
        params["password"] = args.password


def _add_boolean_flags(params: Dict[str, Any], args: argparse.Namespace) -> None:
    """Add boolean flag parameters to params dictionary."""
    if args.admin:
        params["admin"] = True
    if args.no_admin:
        params["admin"] = False
    if args.active:
        params["active"] = True
    if args.inactive:
        params["active"] = False


def _build_update_user_params(args: argparse.Namespace) -> Dict[str, Any]:
    """Build parameters for update-user command."""
    params = {}
    _add_identity_params(params, args)
    _add_update_params(params, args)
    _add_boolean_flags(params, args)
    return params


def _handle_update_user(client: RemoteAdminClient, args: argparse.Namespace) -> Dict[str, Any]:
    """Handle update-user command."""
    params = _build_update_user_params(args)
    return client.invoke_operation("update_user", params, args.confirm)


def _handle_system_stats(client: RemoteAdminClient) -> Dict[str, Any]:
    """Handle system-stats command."""
    return client.invoke_operation("system_stats", {})


def _handle_recent_activity(client: RemoteAdminClient, args: argparse.Namespace) -> Dict[str, Any]:
    """Handle recent-activity command."""
    params = {"days": args.days, "limit": args.limit}
    return client.invoke_operation("recent_activity", params)


def _handle_init_db(client: RemoteAdminClient, args: argparse.Namespace) -> Dict[str, Any]:
    """Handle init-db command."""
    params = {
        "force": args.force,
        "sample_data": args.sample_data,
    }
    return client.invoke_operation("init_db", params, args.confirm)


def _handle_db_maintenance(client: RemoteAdminClient, args: argparse.Namespace) -> Dict[str, Any]:
    """Handle db-maintenance command."""
    params = {"operation": args.operation}
    return client.invoke_operation("db_maintenance", params, args.confirm)


def _execute_command(client: RemoteAdminClient, args: argparse.Namespace) -> Optional[Dict[str, Any]]:
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
    }

    handler = command_handlers.get(args.command)
    return handler() if handler else None


def main():
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
