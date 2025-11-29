"""
AWS Secrets Manager PostgreSQL Rotation Lambda

This Lambda function handles automatic rotation of PostgreSQL database credentials
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

# Standard library imports
import json
import logging
import secrets
import string
from typing import Any, Dict, Optional

# Third-party imports
import boto3
import botocore
from botocore.client import BaseClient
import psycopg2

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Constants
PG_SPECIAL_CHARS = "~!@#$%^&*_-+=|(){}[]:;\"',<>?/."
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle the Lambda function invocation from AWS Secrets Manager.

    This function processes the secret rotation request by delegating to the
    appropriate step handler based on the rotation step. It validates the
    input parameters, sets up the AWS clients with retry configuration, and
    ensures proper error handling and logging.

    Args:
        event (dict): The Lambda event containing rotation details:
            - SecretId: The ARN of the secret to rotate
            - ClientRequestToken: The token for this rotation request
            - Step: The rotation step to execute (createSecret, setSecret,
                    testSecret, finishSecret)
        context: Lambda context object (unused)

    Returns:
        dict: Response with status code and message

    Raises:
        ValueError: If required parameters are missing or invalid
        Exception: For any other errors during processing
    """
    logger.info("Received secret rotation request")
    logger.debug("Event: %s", json.dumps(event, default=str, indent=2))

    try:
        # Validate required fields in the event
        required_fields = ["SecretId", "ClientRequestToken", "Step"]
        missing_fields = [f for f in required_fields if f not in event]
        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        arn = event["SecretId"]
        token = event["ClientRequestToken"]
        step = event["Step"]

        # Validate the token format
        if not isinstance(token, str) or len(token) != 36:
            error_msg = f"Invalid ClientRequestToken format: {token}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Setup AWS clients with retry and timeout configuration
        config = botocore.config.Config(
            retries={"max_attempts": 5, "mode": "standard"},
            connect_timeout=10,
            read_timeout=30,
        )

        service_client = boto3.client("secretsmanager", config=config)

        # Log the start of the rotation step
        logger.info("Processing rotation step: %s for secret: %s", step, arn)

        # Process the rotation step
        if step == "createSecret":
            create_secret(service_client, arn, token)
        elif step == "setSecret":
            set_secret(service_client, arn, token)
        elif step == "testSecret":
            test_secret(service_client, arn, token)
        elif step == "finishSecret":
            finish_secret(service_client, arn, token)
        else:
            error_msg = f"Invalid rotation step: {step}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Log successful completion
        logger.info("Successfully completed step: %s", step)

        return {"statusCode": 200, "body": f"Successfully completed step: {step}"}

    except ValueError as ve:
        # Log and re-raise validation errors
        logger.error("Validation error: %s", str(ve), exc_info=True)
        raise
    except Exception as e:
        # Log and re-raise any other errors
        error_msg = f"Error in lambda_handler: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise


def generate_password(length: int = 16, max_attempts: int = 10) -> str:
    """Generate a cryptographically secure random password.

    The generated password will contain at least one character from each character set
    (lowercase, uppercase, digits, special) and will exclude problematic characters.

    Args:
        length: Length of the password to generate (minimum 8, default: 16)
        max_attempts: Maximum number of attempts to generate a valid password

    Returns:
        str: A securely generated password

    Raises:
        RuntimeError: If unable to generate a valid password after max_attempts
    """
    # Validate input parameters
    if length < 8:
        length = 16  # Enforce minimum length

    # Define character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "~!@#$%^&*_+-=[]{}|;:,.<>?/"  # Special characters allowed by PostgreSQL

    # Characters to exclude (quotes and other problematic characters)
    excluded_chars = "'\"`\\/"

    # Filter out excluded characters
    special = "".join(c for c in special if c not in excluded_chars)

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
            logger.error(f"Error generating password: {e}")
            continue

    raise RuntimeError("Failed to generate a valid password after maximum attempts")


def create_secret(service_client: BaseClient, arn: str, token: str) -> None:
    """Create a new secret with a generated password.

    Args:
        service_client: The secrets manager service client
        arn (str): The secret ARN or identifier
        token (str): The ClientRequestToken for this version
    """
    try:
        # Get the current secret to copy other fields
        current_dict = get_secret_dict(service_client, arn, "AWSCURRENT")

        # Generate a new secure password
        new_password = generate_password()

        # Create a new secret with the same structure but new password
        new_secret = {
            "db_host": current_dict["db_host"],
            "db_port": current_dict["db_port"],
            "db_username": current_dict["db_username"],
            "db_password": new_password,
            "db_name": current_dict["db_name"],
            "engine": "postgres",
        }

        # Put the new secret version
        service_client.put_secret_value(
            SecretId=arn,
            ClientRequestToken=token,
            SecretString=json.dumps(new_secret),
            VersionStages=["AWSPENDING"],
        )
        logger.info("Successfully created new secret version for %s", arn)

    except service_client.exceptions.ResourceNotFoundException:
        # If there's no current version, this is an error
        error_msg = f"Current secret not found for ARN: {arn}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = f"Error creating secret: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ValueError(f"Failed to create secret: {e}") from e


