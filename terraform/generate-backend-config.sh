#!/bin/bash
set -e

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

cat > backend.hcl << EOF
bucket         = "meal-expense-tracker-terraform-state"
key            = "terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "terraform-state-lock"
encrypt        = true
EOF

echo "Backend configuration file created with bucket: meal-expense-tracker-tfstate-${AWS_ACCOUNT_ID}"
