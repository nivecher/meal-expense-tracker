"""AWS Secrets Manager PostgreSQL Rotation Lambda

This module provides functionality for rotating PostgreSQL database credentials
stored in AWS Secrets Manager. It implements the four-step rotation process:
1. createSecret: Creates a new version of the secret
2. setSecret: Sets the new password in the database
3. testSecret: Tests the new secret
4. finishSecret: Finalizes the rotation

Security Notes:
- Uses secrets.SystemRandom() for cryptographically secure random number generation
- Implements secure password generation with proper character sets
- Validates input parameters and handles errors securely
"""

import json
import logging
import secrets
import shlex
import string
import subprocess
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Constants
VERSION_PATTERN = r"^v\d+\.\d+\.\d+$"
MAX_TAG_LENGTH = 50
PG_SPECIAL_CHARS = "~!@#$%^&*_+-=[]{}|;:,.<>?"


def _run_git_command(args: List[str], cwd: Optional[str] = None) -> Tuple[bool, str]:
    """Safely run a git command with proper error handling.

    Args:
        args: List of command arguments
        cwd: Working directory (optional)

    Returns:
        Tuple of (success, output)
    """
    if not args or not all(isinstance(arg, str) for arg in args):
        raise ValueError("Invalid git command arguments")

    git_path = "git"  # Rely on PATH resolution
    cmd = [git_path] + args

    try:
        logger.debug("Running git command: %s", " ".join(shlex.quote(arg) for arg in cmd))
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd,
            timeout=30,
            shell=False,  # 30 second timeout
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error("Git command failed: %s", e.stderr.strip())
        return False, e.stderr.strip()
    except subprocess.TimeoutExpired:
        logger.error("Git command timed out")
        return False, "Command timed out"
    except Exception as e:
        logger.exception("Unexpected error running git command")
        return False, str(e)


def generate_password(length: int = 16, max_attempts: int = 10) -> str:
    """Generate a cryptographically secure random password.

    The generated password will contain at least one character from each character set
    (lowercase, uppercase, digits, special) and will exclude problematic characters.

    Args:
        length: Length of the password to generate (minimum 12, default: 16)
        max_attempts: Maximum number of attempts to generate a valid password

    Returns:
        str: A securely generated password

    Raises:
        RuntimeError: If unable to generate a valid password after max_attempts
    """
    # Enforce minimum length
    if length < 12:
        length = 12

    # Define character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits

    # Filter out problematic characters
    excluded_chars = "'\"`\\/"
    special = "".join(c for c in PG_SPECIAL_CHARS if c not in excluded_chars)

    # Create a secure random number generator
    secure_random = secrets.SystemRandom()

    for _ in range(max_attempts):
        try:
            # Ensure we have at least one of each character type
            password_chars = [
                secure_random.choice(lowercase),
                secure_random.choice(uppercase),
                secure_random.choice(digits),
                secure_random.choice(special),
            ]

            # Fill the rest of the password with random choices from all sets
            all_chars = lowercase + uppercase + digits + special
            remaining_length = length - len(password_chars)

            if remaining_length > 0:
                password_chars.extend(secure_random.choice(all_chars) for _ in range(remaining_length))

            # Shuffle the password characters
            secure_random.shuffle(password_chars)
            password = "".join(password_chars)

            # Verify all required character types are present
            has_lower = any(c in lowercase for c in password)
            has_upper = any(c in uppercase for c in password)
            has_digit = any(c in digits for c in password)
            has_special = any(c in special for c in password)

            if has_lower and has_upper and has_digit and has_special:
                return password

        except Exception as e:
            logger.error("Error generating password: %s", e)
            continue

    raise RuntimeError("Failed to generate a valid password after maximum attempts")


