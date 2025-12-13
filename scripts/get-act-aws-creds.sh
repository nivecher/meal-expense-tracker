#!/bin/bash

# This script assumes your AWS CLI is configured with SSO and a default profile.
# It uses 'aws sts assume-role' to get temporary credentials for a specified role
# and then exports them as environment variables.

# --- Configuration ---
# Get AWS account ID if not set (introspect from logged-in account)
if [ -z "${AWS_ACCOUNT_ID}" ]; then
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    if [ -z "${AWS_ACCOUNT_ID}" ]; then
        echo "❌ ERROR: Could not determine AWS account ID. Please ensure AWS CLI is configured."
        exit 1
    fi
fi

# Replace with the ARN of the GitHub Actions IAM Role from your cloudformation/github-actions-role.yml
# The account ID is automatically detected from your logged-in AWS account
AWS_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/github-actions-role"
AWS_REGION="us-east-1" # Or your desired AWS region
ROLE_SESSION_NAME="act-session" # A name for the assumed role session

# --- Check for AWS CLI ---
if ! command -v aws &> /dev/null
then
    echo "AWS CLI could not be found. Please install it."
    exit 1
fi

echo "AWS Account ID: ${AWS_ACCOUNT_ID}"
echo "Attempting to assume role: $AWS_ROLE_ARN in region $AWS_REGION..."

# --- Assume the role ---
CREDENTIALS=$(aws sts assume-role \
    --role-arn "$AWS_ROLE_ARN" \
    --role-session-name "$ROLE_SESSION_NAME" \
    --duration-seconds 3600 \
    --region "$AWS_REGION" \
    --output json)

if [ $? -ne 0 ]; then
    echo "Failed to assume role. Please check your AWS CLI configuration, SSO login, and the AWS_ROLE_ARN."
    exit 1
fi

# --- Extract and export credentials ---
export AWS_ACCESS_KEY_ID=$(echo "$CREDENTIALS" | jq -r '.Credentials.AccessKeyId')
export AWS_SECRET_ACCESS_KEY=$(echo "$CREDENTIALS" | jq -r '.Credentials.SecretAccessKey')
export AWS_SESSION_TOKEN=$(echo "$CREDENTIALS" | jq -r '.Credentials.SessionToken')
export AWS_DEFAULT_REGION="$AWS_REGION"
export AWS_REGION="$AWS_REGION"

echo "Temporary AWS credentials exported as environment variables."
echo "These credentials are valid for 1 hour."
echo "You can now run 'act' or other AWS CLI commands."

# Optional: Display expiration time
EXPIRATION=$(echo "$CREDENTIALS" | jq -r '.Credentials.Expiration')
echo "Credentials expire at: $EXPIRATION"

# You can then run your act command like this:
# act -j terraform -W .github/workflows/ci.yml \
#     -e AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID}" \
#     -e AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY}" \
#     -e AWS_SESSION_TOKEN="${AWS_SESSION_TOKEN}" \
#     -s AWS_ROLE_ARN="${AWS_ROLE_ARN}"
