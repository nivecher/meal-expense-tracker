#!/usr/bin/env python3
"""Invoke Lambda function to run database migrations.

This script simplifies the process of invoking a Lambda function to run database migrations
using the AWS CLI. It handles the invocation and provides clear success/error messages.
"""

import base64
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
from typing import List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _parse_lambda_response(response_text: str) -> bool:
    """Parse and validate the Lambda function response.

    Args:
        response_text: Raw response text from the Lambda invocation

    Returns:
        bool: True if migrations were successful, False otherwise

    Raises:
        json.JSONDecodeError: If response cannot be parsed as JSON
        KeyError: If required fields are missing from the response
    """
    response = json.loads(response_text)

    # Handle API Gateway response format
    if "statusCode" in response:
        if response["statusCode"] == 200:
            logger.info("✅ Database migrations completed successfully")
            return True
        logger.error("❌ Migration failed with status code: %s", response["statusCode"])
        return False

    # Handle AWS CLI response format
    if "StatusCode" in response:
        if response["StatusCode"] == 200:
            logger.info("✅ Lambda executed successfully")
            return True
        logger.error("❌ Lambda execution failed with status: %s", response["StatusCode"])
        return False

    # Handle error cases
    if "FunctionError" in response:
        error_msg = response.get("errorMessage", "Unknown error occurred")
        logger.error("❌ Lambda error: %s", error_msg)
        return False

    logger.error("❌ Unexpected response format: %s", json.dumps(response, indent=2))
    return False


def process_lambda_response(result: subprocess.CompletedProcess) -> bool:
    """Process the response from the Lambda function.

    Args:
        result: Completed process from subprocess.run()

    Returns:
        bool: True if migrations were successful, False otherwise
    """
    if result.stderr:
        logger.warning("Lambda logs: %s", result.stderr.strip())

    try:
        return _parse_lambda_response(result.stdout)
    except json.JSONDecodeError:
        logger.error("❌ Failed to parse Lambda response: %s", result.stdout)
        return False
    except Exception as e:
        logger.error("❌ Unexpected error processing Lambda response: %s", str(e))
        return False


def _validate_aws_identifier(identifier: str, identifier_type: str) -> None:
    """Validate AWS resource identifiers.

    Args:
        identifier: The identifier to validate
        identifier_type: Type of identifier (e.g., 'function_name', 'region', 'profile')

    Raises:
        ValueError: If the identifier is invalid
    """
    if not identifier or not isinstance(identifier, str):
        raise ValueError(f"Invalid {identifier_type}: must be a non-empty string")

    # Basic pattern validation for AWS identifiers
    if identifier_type == "function_name":
        if not re.match(r"^[a-zA-Z0-9\-_]{1,64}$", identifier):
            raise ValueError(
                "Function name can only contain alphanumeric characters, hyphens, and underscores, "
                "and must be between 1 and 64 characters long"
            )
    elif identifier_type == "region":
        if not re.match(r"^[a-z]{2}-[a-z]+-\d+$", identifier):
            raise ValueError("Invalid AWS region format")
    elif identifier_type == "profile":
        if not re.match(r"^[a-zA-Z0-9_\-]+$", identifier):
            raise ValueError("AWS profile name contains invalid characters")


def _find_aws_cli() -> str:
    """Find the AWS CLI executable.

    Returns:
        str: Path to the AWS CLI executable

    Raises:
        RuntimeError: If AWS CLI is not found
    """
    aws_path = shutil.which("aws")
    if not aws_path:
        raise RuntimeError("AWS CLI is not installed or not in PATH")
    return aws_path


def build_aws_cli_command(function_name: str, region: str | None = None, profile: str | None = None) -> list[str]:
    """Build the AWS CLI command for invoking the Lambda function.

    Args:
        function_name: Name of the Lambda function to invoke
        region: AWS region (optional)
        profile: AWS profile to use (optional)

    Returns:
        list: Command parts as a list

    Raises:
        ValueError: If any of the input parameters are invalid
    """
    # Validate inputs
    _validate_aws_identifier(function_name, "function_name")
    if region:
        _validate_aws_identifier(region, "region")
    if profile:
        _validate_aws_identifier(profile, "profile")

    # Get AWS CLI path
    aws_path = _find_aws_cli()

    # Build command parts
    cmd_parts = [
        aws_path,
        "lambda",
        "invoke",
        "--function-name",
        function_name,
        "--invocation-type",
        "RequestResponse",
        "--log-type",
        "Tail",
        "--payload",
        base64.b64encode(json.dumps({"admin_operation": "run_migrations"}).encode()).decode(),
    ]

    # Add optional parameters
    if region:
        cmd_parts.extend(["--region", region])
    if profile:
        cmd_parts.extend(["--profile", profile])

    # Add output file
    null_device = "nul" if os.name == "nt" else "/dev/null"
    cmd_parts.append(null_device)

    return cmd_parts


def invoke_lambda_migrations(function_name: str, region: str | None = None, profile: str | None = None) -> bool:
    """Invoke the Lambda function to run migrations.

    Args:
        function_name: Name of the Lambda function to invoke
        region: AWS region (optional)
        profile: AWS profile to use (optional)

    Returns:
        bool: True if migrations were successful, False otherwise

    Raises:
        ValueError: If input validation fails
        subprocess.SubprocessError: If the subprocess call fails
    """
    try:
        # Build and validate the command
        cmd = build_aws_cli_command(function_name, region, profile)
        logger.debug("Running command: %s", " ".join(shlex.quote(arg) for arg in cmd))

        # Execute the command with a timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=300,  # 5 minute timeout
            shell=False,  # Prevent shell injection
            encoding="utf-8",
            errors="replace",  # Handle encoding errors gracefully
        )

        if result.returncode != 0:
            logger.error("❌ Failed to invoke Lambda: %s", result.stderr or "Unknown error")
            return False

        return process_lambda_response(result)

    except Exception as e:
        logger.error("❌ Error: %s", str(e))
        return False


def main() -> None:
    """Parse command line arguments and invoke the Lambda function."""
    import argparse

    parser = argparse.ArgumentParser(description="Run database migrations via Lambda")
    parser.add_argument("-f", "--function", required=True, help="Lambda function name")
    parser.add_argument("-r", "--region", help="AWS region")
    parser.add_argument("-p", "--profile", help="AWS profile")

    args = parser.parse_args()

    success = invoke_lambda_migrations(
        function_name=args.function,
        region=args.region,
        profile=args.profile,
    )

    if success:
        logger.info("✅ Database migration completed successfully")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