def get_secret_dict(service_client: Any, arn: str, stage: str, token: Optional[str] = None) -> Dict[str, Any]:
    """Get and validate the secret value as a dictionary.

    This function retrieves a secret from AWS Secrets Manager and validates that
    it contains all required fields for database connection. It performs input
    validation and type conversion where necessary.

    Args:
        service_client: The AWS Secrets Manager client
        arn: The Amazon Resource Name (ARN) or friendly name of the secret
        stage: The secret stage ('AWSCURRENT' or 'AWSPENDING')
        token: The version ID or staging label (optional)

    Returns:
        dict: The secret value as a dictionary with validated fields

    Raises:
        ValueError: If the secret is invalid, missing required fields, or contains
                  invalid values
        botocore.exceptions.ClientError: For AWS service errors
        json.JSONDecodeError: If the secret value is not valid JSON
    """
    # Validate input parameters
    if not arn:
        raise ValueError("Secret ARN cannot be empty")

    if stage not in ("AWSCURRENT", "AWSPENDING"):
        raise ValueError("Stage must be either 'AWSCURRENT' or 'AWSPENDING'")

    # Define required fields and their validation functions
    field_validators = {
        "db_host": {
            "required": True,
            "type": str,
            "validator": lambda x: len(x.strip()) > 0,
            "error": "Database host cannot be empty",
        },
        "db_port": {
            "required": True,
            "type": (int, str),
            "validator": lambda x: 1 <= int(x) <= 65535,
            "error": "Port must be between 1 and 65535",
            "converter": int,
        },
        "db_name": {
            "required": True,
            "type": str,
            "validator": lambda x: len(x.strip()) > 0,
            "error": "Database name cannot be empty",
        },
        "db_user": {
            "required": True,
            "type": str,
            "validator": lambda x: len(x.strip()) > 0,
            "error": "Database user cannot be empty",
        },
        "db_password": {
            "required": True,
            "type": str,
            "validator": lambda x: len(x) >= 12,  # Enforce minimum password length
            "error": "Password must be at least 12 characters long",
        },
    }

    # Prepare the request parameters
    request_params: Dict[str, Any] = {"SecretId": arn}

    # Only use VersionStage with AWSCURRENT or AWSPENDING
    if token:
        if not isinstance(token, str):
            raise ValueError("Token must be a string")
        request_params["VersionId"] = token
    else:
        request_params["VersionStage"] = stage

    try:
        # Get the secret value
        logger.info("Retrieving secret %s (stage: %s)", arn, stage)
        response = service_client.get_secret_value(**request_params)

        if "SecretString" not in response:
            raise ValueError("Secret value is not a string")

        # Parse the secret string as JSON
        secret = json.loads(response["SecretString"])

        if not isinstance(secret, dict):
            raise ValueError("Secret value must be a JSON object")

        # Validate and convert fields
        result: Dict[str, Any] = {}

        for field, validator in field_validators.items():
            if field not in secret and validator["required"]:
                raise ValueError(f"Missing required field: {field}")

            if field in secret:
                value = secret[field]

                # Check type
                expected_types = validator["type"]
                if not isinstance(expected_types, tuple):
                    expected_types = (expected_types,)

                if not any(isinstance(value, t) for t in expected_types):
                    type_names = [t.__name__ for t in expected_types]
                    raise ValueError(f"Field '{field}' must be one of the following types: " f"{', '.join(type_names)}")

                # Convert value if needed
                if "converter" in validator:
                    try:
                        value = validator["converter"](value)
                    except (ValueError, TypeError) as e:
                        raise ValueError(f"Invalid value for field '{field}': {e}")

                # Validate value
                if not validator["validator"](value):
                    raise ValueError(f"Invalid value for field '{field}': {validator['error']}")

                result[field] = value

        return result

    except json.JSONDecodeError as e:
        logger.error("Secret %s does not contain valid JSON: %s", arn, str(e))
        raise ValueError(f"Secret {arn} does not contain valid JSON") from e

    except Exception as e:
        # Handle AWS client exceptions generically since we can't import boto3 in tests
        error_msg = str(e).lower()
        if "not found" in error_msg:
            logger.error("Secret not found: %s", arn)
            raise ValueError(f"Secret not found: {arn}") from e
        elif "invalid request" in error_msg:
            logger.error("Invalid request for secret %s: %s", arn, str(e))
            raise ValueError(f"Invalid request for secret {arn}: {e}") from e
        elif "invalid parameter" in error_msg:
            logger.error("Invalid parameter for secret %s: %s", arn, str(e))
            raise ValueError(f"Invalid parameter for secret {arn}: {e}") from e
        else:
            logger.exception("Unexpected error retrieving secret %s", arn)
            raise ValueError(f"Error retrieving secret {arn}: {str(e)}") from e
