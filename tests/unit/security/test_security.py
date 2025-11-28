"""Tests for security-related functionality.

This module contains tests for the security module, including password generation
and secret validation.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.security import generate_password, get_secret_dict


def test_generate_password() -> None:
    """Test secure password generation with various lengths and validations."""
    # Test default length (16)
    password = generate_password()
    assert len(password) >= 16

    # Test custom length
    password = generate_password(length=20)
    assert len(password) >= 20

    # Test minimum length enforcement
    password = generate_password(length=8)
    assert len(password) >= 12  # Should enforce minimum length of 12

    # Test character requirements
    assert any(c.islower() for c in password)
    assert any(c.isupper() for c in password)
    assert any(c.isdigit() for c in password)
    assert any(c in "~!@#$%^&*_+-=[]{}|;:,.<>?" for c in password)

    # Test no problematic characters
    assert "'" not in password
    assert '"' not in password
    assert "`" not in password
    assert "\\" not in password
    assert "/" not in password

    # Test uniqueness
    password2 = generate_password()
    assert password != password2


def test_generate_password_failure() -> None:
    """Test password generation failure cases."""
    # Test with invalid max_attempts
    with pytest.raises(RuntimeError):
        generate_password(max_attempts=0)


@patch("boto3.client")
def test_get_secret_dict_valid(mock_boto) -> None:
    """Test get_secret_dict with valid secret data."""
    # Setup mock
    mock_client = MagicMock()
    mock_boto.return_value = mock_client

    # Mock secret data
    secret_data = {
        "db_host": "localhost",
        "db_port": "5432",
        "db_name": "testdb",
        "db_user": "testuser",
        "db_password": "TestPassword123!@#",
    }

    # Configure mock to return our test data
    mock_client.get_secret_value.return_value = {"SecretString": json.dumps(secret_data)}

    # Call the function
    result = get_secret_dict(mock_client, "test-arn", "AWSCURRENT")

    # Verify the result
    assert result["db_host"] == "localhost"
    assert result["db_port"] == 5432  # Should be converted to int
    assert result["db_name"] == "testdb"
    assert result["db_user"] == "testuser"
    assert result["db_password"] == "TestPassword123!@#"

    # Verify the boto client was called correctly
    mock_client.get_secret_value.assert_called_once_with(SecretId="test-arn", VersionStage="AWSCURRENT")


@patch("boto3.client")
def test_get_secret_dict_missing_fields(mock_boto) -> None:
    """Test get_secret_dict with missing required fields."""
    # Setup mock
    mock_client = MagicMock()
    mock_boto.return_value = mock_client

    # Mock secret data with missing fields
    secret_data = {
        "db_host": "localhost",
        "db_port": "5432",
        # Missing db_name, db_user, db_password
    }

    # Configure mock to return our test data
    mock_client.get_secret_value.return_value = {"SecretString": json.dumps(secret_data)}

    # Call the function and expect an exception
    with pytest.raises(ValueError) as excinfo:
        get_secret_dict(mock_client, "test-arn", "AWSCURRENT")

    # Check that the error message mentions the missing fields
    assert "Missing required field" in str(excinfo.value)


@patch("boto3.client")
def test_get_secret_dict_invalid_port(mock_boto) -> None:
    """Test get_secret_dict with invalid port number."""
    # Setup mock
    mock_client = MagicMock()
    mock_boto.return_value = mock_client

    # Mock secret data with invalid port
    secret_data = {
        "db_host": "localhost",
        "db_port": "99999",  # Invalid port number
        "db_name": "testdb",
        "db_user": "testuser",
        "db_password": "TestPassword123!@#",
    }

    # Configure mock to return our test data
    mock_client.get_secret_value.return_value = {"SecretString": json.dumps(secret_data)}

    # Call the function and expect an exception
    with pytest.raises(ValueError) as excinfo:
        get_secret_dict(mock_client, "test-arn", "AWSCURRENT")

    # Check that the error message mentions the invalid port
    assert "Port must be between 1 and 65535" in str(excinfo.value)
