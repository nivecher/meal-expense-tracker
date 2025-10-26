#!/bin/bash
# Run database migrations against Supabase
# This can be run from any machine with network access to Supabase

set -e

echo "🎯 Running database migrations against Supabase..."
echo ""
echo "This script will:"
echo "1. Get the Supabase connection string from AWS Secrets Manager"
echo "2. Set it as DATABASE_URL"
echo "3. Run Flask migrations"
echo ""

# Get the connection string from AWS Secrets Manager
CONNECTION_STRING=$(aws secretsmanager get-secret-value \
  --secret-id meal-expense-tracker/dev/supabase-connection \
  --region us-east-1 \
  --query SecretString \
  --output text)

# Export for Flask
export DATABASE_URL="$CONNECTION_STRING"

echo "✅ Retrieved Supabase connection string"
echo "🔧 Connection: ${CONNECTION_STRING%%:*}" # Just show the protocol part for security
echo ""

# Activate venv and run migrations
if [ -d "venv" ]; then
  source venv/bin/activate
fi

echo "🚀 Running migrations..."
flask db upgrade

echo ""
echo "✅ Migrations complete!"
echo ""
echo "Next steps:"
echo "1. Build and redeploy the Lambda function"
echo "2. Test the Lambda invocation"
echo ""
