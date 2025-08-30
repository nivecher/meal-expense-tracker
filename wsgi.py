"""WSGI entry point for local development and production WSGI servers.

This module provides a standard WSGI application that can be used with
development servers (Flask's built-in) or production WSGI servers (Gunicorn).
"""

import os
import sys

# Load environment variables before importing app
from dotenv import load_dotenv

load_dotenv()  # Loads .env file

# Ensure FLASK_ENV is set
if "FLASK_ENV" not in os.environ:
    os.environ["FLASK_ENV"] = "development"
    print(f"FLASK_ENV not set, defaulting to: {os.environ['FLASK_ENV']}", file=sys.stderr)

# Import app after environment is set
from app import create_app

# Create the application instance
app = create_app()
application = app  # This maintains WSGI compatibility

# Log configuration for debugging
print("\nApplication configuration:")
print(f"- FLASK_ENV: {os.environ.get('FLASK_ENV')}")
print(f"- DATABASE_URL: {'Set' if os.environ.get('DATABASE_URL') else 'Not set'}")
print(f"- SQLALCHEMY_DATABASE_URI: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not set')}\n")


def run_migrations() -> None:
    """Run database migrations for local development."""
    from flask_migrate import upgrade

    with application.app_context():
        upgrade()
        print("Database migrations applied successfully")


# AWS Lambda handler
def lambda_handler(event, context):
    """Lambda handler that delegates to the lambda_handler module.

    This function imports and calls the actual lambda_handler from lambda_handler.py.
    This approach keeps WSGI and Lambda concerns separate while satisfying the
    Terraform configuration expectation of wsgi.lambda_handler.
    """
    try:
        from lambda_handler import lambda_handler as actual_handler

        return actual_handler(event, context)
    except ImportError as e:
        # Fallback error response if lambda_handler module is not available
        import json

        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Lambda handler module not found: {str(e)}"}),
            "headers": {"Content-Type": "application/json"},
            "isBase64Encoded": False,
        }


if __name__ == "__main__":
    # Local development server
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))

    # Run migrations if in development mode
    if os.environ.get("FLASK_ENV") == "development":
        try:
            run_migrations()
        except Exception as e:
            print(f"Warning: Could not run migrations: {e}")

    # Start the development server
    application.run(host=host, port=port, debug=True)
