#!/usr/bin/env python3
"""Remote administration client for Lambda-deployed Meal Expense Tracker.

Same as: flask remote user list | flask remote db run-migrations | etc.

Use either:
  - flask remote user list          (requires Flask app)
  - python scripts/remote_admin.py user list   (standalone, no Flask needed)

Both proxy to the deployed Lambda. This script is for CI/CD or when Flask isn't loaded.

Usage:
    python scripts/remote_admin.py [OPTIONS] COMMAND [ARGS]

    # Same structure as: flask user list
    python scripts/remote_admin.py user list
    python scripts/remote_admin.py user list --admin-only

    # Same structure as: flask user create
    python scripts/remote_admin.py user create --username newuser --email user@example.com --password secretpass123

    # Same structure as: flask user update
    python scripts/remote_admin.py user update 1 --admin
    python scripts/remote_admin.py --confirm user update admin --username newname

    # Same structure as: flask category reinit
    python scripts/remote_admin.py category reinit --all-users --dry-run

    # Same structure as: flask restaurant validate
    python scripts/remote_admin.py restaurant validate --user-id 1 --dry-run

    # Database operations (flask db equivalent)
    python scripts/remote_admin.py db run-migrations --dry-run
    python scripts/remote_admin.py --confirm db run-migrations
    python scripts/remote_admin.py --confirm db init --sample-data

    # List available Lambda operations
    python scripts/remote_admin.py list-operations
"""

from __future__ import annotations

import json
import sys
from typing import Any, Callable, cast

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
import click

# --- Lambda Proxy Client ---


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
            config = Config(connect_timeout=10, read_timeout=300, retries={"max_attempts": 5})
            self.lambda_client = boto3.client("lambda", region_name=self.region, config=config)
            self.lambda_client.get_account_settings()
        except NoCredentialsError:
            click.echo("❌ Error: AWS credentials not configured.", err=True)
            click.echo("Please configure using: aws configure", err=True)
            sys.exit(1)
        except Exception as e:
            click.echo(f"❌ Error initializing AWS client: {e}", err=True)
            sys.exit(1)

    def invoke_operation(
        self, operation_name: str, parameters: dict[str, Any], confirm: bool = False
    ) -> dict[str, Any]:
        """Invoke an admin operation on the Lambda function."""
        payload = {"admin_operation": operation_name, "parameters": parameters, "confirm": confirm}

        try:
            response = self.lambda_client.invoke(
                FunctionName=self.function_name,
                InvocationType="RequestResponse",
                Payload=json.dumps(payload),
            )

            response_payload = json.loads(response["Payload"].read())

            if response.get("FunctionError"):
                return {"success": False, "message": f"Lambda function error: {response_payload}"}

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
            if error_code == "AccessDenied":
                return {
                    "success": False,
                    "message": "Access denied. Check AWS permissions for Lambda:InvokeFunction",
                }
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
        """Format users list output (matches flask user list table format when objects)."""
        has_objects = any("expenses" in u for u in users)
        if has_objects:
            headers = ["ID", "Email", "Username", "Admin", "Active", "Expenses", "Restaurants", "Categories"]
            rows = []
            for user in users:
                row = [
                    str(user.get("id", "N/A")),
                    user.get("email", "N/A"),
                    user.get("username") or "-",
                    "✓" if user.get("is_admin") else "",
                    "✓" if user.get("is_active") else "✗",
                    str(user.get("expenses", 0)),
                    str(user.get("restaurants", 0)),
                    str(user.get("categories", 0)),
                ]
                rows.append(row)
            if rows:
                col_widths = [max(len(str(r[i])) for r in [headers] + rows) for i in range(len(headers))]
                output.append("\n " + " | ".join(f"{h.ljust(w)}" for h, w in zip(headers, col_widths)))
                output.append("-" * (sum(col_widths) + 3 * (len(headers) - 1) + 2))
                for row in rows:
                    output.append(" " + " | ".join(str(c).ljust(w) for c, w in zip(row, col_widths)))
        else:
            output.append(f"\n👥 Users ({len(users)}):")
            for user in users[:10]:
                admin_badge = " 👑" if user.get("is_admin") else ""
                active_badge = " ✅" if user.get("is_active") else " ❌"
                output.append(
                    f"  • {user.get('username', 'N/A')} ({user.get('email', 'N/A')}){admin_badge}{active_badge}"
                )
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
                f"\n👥 Users: {stats.get('total', 0)} total, {stats.get('active', 0)} active, "
                f"{stats.get('admin', 0)} admin"
            )
        if "content" in data:
            stats = data["content"]
            output.append(
                f"📝 Content: {stats.get('restaurants', 0)} restaurants, "
                f"{stats.get('expenses', 0)} expenses"
            )

    def _format_validation_results_output(self, data: dict[str, Any], output: list[str]) -> None:
        """Format restaurant validation results output."""
        validation_results = data.get("validation_results", [])
        summary = data.get("summary", {})

        output.append(f"\n🍽️  Restaurant Validation Results ({len(validation_results)} restaurants):")

        for result in validation_results[:5]:
            restaurant_name = result.get("name", "Unknown")
            restaurant_id = result.get("id", "N/A")
            username = result.get("username", "N/A")
            status = result.get("status", "unknown")
            status_icon = "✅" if status == "valid" else ("❌" if status == "invalid" else "⚠️")
            output.append(f"\n🍽️  {restaurant_name} (ID: {restaurant_id})")
            output.append(f"   User: {username}")
            output.append(f"   {status_icon} {status.title()}")

            mismatches = result.get("mismatches", [])
            if mismatches:
                output.append("   ⚠️  Mismatches found:")
                for mismatch in mismatches:
                    output.append(f"      - {mismatch}")

        if len(validation_results) > 5:
            output.append(f"  ... and {len(validation_results) - 5} more restaurants")

        if summary:
            output.append("\n📊 Summary:")
            output.append(f"   Total: {summary.get('total_restaurants', 0)}")
            output.append(f"   Valid: {summary.get('valid_count', 0)}")
            output.append(f"   Invalid: {summary.get('invalid_count', 0)}")


