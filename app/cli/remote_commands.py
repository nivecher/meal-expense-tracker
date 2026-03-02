"""Flask remote command group: flask remote user list (proxies to Lambda)."""

from __future__ import annotations

from typing import Any, Callable, cast

import click

from app.cli.remote_proxy import (
    PARAMS_BUILDERS,
    _format_response,
    _invoke_lambda,
    invoke_remote_operation,
)


def _get_remote_config(ctx: click.Context) -> dict[str, Any]:
    """Get config from remote group's context (ctx.obj set by remote group)."""
    c = ctx
    while c.parent:
        if c.info_name == "remote" and c.obj:
            if isinstance(c.obj, dict):
                return cast(dict[str, Any], c.obj)
            return {}
        c = c.parent
    return {}


def _make_remote_cmd(
    operation: str,
    params_builder: Callable[[click.Context, dict[str, Any]], dict[str, Any]],
) -> Callable[..., None]:
    """Create a command that proxies to Lambda."""

    def callback(**kwargs: Any) -> None:
        ctx = click.get_current_context()
        config = _get_remote_config(ctx)
        params = params_builder(ctx, kwargs)
        result = _invoke_lambda(
            operation,
            params,
            config.get("function_name", "meal-expense-tracker-dev"),
            config.get("region", "us-east-1"),
            config.get("confirm", False),
        )
        if result.get("requires_confirmation") and not config.get("confirm"):
            click.echo(f"⚠️  {result.get('message', 'Operation requires confirmation')}")
            click.echo("Add --confirm to proceed.")
            ctx.exit(1)
        click.echo(_format_response(result, config.get("verbose", False)))
        ctx.exit(0 if result.get("success") else 1)

    return callback


