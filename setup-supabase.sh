#!/bin/bash
# Quick setup script for Supabase migration
# This will save you $95/month!

set -e

echo "🚀 Setting up Supabase for your meal expense tracker"
echo ""
echo "This will save you \$95/month by removing Aurora + RDS Proxy + VPC costs!"
echo ""

# Prompt for Supabase connection details
read -p "Enter your Supabase connection string (postgres:// format): " SUPABASE_URL

if [ -z "$SUPABASE_URL" ]; then
  echo "❌ Connection string is required"
  exit 1
fi

echo ""
echo "📝 Storing Supabase connection in AWS Secrets Manager..."

# Add pg8000 driver to connection string if not present
if [[ "$SUPABASE_URL" != *"pg8000"* ]]; then
  SUPABASE_URL=$(echo "$SUPABASE_URL" | sed 's|postgres://|postgresql+pg8000://|' | sed 's|postgresql://|postgresql+pg8000://|')
fi

# Store in Secrets Manager
aws secretsmanager create-secret \
  --name meal-expense-tracker/dev/supabase-connection \
  --description "Supabase PostgreSQL connection string for meal-expense-tracker dev" \
  --secret-string "$SUPABASE_URL" \
  --kms-key-id alias/meal-expense-tracker-dev-main \
  --region us-east-1 2>/dev/null || \
aws secretsmanager update-secret \
  --secret-id meal-expense-tracker/dev/supabase-connection \
  --secret-string "$SUPABASE_URL" \
  --region us-east-1

echo "✅ Connection string stored in AWS Secrets Manager"
echo ""
echo "📝 Running database migrations against Supabase..."
export DATABASE_URL="$SUPABASE_URL"
cd /home/mtd37/workspace/meal-expense-tracker
flask db upgrade

echo ""
echo "✅ Setup complete! Next steps:"
echo ""
echo "1. Update Terraform to remove VPC from Lambda"
echo "2. Deploy Lambda without VPC"
echo ""
echo "You'll save \$95/month starting now! 🎉"