def set_secret(service_client: BaseClient, arn: str, token: str) -> None:
    """Set the new secret in the database.

    Args:
        service_client: The secrets manager service client
        arn (str): The secret ARN or identifier
        token (str): The ClientRequestToken for this version
    """
    try:
        # Get the pending secret
        pending_dict = get_secret_dict(service_client, arn, "AWSPENDING", token)

        # Get the current secret to get the admin credentials if needed
        current_dict = get_secret_dict(service_client, arn, "AWSCURRENT")

        # Connect to the database and update the password
        conn = None
        try:
            conn = psycopg2.connect(
                host=pending_dict["db_host"],
                port=int(pending_dict["db_port"]),
                dbname=current_dict["db_name"],
                user=current_dict["db_username"],
                password=current_dict["db_password"],
            )

            with conn.cursor() as cur:
                # Set the new password
                # Format the username directly into the query string after proper escaping
                # to prevent SQL injection while maintaining parameterization for the password
                username = pending_dict["db_username"].replace('"', '""')
                sql = f"""
                ALTER USER "{username}" WITH PASSWORD %s;
                """
                cur.execute(sql, (pending_dict["db_password"],))
                conn.commit()

            logger.info("Successfully set new password in database")

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error("Error setting secret in database: %s", str(e))
            raise ValueError(f"Failed to set secret in database: {e}") from e
        finally:
            if conn:
                conn.close()

    except Exception as e:
        error_msg = f"Error in set_secret: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise


def test_secret(service_client: BaseClient, arn: str, token: str) -> None:
    """Test the new secret by connecting to the database.

    Args:
        service_client: The secrets manager service client
        arn (str): The secret ARN or identifier
        token (str): The ClientRequestToken for this version
    """
    try:
        # Get the pending secret to test
        pending_dict = get_secret_dict(service_client, arn, "AWSPENDING", token)

        # Try to connect with the new credentials
        conn = None
        try:
            conn = psycopg2.connect(
                host=pending_dict["db_host"],
                port=int(pending_dict["db_port"]),
                dbname=pending_dict["db_name"],
                user=pending_dict["db_username"],
                password=pending_dict["db_password"],
            )

            # Execute a simple query to verify the connection
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                if result[0] != 1:
                    raise ValueError("Test query did not return expected result")

            logger.info("Successfully tested new secret")

        finally:
            if conn:
                conn.close()

    except Exception as e:
        error_msg = f"Error testing secret: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise


def finish_secret(service_client: BaseClient, arn: str, token: str) -> None:
    """Finish the rotation by marking the new secret as current.

    Args:
        service_client: The secrets manager service client
        arn (str): The secret ARN or identifier
        token (str): The ClientRequestToken for this version

    Raises:
        ValueError: If there's an error during the operation
    """
    try:
        pending_version = _get_pending_version(service_client, arn, token)
        if not pending_version:
            return

        _update_secret_stage(service_client, arn, token, pending_version)
        logger.info("Successfully set version %s as AWSCURRENT", token)

    except Exception as e:
        error_msg = f"Error finishing secret: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ValueError(error_msg) from e


def _get_pending_version(service_client: BaseClient, arn: str, token: str) -> str | None:
    """Get the pending version ID for the secret.

    Args:
        service_client: The secrets manager service client
        arn: The secret ARN
        token: The current token

    Returns:
        The pending version ID or None if not found
    """
    current_version = service_client.describe_secret(SecretId=arn)
    current_version_id = current_version.get("VersionIdsToStages", {})

    for version_id, stages in current_version_id.items():
        if "AWSPENDING" in stages and version_id != token:
            return version_id

    logger.warning("No pending version found for secret %s", arn)
    return None


def _update_secret_stage(service_client: BaseClient, arn: str, token: str, pending_version: str) -> None:
    """Update the secret version stage.

    Args:
        service_client: The secrets manager service client
        arn: The secret ARN
        token: The new version token
        pending_version: The pending version ID to remove
    """
    service_client.update_secret_version_stage(
        SecretId=arn,
        VersionStage="AWSCURRENT",
        MoveToVersionId=token,
        RemoveFromVersionId=pending_version,
    )