def register_remote_commands(app: Any) -> None:
    """Register flask remote command group."""

    @click.group("remote", context_settings={"help_option_names": ["-h", "--help"]})
    @click.option("-f", "--function-name", default="meal-expense-tracker-dev", help="Lambda function name")
    @click.option("-r", "--region", default="us-east-1", help="AWS region")
    @click.option("-v", "--verbose", is_flag=True, help="Verbose output")
    @click.option("-c", "--confirm", is_flag=True, help="Confirm operations that require confirmation")
    @click.pass_context
    def remote_group(ctx: click.Context, function_name: str, region: str, verbose: bool, confirm: bool) -> None:
        """Proxy commands to Lambda (same as flask user/category/restaurant/db but remote)."""
        ctx.obj = {"function_name": function_name, "region": region, "verbose": verbose, "confirm": confirm}

    # Add list-operations
    @remote_group.command("list-operations")
    @click.pass_context
    def list_ops(ctx: click.Context) -> None:
        config = _get_remote_config(ctx)
        result = invoke_remote_operation(
            "list_operations", {}, config["function_name"], config["region"], config["confirm"]
        )
        click.echo(_format_response(result, config.get("verbose", False)))
        ctx.exit(0 if result.get("success") else 1)

    # Clone structure: user, category, restaurant, db
    remote_user = click.Group("user", help="User management (remote)")
    remote_category = click.Group("category", help="Category management (remote)")
    remote_restaurant = click.Group("restaurant", help="Restaurant management (remote)")
    remote_db = click.Group("db", help="Database operations (remote)")

    # User commands
    @remote_user.command("list")
    @click.option("--admin-only", is_flag=True)
    @click.option("--objects", is_flag=True)
    @click.option("--limit", default=100, type=int)
    def user_list(**kwargs: Any) -> None:
        _make_remote_cmd("list_users", PARAMS_BUILDERS["list_users"])(**kwargs)

    @remote_user.command("create")
    @click.option("--username", required=True)
    @click.option("--email", required=True)
    @click.option("--password", required=True)
    @click.option("--admin", is_flag=True)
    @click.option("--advanced", is_flag=True)
    @click.option("--active/--inactive", default=True)
    def user_create(**kwargs: Any) -> None:
        _make_remote_cmd("create_user", PARAMS_BUILDERS["create_user"])(**kwargs)

    @remote_user.command("update")
    @click.argument("user_identifier")
    @click.option("--username", help="New username")
    @click.option("--email", help="New email")
    @click.option("--password", help="New password")
    @click.option("--admin/--no-admin", default=None)
    @click.option("--advanced/--no-advanced", default=None)
    @click.option("--active/--inactive", default=None)
    def user_update(**kwargs: Any) -> None:
        _make_remote_cmd("update_user", PARAMS_BUILDERS["update_user"])(**kwargs)

    @remote_user.command("delete")
    @click.argument("user_identifier")
    @click.option("--force", is_flag=True)
    @click.option("--cascade/--no-cascade", default=True)
    def user_delete(**kwargs: Any) -> None:
        _make_remote_cmd("delete_user", PARAMS_BUILDERS["delete_user"])(**kwargs)

    @remote_user.command("reset-password")
    @click.option("--email", required=True)
    @click.option("--password", required=True)
    def user_reset_password(**kwargs: Any) -> None:
        _make_remote_cmd("reset_admin_password", PARAMS_BUILDERS["reset_admin_password"])(**kwargs)

    # Category commands
    @remote_category.command("reinit")
    @click.option("--user-id", type=int)
    @click.option("--username", type=str)
    @click.option("--all-users", is_flag=True)
    @click.option("--dry-run", is_flag=True)
    @click.option("--force", is_flag=True)
    def category_reinit(**kwargs: Any) -> None:
        _make_remote_cmd("reinit_categories", PARAMS_BUILDERS["reinit_categories"])(**kwargs)

    @remote_category.command("list")
    @click.option("--user-id", type=int)
    @click.option("--username", type=str)
    @click.option("--all-users", is_flag=True)
    def category_list(**kwargs: Any) -> None:
        _make_remote_cmd("list_categories", PARAMS_BUILDERS["list_categories"])(**kwargs)

    # Restaurant commands
    @remote_restaurant.command("list")
    @click.option("--user-id", type=int)
    @click.option("--username", type=str)
    @click.option("--all-users", is_flag=True)
    @click.option("--detailed", is_flag=True)
    @click.option("--with-google-id", is_flag=True)
    def restaurant_list(**kwargs: Any) -> None:
        _make_remote_cmd("list_restaurants", PARAMS_BUILDERS["list_restaurants"])(**kwargs)

    @remote_restaurant.command("validate")
    @click.option("--user-id", type=int)
    @click.option("--username", type=str)
    @click.option("--all-users", is_flag=True)
    @click.option("--restaurant-id", type=int)
    @click.option("--fix-mismatches", "-f", is_flag=True)
    @click.option("--update-service-levels", is_flag=True)
    @click.option("--find-place-id", is_flag=True)
    @click.option("--closest", is_flag=True)
    @click.option("--dry-run", is_flag=True)
    def restaurant_validate(**kwargs: Any) -> None:
        _make_remote_cmd("validate_restaurants", PARAMS_BUILDERS["validate_restaurants"])(**kwargs)

    # DB commands
    @remote_db.command("init")
    @click.option("--force", is_flag=True)
    @click.option("--sample-data", is_flag=True)
    def db_init(**kwargs: Any) -> None:
        _make_remote_cmd("init_db", PARAMS_BUILDERS["init_db"])(**kwargs)

    @remote_db.command("run-migrations")
    @click.option("--dry-run", is_flag=True)
    @click.option("--target-revision", type=str)
    @click.option("--fix-history", is_flag=True)
    def db_run_migrations(**kwargs: Any) -> None:
        _make_remote_cmd("run_migrations", PARAMS_BUILDERS["run_migrations"])(**kwargs)

    @remote_db.command("stamp")
    @click.option("--revision", required=True)
    def db_stamp(**kwargs: Any) -> None:
        _make_remote_cmd("stamp", PARAMS_BUILDERS["stamp"])(**kwargs)

    remote_group.add_command(remote_user)
    remote_group.add_command(remote_category)
    remote_group.add_command(remote_restaurant)
    remote_group.add_command(remote_db)
    app.cli.add_command(remote_group)
