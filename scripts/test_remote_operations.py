#!/usr/bin/env python3
"""Test remote Lambda database operations.

This script helps test the Lambda function's database operations
on AWS.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import boto3

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class LambdaTester:
    def __init__(self, function_name, region, profile=None):
        """Initialize the Lambda tester.

        Args:
            function_name: Name of the Lambda function
            region: AWS region
            profile: AWS profile name (optional)
        """
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.lambda_client = session.client("lambda", region_name=region)
        self.function_name = function_name

    def invoke_operation(self, operation, **kwargs):
        """Invoke a database operation on the Lambda function.

        Args:
            operation: Operation to perform ('status', 'migrate', 'reset')
            **kwargs: Additional arguments for the operation

        Returns:
            dict: Response from the Lambda function
        """
        payload = {"db_operation": operation, **kwargs}

        try:
            response = self.lambda_client.invoke(
                FunctionName=self.function_name,
                InvocationType="RequestResponse",
                Payload=json.dumps(payload).encode("utf-8"),
            )

            # Parse the response
            response_payload = json.loads(response["Payload"].read().decode("utf-8"))

            print(f"\n{'='*50}")
            print(f"Operation: {operation}")
            print(f"Status Code: {response_payload.get('statusCode', 'N/A')}")

            try:
                body = json.loads(response_payload.get("body", "{}"))
                print(f"Response: {json.dumps(body, indent=2)}")
            except (json.JSONDecodeError, AttributeError):
                print(f"Raw Response: {response_payload}")

            print(f"{'='*50}\n")

            return response_payload

        except Exception as e:
            print(f"Error invoking Lambda function: {e}")
            return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Test remote Lambda database operations")
    parser.add_argument("--function-name", required=True, help="Name of the Lambda function")
    parser.add_argument("--region", default="us-east-1", help="AWS region (default: us-east-1)")
    parser.add_argument("--profile", help="AWS profile to use")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Add subparsers for different commands
    subparsers.add_parser("status", help="Check database status")
    subparsers.add_parser("migrate", help="Run database migrations")
    subparsers.add_parser("reset", help="Reset the database")
    subparsers.add_parser("test-all", help="Test all operations")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    tester = LambdaTester(args.function_name, args.region, args.profile)

    if args.command == "status":
        tester.invoke_operation("status")
    elif args.command == "migrate":
        tester.invoke_operation("migrate")
    elif args.command == "reset":
        confirm = input("⚠️  WARNING: This will reset the database. Are you sure? (y/N): ")
        if confirm.lower() == "y":
            tester.invoke_operation("reset")
        else:
            print("Operation cancelled.")
    elif args.command == "test-all":
        print("=== Testing Remote Database Operations ===\n")

        print("1. Checking database status...")
        tester.invoke_operation("status")

        print("\n2. Running migrations...")
        tester.invoke_operation("migrate")

        print("\n3. Verifying status after migration...")
        tester.invoke_operation("status")

        print("\n✅ All tests completed!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
