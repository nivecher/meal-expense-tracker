#!/usr/bin/env python3
"""Invoke Lambda function to run database migrations.

This script simplifies the process of invoking a Lambda function to run database migrations
using the AWS CLI. It handles the invocation and provides clear success/error messages.
"""

import json
import logging
import subprocess
import sys
from typing import Optional

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


def build_aws_cli_command(function_name: str, region: Optional[str] = None, profile: Optional[str] = None) -> list[str]:
    """Build the AWS CLI command for invoking the Lambda function.

    Args:
        function_name: Name of the Lambda function to invoke
        region: AWS region (optional)
        profile: AWS profile to use (optional)

    Returns:
        list: Command parts as a list
    """
    cmd = [
        "aws",
        "lambda",
        "invoke",
        "--function-name",
        function_name,
        "--payload",
        json.dumps({"db_operation": "migrate"}),
        "--cli-binary-format",
        "raw-in-base64-out",
        "/dev/stdout",
    ]

    if region:
        cmd.extend(["--region", region])
    if profile:
        cmd.extend(["--profile", profile])

    return cmd


def invoke_lambda_migrations(function_name: str, region: Optional[str] = None, profile: Optional[str] = None) -> bool:
    """Invoke the Lambda function to run migrations.

    Args:
        function_name: Name of the Lambda function to invoke
        region: AWS region (optional)
        profile: AWS profile to use (optional)

    Returns:
        bool: True if migrations were successful, False otherwise
    """
    try:
        cmd = build_aws_cli_command(function_name, region, profile)
        logger.info("🚀 Invoking Lambda function: %s", function_name)

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

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

    sys.exit(0 if success else 1)

    logger.info("✅ Database migration completed successfully")


if __name__ == "__main__":
    main()
