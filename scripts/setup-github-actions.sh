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
    --query "Stacks[0].Outputs[?OutputKey=='GitHubActionsRoleArn'].OutputValue" \
    --output text)

  echo -e "\n${GREEN}GitHub Actions IAM Role ARN:${NC}"
  echo "$ROLE_ARN"
  echo -e "\n${YELLOW}Add this ARN to your GitHub repository secrets as 'AWS_ROLE_ARN'${NC}"
  echo -e "GitHub Repository: https://github.com/${GITHUB_ORG}/${REPO_NAME}/settings/secrets/actions"
else
  echo -e "${RED}❌ Failed to deploy GitHub Actions IAM role${NC}"
  exit 1
fi

# Create a GitHub Actions workflow example if .github/workflows directory exists
if [ -d ".github/workflows" ]; then
  echo -e "\n${YELLOW}Creating example GitHub Actions workflow...${NC}"
  mkdir -p .github/workflows
  cat >.github/workflows/aws-deploy.yml <<-EOM
name: AWS Deploy

on:
  push:
    branches: [ main ]
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: ${ROLE_ARN}
          aws-region: ${REGION}

      - name: Deploy with Terraform
        run: |
          cd terraform/environments/dev
          terraform init
          terraform validate
          terraform plan
          # Uncomment to apply changes
          # terraform apply -auto-approve
EOM

  echo -e "${GREEN}✅ Created example workflow: .github/workflows/aws-deploy.yml${NC}"
  echo -e "\n${YELLOW}Next steps:"
  echo "1. Commit and push the new workflow file"
  echo "2. Add the AWS_ROLE_ARN secret to your GitHub repository"
  echo "3. Your workflow will run on pushes to the main branch"
  echo -e "${NC}"
fi
