"""Shared Lambda proxy logic for flask --remote and remote_admin.

This module provides the single source of truth for:
- Lambda invocation
- Operation name mapping (CLI path -> Lambda operation)
- Parameter transformation (CLI kwargs -> Lambda params)
- Response formatting
"""

from __future__ import annotations

from functools import wraps
import json
import sys
from typing import Any, Callable, cast

import click

# Lazy import boto3 to avoid dependency when not using remote
_boto3: Any = None


def _get_boto3() -> Any:
    global _boto3
    if _boto3 is None:
        try:
            import boto3
            from botocore.config import Config
            from botocore.exceptions import ClientError, NoCredentialsError

            _boto3 = (boto3, Config, ClientError, NoCredentialsError)
        except ImportError:
            click.echo("❌ Error: boto3 required for --remote. Install with: pip install boto3", err=True)
            sys.exit(1)
    return _boto3


def _get_root_context(ctx: click.Context) -> click.Context:
    """Get the root CLI context (where --remote is set)."""
    root = ctx
    while root.parent:
        root = root.parent
    return root


def is_remote_mode(ctx: click.Context | None = None) -> bool:
    """Check if we're in remote (Lambda proxy) mode."""
    if ctx is None:
        try:
            context = click.get_current_context()
        except RuntimeError:
            return False
    else:
        context = ctx
    root = _get_root_context(context)
    return bool(root.params.get("remote", False))


def get_remote_config(ctx: click.Context) -> dict[str, Any]:
    """Get remote config (function_name, region, confirm, verbose) from context."""
    root = _get_root_context(ctx)
    return {
        "function_name": root.params.get("function_name", "meal-expense-tracker-dev"),
        "region": root.params.get("region", "us-east-1"),
        "confirm": root.params.get("confirm", False),
        "verbose": root.params.get("verbose", False),
    }


def _invoke_lambda(
    operation_name: str,
    parameters: dict[str, Any],
    function_name: str,
    region: str,
    confirm: bool,
) -> dict[str, Any]:
    """Invoke Lambda with the given operation and parameters."""
    boto3, Config, ClientError, NoCredentialsError = _get_boto3()

    try:
        config = Config(connect_timeout=10, read_timeout=300, retries={"max_attempts": 5})
        lambda_client = boto3.client("lambda", region_name=region, config=config)
    except NoCredentialsError:
        return {"success": False, "message": "AWS credentials not configured. Run: aws configure"}
    except Exception as e:
        return {"success": False, "message": f"AWS client error: {e}"}

    payload = {"admin_operation": operation_name, "parameters": parameters, "confirm": confirm}

    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )
        response_payload = json.loads(response["Payload"].read())

        if response.get("FunctionError"):
            return {"success": False, "message": f"Lambda error: {response_payload}"}

        if "body" in response_payload:
            return cast(dict[str, Any], json.loads(response_payload["body"]))
        return cast(dict[str, Any], response_payload)

    except ClientError as e:
        code = e.response["Error"]["Code"]
        msg = e.response["Error"]["Message"]
        if code == "ResourceNotFound":
            return {"success": False, "message": f"Lambda '{function_name}' not found in {region}"}
        if code == "AccessDenied":
            return {"success": False, "message": "Access denied. Check Lambda:InvokeFunction permissions"}
        return {"success": False, "message": f"AWS Error: {msg}"}
    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {str(e)}"}


def _format_response(response: dict[str, Any], verbose: bool = False) -> str:
    """Format Lambda response for display."""
    if not response.get("success"):
        return f"❌ {response.get('message', 'Operation failed')}"

    output = [f"✅ {response.get('message', 'Operation completed')}"]
    data = response.get("data")
    if data:
        if verbose:
            output.append(f"\n📊 Data: {json.dumps(data, indent=2, default=str)}")
        elif "users" in data and isinstance(data["users"], list):
            users = data["users"]
            output.append(f"\n👥 Users ({len(users)}):")
            for u in users[:10]:
                admin_badge = " 👑" if u.get("is_admin") else ""
                active_badge = " ✅" if u.get("is_active") else " ❌"
                output.append(f"  • {u.get('username', 'N/A')} ({u.get('email', 'N/A')}){admin_badge}{active_badge}")
            if len(users) > 10:
                output.append(f"  ... and {len(users) - 10} more")
        elif "operations" in data:
            ops = data["operations"]
            if isinstance(ops, dict):
                output.append(f"\n🛠️  Available Operations ({len(ops)}):")
                for name, info in ops.items():
                    output.append(f"  • {name}: {info.get('description', '')}")

    return "\n".join(output)


def invoke_remote_operation(
    operation_name: str,
    parameters: dict[str, Any],
    function_name: str = "meal-expense-tracker-dev",
    region: str = "us-east-1",
    confirm: bool = False,
) -> dict[str, Any]:
    """Invoke Lambda operation (for use by remote_admin standalone script)."""
    return _invoke_lambda(operation_name, parameters, function_name, region, confirm)


def invoke_remote_and_exit(
    ctx: click.Context,
    operation_name: str,
    parameters: dict[str, Any],
) -> None:
    """Invoke Lambda and exit with appropriate code."""
    config = get_remote_config(ctx)
    result = _invoke_lambda(
        operation_name,
        parameters,
        config["function_name"],
        config["region"],
        config["confirm"],
    )

    if result.get("requires_confirmation") and not config["confirm"]:
        click.echo(f"⚠️  {result.get('message', 'Operation requires confirmation')}")
        click.echo("Add --confirm to proceed.")
        ctx.exit(1)

    click.echo(_format_response(result, config["verbose"]))
    ctx.exit(0 if result.get("success") else 1)


