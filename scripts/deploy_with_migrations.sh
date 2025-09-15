#!/bin/bash

# Deploy Lambda with Automatic Database Migrations
# This script orchestrates the deployment process to ensure migrations run properly

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENVIRONMENT="${ENVIRONMENT:-dev}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-true}"
SKIP_BUILD="${SKIP_BUILD:-false}"
VERBOSE="${VERBOSE:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Help function
show_help() {
  cat <<EOF
Deploy Lambda with Automatic Database Migrations

Usage: $0 [OPTIONS]

Options:
    -e, --environment ENV    Environment to deploy to (dev, staging, prod) [default: dev]
    -m, --migrations         Enable automatic migrations [default: true]
    -n, --no-migrations      Disable automatic migrations
    -s, --skip-build         Skip Docker build step
    -v, --verbose            Enable verbose output
    -h, --help               Show this help message

Environment Variables:
    ENVIRONMENT              Target environment
    RUN_MIGRATIONS           Enable/disable migrations (true/false)
    SKIP_BUILD               Skip Docker build (true/false)
    VERBOSE                  Enable verbose output (true/false)

Examples:
    $0                                    # Deploy to dev with migrations
    $0 -e prod -m                         # Deploy to prod with migrations
    $0 -e staging -n                      # Deploy to staging without migrations
    $0 -e dev --skip-build                # Deploy to dev without rebuilding

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
  -e | --environment)
    ENVIRONMENT="$2"
    shift 2
    ;;
  -m | --migrations)
    RUN_MIGRATIONS="true"
    shift
    ;;
  -n | --no-migrations)
    RUN_MIGRATIONS="false"
    shift
    ;;
  -s | --skip-build)
    SKIP_BUILD="true"
    shift
    ;;
  -v | --verbose)
    VERBOSE="true"
    shift
    ;;
  -h | --help)
    show_help
    exit 0
    ;;
  *)
    log_error "Unknown option: $1"
    show_help
    exit 1
    ;;
  esac
done

# Set verbose mode
if [[ "$VERBOSE" == "true" ]]; then
  set -x
fi

log_info "Starting deployment to $ENVIRONMENT environment"
log_info "Migrations enabled: $RUN_MIGRATIONS"
log_info "Skip build: $SKIP_BUILD"

# Change to project root
cd "$PROJECT_ROOT"

# Validate environment
case "$ENVIRONMENT" in
dev | staging | prod)
  log_info "Valid environment: $ENVIRONMENT"
  ;;
*)
  log_error "Invalid environment: $ENVIRONMENT. Must be dev, staging, or prod"
  exit 1
  ;;
esac

# Check prerequisites
check_prerequisites() {
  log_info "Checking prerequisites..."

  # Check if Docker is running
  if ! docker info >/dev/null 2>&1; then
    log_error "Docker is not running. Please start Docker and try again."
    exit 1
  fi

  # Check if Terraform is available
  if ! command -v terraform >/dev/null 2>&1; then
    log_error "Terraform is not installed or not in PATH"
    exit 1
  fi

  # Check if AWS CLI is configured
  if ! aws sts get-caller-identity >/dev/null 2>&1; then
    log_error "AWS CLI is not configured or credentials are invalid"
    exit 1
  fi

  log_success "Prerequisites check passed"
}

# Build Docker image
build_docker_image() {
  if [[ "$SKIP_BUILD" == "true" ]]; then
    log_info "Skipping Docker build as requested"
    return 0
  fi

  log_info "Building Docker image for Lambda..."

  # Build the production image
  docker build \
    --target production \
    --platform linux/amd64 \
    --tag "meal-expense-tracker:$ENVIRONMENT" \
    --tag "meal-expense-tracker:latest" \
    .

  log_success "Docker image built successfully"
}

# Package Lambda deployment
package_lambda() {
  log_info "Packaging Lambda deployment..."

  # Create dist directory
  mkdir -p "dist/x86_64"

  # Create deployment package
  docker run --rm \
    -v "$(pwd)/dist/x86_64:/output" \
    "meal-expense-tracker:$ENVIRONMENT" \
    sh -c "cp -r /var/task/* /output/ && chmod -R 755 /output"

  # Create ZIP file
  cd "dist/x86_64"
  zip -r "../app-x86_64.zip" . -x "*.pyc" "__pycache__/*" "*.git*" "*.DS_Store"
  cd "$PROJECT_ROOT"

  log_success "Lambda package created: dist/app-x86_64.zip"
}