# --- CLI Factory: Build commands that proxy to Lambda ---


def _make_proxy_callback(
    operation: str,
    params_fn: Callable[..., dict[str, Any]],
    requires_confirm: bool = False,
) -> Callable[..., None]:
    """Create a Click callback that proxies to Lambda."""

    def callback(**kwargs: Any) -> None:
        ctx = click.get_current_context()
        # Traverse to root context where obj is set
        root_ctx = ctx
        while root_ctx.parent:
            root_ctx = root_ctx.parent
        obj = root_ctx.obj or {}
        if not isinstance(obj, dict):
            client = None
        else:
            # Lazy-init client only when invoking (not for --help)
            client = obj.get("client")
            if client is None:
                client = RemoteAdminClient(
                    obj.get("function_name", "meal-expense-tracker-dev"),
                    obj.get("region", "us-east-1"),
                )
                obj["client"] = client
        if not client:
            click.echo("❌ Error: No client in context", err=True)
            ctx.exit(1)
        confirm = obj.get("confirm", False)
        verbose = obj.get("verbose", False)

        params = params_fn(**kwargs)
        result = client.invoke_operation(operation, params, confirm)

        if result.get("requires_confirmation") and not confirm:
            click.echo(f"⚠️  {result.get('message', 'Operation requires confirmation')}")
            click.echo("Add --confirm to proceed with this operation.")
            ctx.exit(1)

        click.echo(client.format_response(result, verbose))
        ctx.exit(0 if result.get("success") else 1)

    return callback


def _parse_user_identifier(identifier: str) -> dict[str, Any]:
    """Parse user identifier to Lambda params (user_id, email, or username)."""
    if identifier.isdigit():
        return {"user_id": int(identifier, 10)}
    if "@" in identifier:
        return {"email": identifier}
    return {"username": identifier}


