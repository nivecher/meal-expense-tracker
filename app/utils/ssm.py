"""Utility functions for interacting with AWS SSM Parameter Store."""

import os
from functools import lru_cache
from typing import Optional

import boto3


def get_ssm_parameter(param_name: str, region: Optional[str] = None, with_decryption: bool = True) -> str:
    """
    Get a parameter from AWS SSM Parameter Store.

    Args:
        param_name: Name of the parameter to retrieve
        region: AWS region (default: None, uses default region)
        with_decryption: Whether to decrypt the parameter value

    Returns:
        The parameter value as a string

    Raises:
        ValueError: If the parameter is not found or an error occurs
    """
    try:
        session = boto3.Session()
        ssm = session.client("ssm", region_name=region)

        response = ssm.get_parameter(Name=param_name, WithDecryption=with_decryption)

        return response["Parameter"]["Value"]
    except Exception as e:
        raise ValueError(f"Failed to get parameter '{param_name}' from SSM: {str(e)}")


@lru_cache(maxsize=32)
def get_cached_ssm_parameter(param_name: str, region: Optional[str] = None) -> str:
    """
    Get a parameter from SSM with caching.

    Args:
        param_name: Name of the parameter to retrieve
        region: AWS region (default: None, uses default region)

    Returns:
        The parameter value as a string
    """
    return get_ssm_parameter(param_name, region, with_decryption=True)


def get_parameter_from_env(env_var_name: str, default: Optional[str] = None) -> str:
    """
    Get a parameter from environment variables or SSM Parameter Store.

    If the environment variable value starts with 'ssm:', it will be treated
    as an SSM parameter path and the value will be fetched from Parameter Store.

    Args:
        env_var_name: Name of the environment variable
        default: Default value if the environment variable is not set

    Returns:
        The parameter value as a string

    Raises:
        ValueError: If the environment variable is not set and no default is provided,
                   or if there's an error fetching from SSM
    """
    value = os.environ.get(env_var_name, default)
    if value is None:
        raise ValueError(f"Environment variable {env_var_name} is required")

    if value.startswith("ssm:"):
        param_name = value[4:]  # Remove 'ssm:' prefix
        return get_cached_ssm_parameter(param_name)

    return value