def _get_field_validators() -> dict[str, dict[str, Any]]:
    """Return the field validation configuration.

    Returns:
        Dict containing field validation rules for secret fields.
    """
    return {
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


def _validate_secret_structure(secret: Any) -> dict[str, Any]:
    """Validate the basic structure of the secret.

    Args:
        secret: The parsed secret value

    Returns:
        The validated secret as a dictionary

    Raises:
        ValueError: If the secret is not a dictionary or is missing required fields
    """
    if not isinstance(secret, dict):
        raise ValueError("Secret value must be a JSON object")
    return secret


def _process_secret_field(field: str, value: Any, validator: dict[str, Any]) -> Any:
    """Process and validate a single secret field.

    Args:
        field: The field name
        value: The field value to validate
        validator: Validation rules for the field

    Returns:
        The processed and validated field value

    Raises:
        ValueError: If validation fails
    """
    # Check type
    if not isinstance(value, validator["type"]):
        expected_type = validator["type"].__name__ if hasattr(validator["type"], "__name__") else str(validator["type"])
        raise ValueError(f"Field '{field}' must be of type {expected_type}")

    # Convert value if needed
    if "converter" in validator:
        try:
            value = validator["converter"](value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid value for field '{field}': {e}") from e

    # Validate value
    if not validator["validator"](value):
        raise ValueError(f"Invalid value for field '{field}': {validator['error']}")

    return value


def _get_secret_value(service_client: Any, request_params: dict[str, Any]) -> dict[str, Any]:
    """Retrieve and parse the secret value from AWS Secrets Manager.

    Args:
        service_client: The AWS Secrets Manager client
        request_params: Parameters for the get_secret_value API call

    Returns:
        The parsed secret as a dictionary

    Raises:
        ValueError: If the secret is invalid or cannot be retrieved
        json.JSONDecodeError: If the secret is not valid JSON
    """
    try:
        response = service_client.get_secret_value(**request_params)
        if "SecretString" not in response:
            raise ValueError("Secret value is not a string")
        return json.loads(response["SecretString"])
    except service_client.exceptions.ResourceNotFoundException as e:
        logger.error("Secret not found: %s", request_params["SecretId"])
        raise ValueError(f"Secret not found: {request_params['SecretId']}") from e
    except service_client.exceptions.InvalidRequestException as e:
        logger.error("Invalid request for secret %s: %s", request_params["SecretId"], str(e))
        raise ValueError(f"Invalid request for secret {request_params['SecretId']}: {e}") from e
    except service_client.exceptions.InvalidParameterException as e:
        logger.error("Invalid parameter for secret %s: %s", request_params["SecretId"], str(e))
        raise ValueError(f"Invalid parameter for secret {request_params['SecretId']}: {e}") from e


def _validate_secret_parameters(arn: str, stage: str, token: str | None) -> None:
    """Validate the input parameters for secret retrieval.

    Args:
        arn: The Amazon Resource Name (ARN) or friendly name of the secret
        stage: The secret stage ('AWSCURRENT' or 'AWSPENDING')
        token: The version ID or staging label (optional)

    Raises:
        ValueError: If any parameter is invalid
    """
    if not arn:
        raise ValueError("Secret ARN cannot be empty")

    if stage not in ("AWSCURRENT", "AWSPENDING"):
        raise ValueError("Stage must be either 'AWSCURRENT' or 'AWSPENDING'")

    if token is not None and not isinstance(token, str):
        raise ValueError("Token must be a string or None")


def _prepare_secret_request_params(arn: str, stage: str, token: str | None) -> dict[str, Any]:
    """Prepare the request parameters for retrieving a secret.

    Args:
        arn: The secret ARN or name
        stage: The secret stage
        token: Optional version token

    Returns:
        Dictionary of request parameters
    """
    request_params: dict[str, Any] = {"SecretId": arn}
    if token:
        request_params["VersionId"] = token
    else:
        request_params["VersionStage"] = stage
    return request_params


def _process_secret_fields(secret: dict[str, Any]) -> dict[str, Any]:
    """Process and validate all fields in the secret.

    Args:
        secret: The raw secret dictionary

    Returns:
        Processed secret dictionary with validated fields

    Raises:
        ValueError: If required fields are missing or invalid
    """
    field_validators = _get_field_validators()
    result: dict[str, Any] = {}

    for field, validator in field_validators.items():
        if field not in secret and validator["required"]:
            raise ValueError(f"Missing required field: {field}")

        if field in secret:
            result[field] = _process_secret_field(field, secret[field], validator)

    return result


def get_secret_dict(service_client: Any, arn: str, stage: str, token: str | None = None) -> dict[str, Any]:
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
        json.JSONDecodeError: If the secret value is not valid JSON
    """
    _validate_secret_parameters(arn, stage, token)
    request_params = _prepare_secret_request_params(arn, stage, token)
    logger.info("Retrieving secret %s (stage: %s)", arn, stage)

    try:
        secret = _get_secret_value(service_client, request_params)
        secret = _validate_secret_structure(secret)
        return _process_secret_fields(secret)

    except json.JSONDecodeError as e:
        logger.error("Secret %s does not contain valid JSON: %s", arn, str(e))
        raise ValueError(f"Secret {arn} does not contain valid JSON") from e
    except Exception as e:
        logger.exception("Unexpected error retrieving secret %s", arn)
        raise ValueError(f"Error retrieving secret {arn}: {str(e)}") from e