def _parse_user_identifier(identifier: str) -> dict[str, Any]:
    """Parse user identifier to Lambda params."""
    if identifier.isdigit():
        return {"user_id": int(identifier, 10)}
    if "@" in identifier:
        return {"email": identifier}
    return {"username": identifier}


def with_remote_proxy(
    operation_name: str,
    params_builder: Callable[[click.Context, dict[str, Any]], dict[str, Any]],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that proxies to Lambda when --remote is set."""

    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            ctx = click.get_current_context()
            if not is_remote_mode(ctx):
                return f(*args, **kwargs)

            params = params_builder(ctx, kwargs)
            invoke_remote_and_exit(ctx, operation_name, params)

        return wrapper

    return decorator


# --- Params builders for each command ---


def _list_users_params(_ctx: click.Context, kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "admin_only": kwargs.get("admin_only", False),
        "objects": kwargs.get("objects", False),
        "limit": kwargs.get("limit", 100),
    }


def _create_user_params(_ctx: click.Context, kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "username": kwargs.get("username", ""),
        "email": kwargs.get("email", ""),
        "password": kwargs.get("password", ""),
        "admin": kwargs.get("admin", False),
        "advanced": kwargs.get("advanced", False),
        "active": kwargs.get("active", True),
    }


def _update_user_params(ctx: click.Context, kwargs: dict[str, Any]) -> dict[str, Any]:
    params = _parse_user_identifier(kwargs.get("user_identifier", ""))
    if kwargs.get("username") is not None:
        params["new_username"] = kwargs["username"]
    if kwargs.get("email") is not None:
        params["new_email"] = kwargs["email"]
    if kwargs.get("password"):
        params["password"] = kwargs["password"]
    if kwargs.get("admin") is not None:
        params["admin"] = kwargs["admin"]
    if kwargs.get("advanced") is not None:
        params["advanced"] = kwargs["advanced"]
    if kwargs.get("active") is not None:
        params["active"] = kwargs["active"]
    return params


def _delete_user_params(_ctx: click.Context, kwargs: dict[str, Any]) -> dict[str, Any]:
    params = _parse_user_identifier(kwargs.get("user_identifier", ""))
    params["force"] = kwargs.get("force", False)
    params["cascade"] = kwargs.get("cascade", True) and not kwargs.get("no_cascade", False)
    return params


def _reset_password_params(_ctx: click.Context, kwargs: dict[str, Any]) -> dict[str, Any]:
    return {"email": kwargs.get("email", ""), "password": kwargs.get("password", "")}


def _reinit_categories_params(_ctx: click.Context, kwargs: dict[str, Any]) -> dict[str, Any]:
    params = {"dry_run": kwargs.get("dry_run", False), "force": kwargs.get("force", False)}
    if kwargs.get("user_id"):
        params["user_id"] = kwargs["user_id"]
    if kwargs.get("username"):
        params["username"] = kwargs["username"]
    if kwargs.get("all_users"):
        params["all_users"] = True
    return params


def _list_categories_params(_ctx: click.Context, kwargs: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if kwargs.get("user_id"):
        params["user_id"] = kwargs["user_id"]
    if kwargs.get("username"):
        params["username"] = kwargs["username"]
    if kwargs.get("all_users"):
        params["all_users"] = True
    return params


def _list_restaurants_params(_ctx: click.Context, kwargs: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {
        "detailed": kwargs.get("detailed", False),
        "with_google_id": kwargs.get("with_google_id", False),
    }
    if kwargs.get("user_id"):
        params["user_id"] = kwargs["user_id"]
    if kwargs.get("username"):
        params["username"] = kwargs["username"]
    if kwargs.get("all_users"):
        params["all_users"] = True
    return params


def _validate_restaurants_params(_ctx: click.Context, kwargs: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {
        "fix_mismatches": kwargs.get("fix_mismatches", False),
        "update_service_levels": kwargs.get("update_service_levels", False),
        "find_place_id": kwargs.get("find_place_id", False),
        "closest": kwargs.get("closest", False),
        "dry_run": kwargs.get("dry_run", False),
    }
    if kwargs.get("user_id"):
        params["user_id"] = kwargs["user_id"]
    if kwargs.get("username"):
        params["username"] = kwargs["username"]
    if kwargs.get("all_users"):
        params["all_users"] = True
    if kwargs.get("restaurant_id"):
        params["restaurant_id"] = kwargs["restaurant_id"]
    return params


def _run_migrations_params(_ctx: click.Context, kwargs: dict[str, Any]) -> dict[str, Any]:
    params = {"dry_run": kwargs.get("dry_run", False), "fix_history": kwargs.get("fix_history", False)}
    if kwargs.get("target_revision"):
        params["target_revision"] = kwargs["target_revision"]
    return params


def _init_db_params(_ctx: click.Context, kwargs: dict[str, Any]) -> dict[str, Any]:
    return {"force": kwargs.get("force", False), "sample_data": kwargs.get("sample_data", False)}


def _stamp_params(_ctx: click.Context, kwargs: dict[str, Any]) -> dict[str, Any]:
    return {"revision": kwargs.get("revision", "")}


# Registry for use by both Flask and remote_admin
PARAMS_BUILDERS: dict[str, Callable[[click.Context, dict[str, Any]], dict[str, Any]]] = {
    "list_users": _list_users_params,
    "create_user": _create_user_params,
    "update_user": _update_user_params,
    "delete_user": _delete_user_params,
    "reset_admin_password": _reset_password_params,
    "reinit_categories": _reinit_categories_params,
    "list_categories": _list_categories_params,
    "list_restaurants": _list_restaurants_params,
    "validate_restaurants": _validate_restaurants_params,
    "run_migrations": _run_migrations_params,
    "init_db": _init_db_params,
    "stamp": _stamp_params,
}
