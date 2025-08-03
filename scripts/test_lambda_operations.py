#!/usr/bin/env python3
"""Test Lambda database operations.

This script helps test the Lambda function's database operations locally
before deploying to AWS.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def test_operation(operation, **kwargs):
    """Test a database operation by invoking the Lambda handler directly."""
    from wsgi import lambda_handler

    # Create a test event
    event = {"db_operation": operation, **kwargs}

    # Call the Lambda handler
    result = lambda_handler(event, {})

    # Parse and display the result
    try:
        body = json.loads(result["body"])
        print(f"\n{'=' * 50}")
        print(f"Operation: {operation}")
        print(f"Status Code: {result['statusCode']}")
        print(f"Response: {json.dumps(body, indent=2)}")
        print(f"{'=' * 50}\n")
        return body.get("status") == "success"
    except Exception as e:
        print(f"Error processing result: {e}")
        print(f"Raw result: {result}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test Lambda database operations")
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

    if args.command == "status":
        return 0 if test_operation("status") else 1
    elif args.command == "migrate":
        return 0 if test_operation("migrate") else 1
    elif args.command == "reset":
        confirm = input("⚠️  WARNING: This will reset the database. Are you sure? (y/N): ")
        if confirm.lower() == "y":
            return 0 if test_operation("reset") else 1
        print("Operation cancelled.")
        return 0
    elif args.command == "test-all":
        print("=== Testing Database Operations ===\n")

        print("1. Checking database status...")
        if not test_operation("status"):
            print("❌ Status check failed")
            return 1

        print("\n2. Running migrations...")
        if not test_operation("migrate"):
            print("❌ Migration failed")
            return 1

        print("\n3. Verifying status after migration...")
        if not test_operation("status"):
            print("❌ Status check after migration failed")
            return 1

        print("\n✅ All tests completed successfully!")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
