#!/bin/bash
set -e

# Default values
DEFAULT_FUNCTION="meal-expense-tracker"
FUNCTION_NAME=""
ENVIRONMENT="dev"
ARCHITECTURE="arm64" # Default to ARM64

# Logging functions
log() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to display usage
usage() {
  echo "Deploy Lambda function"
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  -f, --function NAME  Lambda function name (default: $DEFAULT_FUNCTION)"
  echo "  -e, --env ENV       Environment: dev|staging|prod (default: dev)"
  echo "  -a, --arch ARCH     Architecture: arm64|x86_64 (default: arm64)"
  echo "  -h, --help          Show this help message"
  exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
  -f | --function)
    FUNCTION_NAME="$2"
    shift 2
    ;;
  -e | --env)
    ENVIRONMENT="$2"
    shift 2
    ;;
  -a | --arch)
    ARCHITECTURE="$2"
    shift 2
    ;;
  --arm64)
    ARCHITECTURE="arm64"
    shift
    ;;
  --x86_64)
    ARCHITECTURE="x86_64"
    shift
    ;;
  -h | --help)
    usage
    ;;
  *)
    log "Error: Unknown option: $1"
    usage
    ;;
  esac
done

# Set default function name if not provided
if [ -z "$FUNCTION_NAME" ]; then
  FUNCTION_NAME="${DEFAULT_FUNCTION}-${ENVIRONMENT}"
  log "Using default function name: $FUNCTION_NAME"
fi

# Set deployment timestamp
TIMESTAMP=$(date +%Y%m%d%H%M%S)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
S3_BUCKET="meal-expense-tracker-${ENVIRONMENT}-deployment-${ACCOUNT_ID}"

# Package Lambda
package() {
  log "Packaging Lambda function for $ARCHITECTURE..."
  ./scripts/package.sh --"$ARCHITECTURE"
}

# Upload to S3
upload() {
  log "Uploading to S3 bucket: $S3_BUCKET"

  local app_key="${ENVIRONMENT}/app/${ARCHITECTURE}/app-${TIMESTAMP}.zip"
  local layer_key="${ENVIRONMENT}/layers/${ARCHITECTURE}/python-dependencies-${TIMESTAMP}.zip"
  local latest_app_key="${ENVIRONMENT}/app/${ARCHITECTURE}/app-${ARCHITECTURE}.zip"
  local latest_layer_key="${ENVIRONMENT}/layers/${ARCHITECTURE}/python-dependencies-${ARCHITECTURE}.zip"

  # Upload application package
  log "Uploading application package to s3://${S3_BUCKET}/${app_key}"
  if ! aws s3 cp "dist/${ARCHITECTURE}/app-${ARCHITECTURE}.zip" "s3://${S3_BUCKET}/${app_key}"; then
    log "Failed to upload application package to S3"
    return 1
  fi

  # Upload layer package
  log "Uploading layer package to s3://${S3_BUCKET}/${layer_key}"
  if ! aws s3 cp "dist/${ARCHITECTURE}/layers/python-dependencies-${ARCHITECTURE}-latest.zip" "s3://${S3_BUCKET}/${layer_key}"; then
    log "Failed to upload layer package to S3"
    return 1
  fi

  # Copy to latest versions
  aws s3 cp "s3://${S3_BUCKET}/${app_key}" "s3://${S3_BUCKET}/${latest_app_key}" --copy-props none
  aws s3 cp "s3://${S3_BUCKET}/${layer_key}" "s3://${S3_BUCKET}/${latest_layer_key}" --copy-props none

  # Set the S3 key for Lambda update
  S3_KEY="$app_key"
}

# Update Lambda
update_lambda() {
  log "Updating Lambda function: $FUNCTION_NAME with architecture: $ARCHITECTURE"

  # First update the function code
  if ! aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --s3-bucket "$S3_BUCKET" \
    --s3-key "${ENVIRONMENT}/app/${ARCHITECTURE}/app-${ARCHITECTURE}.zip"; then

    log "Failed to update Lambda function code"
    return 1
  fi

  # Then update the function configuration with the correct architecture
  if ! aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --architectures "$ARCHITECTURE"; then

    log "Warning: Failed to update Lambda function architecture. Continuing..."
  fi
}

# Run database migrations
run_migrations() {
  log "Running database migrations..."
  if [ -f "scripts/invoke_migrations.py" ]; then
    if ! python3 scripts/invoke_migrations.py "$FUNCTION_NAME"; then
      log "Warning: Database migrations completed with errors"
      return 1
    fi
  else
    log "No migrations script found, skipping"
  fi
  return 0
}

# Main function
main() {
  log "🚀 Starting deployment for: $FUNCTION_NAME"
  log "🌍 Environment: $ENVIRONMENT"
  log "📦 S3 Bucket: $S3_BUCKET"

  # Package Lambda
  log "📦 Packaging application..."
  package || return 1

  # Upload to S3
  log "☁️  Uploading to S3..."
  upload || return 1

  # Update Lambda
  log "⚡ Updating Lambda function..."
  update_lambda || return 1

  # Run migrations
  log "🔄 Running database migrations..."
  run_migrations

  log "✅ Deployment completed successfully!"
  log "🔗 Lambda Function: $FUNCTION_NAME"
  log "📌 S3 Package: s3://$S3_BUCKET/$S3_KEY"
}

# Run the script
log "🔍 AWS CLI Version: $(aws --version 2>&1 | cut -d' ' -f1)"
log "📅 Deployment started at: $(date)"

if ! main; then
  log "❌ Deployment failed"
  exit 1
fi

exit 0
