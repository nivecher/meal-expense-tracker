"""
AWS Secrets Manager PostgreSQL Rotation Lambda

This Lambda function handles automatic rotation of PostgreSQL database credentials
stored in AWS Secrets Manager. It implements the four-step rotation process:
1. createSecret: Creates a new version of the secret
2. setSecret: Sets the new password in the database
3. testSecret: Tests the new secret
4. finishSecret: Finalizes the rotation
"""

import boto3
import json
import logging
import string
import random
import psycopg2
import botocore

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# PostgreSQL allowed special characters (excluding those that might cause issues in
# connection strings)
PG_SPECIAL_CHARS = "~!@#$%^&*_-+=|(){}[]:;\"',<>?/."

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds


def lambda_handler(event, context):
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


def generate_password():
    """Generate a random password with special characters allowed by PostgreSQL.

    Returns:
        str: A randomly generated password that meets PostgreSQL complexity requirements
    """
    # Define character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "~!@#$%^&*_+-=[]{}|;:,.<>?"

    # Ensure we have at least one of each character type
    password = [
        random.choice(lowercase),
        random.choice(uppercase),
        random.choice(digits),
        random.choice(special),
    ]

    # Fill the rest of the password with random choices from all sets
    all_chars = lowercase + uppercase + digits + special
    password.extend(random.choice(all_chars) for _ in range(12))

    # Shuffle the password characters
    random.shuffle(password)
    password_str = "".join(password)

    # Ensure password doesn't contain quotes which could break SQL
    if "'" in password_str or '"' in password_str:
        return generate_password()  # Try again if quotes are present

    return password_str


def create_secret(service_client, arn, token):
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
        raise


def set_secret(service_client, arn, token):
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
            raise
        finally:
            if conn:
                conn.close()

    except Exception as e:
        error_msg = f"Error in set_secret: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise


def test_secret(service_client, arn, token):
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


def finish_secret(service_client, arn, token):
    """Finish the rotation by marking the new secret as current.

    Args:
        service_client: The secrets manager service client
        arn (str): The secret ARN or identifier
        token (str): The ClientRequestToken for this version
    """
    try:
        # First describe the secret to get the current version
        metadata = service_client.describe_secret(SecretId=arn)
        current_version = None

        # Find the current version
        for version in metadata.get("VersionIdsToStages", {}):
            if "AWSCURRENT" in metadata["VersionIdsToStages"][version]:
                current_version = version
                break

        if current_version == token:
            logger.info("Version %s already marked as AWSCURRENT", token)
            return

        # Update the secret version stages
        service_client.update_secret_version_stage(
            SecretId=arn,
            VersionStage="AWSCURRENT",
            MoveToVersionId=token,
            RemoveFromVersionId=current_version,
        )

        logger.info("Successfully set version %s as AWSCURRENT", token)

    except Exception as e:
        error_msg = f"Error finishing secret: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise


def get_secret_dict(service_client, arn, stage, token=None):
    """Get the secret value as a dictionary.

    Args:
        service_client: The secrets manager service client
        arn (str): The secret ARN or identifier
        stage (str): The secret stage (AWSCURRENT or AWSPENDING)
        token (str, optional): The version token

    Returns:
        dict: The secret value as a dictionary

    Raises:
        ValueError: If the secret is invalid or missing required fields
    """
    required_fields = ["db_host", "db_port", "db_username", "db_password", "db_name"]

    try:
        # Get the secret value
        if token:
            secret = service_client.get_secret_value(SecretId=arn, VersionId=token, VersionStage=stage)
        else:
            secret = service_client.get_secret_value(SecretId=arn, VersionStage=stage)

        # Parse the secret string
        if "SecretString" in secret:
            secret_dict = json.loads(secret["SecretString"])
        else:
            secret_dict = json.loads(secret["SecretBinary"].decode("utf-8"))

        # Verify all required fields are present and non-empty
        missing_fields = [field for field in required_fields if field not in secret_dict or not secret_dict[field]]

        if missing_fields:
            raise ValueError(f"Secret is missing required fields: {', '.join(missing_fields)}")

        return secret_dict

    except json.JSONDecodeError as e:
        error_msg = "Secret value is not valid JSON"
        logger.error("%s: %s", error_msg, str(e))
        raise ValueError(f"{error_msg}: {str(e)}")
    except service_client.exceptions.ResourceNotFoundException as e:
        error_msg = f"Secret not found: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    except Exception as e:
        error_msg = f"Error retrieving secret: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ValueError(error_msg)
