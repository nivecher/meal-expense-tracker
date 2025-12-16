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

# Get the AWS account ID
if ! AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null); then
  echo -e "${RED}Failed to get AWS account ID. Are you logged in?${NC}"
  exit 1
fi

echo -e "${GREEN}Setting up GitHub Actions IAM role in AWS account: ${AWS_ACCOUNT_ID} (${REGION})${NC}"

# Deploy CloudFormation stack
echo -e "${YELLOW}Deploying CloudFormation stack '${STACK_NAME}'...${NC}"
if aws cloudformation deploy \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --template-file cloudformation/github-actions-role.yml \
  --parameter-overrides "GitHubOrg=${GITHUB_ORG}" "RepositoryName=${REPO_NAME}" \
  --capabilities CAPABILITY_NAMED_IAM; then
  echo -e "${GREEN}✅ GitHub Actions IAM role deployed successfully!${NC}"

  # Get the role ARN
  ROLE_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query "Stacks[0].Outputs[?OutputKey=='RoleARN'].OutputValue" \
    --output text 2>/dev/null)

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
