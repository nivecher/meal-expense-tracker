#!/usr/bin/env python3
"""
Script to set up Google API keys in AWS SSM Parameter Store.

This script creates or updates SSM parameters for Google Maps and Places API keys.
The parameter names follow the pattern:
  /{app_name}/{environment}/google/{service}-api-key
"""

import argparse
import os
import sys

import boto3
from botocore.exceptions import ClientError


def create_or_update_parameter(parameter_name, parameter_value, description, region, profile=None, secure=True):
    """
    Create or update an SSM parameter.

    Args:
        parameter_name(str): Name of the parameter
        parameter_value(str): Value of the parameter
        description(str): Description of the parameter
        region(str): AWS region
        profile(str, optional): AWS profile name. Defaults to None.
        secure(bool): Whether to use SecureString. Defaults to True.

    Returns:
        dict: The response from put_parameter call
    """
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    client = session.client("ssm", region_name=region)

    parameter_type = "SecureString" if secure else "String"

    try:
        response = client.put_parameter(
            Name=parameter_name,
            Value=parameter_value,
            Description=description,
            Type=parameter_type,
            Overwrite=True,
            Tier="Standard",
            DataType="text",
        )
        return response
    except ClientError as e:
        print(f"Error creating/updating parameter {parameter_name}: {str(e)}", file=sys.stderr)
        sys.exit(1)


def get_parameter_arn(parameter_name, region, profile=None):
    """Get the ARN of an SSM parameter."""
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    client = session.client("ssm", region_name=region)

    try:
        response = client.get_parameter(Name=parameter_name, WithDecryption=False)
        return response["Parameter"]["ARN"]
    except ClientError as e:
        print(f"Error getting parameter ARN for {parameter_name}: {str(e)}", file=sys.stderr)
        sys.exit(1)


def get_args():
    """Parse and validate command-line arguments."""
    parser = argparse.ArgumentParser(description="Set up Google API keys in AWS SSM Parameter Store")
    # ... (rest of the argument parsing logic)
    args = parser.parse_args()
    # ... (rest of the validation logic)
    return args


def process_service(service, args):
    """Process a single service(maps or places)."""
    # Get the appropriate parameter name and description based on service type
    if service == "maps":
        parameter_name = f"/meal-expense-tracker/{args.environment}/google/maps/api-key"
        description = "Google Maps API Key"
    else:  # places
        parameter_name = f"/meal-expense-tracker/{args.environment}/google/places/api-key"
        description = "Google Places API Key"

    # Get the API key from environment variable
    env_var = f"GOOGLE_{service.upper()}_API_KEY"
    parameter_value = os.environ.get(env_var)
    if not parameter_value:
        raise ValueError(f"Environment variable {env_var} is not set")

    result = create_or_update_parameter(
        parameter_name=parameter_name,
        parameter_value=parameter_value,
        description=description,
        region=args.region,
        profile=args.profile,
        secure=True,
    )
    parameter_arn = get_parameter_arn(parameter_name, args.region, args.profile)
    return {"name": parameter_name, "arn": parameter_arn, "version": result.get("Version", 0)}


def main():
    """Main entry point."""
    args = get_args()
    services = []
    if args.both or args.maps:
        services.append("maps")
    if args.both or args.places:
        services.append("places")

    results = {}
    for service in services:
        results[service] = process_service(service, args)

    # ... (printing results)


if __name__ == "__main__":
    main()
