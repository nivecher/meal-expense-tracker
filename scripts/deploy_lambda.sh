#!/bin/bash
set -e

# Default values
DEFAULT_FUNCTION="meal-expense-tracker"
FUNCTION_NAME=""
ENVIRONMENT="dev"
ARCHITECTURE="arm64" # Default to ARM64

# Control whether to build new packages or use existing ones
SKIP_PACKAGE="false"

# Logging functions
log() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Checksum calculation for idempotent deployments
calculate_checksums() {
  log "Calculating source code checksums..."

  # Calculate checksum of source code (excluding dist/, venv/, .git/, etc.)
  local source_checksum
  source_checksum=$(find . \
    -type f \
    -name "*.py" \
    -o -name "*.js" \
    -o -name "*.html" \
    -o -name "*.css" \
    -o -name "*.json" \
    -o -name "*.txt" \
    -o -name "*.yml" \
    -o -name "*.yaml" \
    -o -name "*.toml" \
    -o -name "*.sh" \
    -o -name "*.md" \
    | grep -v -E "(dist/|venv/|\.git/|__pycache__/|\.pytest_cache/|node_modules/|\.coverage)" \
    | sort \
    | xargs cat \
    | sha256sum \
    | cut -d' ' -f1)

  # Calculate checksum of requirements.txt
  local requirements_checksum
  if [ -f "requirements.txt" ]; then
    requirements_checksum=$(cat requirements.txt | sha256sum | cut -d' ' -f1)
  else
    requirements_checksum="none"
  fi

  # Combine checksums
  local combined_checksum
  combined_checksum=$(echo "${source_checksum}:${requirements_checksum}:${ARCHITECTURE}" | sha256sum | cut -d' ' -f1)

  echo "${combined_checksum}"
}

# Get stored checksum for comparison
get_stored_checksum() {
  local checksum_file=".deployment_checksums/${ENVIRONMENT}-${ARCHITECTURE}.txt"
  if [ -f "${checksum_file}" ]; then
    cat "${checksum_file}"
  else
    echo "none"
  fi
}

# Store checksum for future comparison
store_checksum() {
  local checksum="$1"
  local checksum_file=".deployment_checksums/${ENVIRONMENT}-${ARCHITECTURE}.txt"
  mkdir -p "$(dirname "${checksum_file}")"
  echo "${checksum}" > "${checksum_file}"
  log "Stored checksum: ${checksum}"
}

# Check if deployment is needed
is_deployment_needed() {
  local current_checksum
  current_checksum=$(calculate_checksums)
  local stored_checksum
  stored_checksum=$(get_stored_checksum)

  log "Current checksum:  ${current_checksum}"
  log "Stored checksum:   ${stored_checksum}"

  if [ "${current_checksum}" = "${stored_checksum}" ]; then
    return 1  # No deployment needed
  else
    return 0  # Deployment needed
  fi
}

# Function to display usage
usage() {
  echo "Deploy Lambda function"
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  -f, --function NAME  Lambda function name (default: $DEFAULT_FUNCTION)"
  echo "  -e, --env ENV       Environment: dev|staging|prod (default: dev)"
  echo "  -a, --arch ARCH     Architecture: arm64|x86_64 (default: arm64)"
  echo "      --no-package    Skip packaging; use existing artifacts in dist/"
  echo "      --no-packge     Alias for --no-package"
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
  --no-package)
    SKIP_PACKAGE="true"
    shift
    ;;
  --no-packge)
    SKIP_PACKAGE="true"
    shift
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
  # Package app and layer separately (layer uses Docker for cross-arch when needed)
  ./scripts/package.sh --app --"$ARCHITECTURE"
  ./scripts/package.sh --layer --"$ARCHITECTURE"
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
  if ! aws s3 cp "dist/${ARCHITECTURE}/app/app-${ARCHITECTURE}.zip" "s3://${S3_BUCKET}/${app_key}"; then
    log "Failed to upload application package to S3"
    return 1
  fi

  # Upload layer package (optional)
  if [ -L "dist/${ARCHITECTURE}/layers/python-dependencies-${ARCHITECTURE}-latest.zip" ] || \
     [ -f "dist/${ARCHITECTURE}/layers/python-dependencies-${ARCHITECTURE}-latest.zip" ]; then
    # Resolve symlink to actual file when present
    local layer_src
    layer_src=$(readlink -f "dist/${ARCHITECTURE}/layers/python-dependencies-${ARCHITECTURE}-latest.zip" 2>/dev/null || echo "dist/${ARCHITECTURE}/layers/python-dependencies-${ARCHITECTURE}-latest.zip")
    log "Uploading layer package to s3://${S3_BUCKET}/${layer_key} from ${layer_src}"
    if ! aws s3 cp "${layer_src}" "s3://${S3_BUCKET}/${layer_key}"; then
      log "Failed to upload layer package to S3"
      return 1
    fi
  else
    log "No layer package found, skipping layer upload"
  fi

  # Copy to latest versions (this is what Terraform expects)
  aws s3 cp "s3://${S3_BUCKET}/${app_key}" "s3://${S3_BUCKET}/${latest_app_key}" --copy-props none
  if [ -f "dist/${ARCHITECTURE}/layers/python-dependencies-${ARCHITECTURE}-latest.zip" ]; then
    aws s3 cp "s3://${S3_BUCKET}/${layer_key}" "s3://${S3_BUCKET}/${latest_layer_key}" --copy-props none
  fi

  # Set the S3 key for Lambda update to the fixed key that Terraform uses
  S3_KEY="$latest_app_key"
}

# Update Lambda
update_lambda() {
  log "Updating Lambda function: $FUNCTION_NAME with architecture: $ARCHITECTURE"

  # First update the function code
  if ! aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --s3-bucket "$S3_BUCKET" \
    --s3-key "$S3_KEY"; then

    log "Failed to update Lambda function code"
    return 1
  fi
}

# Run database migrations
run_migrations() {
  log "Running database migrations..."
  if [ -f "scripts/invoke_migrations.py" ]; then
    # Determine region/profile with sensible defaults
    local REGION
    REGION=${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}
    local PROFILE
    PROFILE=${AWS_PROFILE:-AdministratorAccess-562427544284}

    if ! python3 scripts/invoke_migrations.py -f "$FUNCTION_NAME" -r "$REGION" -p "$PROFILE"; then
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
  if [ "$SKIP_PACKAGE" = "true" ]; then
    log "📦 Skipping packaging (using existing artifacts in dist/)..."
  else
    log "📦 Packaging application..."
    package || return 1
  fi

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
