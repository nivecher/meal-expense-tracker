#!/bin/bash
set -e

if [ $# -ne 1 ]; then
  echo "Usage: $0 <environment>"
  echo "Available environments: dev, staging, prod"
  exit 1
fi

ENV=$1
ENV_DIR="terraform/environments/$ENV"

if [ ! -d "$ENV_DIR" ]; then
  echo "Error: Environment '$ENV' not found in $ENV_DIR"
  exit 1
fi

echo "Switching to $ENV environment..."
cd "$ENV_DIR"

# Initialize Terraform if not already initialized
if [ ! -d ".terraform" ]; then
  echo "Initializing Terraform..."
  terraform init -backend-config=backend.hcl
fi

echo "Environment '$ENV' is ready. You can now run terraform commands."
echo "Example: terraform plan -var-file=terraform.tfvars"
