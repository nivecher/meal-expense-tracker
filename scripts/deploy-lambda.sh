#!/bin/bash
#
# Deploy the application and/or Lambda layer to AWS S3
# and update the Lambda layer and function with the new version
#
set -e

# Configuration
APP_NAME="meal-expense-tracker"
ENVIRONMENT="${ENVIRONMENT:-dev}"
AWS_REGION="${AWS_REGION:-us-east-1}"
S3_BUCKET="${S3_BUCKET:-${APP_NAME}-deployment-$(aws sts get-caller-identity --query Account --output text)}"
DEPLOY_TIMESTAMP=$(date +%Y%m%d%H%M%S)

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print status messages
status() {
  echo -e "${GREEN}[*] $1${NC}"
}

warn() {
  echo -e "${YELLOW}[!] $1${NC}"
}

error() {
  echo -e "${RED}[!] $1${NC}" >&2
  exit 1
}

# Check if AWS CLI is installed and configured
check_aws_cli() {
  if ! command -v aws &>/dev/null; then
    error "AWS CLI is not installed. Please install it first."
  fi

  # Verify AWS credentials are configured
  if ! aws sts get-caller-identity &>/dev/null; then
    error "AWS credentials not configured. Please run 'aws configure' first."
  fi
}

# Ensure the package.sh script exists and is executable
ensure_package_script() {
  if [ ! -f "${SCRIPT_DIR}/package.sh" ]; then
    error "package.sh script not found in ${SCRIPT_DIR}"
  fi

  if [ ! -x "${SCRIPT_DIR}/package.sh" ]; then
    chmod +x "${SCRIPT_DIR}/package.sh"
  fi
}

# Create S3 bucket if it doesn't exist
ensure_s3_bucket() {
  if ! aws s3api head-bucket --bucket "${S3_BUCKET}" 2>/dev/null; then
    status "Creating S3 bucket: ${S3_BUCKET}"

    if [ "${AWS_REGION}" = "us-east-1" ]; then
      aws s3api create-bucket \
        --bucket "${S3_BUCKET}" \
        --region "${AWS_REGION}"
    else
      aws s3api create-bucket \
        --bucket "${S3_BUCKET}" \
        --region "${AWS_REGION}" \
        --create-bucket-configuration LocationConstraint="${AWS_REGION}"
    fi

    # Enable versioning
    aws s3api put-bucket-versioning \
      --bucket "${S3_BUCKET}" \
      --versioning-configuration Status=Enabled

    # Add default encryption
    aws s3api put-bucket-encryption \
      --bucket "${S3_BUCKET}" \
      --server-side-encryption-configuration '{
        "Rules": [
          {
            "ApplyServerSideEncryptionByDefault": {
              "SSEAlgorithm": "AES256"
            }
          }
        ]
      }'
  fi
}

# Upload file to S3 with metadata
upload_to_s3() {
  local file_path="$1"
  local s3_key="$2"

  if [ ! -f "${file_path}" ]; then
    error "File not found: ${file_path}"
  fi

  status "Uploading ${file_path} to s3://${S3_BUCKET}/${s3_key}"

  # Upload with metadata
  aws s3 cp \
    "${file_path}" \
    "s3://${S3_BUCKET}/${s3_key}" \
    --metadata "{\"DeploymentTimestamp\":\"${DEPLOY_TIMESTAMP}\"}" \
    --acl bucket-owner-full-control
}

# Package and deploy the application
deploy_application() {
  local package_type="$1"

  # Run the package script
  "${SCRIPT_DIR}/package.sh" "${package_type}"

  # Upload the packaged files
  if [ "${package_type}" = "--app" ] || [ "${package_type}" = "--both" ]; then
    upload_to_s3 "${OUTPUT_DIR}/app.zip" "${ENVIRONMENT}/app/app-${DEPLOY_TIMESTAMP}.zip"
    # Create a versioned copy
    upload_to_s3 "${OUTPUT_DIR}/app.zip" "${ENVIRONMENT}/app/latest/app.zip"
  fi

  if [ "${package_type}" = "--layer" ] || [ "${package_type}" = "--both" ]; then
    upload_to_s3 "${OUTPUT_DIR}/layers/python-dependencies.zip" "${ENVIRONMENT}/layers/python-dependencies-${DEPLOY_TIMESTAMP}.zip"
    # Create a versioned copy
    upload_to_s3 "${OUTPUT_DIR}/layers/python-dependencies.zip" "${ENVIRONMENT}/layers/latest/python-dependencies.zip"
  fi
}