# --- Main CLI ---


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--function-name",
    "-f",
    default="meal-expense-tracker-dev",
    help="Lambda function name",
)
@click.option("--region", "-r", default="us-east-1", help="AWS region")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output with full data")
@click.option("--confirm", "-c", is_flag=True, help="Confirm operations that require confirmation")
@click.pass_context
def cli(ctx: click.Context, function_name: str, region: str, verbose: bool, confirm: bool) -> None:
    """Remote administration for Lambda-deployed Meal Expense Tracker.

    Same CLI structure as Flask: user, category, restaurant, db.
    Commands are proxied to the deployed Lambda function.
    """
    ctx.ensure_object(dict)
    ctx.obj["function_name"] = function_name
    ctx.obj["region"] = region
    ctx.obj["confirm"] = confirm
    ctx.obj["verbose"] = verbose


# --- list-operations (standalone, like flask --help) ---


@cli.command("list-operations")
@click.pass_context
def list_operations_cmd(ctx: click.Context) -> None:
    """List all available admin operations on the Lambda."""
    obj = ctx.obj or {}
    client = obj.get("client")
    if client is None:
        client = RemoteAdminClient(
            obj.get("function_name", "meal-expense-tracker-dev"),
            obj.get("region", "us-east-1"),
        )
    result = client.list_operations()
    click.echo(client.format_response(result, ctx.obj.get("verbose", False)))
    ctx.exit(0 if result.get("success") else 1)


# --- user group (matches: flask user) ---


@cli.group("user")
@click.pass_context
def user_group(ctx: click.Context) -> None:
    """User management commands (same as: flask user)."""


@user_group.command("list")
@click.option("--admin-only", is_flag=True, help="Show only admin users")
@click.option(
    "--objects",
    is_flag=True,
    help="Show count of related objects (expenses, restaurants, categories)",
)
@click.option("--limit", type=int, default=100, help="Limit number of results")
@click.pass_context
def user_list(ctx: click.Context, admin_only: bool, objects: bool, limit: int) -> None:
    """List all users (same as: flask user list)."""
    callback = _make_proxy_callback(
        "list_users",
        lambda **kw: {
            "admin_only": kw["admin_only"],
            "objects": kw["objects"],
            "limit": kw["limit"],
        },
    )
    callback(admin_only=admin_only, objects=objects, limit=limit)


@user_group.command("create")
@click.option("--username", required=True, help="Username for the new user")
@click.option("--email", required=True, help="Email address for the new user")
@click.option("--password", required=True, help="Password for the new user")
@click.option("--admin", is_flag=True, help="Make the user an admin")
@click.option("--active/--inactive", default=True, help="Set account active status")
@click.pass_context
def user_create(
    ctx: click.Context,
    username: str,
    email: str,
    password: str,
    admin: bool,
    active: bool,
) -> None:
    """Create a new user (same as: flask user create)."""
    callback = _make_proxy_callback(
        "create_user",
        lambda **kw: {
            "username": kw["username"],
            "email": kw["email"],
            "password": kw["password"],
            "admin": kw["admin"],
            "active": kw["active"],
        },
        requires_confirm=True,
    )
    callback(username=username, email=email, password=password, admin=admin, active=active)


@user_group.command("update")
@click.argument("user_identifier")
@click.option("--username", help="New username (same as: flask user update --username)")
@click.option("--email", help="New email address (same as: flask user update --email)")
@click.option("--password", help="New password")
@click.option("--admin/--no-admin", default=None, help="Set or remove admin privileges")
@click.option("--active/--inactive", default=None, help="Activate or deactivate the account")
@click.pass_context
def user_update(
    ctx: click.Context,
    user_identifier: str,
    username: str | None,
    email: str | None,
    password: str | None,
    admin: bool | None,
    active: bool | None,
) -> None:
    """Update an existing user (same as: flask user update)."""
    params = {**_parse_user_identifier(user_identifier)}
    if username:
        params["new_username"] = username
    if email:
        params["new_email"] = email
    if password:
        params["password"] = password
    if admin is not None:
        params["admin"] = admin
    if active is not None:
        params["active"] = active

    callback = _make_proxy_callback("update_user", lambda **kw: params, requires_confirm=True)
    callback()


