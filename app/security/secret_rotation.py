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


# Type aliases for better readability
FieldValidator = Dict[str, Any]
FieldValidators = Dict[str, FieldValidator]
SecretDict = Dict[str, Any]

# Constants for field validation
REQUIRED_FIELDS: FieldValidators = {
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
        "validator": lambda x: len(x) >= 12,
        "error": "Password must be at least 12 characters long",
    },
}


def _validate_secret_arn(arn: str) -> None:
    """Validate the secret ARN.

    Args:
        arn: The Amazon Resource Name to validate

    Raises:
        ValueError: If the ARN is empty or invalid
    """
    if not arn:
        raise ValueError("Secret ARN cannot be empty")


def _validate_stage(stage: str) -> None:
    """Validate the secret stage.

    Args:
        stage: The secret stage to validate

    Raises:
        ValueError: If the stage is not 'AWSCURRENT' or 'AWSPENDING'
    """
    if stage not in ("AWSCURRENT", "AWSPENDING"):
        raise ValueError("Stage must be either 'AWSCURRENT' or 'AWSPENDING'")


def _prepare_request_params(arn: str, stage: str, token: Optional[str] = None) -> Dict[str, Any]:
    """Prepare the request parameters for AWS Secrets Manager.

    Args:
        arn: The secret ARN
        stage: The secret stage
        token: Optional version ID or staging label

    Returns:
        Dictionary of request parameters

    Raises:
        ValueError: If the token is invalid
    """
    params: Dict[str, Any] = {"SecretId": arn}

    if token:
        if not isinstance(token, str):
            raise ValueError("Token must be a string")
        params["VersionId"] = token
    else:
        params["VersionStage"] = stage

    return params


def _parse_secret_response(response: Dict[str, Any], arn: str) -> Dict[str, Any]:
    """Parse and validate the secret response from AWS.

    Args:
        response: The response from AWS Secrets Manager
        arn: The secret ARN for error messages

    Returns:
        The parsed secret dictionary

    Raises:
        ValueError: If the secret is invalid or malformed
    """
    if "SecretString" not in response:
        raise ValueError("Secret value is not a string")

    try:
        secret = json.loads(response["SecretString"])
    except json.JSONDecodeError as e:
        logger.error("Secret %s does not contain valid JSON: %s", arn, str(e))
        raise ValueError(f"Secret {arn} does not contain valid JSON") from e

    if not isinstance(secret, dict):
        raise ValueError("Secret value must be a JSON object")

    return secret


def _validate_field_value(field: str, value: Any, validator: FieldValidator) -> Any:
    """Validate and convert a single field value.

    Args:
        field: The field name
        value: The field value to validate
        validator: The validation rules

    Returns:
        The validated and converted value

    Raises:
        ValueError: If the value is invalid
    """
    # Check type
    expected_types = validator["type"]
    if not isinstance(expected_types, tuple):
        expected_types = (expected_types,)

    if not any(isinstance(value, t) for t in expected_types):
        type_names = [t.__name__ for t in expected_types]
        raise ValueError(f"Field '{field}' must be one of: {', '.join(type_names)}")

    # Convert value if needed
    if "converter" in validator:
        try:
            value = validator["converter"](value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid value for field '{field}': {e}")

    # Validate value
    if not validator["validator"](value):
        raise ValueError(f"Invalid value for field '{field}': {validator['error']}")

    return value


def _validate_secret_fields(secret: Dict[str, Any], validators: FieldValidators) -> SecretDict:
    """Validate all fields in the secret against the validators.

    Args:
        secret: The secret dictionary to validate
        validators: The validation rules

    Returns:
        A new dictionary with validated and converted values

    Raises:
        ValueError: If any validation fails
    """
    result: SecretDict = {}

    for field, validator in validators.items():
        if field not in secret and validator["required"]:
            raise ValueError(f"Missing required field: {field}")

        if field in secret:
            result[field] = _validate_field_value(field, secret[field], validator)

    return result


def _handle_aws_error(error: Exception, arn: str) -> None:
    """Handle AWS client errors and convert to appropriate exceptions.

    Args:
        error: The exception from the AWS client
        arn: The secret ARN for error messages

    Raises:
        ValueError: With appropriate error message based on the AWS error
    """
    error_msg = str(error).lower()

    if "not found" in error_msg:
        logger.error("Secret not found: %s", arn)
        raise ValueError(f"Secret not found: {arn}") from error
    elif "invalid request" in error_msg:
        logger.error("Invalid request for secret %s: %s", arn, str(error))
        raise ValueError(f"Invalid request for secret {arn}: {error}") from error
    elif "invalid parameter" in error_msg:
        logger.error("Invalid parameter for secret %s: %s", arn, str(error))
        raise ValueError(f"Invalid parameter for secret {arn}: {error}") from error
    else:
        logger.exception("Unexpected error retrieving secret %s", arn)
        raise ValueError(f"Error retrieving secret {arn}: {str(error)}") from error


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
    _validate_secret_arn(arn)
    _validate_stage(stage)

    # Prepare and make the request
    request_params = _prepare_request_params(arn, stage, token)

    try:
        logger.info("Retrieving secret %s (stage: %s)", arn, stage)
        response = service_client.get_secret_value(**request_params)

        # Parse and validate the response
        secret = _parse_secret_response(response, arn)
        return _validate_secret_fields(secret, REQUIRED_FIELDS)

    except Exception as e:
        _handle_aws_error(e, arn)
        raise ValueError(f"Error retrieving secret {arn}: {str(e)}") from e
