#!/bin/bash
# Local pipeline workflow equivalent
# This script mirrors the GitHub Actions pipeline workflow locally

set -euo pipefail

echo "🚀 Running Local Pipeline Workflow..."

# Parse arguments
ENVIRONMENT=${1:-dev}
SKIP_TESTS=${2:-false}

# Environment setup
export APP_NAME=meal-expense-tracker
export PYTHON_VERSION=3.13
export NODE_VERSION=22
export PYTHONPATH=$(pwd)
export FLASK_APP=wsgi:app
export FLASK_ENV=test
export TESTING=true
export ENV=$ENVIRONMENT
export TF_ENV=$ENVIRONMENT
export AWS_REGION=us-east-1

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

run_step() {
    local step_name="$1"
    local command="$2"

    echo -e "\n${YELLOW}=== $step_name ===${NC}"
    if eval "$command"; then
        echo -e "${GREEN}✅ $step_name completed${NC}"
    else
        echo -e "${RED}❌ $step_name failed${NC}"
        exit 1
    fi
}

# Quality Gate (mirrors deploy.yml quality-gate job)
if [ "$SKIP_TESTS" = "false" ]; then
    echo -e "\n${BLUE}🔍 Quality Gate${NC}"
    run_step "Unit tests" "make test-unit"
    run_step "Integration tests" "make test-integration"
    run_step "Linting" "make lint"
    run_step "Security checks" "make security-check"
else
    echo -e "\n${YELLOW}⚠️  Skipping tests as requested${NC}"
fi

# Security Scan (mirrors deploy.yml security-scan job)
if [ "$SKIP_TESTS" = "false" ]; then
    echo -e "\n${BLUE}🔒 Enhanced Security Scan${NC}"
    run_step "Bandit security scan" "bandit -r app/"
    run_step "Safety check" "safety scan"
else
    echo -e "\n${YELLOW}⚠️  Skipping security scan as requested${NC}"
fi

# Version Tagging (simulate deploy.yml version-tag job)
if [ "$SKIP_TESTS" = "false" ]; then
    echo -e "\n${BLUE}🏷️  Version & Tag${NC}"
    VERSION=$(python -c "import setuptools_scm; print(setuptools_scm.get_version())" 2>/dev/null || echo "0.1.0")
    echo "Generated version: $VERSION"
else
    VERSION="dev"
    echo -e "\n${YELLOW}⚠️  Using dev version (tests skipped)${NC}"
fi

# Build (mirrors pipeline.yml build job)
echo -e "\n${BLUE}🔨 Build and Push${NC}"
run_step "Docker build" "make docker-build"

# Terraform (mirrors deploy.yml terraform job)
echo -e "\n${BLUE}🏗️  Terraform${NC}"
run_step "Terraform init" "make tf-init"
run_step "Terraform plan" "make tf-plan"

# Note: In real workflow, terraform apply would be conditional
echo -e "\n${YELLOW}⚠️  Terraform apply skipped in local testing${NC}"
echo -e "${YELLOW}   Use 'make tf-apply' manually if needed${NC}"

# Deploy (simulate deploy.yml deploy job)
echo -e "\n${BLUE}🚀 Deploy to $ENVIRONMENT${NC}"
echo "Simulating deployment to $ENVIRONMENT environment..."
echo "In real workflow, this would:"
echo "  - Configure AWS credentials"
echo "  - Deploy infrastructure"
echo "  - Deploy application"
echo "  - Run health checks"

echo -e "\n${GREEN}🎉 Local Deploy Workflow completed successfully!${NC}"
echo -e "${BLUE}Environment: $ENVIRONMENT${NC}"
echo -e "${BLUE}Version: $VERSION${NC}"
echo -e "${BLUE}Skip Tests: $SKIP_TESTS${NC}"
