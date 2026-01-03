#!/bin/bash
set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default values
STACK_NAME="github-actions-role"
REGION="us-east-1"
GITHUB_ORG=""
REPO_NAME="meal-expense-tracker"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
  --stack-name)
    STACK_NAME="$2"
    shift 2
    ;;
  --region)
    REGION="$2"
    shift 2
    ;;
  --github-org)
    GITHUB_ORG="$2"
    shift 2
    ;;
  --repo-name)
    REPO_NAME="$2"
    shift 2
    ;;
  -h | --help)
    echo "Usage: $0 [--stack-name NAME] [--region REGION] [--github-org ORG] [--repo-name REPO]"
    echo "  --stack-name   Name of the CloudFormation stack (default: github-actions-role)"
    echo "  --region       AWS region to deploy to (default: us-east-1)"
    echo "  --github-org   GitHub organization name (required)"
    echo "  --repo-name    GitHub repository name (default: meal-expense-tracker)"
    exit 0
    ;;
  *)
    echo "Unknown argument: $1"
    exit 1
    ;;
  esac
done

# Validate required parameters
if [ -z "$GITHUB_ORG" ]; then
  echo -e "${RED}Error: GitHub organization name is required. Use --github-org flag.${NC}"
  exit 1
fi

# Get the AWS account ID and current caller identity (introspect from logged-in account)
if ! AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null); then
  echo -e "${RED}Failed to get AWS account ID. Are you logged in?${NC}"
  exit 1
fi

# Get the current caller identity ARN for SSO role assumption
CALLER_ARN=$(aws sts get-caller-identity --query Arn --output text 2>/dev/null)
if [ -z "$CALLER_ARN" ]; then
  echo -e "${YELLOW}Warning: Could not get caller ARN. SSO role assumption will not be enabled.${NC}"
  SSO_ROLE_ARN=""
else
  # Extract the SSO role name from the assumed role ARN and convert to IAM role ARN
  # Pattern: arn:aws:sts::ACCOUNT:assumed-role/ROLE_NAME/USERNAME
  # Convert to: arn:aws:iam::ACCOUNT:role/aws-reserved/sso.amazonaws.com/ROLE_NAME
  # This allows any user with the same SSO role to assume the GitHub Actions role
  if echo "$CALLER_ARN" | grep -q "assumed-role.*AWSReservedSSO"; then
    # Extract account and role name, then construct IAM role ARN
    ROLE_NAME=$(echo "$CALLER_ARN" | sed 's|.*assumed-role/\([^/]*\)/.*|\1|')
    SSO_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/aws-reserved/sso.amazonaws.com/${ROLE_NAME}"
    echo -e "${GREEN}Detected SSO role ARN: ${SSO_ROLE_ARN}${NC}"
  else
    echo -e "${YELLOW}Warning: Caller is not using an SSO assumed role. SSO role assumption will not be enabled.${NC}"
    SSO_ROLE_ARN=""
  fi
fi

echo -e "${GREEN}Setting up GitHub Actions IAM role in AWS account: ${AWS_ACCOUNT_ID} (${REGION})${NC}"

# Build parameter overrides
PARAM_OVERRIDES="GitHubOrg=${GITHUB_ORG} RepositoryName=${REPO_NAME}"
if [ -n "$SSO_ROLE_ARN" ]; then
  PARAM_OVERRIDES="${PARAM_OVERRIDES} SSORoleArn=${SSO_ROLE_ARN}"
fi

# Deploy CloudFormation stack
echo -e "${YELLOW}Deploying CloudFormation stack '${STACK_NAME}'...${NC}"
if aws cloudformation deploy \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --template-file cloudformation/github-actions-role.yml \
  --parameter-overrides $PARAM_OVERRIDES \
  --capabilities CAPABILITY_NAMED_IAM; then
  echo -e "${GREEN}✅ GitHub Actions IAM role deployed successfully!${NC}"

  # Get the role ARN
  ROLE_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='RoleARN'].OutputValue" \
    --output text)

  if [ -z "$ROLE_ARN" ]; then
    echo -e "${YELLOW}⚠️  Warning: Could not retrieve role ARN from stack outputs${NC}"
    echo -e "${YELLOW}You can retrieve it manually with:${NC}"
    echo "  aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query \"Stacks[0].Outputs[?OutputKey=='RoleARN'].OutputValue\" --output text"
  else
    echo -e "\n${GREEN}GitHub Actions IAM Role ARN:${NC}"
    echo "$ROLE_ARN"
    echo -e "\n${YELLOW}Add this ARN to your GitHub repository secrets as 'AWS_ROLE_ARN'${NC}"
    echo -e "GitHub Repository: https://github.com/${GITHUB_ORG}/${REPO_NAME}/settings/secrets/actions"
  fi
else
  echo -e "${RED}❌ Failed to deploy GitHub Actions IAM role${NC}"
  exit 1
fi
