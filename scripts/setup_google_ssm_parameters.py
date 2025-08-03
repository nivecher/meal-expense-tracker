#!/usr/bin/env python3
"""
Script to set up Google API keys in AWS SSM Parameter Store.

This script creates or updates SSM parameters for Google Maps API key and Map ID.
The parameter names follow the patterns:
  - Maps API key: /{app_name}/{environment}/google/maps/api-key
  - Map ID: /{app_name}/{environment}/google/maps/map-id
"""

import argparse
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
dotenv_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=dotenv_path)


def get_parameter_value(parameter_name, region, profile=None, with_decryption=True):
    """
    Get the current value of an SSM parameter.

    Args:
        parameter_name(str): Name of the parameter
        region(str): AWS region
        profile(str, optional): AWS profile name. Defaults to None.
        with_decryption(bool): Whether to decrypt the parameter value. Defaults to True.

    Returns:
        str: The parameter value, or None if not found
    """
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    client = session.client("ssm", region_name=region)

    try:
        response = client.get_parameter(Name=parameter_name, WithDecryption=with_decryption)
        return response["Parameter"]["Value"]
    except client.exceptions.ParameterNotFound:
        return None
    except ClientError as e:
        print(f"Error getting parameter {parameter_name}: {str(e)}", file=sys.stderr)
        return None


def create_or_update_parameter(parameter_name, parameter_value, description, region, profile=None, secure=True):
    """
    Create or update an SSM parameter if the value has changed.

    Args:
        parameter_name(str): Name of the parameter
        parameter_value(str): New value for the parameter
        description(str): Description of the parameter
        region(str): AWS region
        profile(str, optional): AWS profile name. Defaults to None.
        secure(bool): Whether to use SecureString. Defaults to True.

    Returns:
        dict: The response from put_parameter call, or None if no update was needed
    """
    # Check if the parameter already exists and has the same value
    current_value = get_parameter_value(parameter_name, region, profile, with_decryption=True)
    if current_value == parameter_value:
        return None

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
    parser = argparse.ArgumentParser(description="Set up Google API keys and Map ID in AWS SSM Parameter Store")

    # Environment and region arguments
    parser.add_argument(
        "-e",
        "--environment",
        required=True,
        choices=["dev", "staging", "prod"],
        help="Environment (dev, staging, prod)",
    )
    parser.add_argument("-r", "--region", required=True, help="AWS region where parameters will be stored")

    # Service selection arguments
    service_group = parser.add_mutually_exclusive_group(required=True)
    service_group.add_argument(
        "--maps", action="store_true", help="Set up Google Maps API key (from GOOGLE_MAPS_API_KEY)"
    )
    service_group.add_argument(
        "--map-id", action="store_true", help="Set up Google Maps Map ID (from GOOGLE_MAPS_MAP_ID)"
    )
    service_group.add_argument("--all", action="store_true", help="Set up both Maps API key and Map ID")

    # Optional arguments
    parser.add_argument("-p", "--profile", help="AWS profile to use")

    args = parser.parse_args()
    return args


def process_service(service, args):
    """Process a single service (maps or map-id)."""
    # Get the appropriate parameter details based on service type
    if service == "maps":
        parameter_name = f"/meal-expense-tracker/{args.environment}/google/maps/api-key"
        description = "Google Maps API Key"
        env_var = "GOOGLE_MAPS_API_KEY"
    elif service == "map-id":
        parameter_name = f"/meal-expense-tracker/{args.environment}/google/maps/map-id"
        description = "Google Maps Map ID"
        env_var = "GOOGLE_MAPS_MAP_ID"
    else:
        raise ValueError(f"Unsupported service: {service}")

    # Get the value from environment variable
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
    current_version = get_parameter_value(parameter_name, args.region, args.profile, with_decryption=False)

    return {
        "name": parameter_name,
        "arn": parameter_arn,
        "version": result["Version"] if result else current_version,
        "updated": result is not None,
    }


def print_updated_services(services: list[str], results: dict) -> None:
    """Print details of updated services.

    Args:
        services: List of service names that were updated
        results: Dictionary containing service results
    """
    print("\nSuccessfully updated the following parameters:")
    for service in services:
        result = results[service]
        print(f"- {service.upper()}:")
        print(f"  Parameter Name: {result['name']}")
        print(f"  ARN: {result['arn']}")
        print(f"  Version: {result['version']}\n")


def print_unchanged_services(services: list[str], results: dict, region: str, profile: str = None) -> None:
    """Print details of unchanged services.

    Args:
        services: List of service names that were unchanged
        results: Dictionary containing service results
        region: AWS region
        profile: Optional AWS profile name
    """
    print("\nThe following parameters were already up to date:")
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    client = session.client("ssm", region_name=region)

    for service in services:
        result = results[service]
        try:
            param_details = client.get_parameter(Name=result["name"], WithDecryption=False)
            version = param_details["Parameter"]["Version"]
            print(f"- {service.upper()}: {result['name']} (v{version})")
        except ClientError:
            print(f"- {service.upper()}: {result['name']} (version unknown)")


def get_services_to_process(args) -> list[str]:
    """Determine which services to process based on command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        list: List of service names to process
    """
    services = []
    if args.all or args.maps:
        services.append("maps")
    if args.all or args.map_id:
        services.append("map-id")
    return services


def main() -> None:
    """Main entry point for the script."""
    args = get_args()
    services = get_services_to_process(args)

    # Process each service and collect results
    results = {service: process_service(service, args) for service in services}

    # Categorize results
    updated = [s for s, r in results.items() if r["updated"]]
    unchanged = [s for s, r in results.items() if not r["updated"]]

    # Print appropriate output based on what was processed
    if updated:
        print_updated_services(updated, results)
    if unchanged:
        print_unchanged_services(unchanged, results, args.region, args.profile)
    if not (updated or unchanged):
        print("\nNo parameters were processed.")


if __name__ == "__main__":
    main()