@user_group.command("delete")
@click.argument("user_identifier")
@click.option("--force", is_flag=True, help="Skip confirmation prompts")
@click.option("--cascade/--no-cascade", default=True, help="Delete related data")
@click.pass_context
def user_delete(
    ctx: click.Context,
    user_identifier: str,
    force: bool,
    cascade: bool,
) -> None:
    """Delete a user (same as: flask user delete)."""
    params = {**_parse_user_identifier(user_identifier), "force": force, "cascade": cascade}
    callback = _make_proxy_callback("delete_user", lambda **kw: params, requires_confirm=True)
    callback()


@user_group.command("reset-password")
@click.option("--email", required=True, help="Email of the user to reset password for")
@click.option("--password", required=True, help="New password")
@click.pass_context
def user_reset_password(ctx: click.Context, email: str, password: str) -> None:
    """Reset password for an admin user (same as: flask user reset-password)."""
    callback = _make_proxy_callback(
        "reset_admin_password",
        lambda **kw: {"email": kw["email"], "password": kw["password"]},
        requires_confirm=True,
    )
    callback(email=email, password=password)


# --- category group (matches: flask category) ---


@cli.group("category")
@click.pass_context
def category_group(ctx: click.Context) -> None:
    """Category management commands (same as: flask category)."""


@category_group.command("reinit")
@click.option("--user-id", type=int, help="Specific user ID")
@click.option("--username", type=str, help="Specific username")
@click.option("--all-users", is_flag=True, help="Reinitialize for all users")
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
@click.option("--force", is_flag=True, help="Remove existing categories and recreate")
@click.pass_context
def category_reinit(
    ctx: click.Context,
    user_id: int | None,
    username: str | None,
    all_users: bool,
    dry_run: bool,
    force: bool,
) -> None:
    """Reinitialize expense categories (same as: flask category reinit)."""
    params = {"dry_run": dry_run, "force": force}
    if user_id:
        params["user_id"] = user_id
    if username:
        params["username"] = username
    if all_users:
        params["all_users"] = all_users

    callback = _make_proxy_callback("reinit_categories", lambda **kw: params)
    callback()


@category_group.command("list")
@click.option("--user-id", type=int, help="Specific user ID")
@click.option("--username", type=str, help="Specific username")
@click.option("--all-users", is_flag=True, help="List for all users")
@click.pass_context
def category_list(
    ctx: click.Context,
    user_id: int | None,
    username: str | None,
    all_users: bool,
) -> None:
    """List expense categories (same as: flask category list)."""
    params: dict[str, Any] = {}
    if user_id:
        params["user_id"] = user_id
    if username:
        params["username"] = username
    if all_users:
        params["all_users"] = all_users

    callback = _make_proxy_callback("list_categories", lambda **kw: params)
    callback()


# --- restaurant group (matches: flask restaurant) ---


@cli.group("restaurant")
@click.pass_context
def restaurant_group(ctx: click.Context) -> None:
    """Restaurant management commands (same as: flask restaurant)."""


@restaurant_group.command("list")
@click.option("--user-id", type=int, help="Specific user ID")
@click.option("--username", type=str, help="Specific username")
@click.option("--all-users", is_flag=True, help="List for all users")
@click.option("--detailed", is_flag=True, help="Show detailed information")
@click.option("--with-google-id", is_flag=True, help="Only show restaurants with Google Place IDs")
@click.pass_context
def restaurant_list(
    ctx: click.Context,
    user_id: int | None,
    username: str | None,
    all_users: bool,
    detailed: bool,
    with_google_id: bool,
) -> None:
    """List restaurants (same as: flask restaurant list)."""
    params: dict[str, Any] = {"detailed": detailed, "with_google_id": with_google_id}
    if user_id:
        params["user_id"] = user_id
    if username:
        params["username"] = username
    if all_users:
        params["all_users"] = all_users

    callback = _make_proxy_callback("list_restaurants", lambda **kw: params)
    callback()


