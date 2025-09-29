#!/bin/bash
# Local CI workflow equivalent
# This script mirrors the GitHub Actions CI workflow locally

set -euo pipefail

echo "🚀 Running Local CI Workflow..."

# Environment setup
export PYTHON_VERSION=3.13
export NODE_VERSION=22
export PYTHONPATH=$(pwd)
export FLASK_ENV=test
export TESTING=true

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to run steps
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

# Checkout simulation (we're already in the repo)
echo "📁 Simulating checkout..."

# Setup Python
run_step "Setup Python $PYTHON_VERSION" "python3 --version"

# Setup Node.js
run_step "Setup Node.js $NODE_VERSION" "node --version"

# Create virtual environment
run_step "Create virtual environment" "python -m venv venv"

# Install dependencies
run_step "Install Python dependencies" "source venv/bin/activate && pip install -r requirements-dev.txt"

# Install Node dependencies
if [ -f package.json ]; then
    run_step "Install Node dependencies" "npm ci"
fi

# Run linting (mirrors ci.yml lint job)
echo -e "\n${BLUE}🔍 Lint & Format Check${NC}"
run_step "Python linting" "source venv/bin/activate && make lint-python"
if [ -f package.json ]; then
    run_step "JavaScript linting" "npm run lint:js"
fi
run_step "CSS linting" "source venv/bin/activate && make lint-css"
run_step "HTML template linting" "source venv/bin/activate && make lint-html"

# Run tests (mirrors ci.yml test job)
echo -e "\n${BLUE}🧪 Test Suite${NC}"
run_step "Unit tests" "source venv/bin/activate && make test-unit"
run_step "Integration tests" "source venv/bin/activate && make test-integration"

# Terraform validation (mirrors ci.yml terraform job)
echo -e "\n${BLUE}🏗️  Terraform Validation${NC}"
run_step "Terraform format check" "terraform -chdir=terraform fmt -check -recursive"
run_step "Terraform validation" "terraform -chdir=terraform init -backend=false && terraform -chdir=terraform validate"

# Security scanning (mirrors ci.yml security job)
echo -e "\n${BLUE}🔒 Security Scan${NC}"
run_step "Bandit security scan" "bandit -r app/ -f json -o bandit-report.json || true; bandit -r app/"
run_step "Safety check" "safety check --json --output safety-report.json || true; safety check"

echo -e "\n${GREEN}🎉 Local CI completed successfully!${NC}"
echo -e "${BLUE}All CI jobs passed: lint, test, terraform, security${NC}"