# Deploy with Terraform
deploy_terraform() {
  log_info "Deploying infrastructure with Terraform..."

  cd terraform

  # Initialize Terraform if needed
  if [[ ! -d ".terraform" ]]; then
    log_info "Initializing Terraform..."
    terraform init
  fi

  # Plan deployment
  log_info "Planning Terraform deployment..."
  terraform plan \
    -var="environment=$ENVIRONMENT" \
    -var="run_migrations=$RUN_MIGRATIONS" \
    -out="terraform.tfplan"

  # Apply deployment
  log_info "Applying Terraform deployment..."
  terraform apply "terraform.tfplan"

  cd "$PROJECT_ROOT"

  log_success "Infrastructure deployed successfully"
}

# Wait for Lambda to be ready
wait_for_lambda() {
  log_info "Waiting for Lambda to be ready..."

  # Get Lambda function name
  FUNCTION_NAME=$(aws lambda list-functions \
    --query "Functions[?contains(FunctionName, 'meal-expense-tracker-$ENVIRONMENT')].FunctionName" \
    --output text)

  if [[ -z "$FUNCTION_NAME" ]]; then
    log_error "Could not find Lambda function for environment: $ENVIRONMENT"
    exit 1
  fi

  log_info "Found Lambda function: $FUNCTION_NAME"

  # Wait for function to be active
  aws lambda wait function-active --function-name "$FUNCTION_NAME"

  log_success "Lambda function is active"
}

# Test Lambda function
test_lambda() {
  log_info "Testing Lambda function..."

  # Get API Gateway URL
  API_URL=$(aws apigatewayv2 get-apis \
    --query "Items[?contains(Name, 'meal-expense-tracker-$ENVIRONMENT')].ApiEndpoint" \
    --output text)

  if [[ -z "$API_URL" ]]; then
    log_warning "Could not find API Gateway URL, skipping API test"
    return 0
  fi

  log_info "Testing API endpoint: $API_URL/health"

  # Test health endpoint
  if curl -f -s "$API_URL/health" >/dev/null; then
    log_success "Health check passed"
  else
    log_warning "Health check failed, but deployment may still be successful"
  fi
}

# Check migration status
check_migration_status() {
  if [[ "$RUN_MIGRATIONS" == "false" ]]; then
    log_info "Migrations disabled, skipping status check"
    return 0
  fi

  log_info "Checking migration status..."

  # Get API Gateway URL
  API_URL=$(aws apigatewayv2 get-apis \
    --query "Items[?contains(Name, 'meal-expense-tracker-$ENVIRONMENT')].ApiEndpoint" \
    --output text)

  if [[ -z "$API_URL" ]]; then
    log_warning "Could not find API Gateway URL, skipping migration status check"
    return 0
  fi

  # Check health endpoint for migration status
  HEALTH_RESPONSE=$(curl -s "$API_URL/health" || echo "{}")

  if echo "$HEALTH_RESPONSE" | jq -e '.initialization.migration_successful' >/dev/null 2>&1; then
    log_success "Migrations completed successfully"
  elif echo "$HEALTH_RESPONSE" | jq -e '.initialization.migration_attempted' >/dev/null 2>&1; then
    log_warning "Migrations were attempted but may have failed"
    log_info "Check Lambda logs for migration details"
  else
    log_warning "Could not determine migration status"
  fi
}

# Cleanup function
cleanup() {
  log_info "Cleaning up temporary files..."
  rm -f terraform/terraform.tfplan
}

# Main deployment function
main() {
  log_info "Starting deployment process..."

  # Set up cleanup trap
  trap cleanup EXIT

  # Run deployment steps
  check_prerequisites
  build_docker_image
  package_lambda
  deploy_terraform
  wait_for_lambda
  test_lambda
  check_migration_status

  log_success "Deployment completed successfully!"
  log_info "Environment: $ENVIRONMENT"
  log_info "Migrations: $RUN_MIGRATIONS"

  # Show useful information
  if [[ "$RUN_MIGRATIONS" == "true" ]]; then
    log_info "Database migrations were automatically applied during deployment"
  fi

  log_info "You can monitor the deployment in the AWS Console:"
  log_info "  - Lambda: https://console.aws.amazon.com/lambda/home?region=$(aws configure get region)#/functions"
  log_info "  - CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/home?region=$(aws configure get region)#logsV2:log-groups"
}

# Run main function
main "$@"
