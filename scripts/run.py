#!/usr/bin/env python3
"""Run the Flask application with environment-specific configuration.

Usage:
    python run.py [environment]

    environment: Optional. One of: dev (default), test, prod
"""

import os
import sys
import signal
import subprocess
import time
from typing import Optional
from dotenv import load_dotenv

# Global process variable to store the Flask subprocess
flask_process: Optional[subprocess.Popen] = None


def signal_handler(sig, frame):
    """Handle interrupt signals (Ctrl+C) to ensure clean shutdown."""
    print("\nShutting down gracefully...")
    if flask_process:
        print("Stopping Flask server...")
        flask_process.terminate()
        try:
            # Wait for process to terminate
            flask_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("Force killing Flask server...")
            flask_process.kill()
    print("Goodbye!")
    sys.exit(0)


def load_environment(env_name: str = "dev") -> None:
    """Load environment variables from the appropriate .env file.

    Args:
        env_name: The environment name (dev, test, prod)
    """
    env_file = f".env.{env_name}"

    if not os.path.exists(env_file):
        print(f"Error: {env_file} not found. Please create it from .env.example")
        sys.exit(1)

    load_dotenv(env_file)
    print(f"Loaded environment: {env_name}")


def start_flask_server(env_name: str) -> int:
    """Start the Flask development server.

    Args:
        env_name: The environment name (dev, test, prod)

    Returns:
        int: The exit code of the Flask process
    """
    global flask_process

    flask_env = "development" if env_name == "dev" else "production"
    os.environ["FLASK_ENV"] = os.getenv("FLASK_ENV", flask_env)

    cmd = [
        "flask",
        "run",
        "--debug" if os.getenv("FLASK_ENV") == "development" else "",
        f'--port={os.getenv("PORT", "5000")}',
    ]
    cmd = [c for c in cmd if c]

    print(f"Starting Flask with command: {' '.join(cmd)}")

    try:
        # Start Flask in a subprocess
        flask_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

        # Stream output in real-time
        for line in iter(flask_process.stdout.readline, ""):
            print(line, end="", flush=True)

        # Wait for process to complete and return its status
        return flask_process.wait()

    except KeyboardInterrupt:
        # This will be caught by the signal handler
        return 0
    except Exception as e:
        print(f"Error running Flask: {e}", file=sys.stderr)
        return 1


def main() -> None:
    """Main entry point for the script.

    Handles command line arguments and starts the Flask development server.
    """
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Parse environment argument
    env_name = "dev"
    if len(sys.argv) > 1:
        env_name = sys.argv[1].lower()

    if env_name not in ("dev", "test", "prod"):
        print("Error: Environment must be one of: dev, test, prod", file=sys.stderr)
        sys.exit(1)

    try:
        # Load environment variables
        load_environment(env_name)

        # Start the Flask server
        return_code = start_flask_server(env_name)

        # Exit with the Flask server's return code
        sys.exit(return_code)

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
