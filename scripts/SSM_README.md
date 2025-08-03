# Google API Keys Management with AWS SSM Parameter Store

This document explains how to manage Google API keys using AWS SSM Parameter Store for the Meal Expense Tracker application.

## Overview

Google API keys are stored securely in AWS SSM Parameter Store with the following naming convention:
- `/meal-expense-tracker/{environment}/google/maps-api-key`

## Prerequisites

- AWS CLI configured with appropriate credentials
- Python 3.6 or higher
- `boto3` Python package (`pip install boto3`)

## Setup Script

A Python script `setup_google_ssm_parameters.py` is provided to manage Google API keys in SSM Parameter Store.

### Installation

```bash
# Make the script executable
chmod +x scripts/setup_google_ssm_parameters.py

# Install required dependencies
pip install boto3
```

### Usage

```bash
# Set both Maps and Places API keys with the same key
./scripts/setup_google_ssm_parameters.py --api-key "your-api-key" --both

# Set different keys for Maps and Places
./scripts/setup_google_ssm_parameters.py --maps-api-key "maps-key"

# Set only Maps API key
./scripts/setup_google_ssm_parameters.py --maps-api-key "maps-key" --maps

# Set only Places API key
./scripts/setup_google_ssm_parameters.py --api-key "your-api-key" --places

# Specify environment and region
./scripts/setup_google_ssm_parameters.py --api-key "your-api-key" --both --environment prod --region us-west-2
```

### Options

- `--api-key`: API key to use for both Maps and Places
- `--maps-api-key`: API key for Google Maps only
- `--both`: Set both Maps and Places API keys
- `--maps`: Set only Maps API key
- `--places`: Set only Places API key
- `--profile`: AWS profile to use
- `--region`: AWS region (default: us-east-1)
- `--app-name`: Application name (default: meal-expense-tracker)
- `--environment`: Deployment environment: dev, staging, or prod (default: dev)
- `--no-secure`: Store parameters as plaintext (not recommended for production)

## Terraform Integration

The Terraform configuration is already set up to read these parameters. The Lambda function has the necessary IAM permissions to access them.

## Security Notes

- By default, parameters are stored as `SecureString` (encrypted at rest)
- The Lambda execution role has been granted the minimum required permissions to access these parameters
- For production environments, always use `SecureString` (default) and ensure proper KMS key policies are in place
- Never commit actual API keys to version control

## Troubleshooting

### Insufficient Permissions

If you encounter permission errors, ensure your AWS credentials have the following permissions:
- `ssm:PutParameter`
- `ssm:GetParameter`
- `ssm:GetParameters`
- `ssm:GetParametersByPath`
- `kms:Decrypt` (if using SecureString)

### Parameter Not Found

If the Lambda function cannot find the parameter, verify:
1. The parameter name matches exactly what's in the Lambda environment variables
2. The parameter exists in the same region as your Lambda function
3. The Lambda execution role has the correct permissions

### Parameter Version Mismatch

If you update a parameter, the Lambda function will get the latest version by default. If you need to pin to a specific version, you can specify the version in the parameter name (e.g., `/path/to/parameter:1`).
