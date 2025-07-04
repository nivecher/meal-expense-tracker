#!/usr/bin/env python3
"""
Script to set up Google API keys in AWS SSM Parameter Store.

This script creates or updates SSM parameters for Google Maps and Places API keys.
The parameter names follow the pattern:
  /{app_name}/{environment}/google/{service}-api-key

Usage:
    python3 setup_google_ssm_parameters.py [options]

Examples:
    # Set both Maps and Places API keys (same key)
    python3 setup_google_ssm_parameters.py --api-key "your-api-key" --both

    # Set only Maps API key
    python3 setup_google_ssm_parameters.py --api-key "your-api-key" --maps

    # Set only Places API key
    python3 setup_google_ssm_parameters.py --api-key "your-api-key" --places

    # Set different keys for Maps and Places
    python3 setup_google_ssm_parameters.py --maps-api-key "maps-key" --places-api-key "places-key" --both
"""

import argparse
import boto3
import sys
from botocore.exceptions import ClientError


def create_or_update_parameter(parameter_name, parameter_value, description, region, profile=None, secure=True):
    """
    Create or update an SSM parameter.

    Args:
        parameter_name (str): Name of the parameter
        parameter_value (str): Value of the parameter
        description (str): Description of the parameter
        region (str): AWS region
        profile (str, optional): AWS profile name. Defaults to None.
        secure (bool): Whether to use SecureString. Defaults to True.

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


def main():
    parser = argparse.ArgumentParser(description="Set up Google API keys in AWS SSM Parameter Store")

    # API key options
    key_group = parser.add_mutually_exclusive_group()
    key_group.add_argument("--api-key", help="API key to use for both Maps and Places")
    key_group.add_argument("--maps-api-key", help="API key for Google Maps only")
    key_group.add_argument("--places-api-key", help="API key for Google Places only")

    # Service selection
    service_group = parser.add_mutually_exclusive_group(required=True)
    service_group.add_argument("--both", action="store_true", help="Set both Maps and Places API keys")
    service_group.add_argument("--maps", action="store_true", help="Set only Maps API key")
    service_group.add_argument("--places", action="store_true", help="Set only Places API key")

    # Common options
    parser.add_argument("--profile", help="AWS profile to use")
    parser.add_argument("--region", default="us-east-1", help="AWS region (default: us-east-1)")
    parser.add_argument(
        "--app-name", default="meal-expense-tracker", help="Application name (default: meal-expense-tracker)"
    )
    parser.add_argument(
        "--environment", default="dev", choices=["dev", "staging", "prod"], help="Deployment environment (default: dev)"
    )
    parser.add_argument(
        "--no-secure",
        action="store_false",
        dest="secure",
        help="Store parameters as plaintext (not recommended for production)",
    )

    args = parser.parse_args()

    # Validate key arguments
    if args.both and not args.api_key and not (args.maps_api_key and args.places_api_key):
        parser.error("--both requires either --api-key or both --maps-api-key and --places-api-key")
    if args.maps and not (args.api_key or args.maps_api_key):
        parser.error("--maps requires either --api-key or --maps-api-key")
    if args.places and not (args.api_key or args.places_api_key):
        parser.error("--places requires either --api-key or --places-api-key")

    # Determine which services to update
    services = []
    if args.both or args.maps:
        services.append("maps")
    if args.both or args.places:
        services.append("places")

    # Process each service
    results = {}
    for service in services:
        # Get the appropriate key
        if args.api_key:
            key = args.api_key
        else:
            key = getattr(args, f"{service}_api_key")

        parameter_name = f"/{args.app_name}/{args.environment}/google/{service}-api-key"
        parameter_description = (
            f"Google {service.capitalize()} API key for {args.app_name} in {args.environment} environment"
        )

        # Create or update the parameter
        result = create_or_update_parameter(
            parameter_name=parameter_name,
            parameter_value=key,
            description=parameter_description,
            region=args.region,
            profile=args.profile,
            secure=args.secure,
        )

        # Get the parameter ARN
        parameter_arn = get_parameter_arn(parameter_name, args.region, args.profile)

        results[service] = {"name": parameter_name, "arn": parameter_arn, "version": result.get("Version", 0)}

    # Print results
    print("\nSuccess! The following parameters have been stored in AWS SSM Parameter Store:")
    for service, data in results.items():
        print(f"\n{service.upper()} API Key:")
        print(f"  Parameter Name: {data['name']}")
        print(f"  Parameter ARN:  {data['arn']}")

    print("\nThese parameters are now available to your Lambda function through environment variables:")
    for service in services:
        print(f"  {service.upper()}_SSM_PATH = \"{results[service]['name']}\"")

    if not args.secure:
        print("\nWARNING: Parameters were stored as plaintext. This is not recommended for production.")
        print("To store securely, remove the --no-secure flag.")


if __name__ == "__main__":
    main()
