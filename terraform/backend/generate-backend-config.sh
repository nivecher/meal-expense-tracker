#!/bin/bash
set -e

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="meal-expense-tracker-tfstate-${AWS_ACCOUNT_ID}"
TABLE_NAME="meal-expense-tracker-tflock"

cat > backend.hcl << EOF
bucket         = "${BUCKET_NAME}"
key            = "terraform.tfstate"
region         = "us-east-1"
dynamodb_table = "${TABLE_NAME}"
encrypt        = true
EOF

echo "Backend configuration file created with bucket: meal-expense-tracker-tfstate-${AWS_ACCOUNT_ID}"