@restaurant_group.command("validate")
@click.option("--user-id", type=int, help="Specific user ID to validate for")
@click.option("--username", type=str, help="Specific username to validate for")
@click.option("--all-users", is_flag=True, help="Validate for all users")
@click.option("--restaurant-id", type=int, help="Validate a specific restaurant by ID")
@click.option("--fix-mismatches", "-f", is_flag=True, help="Fix mismatches from Google data")
@click.option("--update-service-levels", is_flag=True, help="Update service levels")
@click.option("--find-place-id", is_flag=True, help="Find Google Place ID for restaurants without one")
@click.option("--closest", is_flag=True, help="Auto-select closest match when multiple found")
@click.option("--dry-run", is_flag=True, help="Show what would be fixed without making changes")
@click.pass_context
def restaurant_validate(
    ctx: click.Context,
    user_id: int | None,
    username: str | None,
    all_users: bool,
    restaurant_id: int | None,
    fix_mismatches: bool,
    update_service_levels: bool,
    find_place_id: bool,
    closest: bool,
    dry_run: bool,
) -> None:
    """Validate restaurant information (same as: flask restaurant validate)."""
    params: dict[str, Any] = {
        "fix_mismatches": fix_mismatches,
        "update_service_levels": update_service_levels,
        "find_place_id": find_place_id,
        "closest": closest,
        "dry_run": dry_run,
    }
    if user_id:
        params["user_id"] = user_id
    if username:
        params["username"] = username
    if all_users:
        params["all_users"] = all_users
    if restaurant_id:
        params["restaurant_id"] = restaurant_id

    callback = _make_proxy_callback("validate_restaurants", lambda **kw: params)
    callback()


# --- db group (matches: flask db for migrations, plus init) ---


@cli.group("db")
@click.pass_context
def db_group(ctx: click.Context) -> None:
    """Database operations (init, migrations, stamp, stats)."""


@db_group.command("init")
@click.option("--force", is_flag=True, help="Force recreation of existing database")
@click.option("--sample-data", is_flag=True, help="Create sample data")
@click.pass_context
def db_init(ctx: click.Context, force: bool, sample_data: bool) -> None:
    """Initialize database schema and create default data."""
    params = {"force": force, "sample_data": sample_data}
    callback = _make_proxy_callback("init_db", lambda **kw: params, requires_confirm=True)
    callback()


@db_group.command("run-migrations")
@click.option("--dry-run", is_flag=True, help="Show what migrations would be applied")
@click.option("--target-revision", type=str, help="Specific migration revision to run to")
@click.option("--fix-history", is_flag=True, help="Fix migration history for existing tables")
@click.pass_context
def db_run_migrations(
    ctx: click.Context,
    dry_run: bool,
    target_revision: str | None,
    fix_history: bool,
) -> None:
    """Run database migrations (same behavior as migrate_db)."""
    params = {"dry_run": dry_run, "fix_history": fix_history}
    if target_revision:
        params["target_revision"] = target_revision

    callback = _make_proxy_callback("run_migrations", lambda **kw: params, requires_confirm=True)
    callback()


@db_group.command("stamp")
@click.option("--revision", required=True, help="Target revision to stamp to")
@click.pass_context
def db_stamp(ctx: click.Context, revision: str) -> None:
    """Stamp the database to a specific Alembic revision."""
    params = {"revision": revision}
    callback = _make_proxy_callback("stamp", lambda **kw: params, requires_confirm=True)
    callback()


@db_group.command("system-stats")
@click.pass_context
def db_system_stats(ctx: click.Context) -> None:
    """Get system statistics."""
    callback = _make_proxy_callback("system_stats", lambda **kw: {})
    callback()


@db_group.command("recent-activity")
@click.option("--days", type=int, default=7, help="Number of days to look back")
@click.option("--limit", type=int, default=50, help="Limit number of results")
@click.pass_context
def db_recent_activity(ctx: click.Context, days: int, limit: int) -> None:
    """Get recent system activity."""
    callback = _make_proxy_callback(
        "recent_activity",
        lambda **kw: {"days": kw["days"], "limit": kw["limit"]},
    )
    callback(days=days, limit=limit)


@db_group.command("maintenance")
@click.option("--operation", type=click.Choice(["analyze", "vacuum"]), default="analyze")
@click.pass_context
def db_maintenance(ctx: click.Context, operation: str) -> None:
    """Perform database maintenance."""
    params = {"operation": operation}
    callback = _make_proxy_callback("db_maintenance", lambda **kw: params, requires_confirm=True)
    callback()


# --- Entry point ---


def main() -> int:
    """Main entry point."""
    try:
        cli()
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