# Main execution
main() {
  # Get the directory where this script is located
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  OUTPUT_DIR="${SCRIPT_DIR}/../dist"

  # Default to deploying both app and layer
  local package_type="--both"
  local update_lambda=false

  # Parse command line arguments
  while [[ $# -gt 0 ]]; do
    case $1 in
    --app)
      package_type="--app"
      shift
      ;;
    --layer)
      package_type="--layer"
      shift
      ;;
    --both)
      package_type="--both"
      shift
      ;;
    -u | --update)
      update_lambda=true
      shift
      ;;
    -e | --environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    -b | --bucket)
      S3_BUCKET="$2"
      shift 2
      ;;
    -r | --region)
      AWS_REGION="$2"
      shift 2
      ;;
    -h | --help)
      show_help
      exit 0
      ;;
    *)
      error "Unknown option: $1"
      ;;
    esac
  done

  # Ensure output directory exists
  mkdir -p "${OUTPUT_DIR}"

  check_aws_cli
  ensure_package_script
  ensure_s3_bucket

  # Deploy the application
  deploy_application "${package_type}"

  # Update Lambda layer and function if update flag is set
  if [ "${update_lambda}" = true ]; then
    status "Updating Lambda layer and function..."

    # Update Lambda layer
    if [ "${package_type}" = "--layer" ] || [ "${package_type}" = "--both" ]; then
      local layer_arn
      layer_arn=$(aws lambda list-layers --query "Layers[?LayerName=='${APP_NAME}-${ENVIRONMENT}-deps'].LatestMatchingVersion.LayerVersionArn" --output text --region "${AWS_REGION}")
      if [ -n "${layer_arn}" ]; then
        status "Publishing new layer version..."
        local new_layer_version
        if new_layer_version=$(aws lambda publish-layer-version \
          --layer-name "${APP_NAME}-${ENVIRONMENT}-deps" \
          --content "S3Bucket=${S3_BUCKET},S3Key=${ENVIRONMENT}/layers/latest/python-dependencies.zip" \
          --compatible-runtimes "python3.13" \
          --license-info "MIT" \
          --query 'Version' \
          --output text \
          --region "${AWS_REGION}"); then
          status "New layer version published: ${new_layer_version}"
          layer_arn=$(aws lambda list-layer-versions \
            --layer-name "${APP_NAME}-${ENVIRONMENT}-deps" \
            --query "LayerVersions[0].LayerVersionArn" \
            --output text \
            --region "${AWS_REGION}")
        else
          warn "Failed to publish new layer version"
        fi
      fi
    fi

    # Update Lambda function
    if [ "${package_type}" = "--app" ] || [ "${package_type}" = "--both" ]; then
      local function_name="${APP_NAME}-${ENVIRONMENT}"
      if aws lambda get-function --function-name "${function_name}" --region "${AWS_REGION}" &>/dev/null; then
        status "Updating Lambda function code..."
        aws lambda update-function-code \
          --function-name "${function_name}" \
          --s3-bucket "${S3_BUCKET}" \
          --s3-key "${ENVIRONMENT}/app/latest/app.zip" \
          --region "${AWS_REGION}"

        # Update environment variables if needed
        if [ -n "${layer_arn}" ]; then
          status "Updating Lambda function configuration with new layer..."
          aws lambda update-function-configuration \
            --function-name "${function_name}" \
            --layers "${layer_arn}" \
            --region "${AWS_REGION}"
        fi
      else
        warn "Lambda function ${function_name} not found. Skipping update."
      fi
    fi
  fi

  # Output deployment information
  status "Deployment completed successfully!"
  echo -e "\n${GREEN}Deployment Summary:${NC}"
  echo -e "  Environment: ${ENVIRONMENT}"
  echo -e "  S3 Bucket: ${S3_BUCKET}"
  echo -e "  AWS Region: ${AWS_REGION}"
  echo -e "  Timestamp: ${DEPLOY_TIMESTAMP}"

  if [ "${package_type}" = "--app" ] || [ "${package_type}" = "--both" ]; then
    echo -e "\n${GREEN}Application Package:${NC}"
    echo -e "  s3://${S3_BUCKET}/${ENVIRONMENT}/app/app-${DEPLOY_TIMESTAMP}.zip"
    echo -e "  s3://${S3_BUCKET}/${ENVIRONMENT}/app/latest/app.zip"
  fi

  if [ "${package_type}" = "--layer" ] || [ "${package_type}" = "--both" ]; then
    echo -e "\n${GREEN}Lambda Layer:${NC}"
    echo -e "  s3://${S3_BUCKET}/${ENVIRONMENT}/layers/python-dependencies-${DEPLOY_TIMESTAMP}.zip"
    echo -e "  s3://${S3_BUCKET}/${ENVIRONMENT}/layers/latest/python-dependencies.zip"
  fi
}

# Show help information
show_help() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  --app           Deploy only the application"
  echo "  --layer         Deploy only the Lambda layer"
  echo "  --both          Deploy both application and layer (default)"
  echo "  --skip-db-check Skip database verification before deployment"
  echo "  -u, --update      Update Lambda layer and function after deployment"
  echo "  -e, --environment Deployment environment (default: dev)"
  echo "  -b, --bucket     S3 bucket for deployment artifacts"
  echo "  -r, --region     AWS region (default: us-east-1)"
  echo "  -h, --help       Show this help message"
  echo ""
  echo "Examples:"
  echo "  $0 --app -e staging       # Deploy only the app to staging"
  echo "  $0 --layer -e prod       # Deploy only the layer to production"
  echo "  $0 --both -e dev -b my-bucket  # Deploy both with custom bucket"
}

# Run the script
main "$@"
